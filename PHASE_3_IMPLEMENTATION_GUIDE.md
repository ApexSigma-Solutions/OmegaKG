# Phase 3: Capture Server Integration - Implementation Guide

## Overview

Phase 3 integrates the async vector worker into the FastAPI capture server, enabling immediate capture + async embedding generation for all incoming messages.

**Current State:** Vector store and worker modules are ready; waiting to be wired into capture_server.py  
**Blocking Issue:** Neo4j message fetcher in embedding_worker.py needs implementation first  
**Estimated Duration:** 1-2 hours total (Phase 3 + Phase 4 blocking issue fix)

---

## Phase 3a: Implement Neo4j Message Fetcher (BLOCKING)

### Location
File: `omega_kg/workers/embedding_worker.py`  
Method: `_fetch_message_text(message_id: int, node_label: str) -> Optional[str]`

### Current Implementation
Currently returns placeholder text for testing. This needs to be replaced with actual Neo4j queries.

### Required Implementation

```python
async def _fetch_message_text(
    self, message_id: int, node_label: str
) -> Optional[str]:
    """
    Fetch message content from Neo4j by node ID and label.
    
    Args:
        message_id: Neo4j node ID (internal identifier, from id(n))
        node_label: Neo4j node type (ChatMessage, LinearIssue, Decision)
        
    Returns:
        str or None: Message content to embed, or None if not found
    """
    # TODO: Replace with actual Neo4j query logic
    # Implementation steps:
    # 1. Get Neo4j driver from settings or existing connection
    # 2. Query: MATCH (n:<node_label>) WHERE id(n) = $message_id RETURN n.content AS content
    # 3. Try fallback fields in order: content, message, text, body
    # 4. Return None if node not found
    # 5. Handle type errors gracefully
```

### Query Pattern

```cypher
MATCH (n:<node_label>) 
WHERE id(n) = $message_id 
RETURN 
  COALESCE(n.content, n.message, n.text, n.body) AS content
```

### Integration Points

**Neo4j Driver Source:**
- Option 1: Import from `omega_kg.settings.neo4j_driver`
- Option 2: Import from `omega_kg.lifecycle.driver`
- Option 3: Create new async driver via `neo4j.AsyncGraphDriver()`

**Async Pattern:**
```python
from neo4j import AsyncGraphDriver

# Get driver (replace with actual source)
driver: AsyncGraphDriver = await get_neo4j_driver()

async with driver.session() as session:
    result = await session.run(
        f"MATCH (n:{node_label}) WHERE id(n) = $message_id RETURN n.content AS content",
        message_id=message_id
    )
    record = await result.single()
    if record:
        return record.get("content")
return None
```

### Error Handling

```python
try:
    # Query logic here
    pass
except Exception as e:
    logger.error(
        f"Failed to fetch message text: message_id={message_id}, "
        f"node_label={node_label}, error={e}"
    )
    return None  # Worker will mark as FAILED and retry
```

### Testing

After implementation, verify with:
```bash
poetry run python -c "
import asyncio
from omega_kg.workers.embedding_worker import EmbeddingWorker
from omega_kg.vector_store import VectorStore

# Test Neo4j message fetching
async def test():
    worker = EmbeddingWorker(vector_store=None)
    # Should return actual content or None
    text = await worker._fetch_message_text(message_id=1234, node_label='ChatMessage')
    print(f'Fetched: {text}')

asyncio.run(test())
"
```

---

## Phase 3b: Capture Server Integration

### Location
File: `omega_kg/capture_server.py`

### Changes Required

#### 1. Add Imports
```python
from contextlib import asynccontextmanager
from omega_kg.vector_store import get_vector_store, VectorStore
from omega_kg.workers.embedding_worker import start_worker, stop_worker
```

#### 2. Add Global Vector Store
```python
# Global vector store instance (shared across all requests)
_vector_store: Optional[VectorStore] = None

async def get_vector_store_instance() -> VectorStore:
    """Dependency injection for vector store access in endpoints."""
    global _vector_store
    if _vector_store is None:
        _vector_store = await get_vector_store()
    return _vector_store
```

