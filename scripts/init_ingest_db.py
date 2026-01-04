import asyncio
import logging
import sys
from sqlalchemy.ext.asyncio import create_async_engine

# Add project root to path
sys.path.append(".")

from omega_kg.settings import settings
from omega_kg.database.base import Base
# Import models to register them with Base.metadata
from omega_kg.models.terminal import TerminalEvent
from omega_kg.models.raw_storage import RawConversation
from omega_kg.models.linear import RawLinearEvent
from omega_kg.models.webhook import RawWebhookEvent

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("init_ingest_db")

async def init_db():
    ingest_url = settings.ingest_database_url
    logger.info(f"Connecting to Ingest DB: {ingest_url.split('@')[-1]}") # Mask auth
    
    engine = create_async_engine(ingest_url, echo=True)
    
    async with engine.begin() as conn:
        logger.info("Ensuring pgvector extension...")
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        logger.info("Creating tables...")
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Tables created successfully.")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(init_db())
