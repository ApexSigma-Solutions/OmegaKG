# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Build/Lint/Test Commands

### Poetry Commands
```bash
# Install dependencies
poetry install --with dev

# Run the capture server
poetry run capture-server

# Run CLI
poetry run omega --help

# Run tests
poetry run pytest                           # All tests
poetry run pytest tests/test_capture.py     # Specific test file
poetry run pytest tests/test_capture.py::test_html_parsing -v  # Single test

# Test markers
poetry run pytest -m "unit"                 # Fast unit tests only
poetry run pytest -m "requires_neo4j"       # Only Neo4j tests
poetry run pytest -m "integration"          # Integration tests
poetry run pytest -m "not slow"              # Skip slow tests

# Coverage reporting
poetry run pytest --cov=omega_kg --cov-report=term-missing --cov-report=html
poetry run pytest tests/test_lifecycle.py --cov=omega_kg.lifecycle

# Code quality
poetry run ruff check .                     # Lint
poetry run ruff check --fix .               # Lint + auto-fix
poetry run ruff format .                    # Format code
poetry run pre-commit run --all-files       # Run all hooks
poetry run mypy omega_kg/                   # Type checking
poetry run bandit -r .                      # Security linting

# Database migrations
poetry run alembic revision --autogenerate -m "description"
poetry run alembic upgrade head
```

## Code Style Guidelines

### Import Organization
**Order**: Standard library → Third-party → Local (blank lines between groups)

```python
# Standard library
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Third-party
from fastapi import FastAPI, HTTPException, Request
from neo4j import AsyncDriver, AsyncGraphDatabase
from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Local imports
from omega_kg.database.graph import AsyncGraphDriver
from omega_kg.models.capture import ConversationData, CaptureResponse
from omega_kg.settings import settings
```

**Rules**:
- Explicit `from typing` imports (no `*` imports)
- Multi-line imports use parentheses with one import per line
- Blank line between import groups
- Module-level `__all__` for explicit exports

### Type Annotations
**Full type hints on all function signatures**:

```python
async def connect(self) -> None:
    """Initialize connection."""
    pass

def _transition_task(
    session: Any,
    uid: str,
    rule: LifecycleRule,
) -> None:
    """Transition task state."""
    pass

async def capture_conversation(
    data: ConversationData,
    request: Request,
    _token_payload: Dict[str, Any] = Security(validate_access_token),
) -> CaptureResponse:
    """Capture conversation from extension."""
    pass
```

**Type patterns**:
- Return types explicitly declared (even when `None`)
- `Optional[T]` for nullable values
- `Dict[str, Any]` for unstructured dictionaries
- `List[T]` for collections
- Union types: `List[Union[Dict[str, Any], Message]]`
- Modern union syntax: `AsyncDriver | None` when possible

**Pydantic models**:
```python
class ConversationData(BaseModel):
    user_id: str = "extension_user"
    platform: str = "obsidian"
    messages: Optional[List[Union[Dict[str, Any], Message]]] = []
    metadata: Optional[Dict[str, Any]] = None
```

### Naming Conventions
- **Functions**: `snake_case` → `percolate_to_neo4j()`, `_check_ollama_ready()`
- **Classes**: `PascalCase` → `AsyncGraphDriver`, `TaskLifecycle`
- **Private members**: `_prefix` → `_check_connection()`, `_driver`
- **Constants**: `UPPER_CASE` → `MAX_HTML_SIZE = 10 * 1024 * 1024`

### Error Handling
**Three-tier error handling**:

```python
# 1. Specific exception catching
try:
    driver = GraphDatabase.driver(uri, auth=auth)
except (ServiceUnavailable, AuthError, ConnectionError) as e:
    logger.error("Failed to connect: %s: %s", type(e).__name__, e)
    raise

# 2. Generic exception with logging
try:
    response = client.secrets().get(uuid.UUID(secret_uuid))
except Exception:
    logger.warning("Failed to fetch secret for key '%s'", config_key)

# 3. HTTP exceptions for API endpoints
if content_length > MAX_HTML_SIZE:
    raise HTTPException(
        status_code=413,
        detail=f"Payload exceeds maximum allowed size of {MAX_HTML_SIZE} bytes",
    )
```

**Logging patterns**:
- `logger.critical()` - Fatal startup failures
- `logger.error(..., exc_info=True)` - Exceptions with stack traces
- `logger.warning()` - Non-fatal issues
- `logger.info()` - Successful operations
- Structured logging: `logger.info("Message", extra={"key": "value"})`

**Custom exceptions**:
```python
class ConnectionError(Exception):
    """Raised when Neo4j connection cannot be established."""
    pass
```

### Async/Await Patterns
**Consistent async patterns**:

```python
# Async context managers for database operations (MANDATORY)
async with graph_driver.session() as session:
    result = await session.run("MATCH (n) RETURN n LIMIT 1")
    record = await result.single()

# Async with explicit cleanup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await get_vector_store()
    await start_worker()
    heartbeat_task = asyncio.create_task(_run_heartbeat_loop())

    yield

    # Shutdown
    heartbeat_task.cancel()
    await asyncio.sleep(0.1)
    await stop_worker()
    await VectorStore.close_pool()

# Polling with backoff
async def _check_ollama_ready(timeout: int = 30) -> bool:
    async with httpx.AsyncClient() as client:
        for _ in range(timeout):
            try:
                resp = await client.get(f"{url}/api/tags", timeout=2)
                if resp.status_code == 200:
                    return True
            except Exception:
                pass
            await asyncio.sleep(1)
```

**Fallback patterns**:
- Dummy scheduler class when APScheduler unavailable (capture_server.py:71-83)
- Mock mode auto-activation on Neo4j connection failure (lifecycle.py:117-120)
- Non-fatal embedding queue failures with logging

