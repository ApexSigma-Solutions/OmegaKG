"""
Async Background Worker for Embedding Generation

Polls for pending embeddings from PostgreSQL, generates vectors via Ollama/Gemini,
and updates records with completion status. Designed for at-least-once processing
with graceful error handling and crash recovery.

Execution Model:
- Runs continuously in background via FastAPI lifespan event
- Polls every VECTOR_WORKER_POLL_INTERVAL_SECONDS for pending records
- Processes batch_size records per poll cycle
- Retries on failure up to VECTOR_EMBEDDING_MAX_RETRIES times
- Logs metrics for monitoring and alerting

Integration:
- Called by capture_server.py lifespan events (startup/shutdown)
- Shares connection pool with capture endpoint (no resource contention)
- Uses FastAPI contextvars for graceful shutdown signaling

Error Recovery:
- Worker crash: Database records remain pending; worker restarts and continues
- Ollama offline: Falls back to Gemini or marks FAILED with retry tracking
- Database connection lost: Retries with exponential backoff; raises error if unrecoverable
"""

import asyncio
import logging
from typing import Any, Optional

from omega_kg.config import (VECTOR_EMBEDDING_MAX_RETRIES,
                             VECTOR_WORKER_BATCH_SIZE,
                             VECTOR_WORKER_POLL_INTERVAL_SECONDS,
                             VECTOR_WORKER_TIMEOUT_SECONDS)
from omega_kg.vector_store import VectorStore, get_vector_store

logger = logging.getLogger(__name__)

# Global worker state
_worker_task: Optional[asyncio.Task[Any]] = None
_worker_stop_event: Optional[asyncio.Event] = None


