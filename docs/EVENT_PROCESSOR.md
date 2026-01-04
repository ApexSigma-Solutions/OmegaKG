# Event Processor Documentation (TN-103)

**Version:** 1.0  
**Created:** 2025-12-26  
**Status:** Complete

---

## Overview

The Event Processor is an asynchronous background worker that decouples webhook ingestion from business logic processing. It polls the `raw_webhook_events` table for unprocessed events, routes them to appropriate domain handlers based on source (Linear, GitHub, etc.), and updates their processing status.

### Key Features

- **Decoupled Architecture**: Webhook receipt is fast; processing happens asynchronously
- **At-Least-Once Processing**: Events are processed at least once with error recovery
- **Scalability**: Supports multiple event sources through polymorphic design
- **Observability**: Comprehensive logging and metrics for monitoring
- **Graceful Shutdown**: Proper cleanup of resources on application shutdown

---

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Application                    │
│  ┌────────────────────────────────────────────────────┐  │
│  │         Lifespan Manager               │  │
│  │  ┌──────────────────────────────────────┐  │  │
│  │  │  Event Processor (Worker)    │  │  │
│  │  │  ┌────────────────────────────┐  │  │  │
│  │  │  │ Event Router           │  │  │  │
│  │  │  │  ┌────────────────────┐  │  │  │
│  │  │  │  │ Linear Handler   │  │  │  │
│  │  │  │  └────────────────────┘  │  │  │
│  │  │  └────────────────────────────┐  │  │  │
│  │  │  │ GitHub Handler   │  │  │  │
│  │  │  │  (Future)          │  │  │  │
│  │  │  └────────────────────┘  │  │  │
│  │  └────────────────────────────────────┘  │  │  │
│  └────────────────────────────────────────────────────┘  │  │
└─────────────────────────────────────────────────────────────────┘
│                                                   │
│  ┌──────────────────────────────────────────────┐  │
│  │         Domain Layer                   │  │
│  │  ┌────────────────────────────────────┐  │  │
│  │  │  │ Linear Processor      │  │  │
│  │  │  │  Graph Writer        │  │  │
│  │  │  │  Embedding Service   │  │  │
│  │  │  │  Mapper             │  │  │
│  │  │  └────────────────────────────┘  │  │
│  └──────────────────────────────────────────────┘  │
│                                                   │
│  ┌──────────────────────────────────────────────┐  │
│  │         Storage Layer                  │  │
│  │  ┌────────────────────────────────────┐  │  │
│  │  │  │ PostgreSQL (Events)   │  │  │
│  │  │  │ Neo4j (Graph)       │  │  │
│  │  │  │ Obsidian Vault      │  │  │
│  │  │  └────────────────────────────┘  │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Webhook Receipt**: External service sends webhook → FastAPI endpoint
2. **Event Storage**: Webhook receiver stores raw event in `raw_webhook_events` table
3. **Event Polling**: Event Processor polls for `processed_status=False` events
4. **Event Routing**: Event Processor routes to appropriate handler based on `source` field
5. **Domain Processing**: Handler processes event (Linear → markdown, graph, embeddings)
6. **Status Update**: Event Processor updates `processed_status=True` and `error_log` if failed

---

## Configuration

### Environment Variables

| Variable | Type | Default | Description |
|-----------|------|---------|-------------|
| `WEBHOOK_POLL_INTERVAL` | float | 5.0 | Seconds between polling cycles |
| `WEBHOOK_BATCH_SIZE` | int | 10 | Number of events to fetch per batch |
| `DATABASE_URL` | string | - | PostgreSQL connection string |
| `OBSIDIAN_VAULT_PATH` | string | `./vault` | Path to Obsidian vault |
| `NEO4J_URI` | string | `bolt://localhost:7687` | Neo4j connection URI |
| `LOG_LEVEL` | string | `INFO` | Logging level |

### Settings Module

Configuration is managed through [`omega_kg/settings.py`](../omega_kg/settings.py):

```python
# Event Processor Configuration
webhook_poll_interval: float = 5.0  # Seconds between polls
webhook_batch_size: int = 10  # Events per batch
```

---

## Components

### EventProcessor

**Location:** [`omega_kg/workers/event_processor.py`](../omega_kg/workers/event_processor.py)

**Key Classes:**

#### EventProcessor

Main worker class that implements the polling loop and event routing.

**Methods:**
- `start()`: Start the infinite polling loop
- `stop()`: Stop the polling loop gracefully
- `process_batch()`: Process a batch of pending events
- `_fetch_pending()`: Fetch unprocessed events with row locking
- `_dispatch()`: Route event to appropriate handler
- `_handle_linear_event()`: Process Linear webhook events
- `_parse_payload()`: Parse JSON payload from database format
- `_mark_complete()`: Mark event as successfully processed
- `_mark_failed()`: Mark event as failed with error details

#### EventProcessorMetrics