#### 3. Update FastAPI Lifespan Event

**Current Pattern (if using lifespan context manager):**
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown
```

**Update to:**
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting capture server...")
    
    # Initialize vector store
    _vector_store = await get_vector_store()
    logger.info("Vector store initialized")
    
    # Start embedding worker
    await start_worker()
    logger.info("Embedding worker started")
    
    # Start existing scheduler (if any)
    # scheduler.start()
    
    yield
    
    # Shutdown
    logger.info("Shutting down capture server...")
    
    # Stop worker gracefully
    await stop_worker()
    logger.info("Embedding worker stopped")
    
    # Stop scheduler (if any)
    # scheduler.shutdown()

app = FastAPI(lifespan=lifespan)
```

#### 4. Add Vector Store to Capture Endpoint

**Find the message capture endpoint** (likely `POST /capture` or similar):

```python
@app.post("/capture")
async def capture_message(
    request_data: dict,
    vector_store: VectorStore = Depends(get_vector_store_instance),
) -> dict:
    """
    Capture message from client.
    
    Steps:
    1. Insert message into Neo4j
    2. Create pending vector record in PostgreSQL
    3. Return success response
    """
    try:
        # 1. Your existing Neo4j insertion logic
        message_id = await insert_into_neo4j(request_data)
        
        # 2. NEW: Create pending vector record
        node_label = request_data.get("type", "ChatMessage")
        vector_id = await vector_store.store_pending(
            message_id=message_id,
            node_label=node_label
        )
        logger.debug(f"Created pending vector: vector_id={vector_id}")
        
        # 3. Return response (no waiting for embedding generation!)
        return {
            "status": "success",
            "message_id": message_id,
            "vector_id": vector_id,
            "embedding_status": "pending"
        }
        
    except Exception as e:
        logger.error(f"Capture failed: {e}")
        return {"status": "error", "message": str(e)}
```

#### 5. Add Health Check Endpoint (Optional but Recommended)

```python
@app.get("/health/vectors")
async def health_check_vectors(
    vector_store: VectorStore = Depends(get_vector_store_instance),
) -> dict:
    """
    Get vector store health metrics.
    
    Returns: {
        "status": "healthy|degraded|unhealthy",
        "total_records": int,
        "pending_count": int,
        "ready_count": int,
        "failed_count": int,
        "worker_running": bool,
    }
    """
    try:
        stats = await vector_store.get_stats()
        pending_count = stats.get("pending_count", 0)
        failed_count = stats.get("failed_count", 0)
        
        # Determine health status
        if failed_count > 100:  # Threshold
            status = "unhealthy"
        elif pending_count > 1000:  # Threshold
            status = "degraded"
        else:
            status = "healthy"
        
        return {
            "status": status,
            "total_records": stats.get("total_records", 0),
            "pending_count": pending_count,
            "ready_count": stats.get("ready_count", 0),
            "failed_count": failed_count,
            "worker_running": True,  # TODO: Actual worker state check
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}
```

---

## Testing Phase 3 Integration

### 1. Local Testing

```bash
# Start capture server with worker
cd d:\projects\Omega_KG_stable
poetry run python -m omega_kg.capture_server

# In another terminal, send test message
curl -X POST http://localhost:8765/capture \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Test message for embedding",
    "type": "ChatMessage",
    "platform": "test"
  }'

# Expected response:
# {"status": "success", "message_id": 123, "vector_id": 456, "embedding_status": "pending"}
```

### 2. Verify Worker Processing

```bash
# Check pending records
docker exec apexsigma.postgres.stable psql -U omega_user -d omega_kg_stable \
  -c "SELECT COUNT(*) as pending_count FROM omega_vectors_1024 WHERE status = 'pending_embedding';"

# Check ready records (after 10s delay)
docker exec apexsigma.postgres.stable psql -U omega_user -d omega_kg_stable \
  -c "SELECT COUNT(*) as ready_count FROM omega_vectors_1024 WHERE status = 'ready';"

# Sample processed record
docker exec apexsigma.postgres.stable psql -U omega_user -d omega_kg_stable \
  -c "SELECT id, message_id, node_label, status FROM omega_vectors_1024 LIMIT 5;"
```

