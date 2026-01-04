# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Project Overview

**Omega_KG** is a Python 3.12+ FastAPI knowledge management system that captures AI conversations from browser extensions and transforms them into a searchable knowledge graph using dual database architecture (Neo4j + PostgreSQL).

**Tech Stack:**
- **Backend**: FastAPI, Python 3.12+
- **Databases**: Neo4j (graph), PostgreSQL (events/vectors with pgvector)
- **Package Manager**: Poetry
- **Testing**: pytest with testcontainers (Neo4j, Postgres)
- **Code Quality**: ruff (linting), mypy (type checking), black (formatting - via pre-commit), bandit (security)
- **Databases (Docker)**: neo4j:5-community, pgvector/pgvector:pg16
- **Background Tasks**: APScheduler
- **Security**: Bitwarden SDK with environment fallback

---

## Essential Commands

### Development Setup
```bash
# Install dependencies
poetry install --with dev

# Create environment config
cp .env.example .env
# Edit .env with OBSIDIAN_VAULT_PATH, NEO4J_PASSWORD, POSTGRES_PASSWORD, etc.

# Start databases (Docker required)
docker compose up -d neo4j postgres

# Install pre-commit hooks (Windows-compatible)
poetry run pre-commit install
```

### Development Server
```bash
# Start capture server (port 8765)
poetry run capture-server

# Run CLI commands
poetry run omega --help
poetry run omega init              # Initialize Neo4j schema
poetry run omega sync              # Sync Obsidian vault to Neo4j
poetry run omega lifecycle --dry-run  # Preview lifecycle changes
poetry run omega stats             # Show task statistics
poetry run omega status            # Check connection status
poetry run omega report --email    # Generate lifecycle report
```

### Testing
```bash
# Run all tests
poetry run pytest

# Run specific test types
poetry run pytest -m "unit"                    # Unit tests only
poetry run pytest -m "integration"             # Integration tests
poetry run pytest -m "requires_neo4j"          # Neo4j required
poetry run pytest -m "requires_postgres"       # PostgreSQL required

# Run with coverage
poetry run pytest --cov=omega_kg --cov-report=xml

# Skip slow tests
poetry run pytest --skip-slow

# Run specific test file
poetry run pytest tests/test_capture.py -v
```

### Code Quality
```bash
# Install pre-commit hooks
poetry run pre-commit install

# Run all quality checks
poetry run pre-commit run --all-files

# Individual tools
poetry run ruff check .                        # Lint
poetry run ruff check --fix .                  # Lint + auto-fix
poetry run ruff format .                       # Format code
poetry run mypy omega_kg                       # Type checking
poetry run bandit -c pyproject.toml -ll -r .   # Security linting
```

### Docker Operations
```bash
# Start all services
docker compose up -d

# Start specific services
docker compose up -d neo4j postgres

# View logs
docker compose logs -f capture-server
docker compose logs -f neo4j
docker compose logs -f postgres

# Restart specific service
docker compose restart neo4j

# Stop all services
docker compose down

# Environment types (set via ENV_TYPE env var)
# Default: dev (uses dev volumes, ephemeral)
# Set ENV_TYPE=stable for production (uses locked external volumes)
```

### Database Migrations
```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Check current version
alembic current

# Rollback one migration
alembic downgrade -1
```

---

## Code Organization

