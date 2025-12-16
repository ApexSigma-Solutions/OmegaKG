#!/usr/bin/env python
"""
Omega_KG Capture Server

FastAPI server that receives AI conversations from chrome extension,
saves them to Obsidian vault, and percolates to Neo4j.

This module handles:
- Application initialization and lifespan management
- Router registration
- CORS configuration
- Neo4j percolation logic
- Scheduler for batch operations

Modular components:
- omega_kg.models.capture: Pydantic data models
- omega_kg.utils.capture_utils: Helper functions
- omega_kg.routers.capture: Endpoint handlers
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import neo4j
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from neo4j import GraphDatabase

from omega_kg.config import log_config_summary
from omega_kg.linear_sync import LinearSync
from omega_kg.models.capture import ConversationData
from omega_kg.percolation import PercolationEngine
from omega_kg.routers import linear_receiver
from omega_kg.routers.capture import router as capture_router
from omega_kg.routers.capture import set_percolate_function
from omega_kg.settings import settings
from omega_kg.utils.capture_utils import generate_conversation_hash
from omega_kg.vector_store import VectorStore, get_vector_store
from omega_kg.workers.embedding_worker import start_worker, stop_worker

# Async scheduling with graceful fallback
_scheduler_available = True
AsyncIOScheduler = None

if TYPE_CHECKING:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
else:
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
    except ImportError as e:
        _scheduler_available = False

        # Define a dummy class to prevent runtime errors when APScheduler is not available
        class AsyncIOScheduler:  # type: ignore
            def __init__(self):
                pass

            def add_job(self, *args, **kwargs):
                pass

            def start(self):
                pass

            def shutdown(self, *args, **kwargs):
                pass

        import warnings

        warnings.warn(
            f"APScheduler not available: {e}. Background tasks will be disabled.",
            ImportWarning,
        )


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# --- Neo4j Percolation Functions ---
async def _create_decision_nodes_async(
    session: "neo4j.work.async_.AsyncSession", conv_hash: str, data: ConversationData
) -> int:
    """
    Extract decisions from messages and create Decision nodes in Neo4j (async version).

    Only the first matching sentence per message containing a decision keyword is extracted.
    """
    decision_keywords = settings.decision_keywords
    nodes_created = 0
    if data.messages:
        for i, msg in enumerate(data.messages):
            msg_content = (
                msg.get("content", "") if isinstance(msg, dict) else msg.content
            )
            content_lower = msg_content.lower()
            for keyword in decision_keywords:
                if keyword in content_lower:
                    sentences = msg_content.split(".")
                    for sentence in sentences:
                        if keyword in sentence.lower():
                            decision_content = sentence.strip()
                            result = await session.run(
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
                            record = await result.single()
                            if record:
                                nodes_created += 1
                            break
    return nodes_created


async def percolate_to_neo4j_with_embedding(
    file_path: Path,
    data: ConversationData,
) -> int:
    """
    Percolates a captured conversation to Neo4j WITH pending vector record creation.
    Creates a ChatSession node and queues embedding generation via vector_store.
    Captures complete immediately; embeddings are generated asynchronously by worker.

    Uses AsyncGraphDriver for non-blocking Neo4j operations.
    """
    from omega_kg.database.graph import graph_driver

    try:
        conv_hash = generate_conversation_hash(data)

        # Create ChatSession in Neo4j (WITHOUT immediate embedding) using async driver
        async with graph_driver.session() as session:
            result = await session.run(
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

            record = await result.single()
            if not record:
                logger.warning(f"Failed to create ChatSession node for {conv_hash}")
                return 0

            session_id = record["session_id"]
            nodes_created = 1

            # Create Decision nodes (async)
            nodes_created += await _create_decision_nodes_async(
                session, conv_hash, data
            )

        # Queue pending embedding via vector_store (async, non-blocking)
        try:
            vector_store = await get_vector_store()
            vector_id = await vector_store.store_pending(
                message_id=session_id, node_label="ChatSession"
            )
            logger.info(
                f"✓ Queued embedding for ChatSession {conv_hash} "
                f"(neo4j_id={session_id}, vector_id={vector_id})"
            )
        except Exception as e:
            logger.warning(f"Failed to queue embedding for {conv_hash}: {e}")
            # Non-fatal: Node created successfully, embedding will retry

        logger.info(
            f"Created {nodes_created} nodes in Neo4j + pending embedding queued"
        )
        return nodes_created

    except Exception as e:
        logger.error(f"Neo4j percolation failed: {e}")
        raise


# --- Synchronous Neo4j Percolation (for backward compatibility and tests) ---
def _create_chat_session(
    session, conv_hash: str, file_path: Path, data: ConversationData
) -> int:
    """Create or update a ChatSession node in Neo4j."""
    msg_count = len(data.messages) if data.messages else 0
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
        msg_count=msg_count,
        created_at=datetime.now().isoformat(),
    )
    return 1 if result.single() else 0


def _create_decision_nodes(
    session: "neo4j.work.session.Session", conv_hash: str, data: ConversationData
) -> int:
    """
    Extract decisions from messages and create Decision nodes in Neo4j (synchronous version).

    Only the first matching sentence per message containing a decision keyword is extracted.
    """
    decision_keywords = settings.decision_keywords
    nodes_created = 0
    if data.messages:
        for i, msg in enumerate(data.messages):
            msg_content = (
                msg.get("content", "") if isinstance(msg, dict) else msg.content
            )
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


def percolate_to_neo4j(
    file_path: Path,
    data: ConversationData,
    driver=None,
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


def batch_percolate_sessions():
    """
    Batch percolates all session logs from the Obsidian vault to Neo4j.
    Intended to run periodically via scheduler.
    """
    driver = None
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
    except Exception as e:
        logger.error(f"Batch session percolation failed: {e}", exc_info=True)
    finally:
        if driver is not None:
            driver.close()


# --- Lifespan Handler ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler to initialize vector store, start worker, and schedule batch percolation."""
    logger.info("Starting Omega_KG Capture Server...")

    # Initialize scheduler variable to ensure it's available in shutdown
    scheduler = None

    # Initialize vector store
    try:
        await get_vector_store()
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
        if not _scheduler_available:
            logger.warning(
                "Scheduler not available - APScheduler import failed. Background tasks disabled."
            )
        else:
            scheduler = AsyncIOScheduler()  # type: ignore
            scheduler.add_job(
                batch_percolate_sessions,
                "interval",
                minutes=5,
                id="session_percolation",
            )
            scheduler.start()
            logger.info("✓ Session percolation scheduled (every 5 minutes)")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")
        scheduler = None

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

    # Stop scheduler (only if it was started)
    if scheduler is not None:
        try:
            scheduler.shutdown(wait=False)
            logger.info("✓ Scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")
    else:
        logger.info("Scheduler was not started - skipping shutdown")

    # Close vector store pool
    try:
        await VectorStore.close_pool()
        logger.info("✓ Vector store pool closed")
    except Exception as e:
        logger.error(f"Error closing vector store: {e}")


