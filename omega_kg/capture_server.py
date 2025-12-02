#!/usr/bin/env python
"""
Omega_KG Capture Server

FastAPI server that receives AI conversations from chrome extension,
saves them to Obsidian vault, and percolates to Neo4j.
"""

import hashlib
import logging
import neo4j
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Security, Request
from fastapi.middleware.cors import CORSMiddleware
from neo4j import GraphDatabase
from pydantic import BaseModel, Field
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# --- Import your settings and logic classes ---
from omega_kg.settings import settings
from omega_kg.percolation import PercolationEngine
from omega_kg.linear_sync import LinearSync
from omega_kg.auth_utils import (
    get_static_api_key,
    validate_access_token,
    create_access_token,
)
from omega_kg.routers import linear_receiver
from omega_kg.database.session import get_db
from sqlalchemy import text
import uuid
from omega_kg.parsers import parse_html_content

# Eagerly import embedding_service to log initialization at startup
# This import triggers the module-level logging for diagnostics
from omega_kg.domain.common.embedding_service import generate_embedding

# Vector storage and worker imports
from omega_kg.vector_store import get_vector_store, VectorStore
from omega_kg.workers.embedding_worker import start_worker, stop_worker
from omega_kg.config import log_config_summary

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Security limits
MAX_HTML_SIZE = 500_000  # 500KB

# --- App and Engine Initialization ---


# Lifespan for scheduler
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler to initialize vector store, start worker, and schedule batch percolation."""
    logger.info("Starting Omega_KG Capture Server...")
    
    # Initialize vector store
    try:
        vector_store = await get_vector_store()
        logger.info("✓ Vector store initialized")
    except Exception as e:
        logger.error(f"Failed to initialize vector store: {e}")
        raise
    
    # Start embedding worker
    try:
        await start_worker()
        logger.info("✓ Embedding worker started (polling every 10s)")
    except Exception as e:
        logger.error(f"Failed to start embedding worker: {e}")
        raise
    
    # Start scheduler for batch percolation
    try:
        scheduler = AsyncIOScheduler()
        scheduler.add_job(
            batch_percolate_sessions, "interval", minutes=5, id="session_percolation"
        )
        scheduler.start()
        logger.info("✓ Session percolation scheduled (every 5 minutes)")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")
        raise
    
    # Log startup summary
    logger.info(log_config_summary())
    
    yield
    
    # Shutdown sequence
    logger.info("Shutting down Omega_KG Capture Server...")
    
    # Stop embedding worker gracefully
    try:
        await stop_worker()
        logger.info("✓ Embedding worker stopped")
    except Exception as e:
        logger.error(f"Error stopping embedding worker: {e}")
    
    # Stop scheduler
    try:
        scheduler.shutdown()
        logger.info("✓ Scheduler stopped")
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")
    
    # Close vector store pool
    try:
        await VectorStore.close_pool()
        logger.info("✓ Vector store pool closed")
    except Exception as e:
        logger.error(f"Error closing vector store: {e}")


app = FastAPI(
    title="Omega_KG Capture Server",
    description="Receives AI conversations and integrates with Neo4j",
    version="1.0.0",
    lifespan=lifespan,
)

sync_engine = LinearSync()

# Register Linear Receiver Router (New Parallel Endpoint)
app.include_router(linear_receiver.router, tags=["Linear Ingest"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"chrome-extension://{settings.chrome_extension_id}",
    ],
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["X-API-Key", "Authorization", "Content-Type"],
)


# --- Pydantic Models ---
class Token(BaseModel):
    """JWT token response model."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")


class Message(BaseModel):
    role: str = Field(..., description="Message role (user/assistant)")
    content: str = Field(..., description="Message content")
    timestamp: Optional[str] = Field(None, description="Message timestamp")