### Directory Structure
```
omega_kg/
├── capture_server.py       # FastAPI entry point with lifespan management (33KB)
├── main.py                 # FastAPI app factory
├── cli.py                  # CLI commands (poetry run omega)
├── settings.py             # Configuration (Bitwarden + env vars)
├── config.py               # Runtime configuration constants
│
├── database/               # Database layer
│   ├── base.py             # SQLAlchemy Base
│   ├── graph.py            # Neo4j async driver (singleton)
│   ├── session.py          # Async SQLAlchemy sessions
│   └── quipu.py            # PostgreSQL helpers
│
├── domain/                 # Domain-driven design
│   ├── linear/             # Linear integration
│   │   ├── models.py       # Pydantic models
│   │   ├── processor.py    # Webhook processing
│   │   ├── mapper.py       # Data mapping logic
│   │   └── graph_writer.py # Neo4j relationship creation
│   └── common/
│       └── embedding_service.py # Vector embedding service
│
├── models/                 # SQLAlchemy ORM models
│   ├── capture.py          # Capture server Pydantic models
│   └── linear.py           # RawLinearEvent model
│
├── routers/                # FastAPI route modules
│   ├── capture.py          # Capture endpoints
│   └── linear_receiver.py  # Linear webhook endpoint
│
├── workers/                # Background workers
│   └── embedding_worker.py # Async vector generation
│
├── utils/                  # Utility functions
│   └── capture_utils.py    # Capture helper functions
│
├── scripts/                # Utility scripts
│   └── init_vector_index.py # Initialize vector index
│
├── lifecycle.py            # Task state automation
├── linear_sync.py          # Linear API sync
├── percolation.py          # Insight extraction
├── vector_store.py         # PostgreSQL vector operations (pgvector)
├── obsidian_sync.py        # Vault synchronization
├── neo4j_schema.py         # Neo4j schema management
├── parsers.py              # HTML/content parsers
├── smart_parser.py         # Smart parsing logic
└── rate_limiter.py         # Rate limiting

tests/
├── conftest.py             # Master test configuration (testcontainers, fixtures)
├── integration/            # Integration tests
├── test_*.py               # Unit tests
└── pytest.ini              # Pytest configuration

chrome-extension/
├── manifest.json           # Chrome extension manifest
├── background.js           # Extension background script
├── content.js              # Content script for page scraping
├── config.js               # Extension configuration
├── popup.html/js           # Extension UI
└── platforms.json          # Supported AI platforms

alembic/                   # Database migrations
├── versions/               # Migration scripts
└── env.py                 # Alembic environment configuration

docs/                       # Documentation
```

---

## Naming Conventions & Style

### File Naming
- **Python modules**: `snake_case.py` (e.g., `capture_server.py`, `linear_sync.py`)
- **Test files**: `test_*.py` (e.g., `test_capture.py`, `test_lifecycle.py`)
- **Classes**: `PascalCase` (e.g., `TaskLifecycle`, `ObsidianNeo4jSync`)
- **Functions/variables**: `snake_case` (e.g., `enforce_lifecycle`, `get_connection_status`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `NEO4J_IMAGE`, `POSTGRES_IMAGE`)

### Code Style (ruff + mypy)
- **Line length**: 100 characters (configured in pyproject.toml)
- **Imports**: Grouped by standard library, third-party, local
- **Type hints**: Required for function signatures (mypy enforced, but not strict)
- **Docstrings**: Google-style docstrings for modules, classes, and public methods
- **Async patterns**: All database operations use async/await with proper context managers

### Pattern: Settings Management
```python
from omega_kg.settings import settings

# Settings loaded from:
# 1. Bitwarden SDK (if BWS_ACCESS_TOKEN set)
# 2. Environment variables (.env file)
# 3. Defaults (in settings.py)

# Access settings (lowercase attribute names)
settings.neo4j_uri
settings.neo4j_password
settings.obsidian_vault_path
settings.app_port
```

---

## Testing Architecture

### Test Markers
```python
@pytest.mark.unit                    # Isolated unit tests (no external deps)
@pytest.mark.integration             # Requires external services
@pytest.mark.slow                    # Long-running tests
@pytest.mark.requires_neo4j          # Needs Neo4j instance
@pytest.mark.requires_postgres       # Needs PostgreSQL instance
@pytest.mark.requires_linear         # Needs Linear API
@pytest.mark.requires_obsidian       # Needs Obsidian vault
@pytest.mark.requires_ollama         # Needs Ollama service
@pytest.mark.smoke                   # Basic functionality verification
@pytest.mark.regression              # Comprehensive coverage tests
@pytest.mark.security                # Security compliance tests
@pytest.mark.e2e                    # End-to-end tests
```

### Testcontainers Fixtures
```python
# Integration test example
def test_database_integration(db_session, graph_session):
    # db_session: PostgreSQL session with rollback
    # graph_session: Neo4j session (auto-wipes graph before test)
    pass

# Unit test example
def test_unit_function(mock_neo4j_driver, mock_file_system):
    # mock_neo4j_driver: Mocked Neo4j driver
    # mock_file_system: Temporary file system
    pass
```