### 3. Health Endpoint Testing

```bash
# Check vector store health
curl http://localhost:8765/health/vectors | jq

# Expected output:
# {
#   "status": "healthy",
#   "total_records": 50,
#   "pending_count": 2,
#   "ready_count": 48,
#   "failed_count": 0,
#   "worker_running": true
# }
```

---

## Dependency Diagram

```
capture_server.py (FastAPI)
    ├─ lifespan event
    │   ├─ get_vector_store() → VectorStore (singleton)
    │   │   └─ initialize_pool() → asyncpg.Pool (5-20 connections)
    │   │       └─ PostgreSQL omega_vectors_1024 table
    │   │
    │   ├─ start_worker() → EmbeddingWorker
    │   │   ├─ polling loop (every 10s)
    │   │   ├─ fetch_pending_batch() → vector_store
    │   │   ├─ _fetch_message_text() → Neo4j
    │   │   ├─ generate_embedding() → Ollama
    │   │   └─ update_embedding() → vector_store
    │   │
    │   └─ stop_worker() → graceful shutdown
    │
    └─ /capture endpoint
        ├─ insert_message() → Neo4j
        └─ vector_store.store_pending() → PostgreSQL
```

---

## Configuration (via .env)

```bash
# Worker configuration (optional, defaults in config.py)
VECTOR_WORKER_POLL_INTERVAL_SECONDS=10
VECTOR_WORKER_BATCH_SIZE=10
VECTOR_EMBEDDING_MAX_RETRIES=3
VECTOR_WORKER_TIMEOUT_SECONDS=120

# PostgreSQL connection (already configured via settings.py)
POSTGRES_USER=omega_user
POSTGRES_PASSWORD=<from Bitwarden>
POSTGRES_SERVER=localhost
POSTGRES_PORT=5433  # stable, or 5434 for dev
POSTGRES_DB=omega_kg_stable

# Ollama embedding service
OLLAMA_BASE_URL=http://localhost:11434
```

---

## Troubleshooting

### Worker Not Processing Embeddings

1. **Check logs:**
   ```bash
   # Look for error messages in capture_server output
   grep -i "embedding\|error\|exception" capture_server.log
   ```

2. **Verify worker is running:**
   ```bash
   # Should see "Starting embedding worker" in logs
   # Should see "Processing batch of X pending embeddings" every 10s
   ```

3. **Check database state:**
   ```bash
   docker exec apexsigma.postgres.stable psql -U omega_user -d omega_kg_stable \
     -c "SELECT id, status, retry_count FROM omega_vectors_1024 WHERE status != 'ready' LIMIT 10;"
   ```

4. **Verify Ollama is accessible:**
   ```bash
   curl http://localhost:11434/api/tags
   # Should return: {"models": [{"name": "bge-m3:567m", ...}]}
   ```

### Neo4j Message Fetcher Returns None

1. **Verify node exists in Neo4j:**
   ```cypher
   MATCH (n) WHERE id(n) = 1234 RETURN n
   ```

2. **Check node has content field:**
   ```cypher
   MATCH (n:ChatMessage) RETURN DISTINCT keys(n)
   ```

3. **Verify node_label matches:**
   ```bash
   # Check what labels exist in database
   docker exec apexsigma.neo4j.stable cypher-shell "MATCH (n) RETURN DISTINCT labels(n)"
   ```

---

## Next: Phase 4

Once Phase 3 is complete, verify that:
- ✅ Captures create pending vector records
- ✅ Worker polls and processes embeddings
- ✅ Records transition from pending → ready (or failed)
- ✅ Health endpoint shows worker running
- ✅ No capture latency increase

Then proceed to Phase 4: Migration Script (bulk migrate Neo4j embeddings to PostgreSQL).