class ConversationData(BaseModel):
    user_id: str = "extension_user"
    source: str = "chrome_extension"
    platform: str = "obsidian"
    content: Optional[str] = None
    url: Optional[str] = None
    title: Optional[str] = "Untitled Capture"
    tags: List[str] = []
    messages: Optional[List[Dict[str, str]]] = []
    raw_html: Optional[str] = None
    metadata: Optional[Dict] = None


class CaptureResponse(BaseModel):
    success: bool
    file_path: str
    nodes_created: int
    message: str


# --- Helper Functions ---
def generate_conversation_hash(data: ConversationData) -> str:
    """
    Generate a short hash for a conversation using platform, URL, message count, and a limited portion of message content.

    Args:
        data (ConversationData): The conversation data.

    Returns:
        str: An 8-character hash string.
    """
    # Limit to first 5 messages and first 500 characters for scalability
    limited_messages = data.messages[:5]
    # Handle both dict and Message object formats
    messages_text = "|".join(
        (msg.get("content", "") if isinstance(msg, dict) else msg.content)[:100]
        for msg in limited_messages
    )
    content = f"{data.platform}-{data.url}-{len(data.messages)}-{messages_text}"
    hash_obj = hashlib.md5(content.encode())
    return hash_obj.hexdigest()[:8]


def format_conversation_markdown(data: ConversationData) -> str:
    """
    Formats the conversation data into Markdown with Golden Schema Frontmatter.
    Schema:
      - id: CAP-{YYYYMMDD}-{HASH} (Standardized ID)
      - type: Conversation (Standardized Type)
      - status: new (Default status)
      - title: ...
      - created_at: ...
    """
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    timestamp_str = now.isoformat()

    # Generate a robust Content ID
    conv_hash = generate_conversation_hash(data)
    # ID Format: CAP (Capture) - Date - Hash
    content_id = f"CAP-{now.strftime('%Y%m%d')}-{conv_hash}"

    # --- Golden Schema Frontmatter ---
    frontmatter_lines = [
        "---",
        f"id: {content_id}",
        "type: Conversation",
        "status: new",
        f"title: {data.title or f'{data.platform} Conversation'}",
        f"created_at: {timestamp_str}",
        f"date: {date_str}",
        f"platform: {data.platform}",
        f"url: {data.url}",
        f"conversation_hash: {conv_hash}",
        f"message_count: {len(data.messages)}",
    ]

    # Add Participants (Roles) - handle both dict and Message object formats
    roles = list(
        set(
            msg.get("role", "unknown") if isinstance(msg, dict) else msg.role
            for msg in data.messages
        )
    )
    participants_str = ", ".join(sorted(roles))
    frontmatter_lines.append(f"participants: {participants_str}")

    # Add any extra metadata
    if data.metadata:
        for key, value in data.metadata.items():
            # Prevent duplicate keys if they overlap with schema
            if key not in ["id", "type", "status", "title", "created_at"]:
                frontmatter_lines.append(f"{key}: {value}")

    frontmatter_lines.append("---")

    # --- Content Body ---
    title_header = data.title or f"{data.platform} Conversation"
    content_lines = [
        f"\n# {title_header}",
        f"\n**ID**: `{content_id}`",
        f"**Date**: {date_str}",
        f"**Platform**: {data.platform}",
        f"**URL**: [{data.url}]({data.url})",
        "---\n",
    ]

    for i, msg in enumerate(data.messages, 1):
        # Handle both dict and Message object formats
        if isinstance(msg, dict):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            timestamp = msg.get("timestamp")
        else:
            role = msg.role
            content = msg.content
            timestamp = msg.timestamp

        role_emoji = "👤" if role.lower() == "user" else "🤖"
        role_title = role.title()
        content_lines.append(f"\n## {role_emoji} Message {i} ({role_title})\n")
        content_lines.append(content)
        content_lines.append("\n")
        if timestamp:
            content_lines.append(f"*Sent: {timestamp}*\n")

    return "\n".join(frontmatter_lines + content_lines)