### Critical Test Configuration
```python
# tests/conftest.py contains:
# - Testcontainers for Neo4j (neo4j:5-community)
# - Testcontainers for Postgres (pgvector/pgvector:pg16)
# - Mock fixtures for unit tests
# - Async session management
# - Performance monitoring

# Key environment variables for tests
APP_ENV=test
ZERO_TRUST_REQUIRED=false
# Ports injected dynamically by testcontainers
```

---

## Important Gotchas & Non-Obvious Patterns

### 1. Hardcoded Conventions
- **AI_Conversations folder**: Capture server writes to hardcoded `AI_Conversations/{platform}/` folder in Obsidian vault (capture_server.py:339)
- **UID-based task files**: Tasks use glob pattern `f"Tasks/**/{uid}*.md"` for file discovery (lifecycle.py:358)
- **Content ID format**: Conversations use `CAP-{YYYYMMDD}-{HASH}` format for frontmatter IDs (capture_server.py:225)
- **Platform sanitization**: Platform names sanitized via regex `r'[<>:"|?*\x00-\x1f]'` before folder creation (capture_server.py:327)

### 2. Auto-Fallback Behaviors
- **Mock mode activation**: System automatically switches to mock mode when Neo4j connection fails (lifecycle.py:118-120)
- **Embedding worker**: Asynchronous worker polls every 10 seconds for pending embeddings (capture_server.py:75-76)
- **Session scheduler**: Batch percolation runs every 5 minutes via APScheduler (capture_server.py:84-88)
- **APScheduler fallback**: Dummy class provided when APScheduler not available (capture_server.py:71-82)

### 3. Dual Persistence Architecture
- **Neo4j + Markdown sync**: Tasks stored in both Neo4j AND Obsidian markdown files with frontmatter synchronization (lifecycle.py:317-391)
- **Health validation**: Connection checks use `RETURN 1` query pattern (capture_server.py:667)
- **Vector embedding**: ChatSession nodes queue embeddings via `store_pending()` then process asynchronously (capture_server.py:520-526)

### 4. Security & Authentication
- **Bitwarden hybrid secrets**: Zero-trust configuration using Bitwarden SDK for environment variable injection (settings.py:15-67)
- **JWT exchange flow**: Chrome extension exchanges static API key for short-lived JWT tokens (capture_server.py:695-716)
- **CORS origins**: Chrome extension ID must match exactly in CORS configuration (capture_server.py:138)
- **Settings validation**: Pydantic fails fast on missing required env vars (settings.py:108-119)

### 5. Task Lifecycle Enforcement
- **Draft → Archived**: 14 days (auto), 10 days (warn) unless pinned (lifecycle.py:63-77)
- **Active → Blocked**: 30 days without commits (lifecycle.py:79-85)
- **Completed → Archived**: 90 days (lifecycle.py:87-92)

### 6. Database Connection Patterns
```python
# Neo4j: ALWAYS use context manager to prevent connection leaks
from neo4j import GraphDatabase

driver = GraphDatabase.driver(uri, auth=(user, password))
with driver.session() as session:  # REQUIRED
    result = session.run("MATCH (n) RETURN n")

# Async Neo4j (recommended):
from omega_kg.database.graph import AsyncGraphDriver

graph_driver = AsyncGraphDriver()
await graph_driver.connect()
async with graph_driver.session() as session:
    result = await session.run("MATCH (n) RETURN n")

# PostgreSQL async:
from omega_kg.database.session import async_session_maker

async with async_session_maker() as session:
    # Session auto-closes on exit
    pass
```

### 7. File Operations
- **Encoding**: Always use `encoding="utf-8"` for file operations (capture_server.py:355)
- **Path handling**: Use `pathlib.Path` for cross-platform path operations

### 8. Pre-commit Hooks (Windows-Optimized)
```yaml
# .pre-commit-config.yaml contains Windows-compatible checks only
# Full infra checks run in CI/CD or via scripts/pre-commit-full.ps1

# Hooks:
# - ruff (linting + formatting)
# - mypy (type checking - incremental for speed)
# - bandit (security)
# - check-yaml, check-merge-conflict, detect-private-key
```