Tracks event processor metrics for monitoring and observability.

**Metrics:**
- `processed_total`: Total events processed successfully
- `errors_total`: Total processing errors
- `batches_total`: Total batches processed
- `last_batch_duration`: Duration of last batch (seconds)
- `uptime_seconds`: Processor uptime
- `processing_rate`: Events per second

### LinearProcessor

**Location:** [`omega_kg/domain/linear/processor.py`](../omega_kg/domain/linear/processor.py)

Domain processor for Linear webhook events. Accepts parsed JSON payloads and processes them.

**Methods:**
- `process_single_event(payload: dict) -> bool`: Process a single Linear webhook payload
- `_create_tnp_if_needed(issue)`: Create Task Note Plan if it doesn't exist
- `_generate_embedding(issue)`: Generate semantic embedding for issue
- `close()`: Close database connections and cleanup resources

**Singleton Access:**
- `get_linear_processor()`: Get singleton instance of LinearProcessor

---

## Database Schema

### RawWebhookEvent Table

```sql
CREATE TABLE raw_webhook_events (
    id SERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    received_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    processed_status BOOLEAN NOT NULL DEFAULT FALSE,
    headers JSONB NOT NULL,
    payload JSONB NOT NULL,
    event_type VARCHAR(100),
    error_log TEXT
);
```

### Indexes

```sql
-- Efficient querying for pending events
CREATE INDEX idx_raw_webhook_events_processed 
ON raw_webhook_events (processed_status, received_at);

-- Efficient querying by source
CREATE INDEX idx_raw_webhook_events_source 
ON raw_webhook_events (source, processed_status);
```

---

## Event Sources

### Linear

**Supported Event Types:**
- `Issue.created`: New issue created
- `Issue.updated`: Issue updated
- `Comment.created`: New comment created

**Processing Flow:**
1. Validate payload as `LinearWebhookPayload`
2. Extract `LinearIssue` from payload data
3. Map to Obsidian markdown file
4. Create Task Note Plan (.tnp.md) if needed
5. Generate semantic embedding
6. Upsert to Neo4j graph

### GitHub (Future)

**Planned Event Types:**
- `issues.opened`: Issue opened
- `issues.closed`: Issue closed
- `pull_request.opened`: PR opened
- `pull_request.closed`: PR closed

---

## Error Handling

### Error Classification

| Error Type | Handling | Retry |
|-------------|----------|-------|
| Validation Error | Log error, mark as failed, no retry | No |
| Handler Error | Log error, mark as failed, no retry | No |
| Database Error | Log error, apply backoff, retry next cycle | Yes |
| Network Error | Log error, apply backoff, retry next cycle | Yes |
| Unknown Source | Log warning, mark as failed, no retry | No |

### Error Logging Format

```python
logger.error(
    f"Event {event_id}: {error_type} - {error_message}",
    exc_info=True
)
```

---

## Monitoring

### Metrics

The EventProcessor tracks the following metrics:

```python
{
    "processed_total": 1234,
    "errors_total": 5,
    "batches_total": 124,
    "last_batch_duration": 0.45,
    "uptime_seconds": 3600.5,
    "processing_rate": 0.34
}
```

### Health Check

The health check endpoint includes event processor status:

```bash
curl http://localhost:8765/health
```

**Response:**
```json
{
    "status": "online",
    "version": "4.4.2",
    "database": "connected",
    "event_processor": "running"
}
```

### Logging

**Log Levels:**
- `DEBUG`: Detailed diagnostic information
- `INFO`: General operational information
- `WARNING`: Warning messages for potential issues
- `ERROR`: Error messages

**Structured Logging:**
```python
logger.info(
    f"EventProcessor metrics: "
    f"processed={stats['processed_total']}, "
    f"errors={stats['errors_total']}, "
    f"batches={stats['batches_total']}, "
    f"rate={stats['processing_rate']:.2f}/s"
)
```

---

## Testing

### Running Tests

**Unit Tests:**
```bash
# Run all unit tests
poetry run pytest tests/unit/test_event_processor.py -v
poetry run pytest tests/unit/test_linear_processor.py -v
```

**Integration Tests:**
```bash
# Run all integration tests
poetry run pytest tests/integration/test_event_processor_loop.py -v
```

**Test Coverage:**
```bash
# Run with coverage report
poetry run pytest --cov=omega_kg/workers tests/unit/test_event_processor.py --cov-report=html
```

---

## Troubleshooting

### Common Issues

#### Event Not Processing

**Symptoms:**
- Events remain in `processed_status=False`
- No error logs in database

**Diagnosis:**
1. Check event processor is running: `curl http://localhost:8765/health`
2. Check application logs for "Event Processor started"
3. Verify database connection: Check `DATABASE_URL` in environment

**Solutions:**
- Restart application
- Verify environment variables are set
- Check database is accessible

#### High Error Rate