class EmbeddingWorker:
    """
    Background worker for processing pending embeddings.

    Lifecycle:
    - start() -> begins polling loop in background
    - stop() -> signals loop to exit and waits for pending records
    - Integrates with FastAPI lifespan via ContextVar for graceful shutdown

    Metrics:
    - processed_count: Total embeddings successfully generated
    - error_count: Total embeddings marked as failed
    - batch_time: Latest batch processing duration (seconds)
    """

    def __init__(self, vector_store: VectorStore):
        """
        Initialize worker with vector store.

        Args:
            vector_store: Initialized VectorStore instance
        """
        self.vector_store = vector_store
        self.processed_count = 0
        self.error_count = 0
        self.batch_time = 0.0
        self.running = False

    async def start(self) -> None:
        """
        Start the polling loop (runs indefinitely until stop() called).

        Polls for pending embeddings and processes them in batches.
        Logs startup message and enters continuous loop.

        Should be called from FastAPI lifespan (startup event).
        """
        self.running = True
        logger.info(
            f"Starting embedding worker: batch_size={VECTOR_WORKER_BATCH_SIZE}, "
            f"poll_interval={VECTOR_WORKER_POLL_INTERVAL_SECONDS}s, "
            f"max_retries={VECTOR_EMBEDDING_MAX_RETRIES}"
        )

        while self.running:
            try:
                await self._process_batch()
                await asyncio.sleep(VECTOR_WORKER_POLL_INTERVAL_SECONDS)
            except Exception as e:
                logger.exception(f"Worker batch processing failed: {e}")
                await asyncio.sleep(VECTOR_WORKER_POLL_INTERVAL_SECONDS)

    async def stop(self) -> None:
        """
        Signal worker to exit polling loop.

        Allows in-flight batch to complete before shutdown.
        Logs final metrics (processed, errors).

        Should be called from FastAPI lifespan (shutdown event).
        """
        self.running = False
        logger.info(
            f"Stopping embedding worker: processed={self.processed_count}, "
            f"errors={self.error_count}"
        )

    async def _process_batch(self) -> None:
        """
        Fetch pending batch, fetch source text, generate embeddings, update database.

        Steps:
        1. Fetch up to batch_size pending records with FOR UPDATE SKIP LOCKED
        2. For each record, fetch source message text from Neo4j
        3. Generate embedding via Ollama/Gemini
        4. Update database with embedding (mark READY) or error (mark FAILED + retry)

        Raises:
            ConnectionError: If vector store fetch fails (worker will retry in loop)
        """
        import time

        start_time = time.time()

        try:
            # Step 1: Fetch pending batch
            pending = await self.vector_store.fetch_pending_batch(
                batch_size=VECTOR_WORKER_BATCH_SIZE
            )

            if not pending:
                logger.debug("No pending embeddings to process")
                return

            logger.debug(f"Processing batch of {len(pending)} pending embeddings")

            # Step 2-4: Process each record
            for record in pending:
                vector_id = record["vector_id"]
                message_id = record["message_id"]
                node_label = record["node_label"]

                try:
                    # Fetch message content from Neo4j
                    message_text = await self._fetch_message_text(
                        message_id, node_label
                    )
                    if not message_text:
                        logger.warning(
                            f"Message not found: message_id={message_id}, "
                            f"node_label={node_label}"
                        )
                        await self.vector_store.mark_failed(
                            vector_id, increment_retry=True
                        )
                        self.error_count += 1
                        continue

                    # Generate embedding
                    try:
                        from omega_kg.domain.common.embedding_service import \
                            generate_embedding

                        embedding = await asyncio.wait_for(
                            generate_embedding(message_text),
                            timeout=VECTOR_WORKER_TIMEOUT_SECONDS,
                        )

                        # Update database with embedding
                        await self.vector_store.update_embedding(vector_id, embedding)
                        self.processed_count += 1
                        logger.debug(f"Successfully embedded vector_id={vector_id}")

                    except asyncio.TimeoutError:
                        logger.error(
                            f"Embedding generation timed out: vector_id={vector_id}"
                        )
                        await self.vector_store.mark_failed(
                            vector_id, increment_retry=True
                        )
                        self.error_count += 1

                except Exception as e:
                    logger.error(f"Failed to process vector_id={vector_id}: {e}")
                    try:
                        await self.vector_store.mark_failed(
                            vector_id, increment_retry=True
                        )
                    except Exception as mark_error:
                        logger.error(f"Failed to mark vector as failed: {mark_error}")
                    self.error_count += 1

            self.batch_time = time.time() - start_time
            logger.debug(
                f"Batch processing completed in {self.batch_time:.2f}s: "
                f"processed={self.processed_count}, errors={self.error_count}"
            )

        except Exception as e:
            logger.error(f"Batch fetch failed: {e}")
            raise

    async def _fetch_message_text(
        self, message_id: str, node_label: str
    ) -> Optional[str]:
        """
        Fetch message content from Neo4j by node ID and label asynchronously.

        Implements strategic content extraction patterns per node type:
        - ChatMessage: Simple content field
        - LinearIssue: Title + Description (compound context)
        - ChatSession: Summary field with fallback
        - Decision: Multi-field coalesce

        Uses AsyncGraphDriver for non-blocking, pooled connections.

        Args:
            message_id: Neo4j internal node ID (from elementId(n))
            node_label: Neo4j node type (ChatMessage, LinearIssue, Decision, ChatSession)

        Returns:
            str or None: Message content to embed, or None if not found

        Raises:
            No exceptions raised; logs errors and returns None on failure
        """
        logger.debug(
            f"Fetching message: message_id={message_id}, node_label={node_label}"
        )

        try:
            from omega_kg.database.graph import graph_driver

            # Strategic query patterns per node type
            query_map = {
                "ChatMessage": """
                    MATCH (n:ChatMessage)
                    WHERE elementId(n) = $message_id
                    RETURN coalesce(n.content, n.message, n.text, '[Empty message]') AS text
                """,
                "LinearIssue": """
                    MATCH (n:LinearIssue)
                    WHERE elementId(n) = $message_id
                    RETURN coalesce(n.title, '[Untitled issue]') + '\\n\\n' + coalesce(n.description, '') AS text
                """,
                "ChatSession": """
                    MATCH (n:ChatSession)
                    WHERE elementId(n) = $message_id
                    RETURN 'Session Summary: ' + coalesce(n.summary, 'No summary available') AS text
                """,
                "Decision": """
                    MATCH (n:Decision)
                    WHERE elementId(n) = $message_id
                    RETURN coalesce(n.content, n.text, n.description) AS text
                """,
            }

            # Get appropriate query or fallback to generic
            query = query_map.get(
                node_label,
                f"""
                    MATCH (n:{node_label})
                    WHERE elementId(n) = $message_id
                    RETURN coalesce(n.content, n.message, n.text, n.body) AS text
                """,
            )

            # Execute query asynchronously using shared async driver
            async with graph_driver.session() as session:
                result = await session.run(query, message_id=message_id)
                record = await result.single()

                if record:
                    text = record.get("text")
                    if text and isinstance(text, str):
                        logger.debug(
                            f"Fetched text for {node_label}:{message_id} "
                            f"({len(text)} chars)"
                        )
                        return text
                    else:
                        logger.warning(
                            f"Node found but text is empty: {node_label}:{message_id}"
                        )
                        return None

                logger.warning(f"Node not found: {node_label}:{message_id}")
                return None

        except Exception as e:
            logger.error(
                f"Failed to fetch message text: message_id={message_id}, "
                f"node_label={node_label}, error={e}"
            )
            return None


# Singleton instance
_worker: Optional[EmbeddingWorker] = None


async def get_embedding_worker() -> EmbeddingWorker:
    """
    Get or initialize the singleton EmbeddingWorker instance.

    Returns:
        EmbeddingWorker: Shared instance with initialized vector store
    """
    global _worker

    if _worker is None:
        vector_store = await get_vector_store()
        _worker = EmbeddingWorker(vector_store)

    return _worker


async def start_worker() -> None:
    """
    Start the embedding worker background task.

    Called from FastAPI lifespan startup event.
    Creates background task that runs until stop_worker() called.
    """
    global _worker_task, _worker_stop_event

    worker = await get_embedding_worker()
    _worker_stop_event = asyncio.Event()

    _worker_task = asyncio.create_task(worker.start())
    logger.info("Embedding worker started")


async def stop_worker() -> None:
    """
    Stop the embedding worker background task.

    Called from FastAPI lifespan shutdown event.
    Signals worker to exit and waits for graceful completion.
    """
    global _worker_task, _worker_stop_event

    if _worker:
        await _worker.stop()

    if _worker_stop_event:
        _worker_stop_event.set()

    if _worker_task:
        try:
            await asyncio.wait_for(_worker_task, timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning("Embedding worker did not stop gracefully; cancelling")
            _worker_task.cancel()

    logger.info("Embedding worker stopped")


__all__ = [
    "EmbeddingWorker",
    "get_embedding_worker",
    "start_worker",
    "stop_worker",
]
