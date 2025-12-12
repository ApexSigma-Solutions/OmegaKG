# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Build & Test Commands

- **Run single test with coverage**: `poetry run pytest --cov=omega_kg tests/test_filename.py::test_function_name -v`
- **Coverage helper script**: `python scripts/coverage-report.py quick` (quick unit test coverage)
- **Coverage with HTML report**: `python scripts/coverage-report.py full` (generates HTML report)
- **View coverage report**: `python scripts/coverage-report.py view` (opens HTML report in browser)
- **Check coverage threshold**: `python scripts/coverage-report.py minimal` (checks 70% threshold)

## Critical Project-Specific Patterns

### Hardcoded Conventions
- **AI_Conversations folder**: Capture server writes to hardcoded `AI_Conversations/{platform}/` folder in Obsidian vault (capture_server.py:296-342)
- **Task file naming**: Tasks use UID-based naming in `Tasks/` directory with glob pattern `f"Tasks/**/{uid}*.md"` (lifecycle.py:358)
- **Session logs**: Batch percolation scans `Sessions/` directory (capture_server.py:587)
- **Golden Schema Frontmatter**: Conversation files use standardized frontmatter with `id: CAP-{YYYYMMDD}-{HASH}`, `type: Conversation`, `status: new` (capture_server.py:227-239)
- **Content ID format**: `CAP-{YYYYMMDD}-{HASH}` where hash is MD5 of platform+URL+message count (capture_server.py:224)

### Mock Mode Behavior
- **Auto-fallback**: System automatically switches to mock mode when Neo4j connection fails (lifecycle.py:118-120)
- **Mock data**: Lifecycle enforcement returns predefined mock results when no database connection (lifecycle.py:238-260)
- **Graceful degradation**: All major components support `mock_mode=True` parameter (lifecycle.py, obsidian_sync.py)

### Authentication & Security
- **JWT tokens**: Chrome extension exchanges static API key for short-lived JWT tokens (capture_server.py:681-702)
- **Environment-based configuration**: ALL configuration loaded from .env file using .env.example as template - no hardcoded secrets in code (settings.py:16-18)
- **Portable configuration**: Copy .env.example to .env and fill values - application reads all settings from environment variables (settings.py:16-18)
- **Bitwarden integration**: Secrets can be fetched from Bitwarden using `BWS_ACCESS_TOKEN` and secret UUIDs (settings.py:15-67)
- **CORS configuration**: Chrome extension ID must match exactly in CORS origins (capture_server.py:138)
- **Content size limits**: 500KB maximum payload size for capture endpoint (capture_server.py:54)
- **Path traversal protection**: Platform names validated to prevent path traversal (capture_server.py:318-325)

### Database Patterns
- **Dual persistence**: Tasks stored in both Neo4j AND Obsidian markdown files with frontmatter sync (lifecycle.py:317-391)
- **Dual database**: System uses both PostgreSQL (for vector storage) and Neo4j (for graph operations) (capture_server.py:662-668)
- **Session management**: All Neo4j operations use context manager pattern `with driver.session() as session:`
- **Health checks**: Connection validation via `RETURN 1` query before operations (lifecycle.py:138)
- **Async driver**: Capture server uses async Neo4j driver for non-blocking operations (capture_server.py:476-494)

### Task Lifecycle Rules
- **Draft → Archived**: 14 days (auto), 10 days (warn) unless pinned (lifecycle.py:63-77)
- **Active → Blocked**: 30 days without commits (lifecycle.py:79-85)
- **Completed → Archived**: 90 days (lifecycle.py:87-92)
- **Hardcoded thresholds**: Lifecycle thresholds are hardcoded in `lifecycle.py` (lines 63-92) and not configurable via settings

### Vector Store Integration
- **Embedding worker**: Background worker polls for pending embeddings every 10 seconds (capture_server.py:75-76)
- **Vector store health**: `/health/vectors` endpoint provides pending/ready/failed counts (capture_server.py:786-824)
- **Embedding queue**: ChatSession nodes created with pending embedding status (capture_server.py:508-520)
- **Health thresholds**: >100 failed embeddings = unhealthy, >1000 pending = degraded (capture_server.py:802-807)

### Percolation Patterns
- **Decision extraction**: Uses keywords from settings.decision_keywords to extract decisions (capture_server.py:424)
- **Task patterns**: Extracts `[[PROJ-123]]` style task references (percolation.py:105)
- **Commit patterns**: Extracts `#### Git Commit [repo]: hash` with optional Linear ID (percolation.py:152)
- **Decision patterns**: Extracts `## Decision` headers from markdown (percolation.py:220)
- **Batch percolation**: Runs every 5 minutes via scheduler (capture_server.py:85-88)

### Entry Points
- **CLI**: `omega` command via `omega_kg.cli:cli`
- **Capture server**: `capture-server` command via `omega_kg.capture_server:main` (runs on port 8765)
- **Lifecycle enforcement**: `python -m omega_kg.lifecycle --dry-run`

## Code Style Guidelines

- **Type hints**: Required for all functions (mypy configured with `disallow_untyped_defs = false` but `check_untyped_defs = true`)
- **Docstrings**: Google-style docstrings with parameter descriptions
- **Logging**: Use `logger = logging.getLogger(__name__)` pattern
- **Error handling**: Specific exception types (ServiceUnavailable, AuthError, ConnectionError)
- **Import order**: Standard library, third-party, local imports
- **File encoding**: Always use `encoding="utf-8"` for file operations (vault_utils.py:105,147)

## Testing Requirements

- **Test markers**: Use `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.requires_neo4j`
- **Mock fixtures**: Use `mock_env_vars`, `mock_neo4j_driver`, `task_lifecycle_mock` from conftest.py
- **Test vault**: Tests create `./test_vault` directory automatically
- **Neo4j tests**: Mark with `requires_neo4j` and provide mock driver when possible
- **Coverage threshold**: 70% minimum coverage enforced (pyproject.toml:95-108)

## Critical Gotchas

- **Settings validation**: Pydantic fails fast on missing required env vars (settings.py:108-119)
- **File encoding**: Always use `encoding="utf-8"` for file operations
- **Date handling**: Use `datetime.now().isoformat()` for consistent timestamps
- **Pre-commit hooks**: Custom hooks prevent root-level test scripts and bytecode files
- **Environment setup**: Application requires .env file based on .env.example template for all configuration
- **Vector store initialization**: Must be initialized before worker starts (capture_server.py:66-71)
- **Embedding worker**: Must be started and stopped gracefully (capture_server.py:74-78, 102-106)
- **Scheduler shutdown**: Must be shutdown properly to prevent resource leaks (capture_server.py:109-113)
- **Dual persistence sync**: When updating Neo4j, must also update Obsidian frontmatter (lifecycle.py:318)
- **Task file discovery**: Uses glob pattern `Tasks/**/{uid}*.md` to find task files (lifecycle.py:358)
- **Decision ID generation**: Uses hash of first 3 words → "DEC-XXXX" format (percolation.py:268)
- **Conversation hash**: MD5 of platform + URL + message count (8 chars) (capture_server.py:204)
- **Linear webhook security**: Requires HMAC-SHA256 signature verification (linear_sync.py)
