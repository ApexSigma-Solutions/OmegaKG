# Capture Server Startup Logic - Side-by-Side Comparison

## Before (Dev - Original)

```python
# Lifespan for scheduler
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler to initialize vector store, start worker, and schedule batch percolation."""
    logger.info("Starting Omega_KG Capture Server...")
    
    # Initialize vector store
    try:
        vector_store = await get_vector_store()
        logger.info("✓ Vector store initialized")
    except Exception as e:
        logger.error(f"Failed to initialize vector store: {e}")
        raise
```

**Issues**:
- ❌ No retry logic
- ❌ Fails immediately if PostgreSQL not ready
- ❌ Not suitable for Task Scheduler auto-start
- ❌ Generic exception handling

## After (Dev - Aligned with Stable)

```python
async def wait_for_vector_store(max_retries: int = 30, initial_delay: float = 2.0) -> "VectorStore":
    """
    Wait for vector store to become available with exponential backoff.
    
    Designed for Windows Task Scheduler startup where Docker containers
    (PostgreSQL) may not be ready when the server starts at login.
    """
    import asyncio
    
    for attempt in range(max_retries):
        try:
            vector_store = await get_vector_store()
            if attempt > 0:
                logger.info(f"✓ Vector store initialized after {attempt + 1} attempts")
            else:
                logger.info("✓ Vector store initialized")
            return vector_store
        except Exception as e:
            if attempt < max_retries - 1:
                # Exponential backoff capped at 10 seconds
                wait_time = min(initial_delay * (1.5 ** attempt), 10.0)
                logger.warning(
                    f"Vector store not ready (attempt {attempt + 1}/{max_retries}): {e}. "
                    f"Retrying in {wait_time:.1f}s..."
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(
                    f"Failed to initialize vector store after {max_retries} attempts. "
                    f"Ensure PostgreSQL is running."
                )
                raise ConnectionError(
                    f"PostgreSQL unavailable after {max_retries} attempts: {e}"
                )


# Lifespan for scheduler
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler to initialize vector store, start worker, and schedule batch percolation."""
    logger.info("Starting Omega_KG Capture Server...")
    
    # Initialize vector store (with retry for Task Scheduler startup)
    try:
        vector_store = await wait_for_vector_store()
    except ConnectionError as e:
        logger.error(f"Startup failed - vector store unavailable: {e}")
        raise
```

**Improvements**:
- ✅ Retry logic with exponential backoff
- ✅ Handles PostgreSQL startup delays
- ✅ Task Scheduler compatible
- ✅ Detailed logging for debugging
- ✅ Specific ConnectionError handling
- ✅ Configurable retry parameters

## Retry Behavior

| Attempt | Wait Time | Cumulative Time |
|---------|-----------|-----------------|
| 1       | 0s        | 0s              |
| 2       | 2.0s      | 2s              |
| 3       | 3.0s      | 5s              |
| 4       | 4.5s      | 9.5s            |
| 5       | 6.8s      | 16.3s           |
| 6       | 10.0s     | 26.3s           |
| 7-30    | 10.0s     | ~60s total      |

## Alignment Status

| Component | Stable | Dev | Status |
|-----------|--------|-----|--------|
| `wait_for_vector_store()` | ✅ | ✅ | **ALIGNED** |
| `lifespan()` retry logic | ✅ | ✅ | **ALIGNED** |
| Startup scripts | ✅ | ✅ | **ALIGNED** |
| Error handling | ✅ | ✅ | **ALIGNED** |

## Merge Safety

✅ **SAFE TO MERGE** - Dev version now matches stable implementation