### Docstring Conventions
**Google-style docstrings**:

```python
"""
Neo4j Async Graph Driver

Singleton wrapper for Neo4j async driver with connection pooling.
Phase 6: TN-LINEAR-06 - Graph Topology
"""

class AsyncGraphDriver:
    """
    Singleton wrapper for the Neo4j Async Driver.
    Handles connection pooling and session management.
    """

    async def connect(self) -> None:
        """
        Initializes the Neo4j driver if not already connected.

        Raises:
            ConnectionError: If Neo4j connection fails.
        """
        pass

    async def verify_connectivity(self) -> bool:
        """
        Checks if the database is reachable.

        Returns:
            bool: True if connected, False otherwise.
        """
        pass
```

**Docstring patterns**:
- Module-level docstrings with project tags (e.g., "Phase 6: TN-LINEAR-06")
- Class docstrings for all classes
- Method docstrings with Parameters/Returns/Raises sections
- One-line docstrings for simple methods
- Triple-quotes consistently

## Project-Specific Patterns

### Hardcoded Conventions
- **AI_Conversations folder**: Capture server writes to hardcoded `AI_Conversations/{platform}/` folder in Obsidian vault (capture_server.py:339)
- **UID-based task files**: Tasks use glob pattern `f"Tasks/**/{uid}*.md"` for file discovery (lifecycle.py:358)
- **Content ID format**: Conversations use `CAP-{YYYYMMDD}-{HASH}` format for frontmatter IDs (capture_server.py:225)
- **Platform sanitization**: Platform names sanitized via regex `r'[<>:"|?*\x00-\x1f]'` before folder creation (capture_server.py:327)

### Auto-Fallback Behaviors
- **Mock mode activation**: System automatically switches to mock mode when Neo4j connection fails (lifecycle.py:118-120)
- **Embedding worker**: Asynchronous worker polls every 10 seconds for pending embeddings (capture_server.py:75-76)
- **Session scheduler**: Batch percolation runs every 5 minutes via APScheduler (capture_server.py:84-88)
- **APScheduler fallback**: Dummy class provided when APScheduler not available (capture_server.py:71-82)

### Percolation Scan Folders
The batch percolation scheduler scans configured Obsidian vault folders for new sessions to percolate into Neo4j. Configure scan folders via environment variable:

```bash
# Scan only the default Sessions folder (default behavior)
OBSIDIAN_VAULT_SCAN_FOLDERS="Sessions"

# Scan multiple folders
OBSIDIAN_VAULT_SCAN_FOLDERS="Sessions,AI_Conversations,Archive"

# Use colon separator (alternative)
OBSIDIAN_VAULT_SCAN_FOLDERS="Sessions:AI_Conversations:Archive"
```

**Configuration precedence**: Environment variable → `.env` file → Defaults to `["Sessions"]`

**Scheduler behavior**:
- Logs scanned folders on each run (e.g., `[OK] Scheduler completed in 155ms: 2 tasks, 0 commits, 0 decision links (folders: 2)`)
- Validates folder existence and logs warnings for missing folders
- Maintains backward compatibility - empty/missing setting defaults to `["Sessions"]`

### Zero-Trust Security Pattern
- **Bitwarden hybrid secrets**: Zero-trust configuration using Bitwarden SDK for environment variable injection with fallback (settings.py:15-67)
- **Priority order**: Bitwarden SDK → Environment variables (.env) → Defaults (in settings.py)
- **Stable environment enforcement**: Missing Bitwarden secret IDs cause hard failures in stable environment (settings.py:246-252)

### Database Connection Patterns
- **Neo4j async driver**: Use AsyncGraphDriver from omega_kg.database.graph for non-blocking operations
- **Context managers REQUIRED**: Neo4j sessions must use context managers to prevent connection leaks (capture_server.py:307)
- **Dual database sync**: Tasks stored in both Neo4j AND Obsidian markdown files with frontmatter synchronization (lifecycle.py:317-391)
- **Health validation**: Connection checks use `RETURN 1` query pattern (capture_server.py:667)

### Task Lifecycle Automation
- **Draft → Archived**: 14 days (auto), 10 days (warn) unless pinned (lifecycle.py:63-77)
- **Active → Blocked**: 30 days without commits (lifecycle.py:79-85)
- **Completed → Archived**: 90 days (lifecycle.py:87-92)

### Environment Configuration
- **ENV_TYPE isolation**: Docker volumes based on ENV_TYPE (dev=ephemeral, stable=locked) (docker-compose.yml)
- **Testcontainers compatibility**: Critical filter warnings for Python 3.12+ (pytest.ini:144-152)
- **Chrome extension CORS**: Extension ID must match exactly in CORS configuration (capture_server.py:138)

### Testing Infrastructure
- **Test markers**: unit, integration, requires_neo4j, requires_postgres, slow, smoke (pytest.ini:122-140)
- **Testcontainers**: Neo4j 5.x + PostgreSQL with pgvector, exponential backoff for AuthenticationRateLimit
- **Coverage target**: 80%+, current ~46% (81 tests)

## Critical Gotchas
- **Encoding**: Always use `encoding="utf-8"` for file operations (capture_server.py:355)
- **Vector embedding**: ChatSession nodes queue embeddings via `store_pending()` then process asynchronously (capture_server.py:520-526)
- **JWT exchange**: Chrome extension exchanges static API key for short-lived JWT tokens (capture_server.py:695-716)
- **Context leaks**: Neo4j sessions MUST use async context managers to prevent connection leaks
- **Global singletons**: `graph_driver = AsyncGraphDriver()`, `settings = Settings()` - use these, don't instantiate