# NOTE: The folder name 'AI_Conversations' is a hardcoded convention for storing captured AI conversations.
# This convention should be documented in the project README for discoverability and onboarding.
def write_to_obsidian(platform: str, content: str, conversation_hash: str) -> Path:
    """
    Writes the given conversation markdown content to the Obsidian vault under
    the 'AI_Conversations' folder (hardcoded convention; see project architecture).
    Creates a subfolder for the platform and names the file using the current date
    and conversation hash.
    Creates a subfolder for the platform and names the file using the current date
    and conversation hash.

    Args:
        platform (str): The AI platform name (used for subfolder).
        content (str): The markdown content to write.
        conversation_hash (str): Unique hash for the conversation.

    Returns:
        Path: The path to the written markdown file.

    Raises:
        ValueError: If the Obsidian vault path does not exist.
        IOError: If writing the file fails.
    """
    vault_path = Path(settings.obsidian_vault_path)
    if not vault_path.exists():
        logger.warning(
            f"Obsidian vault not found at: {vault_path} - creating directory for write operations."
        )
        vault_path.mkdir(parents=True, exist_ok=True)

    platform_folder = platform.replace(" ", "_")
    ai_conv_path = vault_path / "AI_Conversations" / platform_folder
    ai_conv_path.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"{date_str}-{conversation_hash}.md"
    file_path = ai_conv_path / filename

    try:
        file_path.write_text(content, encoding="utf-8")
        logger.info(f"Wrote conversation to: {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"Failed to write file: {e}")
        raise IOError(f"Failed to write markdown file: {e}")


def percolate_to_neo4j(
    file_path: Path,
    data: ConversationData,
    driver: Optional[GraphDatabase.driver] = None,
) -> int:
    """
    Percolates a captured conversation markdown file and its metadata to Neo4j.
    Creates a ChatSession node and Decision nodes for detected decisions.
    Accepts an optional Neo4j driver for batch efficiency.
    Returns the number of nodes created.
    """
    own_driver = False
    if driver is None:
        driver = GraphDatabase.driver(
            settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
        )
        own_driver = True
    try:
        with driver.session() as session:
            conv_hash = generate_conversation_hash(data)
            nodes_created = _create_chat_session(session, conv_hash, file_path, data)
            nodes_created += _create_decision_nodes(session, conv_hash, data)
        logger.info(f"Created {nodes_created} nodes in Neo4j")
        return nodes_created
    except Exception as e:
        logger.error(f"Neo4j percolation failed: {e}")
        raise
    finally:
        if own_driver:
            driver.close()


def _create_chat_session(
    session, conv_hash: str, file_path: Path, data: ConversationData
) -> int:
    """Create or update a ChatSession node in Neo4j."""
    result = session.run(
        """
        MERGE (s:ChatSession {conversation_hash: $hash})
        ON CREATE SET
            s.date = date($date), s.platform = $platform, s.filepath = $filepath,
            s.url = $url, s.message_count = $msg_count, s.created_at = datetime($created_at)
        ON MATCH SET
            s.updated_at = datetime($created_at)
        RETURN s
        """,
        hash=conv_hash,
        date=datetime.now().strftime("%Y-%m-%d"),
        platform=data.platform,
        filepath=str(file_path),
        url=data.url,
        msg_count=len(data.messages),
        created_at=datetime.now().isoformat(),
    )
    return 1 if result.single() else 0


async def percolate_to_neo4j_with_embedding(
    file_path: Path,
    data: ConversationData,
    driver: Optional[GraphDatabase.driver] = None,
) -> int:
    """
    Percolates a captured conversation to Neo4j WITH pending vector record creation.
    Creates a ChatSession node and queues embedding generation via vector_store.
    Captures complete immediately; embeddings are generated asynchronously by worker.
    """
    own_driver = False
    if driver is None:
        driver = GraphDatabase.driver(
            settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
        )
        own_driver = True
    
    try:
        conv_hash = generate_conversation_hash(data)
        
        # Create ChatSession in Neo4j (WITHOUT immediate embedding)
        with driver.session() as session:
            result = session.run(
                """
                MERGE (s:ChatSession {conversation_hash: $hash})
                ON CREATE SET
                    s.date = date($date), s.platform = $platform, s.filepath = $filepath,
                    s.url = $url, s.message_count = $msg_count, s.created_at = datetime($created_at)
                ON MATCH SET
                    s.updated_at = datetime($created_at)
                RETURN id(s) AS session_id
                """,
                hash=conv_hash,
                date=datetime.now().strftime("%Y-%m-%d"),
                platform=data.platform,
                filepath=str(file_path),
                url=data.url,
                msg_count=len(data.messages) if data.messages else 0,
                created_at=datetime.now().isoformat(),
            )
            
            record = result.single()
            if not record:
                logger.warning(f"Failed to create ChatSession node for {conv_hash}")
                return 0
            
            session_id = record["session_id"]
            nodes_created = 1
            
            # Create Decision nodes
            nodes_created += _create_decision_nodes(session, conv_hash, data)
        
        # Queue pending embedding via vector_store (async, non-blocking)
        try:
            vector_store = await get_vector_store()
            vector_id = await vector_store.store_pending(
                message_id=session_id,
                node_label="ChatSession"
            )
            logger.info(
                f"✓ Queued embedding for ChatSession {conv_hash} "
                f"(neo4j_id={session_id}, vector_id={vector_id})"
            )
        except Exception as e:
            logger.warning(f"Failed to queue embedding for {conv_hash}: {e}")
            # Non-fatal: Node created successfully, embedding will retry
        
        logger.info(f"Created {nodes_created} nodes in Neo4j + pending embedding queued")
        return nodes_created
        
    except Exception as e:
        logger.error(f"Neo4j percolation failed: {e}")
        raise
    finally:
        if own_driver:
            driver.close()


def _create_decision_nodes(
    session: "neo4j.work.session.Session", conv_hash: str, data: ConversationData
) -> int:
    """
    Extract decisions from messages and create Decision nodes in Neo4j.

    Only the first matching sentence per message containing a decision keyword is extracted.
    """
    # Use keywords from settings
    decision_keywords = settings.decision_keywords
    nodes_created = 0
    if data.messages:
        for i, msg in enumerate(data.messages):
            # Handle both dict and Message object formats
            msg_content = msg.get("content", "") if isinstance(msg, dict) else msg.content
            content_lower = msg_content.lower()
            for keyword in decision_keywords:
                if keyword in content_lower:
                    sentences = msg_content.split(".")
                    for sentence in sentences:
                        if keyword in sentence.lower():
                            decision_content = sentence.strip()
                            result = session.run(
                                """
                                MATCH (s:ChatSession {conversation_hash: $hash})
                                CREATE (d:Decision {
                                    content: $content, decision_id: $dec_id,
                                    extracted_at: datetime($created_at)
                                })
                                CREATE (s)-[:CONTAINS]->(d)
                                RETURN d
                                """,
                                hash=conv_hash,
                                content=decision_content,
                                dec_id=f"{conv_hash}-dec-{i}",
                                created_at=datetime.now().isoformat(),
                            )
                            if result.single():
                                nodes_created += 1
                            break
    return nodes_created


def batch_percolate_sessions():
    """
    Batch percolates all session logs from the Obsidian vault to Neo4j.
    Intended to run periodically via scheduler.
    """
    try:
        import time
        start_time = time.time()
        logger.info("→ Scheduler execution started: batch_percolate_sessions")
        
        sessions_path = Path(settings.obsidian_vault_path) / "Sessions"
        if not sessions_path.exists():
            logger.warning(f"Sessions path does not exist: {sessions_path}")
            return

        driver = GraphDatabase.driver(
            settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
        )
        engine = PercolationEngine(driver)
        
        logger.debug(f"Initiating percolation from: {sessions_path}")
        stats = engine.percolate_from_vault(sessions_path)
        
        elapsed_ms = (time.time() - start_time) * 1000
        logger.info(
            f"✓ Scheduler completed in {elapsed_ms:.0f}ms: "
            f"{stats['tasks']} tasks, "
            f"{stats['commits']} commits, {stats['links']} decision links"
        )
        logger.debug(f"Stats detail: {stats}")
        driver.close()
    except Exception as e:
        logger.error(f"Batch session percolation failed: {e}", exc_info=True)


# ===================================================================
# --- ENDPOINTS ---
@app.get("/")
async def root():
    return {
        "service": "Omega_KG Capture Server",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "capture": "POST /capture",
            "health": "GET /health",
            "linear_webhook": "POST /webhook/linear",
        },
        "docs": "/docs",
        "openapi": "/openapi.json",
    }


