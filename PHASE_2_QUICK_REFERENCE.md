# Phase 2 Quick Reference

## What Was Deployed

✅ **Vector Store Module** (`omega_kg/vector_store.py`)
- Async PostgreSQL persistence layer with asyncpg pooling
- Immediate-insert semantics (no blocking on embedding generation)
- Methods: store_pending(), update_embedding(), mark_failed(), fetch_pending_batch()

✅ **Embedding Worker** (`omega_kg/workers/embedding_worker.py`)
- Background async polling worker with configurable intervals
- Fetches pending → generates embeddings → updates database
- Retry tracking (up to 3 attempts by default)
- FastAPI lifespan integration (start_worker, stop_worker)

✅ **Configuration** (`omega_kg/config.py` - updated)
- Added SUPPORTED_NODE_TYPES = ("ChatMessage", "LinearIssue", "Decision")
- Added DEFAULT_NODE_TYPE = "ChatMessage"
- All constants configurable via environment variables

✅ **Database Schema** (both stable & dev)
- Added node_label column to omega_vectors_1024
- Added idx_omega_vectors_node_label index
- Added idx_omega_vectors_neo4j_lookup unique compound index
- Total indexes now: 9 (was 7)

✅ **Dependencies**
- Added pgvector (0.4.1)
- asyncpg already present
- poetry lock updated

## How to Use

### 1. Initialize in Capture Server

```python
# In capture_server.py lifespan startup:
from omega_kg.vector_store import get_vector_store
from omega_kg.workers.embedding_worker import start_worker

vector_store = await get_vector_store()
await start_worker()
```

### 2. Store Pending on Message Capture

```python
# After Neo4j insert in capture endpoint:
vector_id = await vector_store.store_pending(
    message_id=neo4j_node_id,
    node_label="ChatMessage"  # or LinearIssue, Decision
)
```

### 3. Worker Processes Automatically

- Polls every 10 seconds (configurable)
- Fetches up to 10 pending records (configurable)
- Generates embeddings via Ollama
- Updates database with status='ready' or 'failed'

## Configuration

All via environment variables (see config.py):

```bash
VECTOR_WORKER_POLL_INTERVAL_SECONDS=10          # Default: 10
VECTOR_WORKER_BATCH_SIZE=10                     # Default: 10
VECTOR_EMBEDDING_MAX_RETRIES=3                  # Default: 3
VECTOR_WORKER_TIMEOUT_SECONDS=120               # Default: 120
```

## Monitoring

### Database Health
```sql
-- Check pending records
SELECT COUNT(*) FROM omega_vectors_1024 WHERE status = 'pending_embedding';

-- Check ready records
SELECT COUNT(*) FROM omega_vectors_1024 WHERE status = 'ready';

-- Check failed records
SELECT COUNT(*) FROM omega_vectors_1024 WHERE status = 'failed';
```

### Worker Metrics
- `processed_count`: Total embeddings successfully generated
- `error_count`: Total embeddings marked as failed
- `batch_time`: Latest batch processing duration

## Known Limitations

### TODO: Neo4j Message Fetcher
Location: `omega_kg/workers/embedding_worker.py::_fetch_message_text()`

Currently returns placeholder text. Needs implementation:
```python
async def _fetch_message_text(self, message_id: int, node_label: str) -> Optional[str]:
    # TODO: Query Neo4j by node ID and label
    # Return message content or None
```

This is **BLOCKING** for worker to function.

## Error Handling

- **Connection lost**: Worker retries with backoff
- **Neo4j query fails**: Returns None → worker marks record FAILED
- **Embedding timeout**: Increments retry_count
- **Max retries exceeded**: Record marked FAILED (manual review needed)
- **Worker crash**: Database records remain durable; worker resumes on restart

## Testing Imports

```bash
# All three should succeed:
poetry run python -c "from omega_kg.config import SUPPORTED_NODE_TYPES; print('✓')"
poetry run python -c "from omega_kg.vector_store import VectorStore; print('✓')"
poetry run python -c "from omega_kg.workers.embedding_worker import EmbeddingWorker; print('✓')"
```

## File Locations

```
omega_kg/
├── config.py                           ← UPDATED
├── vector_store.py                     ← NEW
└── workers/
    ├── __init__.py                     ← NEW
    └── embedding_worker.py             ← NEW

scripts/
└── migrations/
    ├── 001_create_omega_vectors_1024.sql   (Phase 1)
    └── 002_add_node_label_column.sql       (Phase 2) ← NEW

pyproject.toml                          ← UPDATED (pgvector added)
poetry.lock                             ← UPDATED
```

## Next Phase

**Phase 3: Capture Server Integration**
- Modify capture_server.py to initialize vector_store and start worker in lifespan
- Call vector_store.store_pending() after Neo4j insert in capture endpoint
- Add health check endpoint

**Phase 4: Neo4j Message Fetcher**
- Implement _fetch_message_text() to query Neo4j by node ID and label
- Handle missing nodes and type mismatches gracefully

**Phase 5: Migration Script**
- Bulk migrate embeddings from Neo4j to PostgreSQL
- Dry-run validation
- Rollback support

## Support

For issues:
1. Check logs for worker startup/error messages
2. Verify PostgreSQL connection via docker exec
3. Check Ollama service health: `curl http://localhost:11434/api/tags`
4. Verify Neo4j has nodes: `docker exec apexsigma.neo4j.stable cypher-shell "MATCH (n) RETURN COUNT(n)"`