**Symptoms:**
- Many events marked as failed
- `error_log` contains validation errors

**Diagnosis:**
1. Check webhook payload format
2. Verify Linear API credentials
3. Check Linear webhook secret matches

**Solutions:**
- Verify Linear webhook configuration
- Check Linear API key is valid
- Review webhook payload structure

#### Processing Delays

**Symptoms:**
- Events take long time to process
- Batch processing time > 30 seconds

**Diagnosis:**
1. Check Neo4j connection performance
2. Check embedding service availability
3. Check database query performance

**Solutions:**
- Increase `WEBHOOK_BATCH_SIZE` to reduce per-batch overhead
- Check Neo4j connection pool settings
- Verify embedding service is responsive

---

## Deployment

### Startup

The EventProcessor starts automatically when the FastAPI application starts via lifespan events.

**Startup Sequence:**
1. FastAPI application initializes
2. Lifespan manager creates EventProcessor instance
3. Background task created: `asyncio.create_task(event_processor.start())`
4. EventProcessor begins polling loop

### Shutdown

The EventProcessor stops gracefully when the FastAPI application shuts down.

**Shutdown Sequence:**
1. Lifespan manager calls `event_processor.stop()`
2. EventProcessor sets `running = False`
3. Polling loop exits on next iteration
4. Background task awaited with 10-second timeout
5. Resources cleaned up

### Manual Control

For manual control of the event processor:

```bash
# Check event processor status
curl http://localhost:8765/health

# View recent events
poetry run python -c "
from omega_kg.database.session import AsyncSessionLocal
from omega_kg.models.webhook import RawWebhookEvent
from sqlalchemy import select

async def check_events():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(RawWebhookEvent)
            .order_by(RawWebhookEvent.received_at.desc())
            .limit(10)
        )
        events = result.scalars().all()
        for event in events:
            print(f'ID: {event.id}, Source: {event.source}, '
                  f'Status: {\"Processed\" if event.processed_status else \"Pending\"}, '
                  f'Error: {event.error_log or \"None\"}')

import asyncio
asyncio.run(check_events())
"
```

---

## API Reference

### EventProcessor Class

```python
class EventProcessor:
    """Asynchronous event processor for webhook events."""
    
    def __init__(self) -> None:
        """Initialize event processor with handlers."""
        self.running = False
        self.metrics = EventProcessorMetrics()
        self.handlers = {
            'linear': self._handle_linear_event,
        }
        self.linear_processor = get_linear_processor()
    
    async def start(self) -> None:
        """Start the infinite polling loop."""
        self.running = True
        logger.info("Event Processor started")
        
        while self.running:
            try:
                processed_count = await self.process_batch()
                
                if processed_count > 0:
                    await asyncio.sleep(0.1)
                else:
                    await asyncio.sleep(settings.webhook_poll_interval)
                    
            except Exception as e:
                logger.error(f"Polling loop error: {e}", exc_info=True)
                await asyncio.sleep(5.0)
    
    async def stop(self) -> None:
        """Stop processor gracefully."""
        logger.info("Stopping EventProcessor...")
        self.running = False
```

### LinearProcessor Class

```python
class LinearProcessor:
    """Domain processor for Linear webhook events."""
    
    def __init__(self, vault_path: Optional[Path] = None) -> None:
        """Initialize LinearProcessor."""
        self.vault_path = Path(vault_path) if vault_path else Path(settings.obsidian_vault_path)
        self.graph_writer = GraphWriter(graph_driver)
        self.mapper = LinearToObsidianMapper(self.vault_path)
    
    async def process_single_event(self, payload: Dict[str, Any]) -> bool:
        """Process a single Linear webhook payload."""
        # Validate and parse payload
        # Map to Obsidian markdown
        # Create Task Note Plan if needed
        # Generate embedding
        # Sync to Neo4j
        return True  # or False on failure
```

---

## Related Documentation

- [Implementation Plan](../omegavault.as/01_Active/Implementation_Plan.md) - TN-103 Implementation Plan
- [Linear Domain Models](../omega_kg/domain/linear/models.py) - Linear data models
- [Graph Writer](../omega_kg/domain/linear/graph_writer.py) - Neo4j integration
- [Mapper](../omega_kg/domain/linear/mapper.py) - Obsidian markdown mapping
- [Settings](../omega_kg/settings.py) - Configuration management

---

## Changelog

### Version 1.0 (2025-12-26)

**Added:**
- EventProcessor worker with polling loop
- Event routing architecture with handler registry
- LinearProcessor domain processor refactored for payload-based processing
- EventProcessorMetrics for observability
- Lifespan integration with FastAPI
- Comprehensive unit and integration tests
- Complete documentation

---

## Support

For issues or questions about the Event Processor:

1. Check this documentation
2. Review logs in `logs/` directory
3. Run health check: `curl http://localhost:8765/health`
4. Check metrics in application logs

---

**Document End**
