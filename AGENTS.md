# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Project-Specific Patterns (Non-Obvious)

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

### Zero-Trust Security Pattern
- **Bitwarden hybrid secrets**: Zero-trust configuration using Bitwarden SDK for environment variable injection with fallback (settings.py:15-67)
- **Priority order**: Bitwarden SDK → Environment variables (.env) → Defaults (in settings.py)
- **Stable environment enforcement**: Missing Bitwarden secret IDs cause hard failures in stable environment (settings.py:246-252)

### Database Connection Patterns
- **Neo4j async driver**: Use AsyncGraphDriver from omega_kg.database.graph for non-blocking operations
- **Context managers REQUIRED**: Neo4j sessions must use context managers to prevent connection leaks (capture_server.py:307)
- **Dual database sync**: Tasks stored in both Neo4j AND Obsidian markdown files with frontmatter synchronization (lifecycle.py:317-391)

### Task Lifecycle Automation
- **Draft → Archived**: 14 days (auto), 10 days (warn) unless pinned (lifecycle.py:63-77)
- **Active → Blocked**: 30 days without commits (lifecycle.py:79-85)
- **Completed → Archived**: 90 days (lifecycle.py:87-92)

### Environment Configuration
- **ENV_TYPE isolation**: Docker volumes based on ENV_TYPE (dev=ephemeral, stable=locked) (docker-compose.yml)
- **Testcontainers compatibility**: Critical filter warnings for Python 3.12+ (pytest.ini:147-155)
- **Chrome extension CORS**: Extension ID must match exactly in CORS configuration (capture_server.py:138)

### Testing Architecture
- **Test markers**: unit, integration, requires_neo4j, requires_postgres, slow, smoke (pytest.ini:125-143)
- **Testcontainers**: Neo4j 5.x + PostgreSQL with pgvector, exponential backoff for AuthenticationRateLimit
- **Coverage target**: 80%+, current ~46% (81 tests)

### Non-Standard Commands
```bash
# Single test execution
poetry run pytest tests/test_capture.py::test_specific_function -v

# Database-specific tests
poetry run pytest -m "requires_neo4j"  # Only Neo4j tests
poetry run pytest -m "unit"            # Fast unit tests only

# Code quality (non-standard setup)
poetry run pre-commit run --all-files   # Run all hooks
poetry run ruff check --fix .           # Lint + auto-fix
```

### Critical Gotchas
- **Encoding**: Always use `encoding="utf-8"` for file operations (capture_server.py:355)
- **Vector embedding**: ChatSession nodes queue embeddings via `store_pending()` then process asynchronously (capture_server.py:520-526)
- **Health validation**: Connection checks use `RETURN 1` query pattern (capture_server.py:667)
- **JWT exchange**: Chrome extension exchanges static API key for short-lived JWT tokens (capture_server.py:695-716)
