import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text
from omega_kg.routers import linear_receiver, github_receiver
from omega_kg.settings import settings
from omega_kg.database.session import get_db
from omega_kg.workers.event_processor import EventProcessor

logger = logging.getLogger(__name__)

# Global event processor instance
event_processor = EventProcessor()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle with EventProcessor integration.
    
    Startup:
        - Initialize EventProcessor
        - Create background task for polling loop
    
    Shutdown:
        - Stop EventProcessor gracefully
        - Wait for task completion with timeout
    """
    # Startup
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


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.include_router(linear_receiver.router, tags=["Linear Ingest"])
app.include_router(github_receiver.router, tags=["GitHub Ingest"])


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

    return {
        "status": "online",
        "version": settings.VERSION,
        "database": db_status,
        "event_processor": "running" if event_processor.running else "stopped",
    }