### 9. Docker Volume Isolation
```yaml
# docker-compose.yml uses dynamic volumes based on ENV_TYPE:
# - ENV_TYPE=dev: Uses ephemeral volumes (postgres_data_dev, neo4j_data_dev)
# - ENV_TYPE=stable: Uses locked external volumes (postgres_data_stable, neo4j_data_stable)

# This ensures strict isolation between dev and stable environments
```

### 10. Testcontainers Warnings
```python
# tests/conftest.py contains critical fix for Testcontainers:
# filterwarnings = [
#     "ignore::DeprecationWarning",
#     "ignore:The @wait_container_is_ready decorator is deprecated:DeprecationWarning",
# ]

# Without these, Testcontainers 4.x fails on Python 3.12+
```

---

## Configuration

### Environment Variables (Priority Order)
1. **Bitwarden Secrets** (if `BWS_ACCESS_TOKEN` set)
2. **Environment Variables** (`.env` file)
3. **Defaults** (in `settings.py`)

### Critical .env Variables
```bash
# Required
OBSIDIAN_VAULT_PATH=D:\path\to\vault
NEO4J_URI=bolt://localhost:7687
NEO4J_PASSWORD=your-password
POSTGRES_SERVER=127.0.0.1
POSTGRES_PORT=5433
POSTGRES_DB=omega_kg
POSTGRES_USER=omega_user
POSTGRES_PASSWORD=your-password
APP_PORT=8765
APP_HOST=127.0.0.1

# Security (Bitwarden)
ZERO_TRUST_REQUIRED=true
BWS_ACCESS_TOKEN=<bitwarden_access_token>
LINEAR_API_KEY_PRD_ID=<uuid>
EXTENSION_API_KEY_PRD_ID=<uuid>
# ... other secret IDs

# Extension Authentication
EXTENSION_API_KEY_PRD=your-api-key  # Or via Bitwarden

# Embedding Providers
EMBEDDING_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
GEMINI_API_KEY=your-gemini-key
PERPLEXITY_API_KEY=your-perplexity-key

# Linear Integration
LINEAR_API_KEY=your-linear-key
LINEAR_TEAM_ID=team-uuid
LINEAR_WEBHOOK_SECRET=webhook-secret

# Ngrok (optional)
ENABLE_NGROK=false
NGROK_API_KEY=your-ngrok-key

# Environment Type (for Docker volumes)
ENV_TYPE=dev  # or 'stable'
```

---

## Port Reference

| Service | Port | Purpose | Notes |
|---------|------|---------|-------|
| Capture Server | 8765 | FastAPI server | Default port |
| Capture Server (Dev) | 8766 | Dev instance | Only if using dev profile |
| Neo4j HTTP | 7474 | Neo4j Browser UI | Web interface |
| Neo4j Bolt | 7687 | Neo4j Database | Protocol port |
| PostgreSQL | 5433 | PostgreSQL DB | Default dev port |
| Ollama | 11434 | Ollama API | Local embeddings |

---

## Architecture Patterns

### Dual Database Strategy
- **Neo4j**: Graph relationships (Sessions → Decisions → Tasks → Commits)
- **PostgreSQL**: Event storage, vector embeddings (pgvector)
- **Sync pattern**: Data written to both, with bidirectional sync for tasks

### Write-Behind Pattern
- Immediate capture to Obsidian vault + PostgreSQL events
- Async embedding generation via background worker
- Neo4j percolation via scheduled jobs

### Background Workers
```python
# Embedding Worker (workers/embedding_worker.py):
# - Polls PostgreSQL for pending embeddings every 10 seconds
# - Batch processing with retry mechanism
# - Provider fallback: Ollama → Gemini → Perplexity

# Lifecycle Scheduler (capture_server.py):
# - Runs every 5 minutes via APScheduler
# - Automates task state transitions
# - Auto-archives old drafts/completed tasks
```

### Graph Schema (Neo4j)
```
Session → contains → Decision
Decision → becomes → Task
Task → implemented by → Commit
Session ↔ related_to ↔ Session
```

### Task Lifecycle States
```
Draft → Ready → Active → Blocked → Completed → Archived
```

**Auto-Transitions**:
- Draft → Archived (inactive for 14 days)
- Ready → Draft (needs more info)
- Active → Blocked (no commits for 30 days)
- Blocked → Archived (stuck too long)
- Completed → Archived (after 90 days)

