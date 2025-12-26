# Implementation Plan: TN-103 - Asynchronous Event Processor

**Document Version:** 1.1  
**Created:** 2025-12-26  
**Status:** Draft  
**Target Directory:** D:\projects\OmegaKG\Omega_KG_stable

---

## Table of Contents

1. [Overview](#overview)
2. [Functional Requirements](#functional-requirements)
3. [Non-Functional Requirements](#non-functional-requirements)
4. [System Architecture](#system-architecture)
5. [Detailed Implementation Approaches](#detailed-implementation-approaches)
6. [Detailed Task Breakdown](#detailed-task-breakdown)
7. [Milestones and Timeline](#milestones-and-timeline)
8. [Risk Analysis](#risk-analysis)
9. [Testing Strategy](#testing-strategy)
10. [Deployment Considerations](#deployment-considerations)
11. [Success Criteria](#success-criteria)

---

## Overview

### Project Summary

TN-103 implements an asynchronous event processor service that decouples webhook ingestion from business logic processing. The "Refinery" component polls `raw_webhook_events` table for unprocessed events, routes them to appropriate domain handlers based on source (Linear, GitHub, etc.), and updates their processing status.

### Strategic Objectives

1. **Decoupling**: Separate fast webhook receipt from potentially slow processing logic
2. **Reliability**: Ensure at-least-once processing with error recovery
3. **Scalability**: Support multiple event sources through polymorphic design
4. **Observability**: Provide comprehensive logging and metrics for monitoring

### Scope

- **In Scope**: Event processor service, Linear handler integration, FastAPI lifespan integration
- **Out of Scope**: Additional source handlers (GitHub, etc.), separate microservice deployment, advanced retry mechanisms beyond basic error logging

### Dependencies

- **TN-102**: Raw webhook storage (RawWebhookEvent model) - COMPLETE
- **Existing Components**: Linear domain processor, Neo4j graph writer, embedding service

---

## Functional Requirements

### FR-1: Event Polling

The system shall poll the `raw_webhook_events` table at configurable intervals to retrieve unprocessed events.

**Acceptance Criteria:**
- Polling interval defaults to 5.0 seconds
- Polling interval is configurable via `WEBHOOK_POLL_INTERVAL` environment variable
- Only events with `processed_status=False` are retrieved
- Batch size is configurable via `WEBHOOK_BATCH_SIZE` (default: 10)

### FR-2: Event Routing

The system shall route events to appropriate handlers based on the `source` field.

**Acceptance Criteria:**
- Events with `source='linear'` are routed to Linear processor
- Unknown sources are logged and marked as failed
- Routing logic is extensible for future sources

### FR-3: Linear Event Processing

The system shall process Linear webhook events using existing domain logic.

**Acceptance Criteria:**
- Linear processor accepts parsed JSON payload as input
- Issue creation/update events are processed
- Comment creation events are processed
- Events are mapped to Obsidian markdown files
- Events are synced to Neo4j graph
- Embeddings are generated for semantic search

### FR-4: Status Management

The system shall update event status after processing attempts.

**Acceptance Criteria:**
- Successful processing sets `processed_status=True`
- Failed processing sets `processed_status=True` with error details in `error_log`
- Processing timestamp is recorded
- Failed events are not retried automatically (manual replay required)

### FR-5: Error Handling

The system shall handle errors gracefully without crashing the processing loop.

**Acceptance Criteria:**
- Individual event failures do not stop the loop
- Errors are logged with full stack traces
- Failed events are marked with error details
- Loop continues after error with configurable backoff

### FR-6: Lifecycle Management

The system shall integrate with FastAPI lifespan events for graceful startup and shutdown.

**Acceptance Criteria:**
- Event processor starts on application startup
- Event processor stops gracefully on application shutdown
- In-flight processing completes before shutdown
- Resources are properly released

---

## Non-Functional Requirements

### NFR-1: Performance

- **Polling Latency**: Maximum 5.0 seconds between polls (configurable)
- **Processing Throughput**: Support processing of 10 events per batch
- **API Impact**: Event processing must not block HTTP API endpoints
- **Database Load**: Use efficient queries with appropriate indexes

### NFR-2: Reliability

- **At-Least-Once Processing**: Events are processed at least once
- **Crash Recovery**: Worker restarts and continues processing after crash
- **No Data Loss**: Failed events are preserved in database
- **Graceful Degradation**: System continues operating with partial failures

### NFR-3: Scalability

- **Horizontal Scaling**: Design supports future separation into microservice
- **Multi-Source Support**: Architecture supports adding new event sources
- **Batch Processing**: Support for configurable batch sizes
- **Connection Pooling**: Efficient database connection management

### NFR-4: Maintainability

- **Code Organization**: Clear separation of concerns (worker, handlers, domain logic)
- **Documentation**: Comprehensive docstrings and inline comments
- **Configuration**: All tunable parameters exposed via environment variables
- **Logging**: Structured logging with appropriate log levels

### NFR-5: Observability

- **Metrics**: Track processed count, error count, batch processing time
- **Logging**: Detailed logs for debugging and monitoring
- **Health Checks**: Processor status visible in application logs
- **Error Tracking**: Failed events logged with full context

### NFR-6: Security

- **Input Validation**: Validate all webhook payloads before processing
- **Error Messages**: Do not expose sensitive information in error logs
- **Access Control**: Database access follows existing security model
- **Audit Trail**: All processing attempts are logged

---

## System Architecture

### High-Level Architecture

```mermaid
graph TB
    subgraph External
        A[Linear Webhook]
        B[GitHub Webhook]
    end
    
    subgraph FastAPI
        C[Webhook Receiver]
        D[RawWebhookEvent DB]
    end
    
    subgraph EventProcessor
        E[Polling Loop]
        F[Event Router]
        G[Linear Handler]
        H[GitHub Handler]
    end
    
    subgraph Domain
        I[Linear Processor]
        J[Graph Writer]
        K[Embedding Service]
    end
    
    subgraph Storage
        L[Neo4j Graph]
        M[Obsidian Vault]
    end
    
    A --> C
    B --> C
    C --> D
    E --> D
    E --> F
    F --> G
    F --> H
    G --> I
    I --> J
    I --> K
    J --> L
    I --> M
```

### Component Architecture

```mermaid
graph LR
    subgraph Application Layer
        A[FastAPI App]
        B[Lifespan Manager]
    end
    
    subgraph Worker Layer
        C[EventProcessor]
        D[EmbeddingWorker]
    end
    
    subgraph Handler Layer
        E[LinearHandler]
        F[GitHubHandler]
    end
    
    subgraph Domain Layer
        G[LinearProcessor]
        H[GraphWriter]
        I[EmbeddingService]
    end
    
    A --> B
    B --> C
    B --> D
    C --> E
    C --> F
    E --> G
    G --> H
    G --> I
```

### Data Flow

```mermaid
sequenceDiagram
    participant WH as Webhook
    participant EP as EventProcessor
    participant DB as Database
    participant LH as LinearHandler
    participant LP as LinearProcessor
    participant GW as GraphWriter
    participant ES as EmbeddingService
    participant NEO as Neo4j
    participant VAULT as Obsidian Vault
    
    WH->>DB: Store raw event
    EP->>DB: Poll for unprocessed events
    DB-->>EP: Return batch of events
    EP->>EP: Parse payload
    EP->>LH: Route to Linear handler
    LH->>LP: Process event
    LP->>LP: Map to markdown
    LP->>VAULT: Write markdown file
    LP->>ES: Generate embedding
    ES-->>LP: Return embedding
    LP->>GW: Upsert to graph
    GW->>NEO: Write node/edges
    NEO-->>GW: Success
    GW-->>LP: Success
    LP-->>LH: Success
    LH-->>EP: Success
    EP->>DB: Mark as processed
```

### Database Schema

```mermaid
erDiagram
    RAW_WEBHOOK_EVENTS {
        int id PK
        string source UK
        timestamp received_at
        boolean processed_status
        jsonb headers
        jsonb payload
        string event_type
        string error_log
    }
```

### Configuration Architecture

```mermaid
graph TB
    A[Environment Variables] --> B[Settings Module]
    B --> C[WEBHOOK_POLL_INTERVAL]
    B --> D[WEBHOOK_BATCH_SIZE]
    B --> E[Database Config]
    B --> F[Logging Config]
    
    C --> G[EventProcessor]
    D --> G
    E --> G
    F --> G
```

---

## Detailed Implementation Approaches

### Approach 1: Event Processor Polling Strategy

**Design Pattern:** Producer-Consumer with Database as Queue

The event processor implements a polling-based producer-consumer pattern where the database acts as a persistent queue. This approach provides durability and crash recovery without requiring external message queue infrastructure.

**Key Implementation Details:**

1. **Polling Loop Structure**
```python
async def start(self):
    """Starts the infinite polling loop."""
    self.running = True
    logger.info(f"🚀 Event Processor started. Polling every {settings.WEBHOOK_POLL_INTERVAL}s.")
    
    while self.running:
        try:
            processed_count = await self.process_batch()
            
            # Adaptive Sleep: If we did work, check again soon. If idle, sleep full interval.
            if processed_count == 0:
                await asyncio.sleep(settings.WEBHOOK_POLL_INTERVAL)
            else:
                await asyncio.sleep(0.1)  # Yield to event loop
                    
        except asyncio.CancelledError:
            logger.info("Event Processor task cancelled.")
            break
        except Exception as e:
            logger.error(f"Event Processor Loop Crash: {e}", exc_info=True)
            await asyncio.sleep(5.0)  # Backoff on crash
```

2. **Database Query with Row Locking**
```python
async def process_batch(self) -> int:
    """Atomic batch processing."""
    async with AsyncSessionLocal() as session:
        # 1. Fetch Pending (processed=False)
        query = select(RawWebhookEvent).where(
            RawWebhookEvent.processed == False
        ).limit(settings.WEBHOOK_BATCH_SIZE)
        
        result = await session.execute(query)
        events = result.scalars().all()
        
        if not events:
            return 0

        count = 0
        for event in events:
            success = False
            error_msg = None
            
            try:
                # 2. Router Logic (Strategy Pattern)
                handler = self._handlers.get(event.source)
                
                if not handler:
                    raise ValueError(f"No handler registered for source '{event.source}'")

                # 3. Parse & Execute
                # Handle bytes vs string payload
                raw_payload = event.payload
                if isinstance(raw_payload, bytes):
                    payload_dict = json.loads(raw_payload.decode('utf-8'))
                elif isinstance(raw_payload, str):
                    payload_dict = json.loads(raw_payload)
                else:
                    # Already dict?
                    payload_dict = raw_payload

                # Invoke Domain Processor
                success = handler(payload_dict)
                
                if not success:
                    error_msg = "Handler returned False (Processing Failed)"
                    
            except Exception as e:
                success = False
                error_msg = str(e)
                logger.error(f"Event {event.id} processing error: {e}")

            # 4. State Update (Atomic)
            event.processed = True
            event.processed_at = datetime.utcnow()
            
            if success:
                event.status = "COMPLETED"
            else:
                event.status = "FAILED"
                event.error_msg = error_msg
            
            count += 1
        
        # Commit batch status updates
        await session.commit()
        return count
```

3. **Error Handling Strategy**
- **Individual Event Errors**: Log error, mark as failed, continue processing
- **Batch Errors**: Log error, rollback transaction, continue loop
- **Loop Errors**: Log with stack trace, apply backoff, continue
- **Critical Errors**: Stop processor, alert via monitoring

---

### Approach 2: Event Routing Architecture

**Design Pattern:** Strategy Pattern with Handler Registry

The routing system uses a dictionary-based dispatcher that maps event sources to handler functions. This provides extensibility without modifying core routing logic.

**Key Implementation Details:**

1. **Handler Registry**
```python
class EventProcessor:
    def __init__(self):
        self.running = False
        # Registry: Source String -> Handler Function
        self._handlers: Dict[str, Callable[[Dict[str, Any]], bool]] = {}
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Registers known domain processors."""
        linear = get_linear_processor()
        self.register_handler("linear", linear.process_single_event)
        # Future: self.register_handler("github", github.process_event)
    
    def register_handler(self, source: str, handler: Callable[[Dict[str, Any]], bool]):
        """Allows dynamic registration of new webhook sources."""
        self._handlers[source] = handler
        logger.info(f"EventProcessor: Registered handler for source '{source}'")
```

2. **Linear Handler Implementation**
```python
async def _handle_linear_event(self, event: RawWebhookEvent, payload: dict) -> bool:
    """Process Linear webhook event."""
    try:
        # Parse payload to validate structure
        webhook_payload = LinearWebhookPayload.model_validate(payload)
        
        # Extract event type for routing
        event_type = webhook_payload.type
        action = webhook_payload.action
        
        logger.info(f"Processing Linear event: {event_type}.{action}")
        
        # Call domain processor (synchronous for now, can be async later)
        success = self.linear_processor.process_single_event(payload)
        
        return success
        
    except ValidationError as e:
        logger.error(f"Payload validation failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Linear handler error: {e}", exc_info=True)
        return False
```

---

### Approach 3: Status Management Pattern

**Design Pattern:** State Machine with Atomic Updates

Event status is managed through atomic database updates to ensure consistency and prevent race conditions.

**Key Implementation Details:**

1. **Status Update Methods**
```python
async def mark_complete(self, session: AsyncSession, event: RawWebhookEvent) -> None:
    """Mark event as successfully processed."""
    event.processed_status = True
    event.error_log = None
    # Optional: Add processed_at timestamp if column exists
    # event.processed_at = datetime.utcnow()
    
    await session.commit()

async def mark_failed(self, session: AsyncSession, event: RawWebhookEvent, error: str) -> None:
    """Mark event as failed with error details."""
    event.processed_status = True  # Mark as processed to prevent retry loop
    event.error_log = error[:1000]  # Truncate to prevent oversized logs
    
    await session.commit()
```

2. **Transaction Management**
```python
async def process_batch(self) -> int:
    """Process batch with transaction safety."""
    async with AsyncSessionLocal() as session:
        try:
            events = await self.fetch_pending(session)
            
            if not events:
                return 0
            
            processed_count = 0
            for event in events:
                try:
                    payload = self._parse_payload(event.payload)
                    success = await self.dispatch(event, payload)
                    
                    if success:
                        await self.mark_complete(session, event)
                    else:
                        await self.mark_failed(session, event, "Handler returned False")
                    
                    processed_count += 1
                    
                except Exception as e:
                    await self.mark_failed(session, event, str(e))
                    processed_count += 1
            
            return processed_count
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Batch processing failed: {e}", exc_info=True)
            return 0
```

---

### Approach 4: Linear Processor Refactoring

**Design Pattern:** Pure Function with Dependency Injection

The Linear processor is refactored to accept parsed JSON payload instead of querying the database, making it a pure function that can be tested independently.

**Key Implementation Details:**

1. **Processor Class Structure**
```python
class LinearProcessor:
    """Domain processor for Linear webhook events.
    
    This processor is decoupled from database and HTTP layers,
    making it testable and reusable.
    """
    
    def __init__(self):
        self.graph_writer = GraphWriter(graph_driver)
        self.mapper = LinearToObsidianMapper(vault_path)
    
    def process_single_event(self, payload: Dict[str, Any]) -> bool:
        """Process a single Linear webhook payload.
        
        Args:
            payload: Parsed JSON dictionary from webhook
            
        Returns:
            bool: True if processed successfully, False otherwise
        """
        try:
            # Validate and parse payload
            webhook_payload = LinearWebhookPayload.model_validate(payload)
            
            # Skip if no data
            if not webhook_payload.data:
                logger.debug("Event has no data, skipping")
                return True
            
            # Extract issue
            issue = LinearIssue.model_validate(webhook_payload.data)
            
            # Step 1: Map to Obsidian markdown
            file_path, markdown_content = self.mapper.map_issue_to_markdown(issue)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(markdown_content, encoding="utf-8")
            
            # Step 2: Create Task Note Plan if needed
            self._create_tnp_if_needed(issue)
            
            # Step 3: Generate embedding (non-blocking)
            embedding = self._generate_embedding(issue)
            
            # Step 4: Sync to Neo4j
            self.graph_writer.upsert_issue(issue, embedding=embedding)
            
            logger.info(f"Successfully processed Linear issue: {issue.identifier}")
            return True
            
        except ValidationError as e:
            logger.error(f"Payload validation failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Processing failed: {e}", exc_info=True)
            return False
```

2. **Embedding Generation**
```python
def _generate_embedding(self, issue: LinearIssue) -> Optional[List[float]]:
    """Generate semantic embedding for issue.
    
    Non-blocking: Returns None on failure rather than raising.
    """
    payload = f"{issue.title}"
    if issue.description:
        payload += f" {issue.description}"
    
    try:
        embedding = asyncio.run(generate_embedding(payload))
        logger.debug(f"Generated embedding for {issue.identifier}")
        return embedding
    except Exception as e:
        logger.warning(f"Embedding generation failed: {e}")
        return None
```

---

### Approach 5: Lifespan Integration

**Design Pattern:** Context Manager with Background Tasks

The event processor integrates with FastAPI's lifespan events to ensure proper startup and shutdown sequencing.

**Key Implementation Details:**

1. **Lifespan Context Manager**
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from omega_kg.workers.event_processor import EventProcessor

# Global processor instance
event_processor = EventProcessor()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    
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
    title="Omega KG",
    version="1.6.0",
    lifespan=lifespan
)
```

2. **Graceful Shutdown Handling**
```python
async def stop(self) -> None:
    """Stop processor gracefully."""
    logger.info("Stopping EventProcessor...")
    self.running = False
    
    # Wait for in-flight processing to complete
    # The loop will exit on next iteration
    # No need to wait for tasks as they complete within the loop
```

---

### Approach 6: Database Schema Considerations

**Design Pattern:** Minimal Schema with Status Tracking

The database schema uses minimal columns to track event processing state while maintaining flexibility for future enhancements.

**Schema Requirements:**

1. **Existing Columns (Verified)**
- `id`: Primary key
- `source`: Event source (linear, github, etc.)
- `received_at`: Timestamp when webhook was received
- `processed_status`: Boolean flag for processing state
- `headers`: JSONB of HTTP headers
- `payload`: JSONB of webhook payload
- `event_type`: String for event type (issue.created, etc.)
- `error_log`: String for error details

2. **Optional Enhancements (Future)**
- `processed_at`: Timestamp when processing completed
- `retry_count`: Integer for tracking retry attempts
- `status`: Enum (PENDING, PROCESSING, COMPLETED, FAILED)

3. **Index Requirements**
```sql
-- Ensure efficient querying for pending events
CREATE INDEX idx_raw_webhook_events_processed 
ON raw_webhook_events (processed_status, received_at);

-- Ensure efficient querying by source
CREATE INDEX idx_raw_webhook_events_source 
ON raw_webhook_events (source, processed_status);
```

---

### Approach 7: Error Handling and Logging

**Design Pattern:** Structured Logging with Context

All errors are logged with structured context to enable debugging and monitoring.

**Key Implementation Details:**

1. **Structured Logging**
```python
import logging
import json

logger = logging.getLogger(__name__)

def log_event_processing(event_id: int, source: str, status: str, error: str = None):
    """Log event processing with structured context."""
    log_data = {
        "event_id": event_id,
        "source": source,
        "status": status,
        "error": error
    }
    logger.info(json.dumps(log_data))
```

2. **Error Classification**
```python
class ProcessingError(Exception):
    """Base class for processing errors."""
    pass

class ValidationError(ProcessingError):
    """Payload validation failed."""
    pass

class HandlerError(ProcessingError):
    """Handler execution failed."""
    pass

class DatabaseError(ProcessingError):
    """Database operation failed."""
    pass
```

3. **Error Recovery Strategy**
```python
async def process_batch(self) -> int:
    """Process batch with error recovery."""
    try:
        # Main processing logic
        pass
    except ValidationError as e:
        # Validation errors: Don't retry, mark as failed
        await self.mark_failed(session, event, f"Validation: {e}")
    except DatabaseError as e:
        # Database errors: Log and retry next cycle
        logger.error(f"Database error: {e}")
        raise  # Let outer loop handle retry
    except HandlerError as e:
        # Handler errors: Mark as failed, continue
        await self.mark_failed(session, event, f"Handler: {e}")
    except Exception as e:
        # Unexpected errors: Log and mark as failed
        logger.error(f"Unexpected error: {e}", exc_info=True)
        await self.mark_failed(session, event, f"Unexpected: {e}")
```

---

### Approach 8: Metrics Collection

**Design Pattern:** Counter and Gauge Metrics

Metrics are collected using simple counters and gauges that can be exported to Prometheus or other monitoring systems.

**Key Implementation Details:**

1. **Metrics Class**
```python
class EventProcessorMetrics:
    """Track event processor metrics."""
    
    def __init__(self):
        self.processed_count = 0
        self.error_count = 0
        self.batch_count = 0
        self.last_batch_time = 0.0
        self.start_time = time.time()
    
    def record_processed(self):
        """Record successful processing."""
        self.processed_count += 1
    
    def record_error(self):
        """Record processing error."""
        self.error_count += 1
    
    def record_batch(self, duration: float):
        """Record batch processing."""
        self.batch_count += 1
        self.last_batch_time = duration
    
    def get_stats(self) -> dict:
        """Get current statistics."""
        uptime = time.time() - self.start_time
        return {
            "processed_total": self.processed_count,
            "errors_total": self.error_count,
            "batches_total": self.batch_count,
            "last_batch_duration": self.last_batch_time,
            "uptime_seconds": uptime,
            "processing_rate": self.processed_count / uptime if uptime > 0 else 0
        }
```

2. **Logging Metrics**
```python
def log_metrics(self):
    """Log current metrics."""
    stats = self.metrics.get_stats()
    logger.info(
        f"EventProcessor metrics: "
        f"processed={stats['processed_total']}, "
        f"errors={stats['errors_total']}, "
        f"batches={stats['batches_total']}, "
        f"rate={stats['processing_rate']:.2f}/s"
    )
```

---

## Deployment and Monitoring Configuration Examples

### Example 1: Production Environment Configuration

**File:** `.env` (production)

```bash
# ============================================================
# Omega KG - Production Environment Configuration
# ============================================================

# Database Configuration
DATABASE_URL=postgresql+asyncpg://omegakg:secure_password@prod-db.example.com:5432/omegakg_prod
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Event Processor Configuration (TN-103)
WEBHOOK_POLL_INTERVAL=5.0
WEBHOOK_BATCH_SIZE=10
WEBHOOK_MAX_RETRIES=3

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=/var/log/omega_kg/event_processor.log

# Linear Integration
LINEAR_WEBHOOK_SECRET=prod_secret_key_here
LINEAR_API_KEY=prod_api_key_here
LINEAR_TEAM_ID=team_abc123

# Neo4j Configuration
NEO4J_URI=bolt://prod-neo4j.example.com:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=secure_password_here
NEO4J_MAX_CONNECTION_LIFETIME=3600

# Embedding Service Configuration
OLLAMA_BASE_URL=http://ollama-service.internal:11434
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_TIMEOUT=30
EMBEDDING_DIMENSIONS=1024

# Obsidian Vault Configuration
OBSIDIAN_VAULT_PATH=/data/obsidian/vaults/production
OBSIDIAN_VAULT_NAME=Production Vault

# Monitoring Configuration
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090
GRAFANA_ENABLED=true
GRAFANA_PORT=3000
HEALTH_CHECK_INTERVAL=60
```

### Example 2: Staging Environment Configuration

**File:** `.env.staging`

```bash
# ============================================================
# Omega KG - Staging Environment Configuration
# ============================================================

# Database Configuration
DATABASE_URL=postgresql+asyncpg://omegakg:staging_password@staging-db.example.com:5432/omegakg_staging
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=5

# Event Processor Configuration (TN-103)
WEBHOOK_POLL_INTERVAL=2.0
WEBHOOK_BATCH_SIZE=5
WEBHOOK_MAX_RETRIES=3

# Logging Configuration
LOG_LEVEL=DEBUG
LOG_FORMAT=json
LOG_FILE=/var/log/omega_kg/event_processor_staging.log

# Linear Integration
LINEAR_WEBHOOK_SECRET=staging_secret_key_here
LINEAR_API_KEY=staging_api_key_here
LINEAR_TEAM_ID=team_staging123

# Neo4j Configuration
NEO4J_URI=bolt://staging-neo4j.example.com:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=staging_password_here
NEO4J_MAX_CONNECTION_LIFETIME=1800

# Embedding Service Configuration
OLLAMA_BASE_URL=http://localhost:11434
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_TIMEOUT=30
EMBEDDING_DIMENSIONS=1024

# Obsidian Vault Configuration
OBSIDIAN_VAULT_PATH=/data/obsidian/vaults/staging
OBSIDIAN_VAULT_NAME=Staging Vault

# Monitoring Configuration
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090
GRAFANA_ENABLED=true
GRAFANA_PORT=3000
HEALTH_CHECK_INTERVAL=30
```

### Example 3: Docker Compose Configuration

**File:** `docker-compose.yml`

```yaml
version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    container_name: omega_kg_postgres
    environment:
      POSTGRES_USER: omegakg
      POSTGRES_PASSWORD: ${DATABASE_PASSWORD}
      POSTGRES_DB: omegakg
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U omegakg"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Neo4j Graph Database
  neo4j:
    image: neo4j:5.15-community
    container_name: omega_kg_neo4j
    environment:
      NEO4J_AUTH: neo4j/${NEO4J_PASSWORD}
      NEO4J_dbms.connector.bolt.thread_pool_max_size: 50
    ports:
      - "7687:7687"
      - "7474:7474"
    volumes:
      - neo4j_data:/data
    healthcheck:
      test: ["CMD-SHELL", "wget --spider-bots=off --tries=10 --waitretry=10 http://localhost:7474 || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 5

  # Ollama Embedding Service
  ollama:
    image: ollama/ollama:latest
    container_name: omega_kg_ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    environment:
      OLLAMA_MODELS: nomic-embed-text
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:11434/api/generate || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Omega KG Application
  omega_kg:
    build: .
    container_name: omega_kg_app
    depends_on:
      - postgres
      - neo4j
      - ollama
    environment:
      - DATABASE_URL=postgresql+asyncpg://omegakg:${DATABASE_PASSWORD}@postgres:5432/omegakg
      - NEO4J_URI=bolt://neo4j:${NEO4J_PASSWORD}@neo4j:7687
      - OLLAMA_BASE_URL=http://ollama:11434
      - WEBHOOK_POLL_INTERVAL=${WEBHOOK_POLL_INTERVAL:-5.0}
      - WEBHOOK_BATCH_SIZE=${WEBHOOK_BATCH_SIZE:-10}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    ports:
      - "8000:8000"
    volumes:
      - ./logs:/app/logs
      - ./data/obsidian:/app/vault
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Prometheus Monitoring
  prometheus:
    image: prom/prometheus:latest
    container_name: omega_kg_prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus:/etc/prometheus
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=200h'
      - '--web.enable-lifecycle'

  # Grafana Dashboard
  grafana:
    image: grafana/grafana:latest
    container_name: omega_kg_grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD:-admin}
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning
      - ./monitoring/grafana/dashboards:/var/lib/grafana/dashboards

volumes:
  postgres_data:
  neo4j_data:
  ollama_data:
  prometheus_data:
  grafana_data:
```

### Example 4: Prometheus Configuration

**File:** `monitoring/prometheus/prometheus.yml`

```yaml
# ============================================================
# Prometheus Configuration for Omega KG Event Processor
# ============================================================

global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'omega-kg'
    environment: 'production'

scrape_configs:
  - job_name: 'omega_kg_app'
    static_configs:
      - targets: ['omega_kg:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s

  - job_name: 'postgres_exporter'
    static_configs:
      - targets: ['postgres_exporter:9187']
    scrape_interval: 30s

  - job_name: 'neo4j_exporter'
    static_configs:
      - targets: ['neo4j:2004']
    scrape_interval: 30s

  - job_name: 'node_exporter'
    static_configs:
      - targets: ['localhost:9100']
    scrape_interval: 15s
```

### Example 5: Prometheus Alerting Rules

**File:** `monitoring/prometheus/event_processor_rules.yml`

```yaml
# ============================================================
# Alerting Rules for Omega KG Event Processor
# ============================================================

groups:
  - name: event_processor_alerts
    interval: 30s
    rules:
      # High Error Rate Alert
      - alert: HighErrorRate
        expr: |
          rate(event_processor_errors_total[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
          service: event_processor
        annotations:
          summary: "Event processor error rate is too high"
          description: "More than 5% of events are failing over the last 5 minutes"

      # Processing Latency Alert
      - alert: HighProcessingLatency
        expr: |
          histogram_quantile(0.95, event_processing_duration_seconds[5m]) > 30
        for: 5m
        labels:
          severity: warning
          service: event_processor
        annotations:
          summary: "Event processing latency is too high"
          description: "95th percentile of event processing time exceeds 30 seconds"

      # Processor Not Running Alert
      - alert: EventProcessorDown
        expr: |
          up{job="omega_kg_app"} == 0
        for: 1m
        labels:
          severity: critical
          service: event_processor
        annotations:
          summary: "Event processor is not running"
          description: "The event processor service is down"

      # Database Connection Pool Exhaustion
      - alert: DatabaseConnectionPoolExhaustion
        expr: |
          pg_stat_activity_count{datname="omegakg"} / pg_settings_max_connections > 0.8
        for: 2m
        labels:
          severity: warning
          service: database
        annotations:
          summary: "Database connection pool is nearly exhausted"
          description: "More than 80% of database connections are in use"

      # Memory Usage Alert
      - alert: HighMemoryUsage
        expr: |
          process_resident_memory_bytes{job="omega_kg_app"} / 1024 / 1024 > 1073741824
        for: 5m
        labels:
          severity: warning
          service: event_processor
        annotations:
          summary: "Event processor memory usage is high"
          description: "Memory usage exceeds 1GB"

      # No Events Processed Alert
      - alert: NoEventsProcessed
        expr: |
          increase(event_processor_processed_total[10m]) == 0
        for: 10m
        labels:
          severity: info
          service: event_processor
        annotations:
          summary: "No events processed in last 10 minutes"
          description: "Event processor has not processed any events in the last 10 minutes"
```

### Example 6: Grafana Dashboard Configuration

**File:** `monitoring/grafana/dashboards/event_processor.json`

```json
{
  "dashboard": {
    "title": "Omega KG Event Processor",
    "tags": ["omega-kg", "event-processor"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "Event Processing Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(event_processor_processed_total[5m])",
            "legendFormat": "{{rate}} events/sec",
            "refId": "processingRate"
          }
        ],
        "gridPos": { "h": 0, "v": 0 },
        "width": 12,
        "height": 8,
        "datasource": "Prometheus",
        "fieldConfig": {
          "defaults": {
            "custom": {
              "lineWidth": 2,
              "fillOpacity": 0.1
            }
          }
        }
      },
      {
        "id": 2,
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(event_processor_errors_total[5m])",
            "legendFormat": "{{rate}} errors/sec",
            "refId": "errorRate"
          }
        ],
        "gridPos": { "h": 0, "v": 8 },
        "width": 12,
        "height": 8,
        "datasource": "Prometheus",
        "fieldConfig": {
          "defaults": {
            "custom": {
              "lineWidth": 2,
              "fillOpacity": 0.1
            }
          }
        }
      },
      {
        "id": 3,
        "title": "Processing Latency",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, event_processing_duration_seconds[5m])",
            "legendFormat": "{{value}}s",
            "refId": "latency"
          }
        ],
        "gridPos": { "h": 8, "v": 0 },
        "width": 12,
        "height": 8,
        "datasource": "Prometheus",
        "fieldConfig": {
          "defaults": {
            "custom": {
              "lineWidth": 2,
              "fillOpacity": 0.1
            }
          }
        }
      },
      {
        "id": 4,
        "title": "Batch Processing Time",
        "type": "graph",
        "targets": [
          {
            "expr": "event_batch_duration_seconds",
            "legendFormat": "{{value}}s",
            "refId": "batchTime"
          }
        ],
        "gridPos": { "h": 8, "v": 0 },
        "width": 12,
        "height": 8,
        "datasource": "Prometheus",
        "fieldConfig": {
          "defaults": {
            "custom": {
              "lineWidth": 2,
              "fillOpacity": 0.1
            }
          }
        }
      },
      {
        "id": 5,
        "title": "Database Connection Pool",
        "type": "gauge",
        "targets": [
          {
            "expr": "pg_stat_activity_count{datname=\"omegakg\"} / pg_settings_max_connections",
            "legendFormat": "{{value}}",
            "refId": "dbPool"
          }
        ],
        "gridPos": { "h": 8, "v": 16 },
        "width": 6,
        "height": 8,
        "datasource": "Prometheus",
        "fieldConfig": {
          "defaults": {
            "thresholds": {
              "steps": [
                0.5,
                0.7,
                0.9
              ]
            }
          }
        }
      },
      {
        "id": 6,
        "title": "Memory Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "process_resident_memory_bytes{job=\"omega_kg_app\"} / 1024 / 1024 / 1024",
            "legendFormat": "{{value}} GB",
            "refId": "memory"
          }
        ],
        "gridPos": { "h": 16, "v": 16 },
        "width": 12,
        "height": 8,
        "datasource": "Prometheus",
        "fieldConfig": {
          "defaults": {
            "custom": {
              "lineWidth": 2,
              "fillOpacity": 0.1
            }
          }
        }
      }
    ]
  }
}
```

### Example 7: Systemd Service Configuration

**File:** `/etc/systemd/system/omega-kg-event-processor.service`

```ini
[Unit]
Description=Omega KG Event Processor Service
After=network.target postgresql.service neo4j.service ollama.service
Wants=network.target postgresql.service neo4j.service ollama.service

[Service]
Type=simple
User=omegakg
Group=omegakg
WorkingDirectory=/opt/omega-kg
Environment="PATH=/opt/omega-kg/venv/bin"
EnvironmentFile=/opt/omega-kg/.env
ExecStart=/opt/omega-kg/venv/bin/python -m omega_kg.workers.event_processor
ExecStop=/bin/kill -TERM $MAINPID
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=omega-kg-event-processor

[Install]
WantedBy=multi-user.target
```

### Example 8: Kubernetes Deployment Configuration

**File:** `k8s/deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: omega-kg-event-processor
  namespace: omega-kg
  labels:
    app: omega-kg
    component: event-processor
spec:
  replicas: 2
  selector:
    matchLabels:
      app: omega-kg
      component: event-processor
  template:
    metadata:
      labels:
        app: omega-kg
        component: event-processor
    spec:
      containers:
      - name: omega-kg-app
        image: omega-kg:latest
        ports:
          - containerPort: 8000
            name: http
        env:
          - name: DATABASE_URL
            valueFrom:
              secretKeyRef:
                name: omega-kg-db-url
          - name: WEBHOOK_POLL_INTERVAL
            value: "5.0"
          - name: WEBHOOK_BATCH_SIZE
            value: "10"
          - name: LOG_LEVEL
            value: "INFO"
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        volumeMounts:
          - name: logs
            mountPath: /app/logs
          - name: vault
            mountPath: /app/vault
      volumes:
      - name: logs
        persistentVolumeClaim:
          claimName: omega-kg-logs
      - name: vault
        persistentVolumeClaim:
          claimName: omega-kg-vault
---
apiVersion: v1
kind: Service
metadata:
  name: omega-kg-event-processor
  namespace: omega-kg
spec:
  selector:
    app: omega-kg
    component: event-processor
  ports:
    - protocol: TCP
      port: 8000
      targetPort: 8000
  type: ClusterIP
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: omega-kg-event-processor-hpa
  namespace: omega-kg
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: omega-kg-event-processor
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Example 9: Health Check Endpoint

**File:** `omega_kg/routers/health.py` (NEW)

```python
from fastapi import APIRouter, HTTPException
from datetime import datetime
from omega_kg.workers.event_processor import event_processor

router = APIRouter(prefix="/health")

@router.get("/")
async def health_check():
    """
    Health check endpoint for monitoring.
    
    Returns overall system health status including:
    - Application status
    - Event processor status
    - Database connectivity
    - Neo4j connectivity
    - Ollama service availability
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }
    
    # Check Event Processor Status
    try:
        health_status["checks"]["event_processor"] = {
            "status": "running" if event_processor.running else "stopped",
            "uptime_seconds": time.time() - event_processor.start_time if hasattr(event_processor, 'start_time') else 0
        }
    except Exception as e:
        health_status["checks"]["event_processor"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "unhealthy"
    
    # Check Database Connectivity
    try:
        from omega_kg.database.session import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            await session.execute("SELECT 1")
        health_status["checks"]["database"] = {
            "status": "healthy",
            "message": "Database connection successful"
        }
    except Exception as e:
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "unhealthy"
    
    # Check Neo4j Connectivity
    try:
        from omega_kg.database.graph import graph_driver
        async with graph_driver.session() as session:
            await session.run("RETURN 1")
        health_status["checks"]["neo4j"] = {
            "status": "healthy",
            "message": "Neo4j connection successful"
        }
    except Exception as e:
        health_status["checks"]["neo4j"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "unhealthy"
    
    # Check Ollama Service
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.OLLAMA_BASE_URL}/api/tags",
                timeout=5.0
            )
        health_status["checks"]["ollama"] = {
            "status": "healthy" if response.status_code == 200 else "unhealthy",
            "message": "Ollama service is accessible"
        }
    except Exception as e:
        health_status["checks"]["ollama"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "unhealthy"
    
    # Determine overall status
    all_healthy = all(
        check["status"] == "healthy"
        for check in health_status["checks"].values()
    )
    
    if not all_healthy:
        health_status["status"] = "degraded"
    
    # Return appropriate status code
    status_code = 200 if all_healthy else 503
    raise HTTPException(status_code=status_code, detail=health_status)
```

### Example 10: Log Rotation Configuration

**File:** `/etc/logrotate.d/omega-kg-event-processor`

```bash
# ============================================================
# Log Rotation Configuration for Omega KG Event Processor
# ============================================================

/var/log/omega_kg/event_processor.log {
    daily
    rotate 7
    missingok
    notifempty
    compress
    delaycompress
    copytruncate
    create 640
    dateext
    size 100M
}

/var/log/omega_kg/event_processor_error.log {
    daily
    rotate 7
    missingok
    notifempty
    compress
    delaycompress
    copytruncate
    create 640
    dateext
    size 50M
}
```

---

## Detailed Task Breakdown

### Task 1: Configuration Updates

**File:** `omega_kg/settings.py`

**Description:** Add webhook processor configuration settings to support configurable polling and batch processing.

**Subtasks:**
1. Add `WEBHOOK_POLL_INTERVAL: float = 5.0` to Settings class
2. Add `WEBHOOK_BATCH_SIZE: int = 10` to Settings class
3. Add `WEBHOOK_MAX_RETRIES: int = 3` to Settings class (future use)
4. Add documentation comments for new settings
5. Validate settings on initialization

**Dependencies:** None

**Deliverables:**
- Updated `settings.py` with new configuration parameters
- Documentation of configuration options

**Implementation Code:**
```python
# ... existing imports ...
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # ... existing settings ...

    # ----------------------------------------------------------------
    # WEBHOOK REFINERY SETTINGS (TN-103)
    # ----------------------------------------------------------------
    # Polling interval in seconds (Adaptive sleep baseline)
    WEBHOOK_POLL_INTERVAL: float = 5.0
    # Batch size for processing events
    WEBHOOK_BATCH_SIZE: int = 10
    # Max retries before marking as DEAD (Future use)
    WEBHOOK_MAX_RETRIES: int = 3

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
```

---

### Task 2: Domain Logic Refactor

**File:** `omega_kg/domain/linear/processor.py`

**Description:** Refactor existing Linear processor to accept parsed JSON payload instead of querying database directly, making it a pure function callable by event processor.

**Subtasks:**
1. Create `LinearProcessor` class with `process_single_event(payload: dict) -> bool` method
2. Extract payload parsing logic from existing `process_pending_events` function
3. Ensure method handles Issue and Comment events
4. Integrate with existing `GraphWriter` and embedding generation
5. Add comprehensive error handling and logging
6. Create singleton getter function `get_linear_processor()`

**Dependencies:** Task 1 (Configuration)

**Deliverables:**
- Refactored `LinearProcessor` class
- Updated imports and dependencies
- Unit tests for processor methods

**Implementation Code:**
```python
import logging
import json
from typing import Dict, Any
from omega_kg.domain.linear.mapper import map_linear_to_graph
from omega_kg.domain.linear.graph_writer import LinearGraphWriter
from omega_kg.neo4j_schema import get_driver

logger = logging.getLogger(__name__)

class LinearProcessor:
    """
    Domain service for processing Linear webhooks.
    Designed as a 'Strategy' for EventProcessor.
    """
    def __init__(self):
        # Dependency Injection of Graph Writer
        self.driver = get_driver()
        self.writer = LinearGraphWriter(self.driver)

    def process_single_event(self, payload: Dict[str, Any]) -> bool:
        """
        Pure function logic: Dict -> Graph Update.
        
        Args:
            payload: The decoded JSON dictionary from webhook.
            
        Returns:
            bool: True if processed successfully, False otherwise.
        """
        try:
            event_type = payload.get("type")
            action = payload.get("action")
            data = payload.get("data", {})
            
            logger.info(f"LinearProcessor: Processing {event_type}.{action} (ID: {data.get('id')})")

            # 1. Map to Graph Model
            graph_entities = map_linear_to_graph(payload)
            
            if not graph_entities:
                logger.info(f"LinearProcessor: No graph entities mapped for {event_type}.{action}. Skipping.")
                return True  # Successful 'no-op'

            # 2. Write to Neo4j (Atomic Graph Updates)
            for entity in graph_entities:
                self.writer.upsert_entity(entity)
                
            return True

        except Exception as e:
            logger.error(f"LinearProcessor Error: {e}", exc_info=True)
            # We return False to signal to EventProcessor to mark this as FAILED
            return False

    def close(self):
        if self.driver:
            self.driver.close()

# Singleton for Registry
_processor = None

def get_linear_processor():
    global _processor
    if not _processor:
        _processor = LinearProcessor()
    return _processor
```

---

### Task 3: Event Processor Worker

**File:** `omega_kg/workers/event_processor.py` (NEW)

**Description:** Create core EventProcessor class that implements polling loop, event routing, and status management.

**Subtasks:**
1. Create `EventProcessor` class with lifecycle methods
2. Implement `start()` method with infinite polling loop
3. Implement `stop()` method for graceful shutdown
4. Implement `fetch_pending()` method to query database
5. Implement `dispatch()` method for event routing
6. Implement `mark_complete()` and `mark_failed()` methods
7. Add batch processing logic with configurable batch size
8. Implement error handling with backoff strategy
9. Add metrics tracking (processed count, error count, batch time)
10. Integrate with Linear processor

**Dependencies:** Task 1 (Configuration), Task 2 (Domain Refactor)

**Deliverables:**
- Complete `EventProcessor` class
- Comprehensive logging throughout
- Metrics collection

**Implementation Code:**
```python
import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, Callable, Any
from sqlalchemy import select
from omega_kg.database.session import AsyncSessionLocal
# Importing from models.webhook based on commit history
try:
    from omega_kg.models.webhook import RawWebhookEvent
except ImportError:
    # Fallback if user put it in linear.py
    from omega_kg.models.linear import RawWebhookEvent

from omega_kg.settings import settings
from omega_kg.domain.linear.processor import get_linear_processor

logger = logging.getLogger(__name__)

class EventProcessor:
    """
    TN-103: The Refinery.
    Implements a Producer-Consumer loop with a Strategy Pattern for routing.
    """
    def __init__(self):
        self.running = False
        # Registry: Source String -> Handler Function
        self._handlers: Dict[str, Callable[[Dict[str, Any]], bool]] = {}
        self._register_default_handlers()

    def _register_default_handlers(self):
        """Registers known domain processors."""
        linear = get_linear_processor()
        self.register_handler("linear", linear.process_single_event)
        # Future: self.register_handler("github", github.process_event)

    def register_handler(self, source: str, handler: Callable[[Dict[str, Any]], bool]):
        """Allows dynamic registration of new webhook sources."""
        self._handlers[source] = handler
        logger.info(f"EventProcessor: Registered handler for source '{source}'")

    async def start(self):
        """Starts the infinite polling loop."""
        self.running = True
        logger.info(f"🚀 Event Processor started. Polling every {settings.WEBHOOK_POLL_INTERVAL}s.")
        
        while self.running:
            try:
                processed_count = await self.process_batch()
                
                # Adaptive Sleep: If we did work, check again soon. If idle, sleep full interval.
                if processed_count == 0:
                    await asyncio.sleep(settings.WEBHOOK_POLL_INTERVAL)
                else:
                    await asyncio.sleep(0.1)  # Yield to event loop
                    
            except asyncio.CancelledError:
                logger.info("Event Processor task cancelled.")
                break
            except Exception as e:
                logger.error(f"Event Processor Loop Crash: {e}", exc_info=True)
                await asyncio.sleep(5.0)  # Backoff

    async def stop(self):
        """Graceful shutdown signal."""
        self.running = False
        logger.info("🛑 Event Processor stopping...")
        # Cleanup resources if needed
        get_linear_processor().close()

    async def process_batch(self) -> int:
        """Atomic batch processing."""
        async with AsyncSessionLocal() as session:
            # 1. Fetch Pending (processed=False)
            query = select(RawWebhookEvent).where(
                RawWebhookEvent.processed == False
            ).limit(settings.WEBHOOK_BATCH_SIZE)
            
            result = await session.execute(query)
            events = result.scalars().all()
            
            if not events:
                return 0

            count = 0
            for event in events:
                success = False
                error_msg = None
                
                try:
                    # 2. Router Logic (Strategy Pattern)
                    handler = self._handlers.get(event.source)
                    
                    if not handler:
                        raise ValueError(f"No handler registered for source '{event.source}'")

                    # 3. Parse & Execute
                    # Handle bytes vs string payload
                    raw_payload = event.payload
                    if isinstance(raw_payload, bytes):
                        payload_dict = json.loads(raw_payload.decode('utf-8'))
                    elif isinstance(raw_payload, str):
                        payload_dict = json.loads(raw_payload)
                    else:
                        # Already dict?
                        payload_dict = raw_payload

                    # Invoke Domain Processor
                    success = handler(payload_dict)
                    
                    if not success:
                        error_msg = "Handler returned False (Processing Failed)"
                    
                except Exception as e:
                    success = False
                    error_msg = str(e)
                    logger.error(f"Event {event.id} processing error: {e}")

                # 4. State Update (Atomic)
                event.processed = True
                event.processed_at = datetime.utcnow()
                
                if success:
                    event.status = "COMPLETED"
                else:
                    event.status = "FAILED"
                    event.error_msg = error_msg
                
                count += 1
            
            # Commit batch status updates
            await session.commit()
            return count
```

---

### Task 4: Lifespan Integration

**File:** `omega_kg/main.py`

**Description:** Integrate EventProcessor with FastAPI lifespan events for automatic startup and shutdown.

**Subtasks:**
1. Import `EventProcessor` and required modules
2. Create global `event_processor` instance
3. Update `lifespan` context manager
4. Add startup logic to create background task
5. Add shutdown logic to stop processor gracefully
6. Ensure proper cleanup of resources
7. Add logging for lifecycle events

**Dependencies:** Task 3 (Event Processor Worker)

**Deliverables:**
- Updated `main.py` with lifespan integration
- Graceful startup/shutdown behavior

**Implementation Code:**
```python
# ... imports ...
from contextlib import asynccontextmanager
from fastapi import FastAPI
from omega_kg.workers.event_processor import EventProcessor
# ... existing imports ...

# Global Singleton
event_processor = EventProcessor()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application Lifespan Manager.
    Handles startup/shutdown of background refineries.
    """
    logger.info("--- [Omega KG] Startup Sequence ---")
    
    # 1. Start Event Processor (The Refinery)
    # Run as a background task
    processor_task = asyncio.create_task(event_processor.start())
    logger.info("✅ Background Worker: EventProcessor launched.")

    yield
    
    logger.info("--- [Omega KG] Shutdown Sequence ---")
    
    # 2. Stop Event Processor
    await event_processor.stop()
    try:
        await processor_task
    except asyncio.CancelledError:
        pass
    logger.info("✅ Background Worker: EventProcessor stopped.")

app = FastAPI(
    title="Omega KG",
    version="1.6.0",  # Phase 2
    lifespan=lifespan
)

# ... routes ...
```

---

### Task 5: Database Model Verification

**File:** `omega_kg/models/webhook.py`

**Description:** Verify and update RawWebhookEvent model to support all required fields for event processing.

**Subtasks:**
1. Verify `processed_status` column exists
2. Verify `error_log` column exists
3. Verify `event_type` column exists
4. Add `processed_at` timestamp column if missing
5. Add `status` enum column (COMPLETED/FAILED) if needed
6. Create database migration if schema changes required
7. Test model with sample data

**Dependencies:** None

**Deliverables:**
- Verified/updated database model
- Migration script if needed
- Model validation tests

---

### Task 6: Integration Tests

**File:** `tests/integration/test_event_processor_loop.py` (NEW)

**Description:** Create comprehensive integration tests to verify end-to-end event processing flow.

**Subtasks:**
1. Test event insertion and retrieval
2. Test successful Linear event processing
3. Test failed event processing with error logging
4. Test batch processing with multiple events
5. Test unknown source handling
6. Test graceful shutdown
7. Test metrics tracking
8. Test concurrent processing scenarios

**Dependencies:** Task 3 (Event Processor Worker), Task 4 (Lifespan Integration)

**Deliverables:**
- Complete integration test suite
- Test fixtures and utilities
- Test documentation

**Implementation Code:**
```python
import pytest
import asyncio
import json
import uuid
from sqlalchemy import select
from omega_kg.database.session import AsyncSessionLocal
from omega_kg.models.linear import RawWebhookEvent
from omega_kg.workers.event_processor import EventProcessor

@pytest.mark.asyncio
async def test_event_processor_flow():
    """
    TN-103 Verification:
    1. Insert a dummy raw event.
    2. Run the processor for one cycle.
    3. Assert the event is marked processed.
    """
    # 1. Setup
    dummy_id = str(uuid.uuid4())
    dummy_payload = {
        "action": "create",
        "type": "Issue",
        "data": {"id": dummy_id, "title": "TN-103 Test Issue"}
    }
    
    async with AsyncSessionLocal() as session:
        event = RawWebhookEvent(
            id=dummy_id,
            source="linear",
            payload=json.dumps(dummy_payload).encode("utf-8"),
            processed=False
        )
        session.add(event)
        await session.commit()

    # 2. Run Processor
    processor = EventProcessor()
    # We don't use .start() because that loops forever.
    # We call .process_batch() directly for testing.
    count = await processor.process_batch()
    
    # 3. Verify
    assert count == 1, "Processor should have picked up exactly 1 event"
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(RawWebhookEvent).where(RawWebhookEvent.id == dummy_id))
        updated_event = result.scalar_one()
        
        assert updated_event.processed is True
        assert updated_event.status == "COMPLETED"
        assert updated_event.processed_at is not None
```

---

### Task 7: Unit Tests

**Files:** `tests/unit/test_event_processor.py`, `tests/unit/test_linear_processor.py` (NEW)

**Description:** Create unit tests for individual components to ensure correctness in isolation.

**Subtasks:**
1. Test EventProcessor initialization
2. Test event routing logic
3. Test status update methods
4. Test LinearProcessor with various payloads
5. Test error handling scenarios
6. Test configuration loading
7. Test metrics collection

**Dependencies:** Task 2 (Domain Refactor), Task 3 (Event Processor Worker)

**Deliverables:**
- Complete unit test suite
- Mock utilities for external dependencies
- Test coverage report

---

### Task 8: Documentation

**Files:** `docs/EVENT_PROCESSOR.md` (NEW), `README.md` (UPDATE)

**Description:** Create comprehensive documentation for the event processor system.

**Subtasks:**
1. Write architecture overview
2. Document configuration options
3. Create usage examples
4. Document API interfaces
5. Create troubleshooting guide
6. Update main README with event processor section
7. Add inline code documentation

**Dependencies:** All implementation tasks

**Deliverables:**
- Complete documentation suite
- Updated README
- Code comments and docstrings

---

### Task 9: Monitoring and Observability

**Files:** `monitoring/prometheus/event_processor_rules.yml` (NEW)

**Description:** Add monitoring and alerting rules for the event processor.

**Subtasks:**
1. Define Prometheus metrics for event processor
2. Create alerting rules for failure rates
3. Add Grafana dashboard configuration
4. Implement health check endpoint
5. Add structured logging with correlation IDs
6. Create monitoring documentation

**Dependencies:** Task 3 (Event Processor Worker)

**Deliverables:**
- Prometheus metrics configuration
- Alerting rules
- Monitoring documentation

---

### Task 10: Deployment Scripts

**Files:** `scripts/start-event-processor.sh` (NEW), `scripts/stop-event-processor.sh` (NEW)

**Description:** Create deployment and management scripts for the event processor.

**Subtasks:**
1. Create startup script with environment validation
2. Create shutdown script with graceful termination
3. Create status check script
4. Create log rotation configuration
5. Create systemd service file (if applicable)
6. Add script documentation

**Dependencies:** Task 4 (Lifespan Integration)

**Deliverables:**
- Deployment scripts
- Service configuration
- Script documentation

---

## Milestones and Timeline

### Milestone 1: Foundation (Tasks 1-2)

**Objective:** Establish configuration and refactor domain logic

**Tasks:**
- Task 1: Configuration Updates
- Task 2: Domain Logic Refactor

**Deliverables:**
- Updated settings module
- Refactored Linear processor
- Unit tests for refactored components

**Success Criteria:**
- Configuration loads correctly from environment
- Linear processor accepts parsed JSON payload
- Unit tests pass

---

### Milestone 2: Core Implementation (Tasks 3-5)

**Objective:** Implement event processor worker and integrate with application

**Tasks:**
- Task 3: Event Processor Worker
- Task 4: Lifespan Integration
- Task 5: Database Model Verification

**Deliverables:**
- Complete EventProcessor class
- Integrated lifespan management
- Verified database schema

**Success Criteria:**
- Event processor starts and stops gracefully
- Events are polled and routed correctly
- Database schema supports all operations

---

### Milestone 3: Testing (Tasks 6-7)

**Objective:** Ensure system correctness through comprehensive testing

**Tasks:**
- Task 6: Integration Tests
- Task 7: Unit Tests

**Deliverables:**
- Complete test suite
- Test coverage report
- Test documentation

**Success Criteria:**
- All tests pass
- Test coverage meets threshold (>80%)
- Integration tests verify end-to-end flow

---

### Milestone 4: Production Readiness (Tasks 8-10)

**Objective:** Prepare system for production deployment

**Tasks:**
- Task 8: Documentation
- Task 9: Monitoring and Observability
- Task 10: Deployment Scripts

**Deliverables:**
- Complete documentation
- Monitoring configuration
- Deployment scripts

**Success Criteria:**
- Documentation is comprehensive and accurate
- Monitoring and alerting are functional
- Deployment scripts work correctly

---

## Risk Analysis

### Risk 1: Database Connection Exhaustion

**Description:** Event processor may exhaust database connection pool under high load.

**Probability:** Medium  
**Impact:** High

**Mitigation Strategies:**
- Use connection pooling with appropriate limits
- Implement connection health checks
- Add backoff strategy on connection errors
- Monitor connection pool metrics

**Contingency Plan:**
- Increase connection pool size
- Implement circuit breaker pattern
- Scale database resources

---

### Risk 2: Processing Loop Blocking

**Description:** Long-running event processing may block the polling loop, causing delays.

**Probability:** Medium  
**Impact:** Medium

**Mitigation Strategies:**
- Use asyncio for non-blocking operations
- Implement timeout for individual event processing
- Use batch processing with reasonable limits
- Monitor batch processing times

**Contingency Plan:**
- Reduce batch size
- Implement parallel processing
- Add timeout enforcement

---

### Risk 3: Event Loss During Crash

**Description:** Events may be lost if application crashes during processing.

**Probability:** Low  
**Impact:** High

**Mitigation Strategies:**
- Mark events as processed only after successful completion
- Use database transactions for atomic updates
- Implement crash recovery logic
- Log all processing attempts

**Contingency Plan:**
- Manual replay of failed events
- Implement event replay mechanism
- Add data backup procedures

---

### Risk 4: Memory Leaks

**Description:** Long-running worker may accumulate memory over time.

**Probability:** Low  
**Impact:** Medium

**Mitigation Strategies:**
- Use memory profiling during development
- Implement periodic worker restart
- Monitor memory usage
- Use efficient data structures

**Contingency Plan:**
- Implement automatic restart on memory threshold
- Add memory limit enforcement
- Optimize memory usage

---

### Risk 5: Integration with Existing Code

**Description:** Refactoring existing Linear processor may break dependent code.

**Probability:** Medium  
**Impact:** Medium

**Mitigation Strategies:**
- Maintain backward compatibility
- Run comprehensive test suite before and after changes
- Use feature flags for gradual rollout
- Document all API changes

**Contingency Plan:**
- Rollback to previous version
- Fix compatibility issues
- Update dependent code

---

### Risk 6: Configuration Errors

**Description:** Incorrect configuration may cause unexpected behavior.

**Probability:** Medium  
**Impact:** Medium

**Mitigation Strategies:**
- Validate configuration on startup
- Provide sensible defaults
- Document all configuration options
- Add configuration examples

**Contingency Plan:**
- Fix configuration errors
- Add validation rules
- Improve documentation

---

## Testing Strategy

### Unit Testing

**Scope:** Individual components in isolation

**Tools:** pytest, pytest-asyncio, unittest.mock

**Coverage Target:** >80%

**Test Cases:**
- Configuration loading and validation
- EventProcessor initialization
- Event routing logic
- Status update methods
- LinearProcessor with various payloads
- Error handling scenarios
- Metrics collection

**Execution:** Run on every commit via CI/CD

---

### Integration Testing

**Scope:** End-to-end event processing flow

**Tools:** pytest, testcontainers, PostgreSQL, Neo4j

**Test Cases:**
- Event insertion and retrieval
- Successful Linear event processing
- Failed event processing with error logging
- Batch processing with multiple events
- Unknown source handling
- Graceful shutdown
- Concurrent processing scenarios
- Database transaction rollback on errors

**Execution:** Run on every pull request via CI/CD

---

### End-to-End Testing

**Scope:** Complete system with real webhooks

**Tools:** Postman, curl, Linear webhook simulator

**Test Cases:**
- Real Linear webhook receipt and processing
- Multiple concurrent webhooks
- Large payload handling
- Network failure scenarios
- Database failure scenarios
- Long-running processing scenarios

**Execution:** Run before major releases

---

### Performance Testing

**Scope:** System performance under load

**Tools:** locust, k6, Prometheus

**Test Cases:**
- Polling latency under various loads
- Processing throughput with batch sizes
- Database query performance
- Memory usage over time
- CPU utilization under load

**Execution:** Run before production deployment

---

### Security Testing

**Scope:** Security vulnerabilities and data protection

**Tools:** OWASP ZAP, bandit, safety

**Test Cases:**
- Input validation
- SQL injection prevention
- XSS prevention
- Authentication and authorization
- Error message information disclosure
- Logging of sensitive data

**Execution:** Run before production deployment

---

### Manual Testing

**Scope:** User acceptance testing

**Test Cases:**
- Verify event processing in production-like environment
- Test monitoring and alerting
- Verify documentation accuracy
- Test deployment scripts
- Verify rollback procedures

**Execution:** Run by QA team before release

---

## Deployment Considerations

### Environment Configuration

**Required Environment Variables:**
```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/omegakg

# Event Processor
WEBHOOK_POLL_INTERVAL=5.0
WEBHOOK_BATCH_SIZE=10

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Linear Integration
LINEAR_WEBHOOK_SECRET=your_secret_here
LINEAR_API_KEY=your_api_key_here

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# Embedding Service
OLLAMA_BASE_URL=http://localhost:11434
EMBEDDING_MODEL=nomic-embed-text
```

### Database Migrations

**Migration Steps:**
1. Backup existing database
2. Review migration scripts
3. Test migration in staging environment
4. Apply migration to production
5. Verify schema changes
6. Run data validation queries

**Rollback Plan:**
1. Stop application
2. Restore database from backup
3. Restart application
4. Verify system functionality

### Deployment Process

**Pre-Deployment Checklist:**
- [ ] All tests pass
- [ ] Code review approved
- [ ] Documentation updated
- [ ] Configuration validated
- [ ] Monitoring configured
- [ ] Rollback plan tested
- [ ] Stakeholders notified

**Deployment Steps:**
1. Create deployment branch
2. Merge to main branch
3. Build Docker image
4. Run database migrations
5. Deploy new version
6. Verify health checks
7. Monitor logs and metrics

**Post-Deployment Verification:**
- [ ] Application starts successfully
- [ ] Event processor is running
- [ ] Webhooks are being received
- [ ] Events are being processed
- [ ] No errors in logs
- [ ] Metrics are within normal ranges

### Monitoring and Alerting

**Key Metrics to Monitor:**
- Event processing rate (events/second)
- Processing latency (time from receipt to completion)
- Error rate (failed events / total events)
- Batch processing time
- Database connection pool usage
- Memory usage
- CPU utilization

**Alert Thresholds:**
- Error rate > 5% for 5 minutes
- Processing latency > 30 seconds
- Database connection pool > 80% utilization
- Memory usage > 80% of limit
- Event processor not running

### Rollback Procedure

**Trigger Conditions:**
- Critical errors in production
- Data corruption
- Performance degradation
- Security vulnerability discovered

**Rollback Steps:**
1. Stop current deployment
2. Restore previous version
3. Restore database if needed
4. Restart application
5. Verify system functionality
6. Notify stakeholders

---

## Success Criteria

### Functional Success

- [ ] Event processor successfully polls for unprocessed events
- [ ] Events are correctly routed to appropriate handlers
- [ ] Linear events are processed and synced to Neo4j
- [ ] Markdown files are created in Obsidian vault
- [ ] Embeddings are generated for semantic search
- [ ] Failed events are logged with error details
- [ ] Processing status is updated correctly

### Non-Functional Success

- [ ] Polling interval is configurable and respects settings
- [ ] Processing does not block HTTP API endpoints
- [ ] System handles errors gracefully without crashing
- [ ] Worker restarts and continues after crash
- [ ] No events are lost during processing
- [ ] System supports multiple event sources
- [ ] Metrics are collected and available for monitoring

### Quality Success

- [ ] Unit test coverage > 80%
- [ ] All integration tests pass
- [ ] Code follows project style guidelines
- [ ] Documentation is comprehensive and accurate
- [ ] No critical or high-severity security vulnerabilities
- [ ] Performance meets requirements

### Operational Success

- [ ] Deployment scripts work correctly
- [ ] Monitoring and alerting are functional
- [ ] Rollback procedure is tested and documented
- [ ] Team is trained on new system
- [ ] Stakeholders are satisfied with functionality

---

## Appendix

### A. File Structure

```
Omega_KG_stable/
├── omega_kg/
│   ├── workers/
│   │   ├── __init__.py
│   │   ├── event_processor.py          # NEW
│   │   └── embedding_worker.py         # EXISTING
│   ├── domain/
│   │   └── linear/
│   │       ├── processor.py             # MODIFIED
│   │       ├── mapper.py               # EXISTING
│   │       └── graph_writer.py        # EXISTING
│   ├── models/
│   │   └── webhook.py                 # VERIFIED
│   ├── settings.py                   # MODIFIED
│   └── main.py                       # MODIFIED
├── tests/
│   ├── unit/
│   │   ├── test_event_processor.py     # NEW
│   │   └── test_linear_processor.py   # NEW
│   └── integration/
│       └── test_event_processor_loop.py # NEW
├── docs/
│   └── EVENT_PROCESSOR.md             # NEW
├── scripts/
│   ├── start-event-processor.sh        # NEW
│   └── stop-event-processor.sh       # NEW
└── Implementation_Plan.md              # THIS FILE
```

### B. Configuration Reference

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `WEBHOOK_POLL_INTERVAL` | float | 5.0 | Seconds between polling cycles |
| `WEBHOOK_BATCH_SIZE` | int | 10 | Number of events to fetch per batch |
| `WEBHOOK_MAX_RETRIES` | int | 3 | Max retries before marking as DEAD (future) |
| `DATABASE_URL` | string | - | PostgreSQL connection string |
| `LOG_LEVEL` | string | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |

### C. API Reference

#### EventProcessor Class

```python
class EventProcessor:
    """Asynchronous event processor for webhook events."""
    
    def __init__(self) -> None:
        """Initialize event processor with handlers."""
    
    async def start(self) -> None:
        """Start the infinite polling loop."""
    
    async def stop(self) -> None:
        """Stop the polling loop gracefully."""
    
    async def process_batch(self) -> int:
        """Process a batch of pending events."""
    
    def register_handler(self, source: str, handler: Callable) -> None:
        """Register a new event handler."""
```

#### LinearProcessor Class

```python
class LinearProcessor:
    """Domain processor for Linear webhook events."""
    
    def process_single_event(self, payload: Dict[str, Any]) -> bool:
        """Process a single Linear webhook payload."""
    
    def close(self) -> None:
        """Close database connections."""
```

### D. Glossary

- **Event Processor**: Background worker that polls for and processes webhook events
- **RawWebhookEvent**: Database model storing raw webhook payloads
- **Polling Loop**: Infinite loop that periodically checks for new events
- **Handler**: Domain-specific logic for processing events from a source
- **Lifespan**: FastAPI context manager for startup/shutdown events
- **At-Least-Once Processing**: Guarantee that events are processed at least once
- **Graceful Shutdown**: Process stops cleanly, completing in-flight work
- **Handler Registry**: Dictionary mapping event sources to handler functions
- **Strategy Pattern**: Design pattern that allows runtime selection of algorithms

---

**Document End**