# --- App Initialization ---
app = FastAPI(
    title="Omega_KG Capture Server",
    description="Receives AI conversations and integrates with Neo4j",
    version="1.0.0",
    lifespan=lifespan,
)

sync_engine = LinearSync()

# Inject percolate function into capture router
set_percolate_function(percolate_to_neo4j_with_embedding)

# Register routers
app.include_router(capture_router)
app.include_router(linear_receiver.router, tags=["Linear Ingest"])

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"chrome-extension://{settings.chrome_extension_id}",
    ],
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["X-API-Key", "Authorization", "Content-Type"],
)


# --- Root Endpoint ---
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


# --- Linear Webhook Endpoint ---
@app.post("/webhook/linear")
async def linear_webhook_endpoint(request: Request):
    """
    Receives and validates webhooks from Linear.
    This endpoint just passes the raw request to the sync_engine.
    """
    return await sync_engine.handle_linear_webhook_request(request)


# --- Main Entry Point ---
def main():
    """Starts the Omega_KG Capture Server using Uvicorn."""
    import uvicorn

    logger.info("Starting Omega_KG Capture Server...")
    logger.info(f"Vault path: {settings.obsidian_vault_path}")
    logger.info(f"Neo4j URI: {settings.neo4j_uri}")

    uvicorn.run(
        "omega_kg.capture_server:app",
        host=settings.app_host,
        port=settings.app_port,
        log_level="info",
        reload=False,
    )


if __name__ == "__main__":
    main()
    main()