---

## API Endpoints

### Public Endpoints
- `GET /health` - Health check with database status
- `POST /auth/token` - Exchange API key for JWT token
- `POST /capture` - Receive conversation from extension (requires JWT)
- `POST /obsidian-update` - Linear sync endpoint
- `POST /linear/webhook` - Linear webhook receiver
- `GET /docs` - Swagger API documentation

### Authentication Flow
1. Extension sends static API key to `/auth/token`
2. Server returns short-lived JWT token
3. Extension uses JWT in `Authorization: Bearer <token>` header
4. JWT validates on each request

---

## Supported AI Platforms

| Platform | Status | Auto-Capture | Parser Location |
|----------|--------|--------------|-----------------|
| ChatGPT | ✅ Supported | Yes | parsers.py |
| Claude | ✅ Supported | Yes | parsers.py |
| Gemini | ✅ Supported | Yes | parsers.py |
| Perplexity | ✅ Supported | Yes | parsers.py |
| DeepSeek | ✅ Supported | Yes | parsers.py |
| Mistral | ✅ Supported | Yes | parsers.py |
| Qwen | ✅ Supported | Yes | parsers.py |
| AI Studio | ✅ Supported | Yes | smart_parser.py |

Platform configuration in `chrome-extension/platforms.json`

---

## Entry Points

### CLI Commands (`poetry run omega`)
- `init` - Initialize Neo4j schema
- `sync` - Sync Obsidian vault to Neo4j
- `lifecycle` - Enforce task lifecycle rules
- `status` - Check connection status
- `report` - Generate lifecycle report
- `stats` - Show task statistics
- `stale` - List stale tasks

### Server Commands
- `poetry run capture-server` - Start FastAPI server

### Python Module Execution
- `python -m omega_kg.lifecycle --dry-run` - Preview lifecycle changes

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `pyproject.toml` | Dependencies, scripts, test config |
| `docker-compose.yml` | Database services (Neo4j, PostgreSQL) |
| `.env.example` | Complete environment template |
| `pytest.ini` | Test markers and configuration |
| `.pre-commit-config.yaml` | Code quality hooks |
| `settings.py` | Configuration management (Bitwarden + env) |
| `capture_server.py` | FastAPI server with lifespan management |
| `lifecycle.py` | Task state automation |
| `linear_sync.py` | Linear API sync |
| `conftest.py` | Test fixtures and testcontainers config |

---

## Troubleshooting

### Extension Issues
```powershell
# Diagnose extension
.\scripts\diagnose-extension.ps1

# Reload extension tabs
.\scripts\reload-extension-tabs.ps1
```

### Server Issues
```bash
# Check server health
curl http://localhost:8765/health

# View server logs
docker compose logs -f capture-server
```

### Database Issues
```bash
# Check Neo4j connection
docker compose exec neo4j cypher-shell -u neo4j -p password "MATCH (n) RETURN count(n)"

# Check PostgreSQL
docker compose exec postgres psql -U omega_user -d omega_kg -c "SELECT count(*) FROM raw_linear_events;"
```

### Testcontainers Issues
```bash
# If tests fail with "AuthenticationRateLimit"
# This is a known Neo4j 5.x issue with Testcontainers
# conftest.py handles this with exponential backoff

# Ensure Docker is running
docker ps
```

---

## Development Workflow

### Daily Development
```bash
# 1. Setup (first time only)
poetry install --with dev
cp .env.example .env

# 2. Start services
docker compose up -d

# 3. Start development
poetry run capture-server

# 4. Load Chrome extension
.\scripts\load-extension.ps1  # Windows
# OR manually: chrome://extensions → Load unpacked → chrome-extension/
```

### Before Submitting PR
```bash
# Run quality checks
poetry run pre-commit run --all-files

# Run tests
poetry run pytest -m "unit"

# Run specific integration tests
poetry run pytest -m "integration" -v
```

---

## Related Documentation

- **CLAUDE.md** - Comprehensive developer guide with examples
- **README.md** - Project overview with architecture diagrams
- **docs/20251130/DEVELOPER_QUICKSTART.md** - Detailed setup guide
- **docs/TROUBLESHOOTING.md** - Common issues and solutions
- **docs/PORT_MAPPING.md** - Network configuration