@app.get("/health")
async def health_check():
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "vault_accessible": False,
        "neo4j_connected": False,
        "postgres_connected": False,
    }
    try:
        vault_path = Path(settings.obsidian_vault_path)
        health_status["vault_accessible"] = vault_path.exists()
        health_status["vault_path"] = str(vault_path)
    except Exception as e:
        logger.warning(f"Vault check failed: {e}")
    try:
        driver = GraphDatabase.driver(
            settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
        )
        with driver.session() as session:
            session.run("RETURN 1")
        driver.close()
        health_status["neo4j_connected"] = True
    except Exception as e:
        logger.warning(f"Neo4j check failed: {e}")
        health_status["neo4j_error"] = str(e)

    # PostgreSQL Health Check (Async)
    try:
        async for session in get_db():
            await session.execute(text("SELECT 1"))
            health_status["postgres_connected"] = True
            break
    except Exception as e:
        logger.warning(f"PostgreSQL check failed: {e}")
        health_status["postgres_error"] = str(e)

    return health_status


@app.on_event("startup")
async def startup_event():
    """Log deprecation notice for legacy endpoint."""
    logger.warning(
        "⚠️  Legacy endpoint /webhook/linear active. New endpoint: /webhooks/linear"
    )


@app.post("/auth/token", response_model=Token)
async def login_for_access_token(
    _api_key: str = Security(get_static_api_key),
) -> Token:
    """
    Exchange static API key for a short-lived JWT Bearer token.

    The Chrome extension calls this endpoint with the bootstrap API key (X-API-Key header)
    to receive a short-lived JWT token for subsequent API requests.

    Args:
        _api_key: Validated static API key from X-API-Key header

    Returns:
        Token model with access_token and token_type

    Raises:
        HTTPException: 403 if API key is invalid
    """
    logger.info("Token request received")
    access_token = create_access_token(data={"sub": "chrome_extension_user"})
    return Token(access_token=access_token, token_type="bearer")


