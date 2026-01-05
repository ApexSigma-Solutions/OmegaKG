"""
Capture Router

FastAPI router for conversation capture endpoints.
Handles Chrome extension conversation capture, JWT token exchange, and vector health checks.

Extracted from capture_server.py for modularity.
"""

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request, Security, Depends
from neo4j import GraphDatabase
from sqlalchemy import text, select, desc

from omega_kg.auth_utils import (create_access_token, get_static_api_key,
                                 validate_access_token)
from omega_kg.database.session import get_db
# Use Ingest Session for Raw Storage (same as Terminal)
from omega_kg.database.ingest_session import get_ingest_db 
from omega_kg.models.capture import CaptureResponse, ConversationData, Token
from omega_kg.models.raw_storage import RawConversation
from omega_kg.parsers import parse_html_content
from omega_kg.settings import settings
from omega_kg.utils.capture_utils import generate_conversation_hash
from omega_kg.vector_store import get_vector_store

logger = logging.getLogger(__name__)

# Security limits
MAX_HTML_SIZE = 10 * 1024 * 1024  # 10MB - increased to accommodate larger conversation captures

router = APIRouter(tags=["Capture"])


# Import percolate function from main module (to avoid circular import)
# This will be injected/passed when the router is used
_percolate_to_neo4j_with_embedding = None


def set_percolate_function(func):
    """Set the percolate function to avoid circular imports."""
    global _percolate_to_neo4j_with_embedding
    _percolate_to_neo4j_with_embedding = func


@router.post("/auth/token", response_model=Token)
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


@router.options("/capture")
async def capture_options():
    """Handle CORS preflight requests for /capture endpoint"""
    return {"message": "CORS preflight OK"}


from sqlalchemy.exc import IntegrityError

@router.post("/capture", response_model=CaptureResponse)
async def capture_conversation(
    data: ConversationData,
    request: Request,
    _token_payload: Dict[str, Any] = Security(validate_access_token),
    db_session: Any = Depends(get_ingest_db),
) -> CaptureResponse:
    """
    Capture a conversation from the Chrome extension.
    
    NEW: Writes raw JSON to 'raw_conversations' table in Ingest Database.
    Does NOT write to filesystem or Neo4j directly anymore.
    """
    # --- Security Hardening ---
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

    # 4. VALIDATION
    if not data.messages and not data.content:
        raise HTTPException(
            status_code=422, detail="No messages provided and HTML parsing failed."
        )

    # 5. STORAGE (Raw SQL)
    try:
        conv_hash = generate_conversation_hash(data)
        
        # Create Raw Record
        raw_record = RawConversation(
            source_id=conv_hash,
            platform=data.platform,
            raw_payload=data.model_dump(mode="json"),
            captured_at=datetime.utcnow(),
            processed=False
        )
        
        db_session.add(raw_record)
        await db_session.commit()
        
        logger.info(f"Raw conversation captured: {conv_hash} to DB.")

        return CaptureResponse(
            success=True,
            file_path="[DB STORAGE]",
            nodes_created=0,
            message=f"Successfully queued conversation {conv_hash} for processing.",
        )
    except IntegrityError:
        await db_session.rollback()
        logger.info(f"Duplicate conversation captured: {conv_hash}. Ignoring.")
        return CaptureResponse(
            success=True,
            file_path="[DB STORAGE]",
            nodes_created=0,
            message=f"Conversation {conv_hash} already exists. Ignored.",
        )
    except Exception as e:
        support_id = str(uuid.uuid4())
        logger.exception(f"Critical Error {support_id} during capture: {e}")
        await db_session.rollback()
        raise HTTPException(
            status_code=500, detail={"message": "Internal error storing raw conversation", "id": support_id}
        )


@router.get("/capture/recent", response_model=List[CaptureResponse])
async def get_recent_captures(
    limit: int = 10,
    db_session: Any = Depends(get_ingest_db),
    _token_payload: Dict[str, Any] = Security(validate_access_token),
) -> List[CaptureResponse]:
    """
    Get the most recent captured conversations.
    """
    try:
        stmt = select(RawConversation).order_by(desc(RawConversation.captured_at)).limit(limit)
        result = await db_session.execute(stmt)
        raw_conversations = result.scalars().all()
        
        response = []
        for conv in raw_conversations:
             # Basic adaptation to CaptureResponse model for UI display
            response.append(CaptureResponse(
                success=True,
                file_path=f"db://{conv.source_id}",
                nodes_created=0,
                message=f"Captured via {conv.platform} at {conv.captured_at}",
            ))
            
        return response
    except Exception as e:
        logger.error(f"Failed to fetch recent captures: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health/vectors")
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


@router.get("/health")
async def health_check():
    """
    Comprehensive health check endpoint.

    Checks connectivity to Obsidian vault, Neo4j, and PostgreSQL.
    """
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


@router.get("/health/installation")
async def get_installation_status() -> Dict[str, Any]:
    """
    Get real-time status of Python environment and package installation.

    Returns:
        JSON with installation status, version, and troubleshooting links
    """
    try:
        import omega_kg
        version = getattr(omega_kg, "__version__", "unknown")
        installed = True
    except ImportError:
        installed = False
        version = None

    status = {
        "status": "healthy" if installed else "unhealthy",
        "omega_kg_installed": installed,
        "version": version,
        "timestamp": datetime.now().isoformat()
    }

    if not installed:
        status["details"] = {
            "error": "Package not installed",
            "troubleshooting": "Run scripts/setup_omega_kg.ps1 or pip install -e .",
            "documentation": "docs/INSTALLATION_TROUBLESHOOTING.md"
        }

    return status


__all__ = ["router", "set_percolate_function"]
