import asyncio
import json
import logging
import time
from typing import Any, Awaitable, Callable, Dict, Optional, Tuple

from sqlalchemy import select

from omega_kg.database.session import AsyncSessionLocal
from omega_kg.domain.linear.processor import get_linear_processor
from omega_kg.models.webhook import RawWebhookEvent
from omega_kg.settings import settings

logger = logging.getLogger(__name__)

class EventProcessorMetrics:
    """Track event processor metrics for monitoring."""

    def __init__(self) -> None:
        self.processed_count: int = 0
        self.error_count: int = 0
        self.batch_count: int = 0
        self.last_batch_time: float = 0.0
        self.start_time: float = time.time()

    def record_processed(self) -> None:
        self.processed_count += 1

    def record_error(self) -> None:
        self.error_count += 1

    def record_batch(self, duration_seconds: float) -> None:
        self.batch_count += 1
        self.last_batch_time = duration_seconds

    def get_stats(self) -> Dict[str, float]:
        uptime = time.time() - self.start_time
        return {
            "processed_total": self.processed_count,
            "errors_total": self.error_count,
            "batches_total": self.batch_count,
            "last_batch_time": self.last_batch_time,
            "uptime_seconds": uptime,
        }

    def log_metrics(self) -> None:
        stats = self.get_stats()
        logger.info(
            "EventProcessor metrics: processed=%s errors=%s batches=%s last_batch_time=%.4fs uptime=%.2fs",
            stats["processed_total"],
            stats["errors_total"],
            stats["batches_total"],
            stats["last_batch_time"],
            stats["uptime_seconds"],
        )

class EventProcessor:
    """
    TN-103: The Refinery (Schema Aligned).
    Polls 'raw_webhook_events' and dispatches to domain strategies.
    
    Architecture:
    - Producer: Database Poller (processed_status=False)
    - Consumer: Strategy Handler (Linear, etc.)
    - Concurrency: Row Locking (SKIP LOCKED)
    """
    def __init__(self) -> None:
        self.running = False
        self.metrics = EventProcessorMetrics()
        self._handlers: Dict[str, Callable[[Dict[str, Any]], Awaitable[bool] | bool]] = {}
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        """Registers the known domain processors."""
        linear = get_linear_processor()
        self.register_handler("linear", linear.process_single_event)

        # Register GitHub handler
        from omega_kg.domain.github.processor import get_github_processor
        github = get_github_processor()
        self.register_handler("github", github.process_single_event)

    def register_handler(
        self, source: str, handler: Callable[[Dict[str, Any]], Awaitable[bool] | bool]
    ) -> None:
        self._handlers[source] = handler
        logger.info("EventProcessor: Registered handler for source '%s'", source)

    @property
    def handlers(self) -> Dict[str, Callable[[Dict[str, Any]], Awaitable[bool] | bool]]:
        return self._handlers

    async def start(self) -> None:
        self.running = True
        poll_interval = getattr(settings, "webhook_poll_interval", 0.5)
        logger.info(
            "🚀 Event Processor started. Polling every %ss.",
            poll_interval,
        )
        
        while self.running:
            try:
                processed_count = await self.process_batch()
                if processed_count == 0:
                    await asyncio.sleep(poll_interval)
                else:
                    await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                logger.info("Event Processor task cancelled.")
                break
            except Exception as e:
                logger.error(f"Event Processor Loop Crash: {e}", exc_info=True)
                await asyncio.sleep(5.0)

    async def stop(self) -> None:
        self.running = False
        logger.info("🛑 Event Processor stopping...")
        get_linear_processor().close()
        from omega_kg.domain.github.processor import get_github_processor
        get_github_processor().close()

    async def process_batch(self) -> int:
        """Process a batch of pending webhook events with robust error handling."""

        batch_start = time.time()
        batch_size = getattr(settings, "webhook_batch_size", 10)

        async with AsyncSessionLocal() as session:
            # 1) Fetch pending events with row locking
            query = (
                select(RawWebhookEvent)
                .where(RawWebhookEvent.processed_status.is_(False))
                .limit(batch_size)
                .with_for_update(skip_locked=True)
            )

            result = await session.execute(query)
            events = result.scalars().all()

            if not events:
                return 0

            processed = 0
            for event in events:
                try:
                    payload = self._parse_payload(event.payload)
                    success, error_msg = await self._dispatch(event, payload)

                    if success:
                        await self._mark_complete(session, event)
                        # Linear successes already counted inside _handle_linear_event
                        if getattr(event, "source", None) != "linear":
                            self.metrics.record_processed()
                    else:
                        await self._mark_failed(session, event, error_msg)
                        # Linear failures already counted in _handle_linear_event
                        if getattr(event, "source", None) != "linear":
                            self.metrics.record_error()
                except Exception as exc:  # pragma: no cover - defensive
                    logger.error("Event %s processing error: %s", event.id, exc)
                    await self._mark_failed(session, event, str(exc))
                    self.metrics.record_error()

                processed += 1

            self.metrics.record_batch(time.time() - batch_start)
            return processed

    def _parse_payload(self, payload: Any) -> Dict[str, Any]:
        """Normalize payload into a dictionary, handling bytes/str gracefully."""

        if payload is None:
            return {}

        if isinstance(payload, dict):
            return payload

        try:
            if isinstance(payload, bytes):
                return json.loads(payload.decode("utf-8"))
            if isinstance(payload, str):
                return json.loads(payload)
        except Exception:
            logger.warning("Failed to parse payload as JSON; returning empty dict")
            return {}

        return {}

    async def _dispatch(self, event: RawWebhookEvent, payload: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Dispatch event to the appropriate handler and capture error message."""

        source = getattr(event, "source", None)
        if source == "linear":
            return await self._handle_linear_event(event, payload)

        handler = self._handlers.get(source or "")
        if not handler:
            logger.warning("No handler registered for source '%s'", source)
            return False, f"No handler for source '{source}'"

        try:
            result = handler(payload)
            if asyncio.iscoroutine(result):
                result = await result
            return bool(result), None if result else "Handler returned False"
        except Exception as exc:  # pragma: no cover
            logger.error("Handler for source %s raised: %s", source, exc)
            return False, str(exc)

    async def _handle_linear_event(
        self, event: RawWebhookEvent, payload: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Handle Linear events via the domain processor."""

        try:
            linear_processor = get_linear_processor()
            result = linear_processor.process_single_event(payload)
            if asyncio.iscoroutine(result):
                result = await result
            if result:
                self.metrics.record_processed()
                return True, None
            return False, "Handler returned False"
        except Exception as exc:
            logger.error("Linear event %s failed: %s", getattr(event, "id", "<no id>"), exc)
            self.metrics.record_error()
            return False, str(exc)

    async def _mark_complete(self, session: Any, event: RawWebhookEvent) -> None:
        event.processed_status = True
        event.error_log = None
        await session.commit()

    async def _mark_failed(
        self, session: Any, event: RawWebhookEvent, error_message: Optional[str]
    ) -> None:
        event.processed_status = True
        if error_message:
            event.error_log = (error_message or "Unknown Error")[:1000]
        else:
            event.error_log = "Unknown Error"
        await session.commit()