# --- ENDPOINT 1: Chrome Extension Capture (FIXED) ---
@app.options("/capture")
async def capture_options():
    """Handle CORS preflight requests for /capture endpoint"""
    return {"message": "CORS preflight OK"}


@app.post("/capture", response_model=CaptureResponse)
async def capture_conversation(
    data: ConversationData,
    request: Request,
    _token_payload: Dict[str, Any] = Security(validate_access_token),
) -> CaptureResponse:
    # --- FIX #3: Security Hardening ---
    # 1. Check Content-Length Header (Fail Fast)
    content_length = int(request.headers.get("content-length", 0))
    if content_length > MAX_HTML_SIZE:
        logger.warning(f"Payload too large: {content_length} bytes")
        raise HTTPException(
            status_code=413,
            detail=f"Payload exceeds maximum allowed size of {MAX_HTML_SIZE} bytes",
        )

    # 2. Check parsed HTML content size (Logic Validation)
    if hasattr(data, "raw_html") and data.raw_html:
        if len(data.raw_html) > MAX_HTML_SIZE:
            logger.warning("HTML content field exceeds limit")
            raise HTTPException(status_code=413, detail="HTML content too large")
    # --- FIX #3 END ---

    # 3. PARSING LOGIC
    if (not data.messages) and data.raw_html:
        logger.info(
            f"Detecting Raw HTML. Attempting server-side parsing for: {data.url}"
        )
        try:
            data.messages = parse_html_content(data.raw_html, data.url or "unknown")
            logger.info(f"✓ Successfully parsed {len(data.messages)} messages.")
        except Exception as e:
            logger.error(f"HTML Parsing failed: {e}")
            data.messages = [{"role": "system", "content": f"Parsing failed: {e}"}]

    # 2. VALIDATION
    if not data.messages and not data.content:
        raise HTTPException(
            status_code=422, detail="No messages provided and HTML parsing failed."
        )

    # 3. PROCESSING (With Robust Error Handling)
    try:
        markdown_content = format_conversation_markdown(data)
        conv_hash = generate_conversation_hash(data)
        file_path = write_to_obsidian(data.platform, markdown_content, conv_hash)

        # Percolate to Neo4j WITH embedding generation
        nodes_created = 0
        try:
            nodes_created = await percolate_to_neo4j_with_embedding(file_path, data)
        except Exception as e:
            logger.warning(f"Neo4j percolation failed (non-fatal): {e}")

        logger.info(
            "Capture processed",
            extra={"platform": data.platform, "file": str(file_path), "nodes": nodes_created},
        )

        return CaptureResponse(
            success=True,
            file_path=str(file_path),
            nodes_created=nodes_created,
            message=f"Successfully captured {len(data.messages) if data.messages else 1} items with embedding.",
        )
    except Exception:
        support_id = str(uuid.uuid4())
        logger.exception(f"Critical Error {support_id}")
        raise HTTPException(
            status_code=500, detail={"message": "Internal error", "id": support_id}
        )


