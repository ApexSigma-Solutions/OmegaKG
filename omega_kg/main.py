import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, APIRouter
from sqlalchemy import text
from omega_kg.routers import linear_receiver, github_receiver
from omega_kg.settings import settings
from omega_kg.database.session import get_db
from omega_kg.workers.event_processor import EventProcessor
from omega_kg.intelligence import Codex, Mirmir

logger = logging.getLogger(__name__)

# Global instances
event_processor = EventProcessor()
codex: Codex = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle with EventProcessor and Intelligence Layer integration.

    Startup:
        - Initialize EventProcessor
        - Initialize Codex for constraint governance
        - Create background task for polling loop

    Shutdown:
        - Stop EventProcessor gracefully
        - Close Codex connection
        - Wait for task completion with timeout
    """
    global codex

    # Startup - Initialize Codex
    logger.info("Application startup: Initializing Codex")
    try:
        codex = Codex()
        codex.connect()
        logger.info("[OK] Codex initialized and connected")
    except Exception as e:
        logger.warning(f"Failed to initialize Codex: {e}. Intelligence layer will be unavailable.")
        codex = None

    logger.info("Application startup: Initializing EventProcessor")
    processor_task = asyncio.create_task(event_processor.start())

    try:
        yield  # Application runs here

    finally:
        # Shutdown
        logger.info("Application shutdown: Stopping EventProcessor")
        await event_processor.stop()

        # Wait for task to complete (with timeout)
        try:
            await asyncio.wait_for(processor_task, timeout=10.0)
        except asyncio.TimeoutError:
            logger.warning("EventProcessor did not stop gracefully, cancelling")
            processor_task.cancel()

        # Close Codex connection
        if codex:
            codex.close()
            logger.info("[OK] Codex connection closed")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.include_router(linear_receiver.router, tags=["Linear Ingest"])
app.include_router(github_receiver.router, tags=["GitHub Ingest"])

# MCP router for intelligence layer tools
mcp_router = APIRouter(prefix="/mcp", tags=["MCP"])


@mcp_router.post("/tools/consult_codex")
async def consult_codex(action_description: str) -> Dict[str, Any]:
    """
    Consult the Codex before implementing complex features.

    Agents must call this before implementing features to check for known prohibitions.

    Args:
        action_description: Description of proposed action

    Returns:
        Mirmir verdict with approval status and details
    """
    if not codex:
        return {
            "error": "Codex not initialized",
            "message": "Intelligence layer unavailable"
        }

    mirmir = Mirmir(codex)
    verdict = mirmir.review_action(action_description)

    return {
        "allowed": verdict.approved,
        "reason": verdict.message,
        "constraint_id": verdict.violations[0] if verdict.violations else None,
        "verdict": verdict.dict()
    }


app.include_router(mcp_router)


@app.get("/health")
async def health_check():
    """
    Validates App and DB Health
    """
    db_status = "disconnected"
    try:
        # Probe DB
        async for session in get_db():
            await session.execute(text("SELECT 1"))
            db_status = "connected"
            break # Only need one
    except Exception as e:
        db_status = f"error: {str(e)}"

    codex_status = "unavailable"
    if codex and codex.is_connected():
        codex_status = "connected"

    return {
        "status": "online",
        "version": settings.VERSION,
        "database": db_status,
        "event_processor": "running" if event_processor.running else "stopped",
        "codex": codex_status,
    }
