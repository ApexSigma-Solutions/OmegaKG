from fastapi import FastAPI
from sqlalchemy import text
from omega_kg.routers import linear_receiver
from omega_kg.settings import settings
from omega_kg.database.session import get_db

# Import models to ensure SQLAlchemy tracks them
from omega_kg.database.models import RawWebhookEvent  # noqa: F401
from omega_kg.models.linear import RawLinearEvent  # noqa: F401

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(linear_receiver.router, tags=["Linear Ingest"])


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
            break  # Only need one
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {"status": "online", "version": settings.VERSION, "database": db_status}