# --- ENDPOINT 2: Health Check (Vector Store) ---
@app.get("/health/vectors")
async def health_check_vectors() -> Dict[str, Any]:
    """
    Get vector store health metrics for monitoring.
    
    Returns:
        dict: Health status with pending/ready/failed counts and worker state
    """
    try:
        vector_store = await get_vector_store()
        stats = await vector_store.get_stats()
        
        pending_count = stats.get("pending_count", 0)
        failed_count = stats.get("failed_count", 0)
        
        # Determine health status
        if failed_count > 100:
            status = "unhealthy"
        elif pending_count > 1000:
            status = "degraded"
        else:
            status = "healthy"
        
        return {
            "status": status,
            "total_records": stats.get("total_records", 0),
            "pending_count": pending_count,
            "ready_count": stats.get("ready_count", 0),
            "failed_count": failed_count,
            "avg_retry_count": round(stats.get("avg_retry_count", 0), 2),
            "worker_running": True,
        }
    except Exception as e:
        logger.error(f"Vector health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "worker_running": False,
        }


# --- ENDPOINT 3: Linear Webhook (NEW) ---
@app.post("/webhook/linear")
async def linear_webhook_endpoint(request: Request):
    """
    Receives and validates webhooks from Linear.
    This endpoint just passes the raw request to the sync_engine.
    """
    # The sync_engine's method handles all verification and logic
    return await sync_engine.handle_linear_webhook_request(request)


# --- Main ---
def main():
    """Starts the Omega_KG Capture Server using Uvicorn."""
    import uvicorn

    logger.info("Starting Omega_KG Capture Server...")
    logger.info(f"Vault path: {settings.obsidian_vault_path}")
    logger.info(f"Neo4j URI: {settings.neo4j_uri}")

    # Use reload only in development mode
    uvicorn.run(
        "omega_kg.capture_server:app",
        host=settings.app_host,
        port=settings.app_port,
        log_level="info",
        reload=False,  # Disable reload for stability
    )


if __name__ == "__main__":
    main()
