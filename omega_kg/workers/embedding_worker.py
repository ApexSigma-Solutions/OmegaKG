# Dual-Write Saga Weaver
import asyncio
import logging
from datetime import datetime
import re
from typing import List, Any, Optional
from sqlalchemy import select

# Internal Imports
from omega_kg.database import get_ingest_session
from omega_kg.models.terminal import TerminalEvent
from omega_kg.services.openai_service import generate_embedding
from omega_kg.services.omegakg_client import OmegaKGInternalClient
from omega_kg.models.validation_schemas import KnowledgeDigest, DigestType

# Setup Logger
logger = logging.getLogger("omega.worker.embedding")
# Ensuring level is set if not configured elsewhere
logger.setLevel(logging.INFO)

# --- CONFIGURATION ---
BATCH_SIZE = 10
POLL_INTERVAL = 5  # Seconds
AGENT_ID = "ghost-monitor"  # The persona for these automated memories

# --- REGEX FOR ENTITY EXTRACTION ---
# Matches LIN-123 or #123
ISSUE_PATTERN = re.compile(r"\b([A-Z]{2,5}-\d+)\b|\b#(\d+)\b")


class SagaWeaver:
    """
    The Loom that stitches raw events into the Knowledge Graph (Neo4j)
    AND the Semantic Memory (PGVector).
    """

    def __init__(self):
        self.omegakg_client = OmegaKGInternalClient()
        self.running = True

    async def start(self):
        logger.info("🕸️  Saga Weaver (API-Based) Started.")
        while self.running:
            try:
                await self.process_terminal_queue()
                await asyncio.sleep(POLL_INTERVAL)
            except Exception as e:
                logger.error(f"Worker Loop Error: {e}", exc_info=True)
                await asyncio.sleep(POLL_INTERVAL)
        await self.omegakg_client.close()

    async def process_terminal_queue(self):
        """
        Fetches unprocessed terminal events and weaves them into the Graph and Vector Store.
        """
        # We use the Ingest DB to read events
        # Utilizing async context manager for session
        async with get_ingest_session() as read_session:
            # 1. Fetch unprocessed events
            statement = (
                select(TerminalEvent)
                .where(not TerminalEvent.processed)
                .limit(BATCH_SIZE)
            )
            result = await read_session.execute(statement)
            events = result.scalars().all()

            if not events:
                return

            logger.info(f"Processing {len(events)} terminal events via API...")

            for event in events:
                try:
                    # 2. Extract Entities (The "Saga" Link)
                    linked_entities = self._extract_references(event.command)

                    # 3. Compile Context String (The "Memory")
                    context_text = self._compile_context(event)

                    # 4. Generate Vector (1024d)
                    embedding = await generate_embedding(context_text)

                    # 5. Construct Digest for Validation API
                    digest = KnowledgeDigest(
                        source_id=str(event.event_id),
                        digest_type=DigestType.TERMINAL_EVENT,
                        title=f"Terminal: {event.command[:50]}",
                        content=context_text,
                        embedding=embedding,
                        metadata={
                            "cwd": event.cwd,
                            "session_id": event.session_id,
                            "exit_code": event.exit_code,
                            "user": event.user,
                            "host": event.host,
                        },
                        tags=["terminal", "ghost", "auto-capture"],
                        references={
                            "session_id": [event.session_id]
                            if event.session_id
                            else [],
                            "linear_issue": linked_entities,
                        },
                        captured_at=event.captured_at,
                    )

                    # 6. Submit to Validation API
                    response = await self.omegakg_client.validate_and_store(digest)

                    if response["status"] in ["accepted", "duplicate"]:
                        logger.info(
                            f"Accepted Event {event.event_id}: {response.get('message')}"
                        )
                        event.processed = True
                        event.processed_at = datetime.utcnow()
                        event.last_error = None
                    else:
                        logger.warning(
                            f"Rejected Event {event.event_id}: {response.get('message')}"
                        )
                        event.processed = (
                            True  # Mark as processed even if rejected by policy
                        )
                        event.processed_at = datetime.utcnow()
                        event.last_error = response.get("message")

                    await read_session.commit()

                except Exception as e:
                    logger.error(
                        f"Failed to process event {event.id}: {e}", exc_info=True
                    )
                    event.processing_attempts += 1
                    event.last_error = str(e)
                    await read_session.commit()

    def _extract_references(self, text: str) -> List[str]:
        if not text:
            return []
        matches = ISSUE_PATTERN.findall(text)
        refs = []
        for m in matches:
            refs.extend([item for item in m if item])
        return list(set(refs))

    def _compile_context(self, event: TerminalEvent) -> str:
        status = "Success" if event.exit_code == 0 else "Failed"
        ts = event.captured_at.isoformat() if event.captured_at else "UNKNOWN_TIME"
        return (
            f"TERMINAL EXECUTION [{ts}]\n"
            f"Command: {event.command}\n"
            f"Directory: {event.cwd}\n"
            f"Result: {status} (Exit Code: {event.exit_code})\n"
            f"Host: {event.host}"
        )

    async def process_single_event(self, event_id: Any) -> bool:
        """Fetches and processes a single specific event by UUID."""
        async with get_ingest_session() as session:
            stmt = select(TerminalEvent).where(TerminalEvent.event_id == event_id)
            result = await session.execute(stmt)
            event = result.scalar_one_or_none()
            if event and not event.processed:
                await self.process_terminal_event(session, event)
                return True
        return False

    # REMOVED: _push_to_neo4j - Now handled by KnowledgeStore via Validation API
    # REMOVED: _push_to_pgvector - Now handled by KnowledgeStore via Validation API


if __name__ == "__main__":
    # Configure root logger to see output
    logging.basicConfig(level=logging.INFO)
    weaver = SagaWeaver()
    try:
        asyncio.run(weaver.start())
    except KeyboardInterrupt:
        logger.info("Worker stopped.")


# --- Integration Helpers for Capture Server ---
_weaver_instance: Any = None
_weaver_task: Optional[asyncio.Task] = None


async def start_worker() -> None:
    """Start the Saga Weaver as a background task."""
    global _weaver_instance, _weaver_task

    if _weaver_instance is not None:
        logger.warning("Worker already running")
        return

    _weaver_instance = SagaWeaver()
    _weaver_task = asyncio.create_task(_weaver_instance.start())
    logger.info("Saga Weaver task created")


async def stop_worker() -> None:
    """Stop the Saga Weaver."""
    global _weaver_instance, _weaver_task

    if _weaver_instance:
        _weaver_instance.running = False
        logger.info("Stopping Saga Weaver...")

    if _weaver_task:
        try:
            # Wait for graceful shutdown (poll interval is 5s, so this might take a bit)
            # functionality depends on 'start' loop checking 'self.running'
            # We can also cancel if needed
            await asyncio.wait_for(_weaver_task, timeout=10)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            logger.warning("Forcing worker shutdown")
            _weaver_task.cancel()
            try:
                await _weaver_task
            except asyncio.CancelledError:
                pass

    _weaver_instance = None
    _weaver_task = None


async def process_terminal_event_background(event_id: Any) -> None:
    """Helper for FastAPI BackgroundTasks to process an event quickly."""
    weaver = SagaWeaver()
    try:
        await weaver.process_single_event(event_id)
    except Exception as e:
        logger.error(f"Background processing failed for {event_id}: {e}")
    finally:
        await weaver.omegakg_client.close()
