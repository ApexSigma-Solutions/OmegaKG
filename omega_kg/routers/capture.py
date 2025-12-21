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
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request, Security
from neo4j import GraphDatabase
from sqlalchemy import text

from omega_kg.auth_utils import (create_access_token, get_static_api_key,
                                 validate_access_token)
from omega_kg.database.session import get_db
from omega_kg.models.capture import CaptureResponse, ConversationData, Token
from omega_kg.parsers import parse_html_content
from omega_kg.settings import settings
from omega_kg.utils.capture_utils import (format_conversation_markdown,
                                          generate_conversation_hash,
                                          write_to_obsidian)
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


@router.post("/capture", response_model=CaptureResponse)
async def capture_conversation(
    data: ConversationData,
    request: Request,
    _token_payload: Dict[str, Any] = Security(validate_access_token),
) -> CaptureResponse:
    """
    Capture a conversation from the Chrome extension.

    Processes the conversation data, saves to Obsidian vault,
    and percolates to Neo4j with embedding generation.
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

    # 5. PROCESSING (With Robust Error Handling)
    try:
        markdown_content = format_conversation_markdown(data)
        conv_hash = generate_conversation_hash(data)
        file_path = write_to_obsidian(data.platform, markdown_content, conv_hash)

        # Percolate to Neo4j WITH embedding generation
        nodes_created = 0
        if _percolate_to_neo4j_with_embedding:
            try:
                nodes_created = await _percolate_to_neo4j_with_embedding(
                    file_path, data
                )
            except Exception as e:
                logger.warning(f"Neo4j percolation failed (non-fatal): {e}")

        logger.info(
            "Capture processed",
            extra={
                "platform": data.platform,
                "file": str(file_path),
                "nodes": nodes_created,
            },
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


__all__ = ["router", "set_percolate_function"]
