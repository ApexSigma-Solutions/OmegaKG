# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is Omega_KG?

Omega_KG is a **FastAPI-based knowledge management system** that automatically captures AI conversations (ChatGPT, Claude, Gemini, etc.) and transforms them into a searchable knowledge graph. It uses a Chrome extension to capture conversations, a FastAPI capture server to process them, and dual databases (PostgreSQL for events/vectors + Neo4j for graph relationships) to store and connect ideas.

**System Flow**: Chrome Extension → Capture Server (FastAPI) → Obsidian Vault + Neo4j + PostgreSQL

---

## Common Development Commands

### Project Setup
```bash
# Install dependencies
poetry install --with dev

# Create environment config
cp .env.example .env
# Edit .env with OBSIDIAN_VAULT_PATH, NEO4J_PASSWORD, POSTGRES_PASSWORD, etc.

# Start databases
docker compose up -d neo4j-db postgres-db
```

### Development Server
```bash
# Start capture server (port 8765)
poetry run capture-server

# Run lifecycle checks (task state management)
poetry run python -m omega_kg.lifecycle --dry-run

# Run CLI commands
poetry run omega --help
```

### Testing
```bash
# Run all tests
poetry run pytest

# Run specific test types
poetry run pytest -m "unit"                    # Unit tests only
poetry run pytest -m "integration"             # Integration tests
poetry run pytest -m "requires_neo4j"          # Neo4j required

# Run with coverage
poetry run pytest --cov=omega_kg --cov-report=xml

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

### Docker
```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f omega-kg

# Restart specific service
docker compose restart neo4j-db

# Stop all services
docker compose down
```

### Documentation
```bash
# Serve documentation locally
poetry run mkdocs serve

# Build documentation
poetry run mkdocs build
```

### PowerShell Scripts (Windows)
```powershell
.\scripts\Start-OmegaKGDev.ps1           # Quick start dev environment
.\scripts\smoke_test.py                   # Run smoke tests
.\scripts\diagnose-extension.ps1          # Debug extension issues
.\scripts\load-extension.ps1              # Load Chrome extension
```

---

## Architecture Overview

### What Makes This Project Unique

1. **Dual Database Strategy**: PostgreSQL for events/vectors + Neo4j for graph relationships
2. **Zero-Trust Security**: Bitwarden SDK integration with fallback to environment variables
3. **Async Everything**: Async/await throughout (FastAPI, SQLAlchemy, Neo4j, asyncpg)
4. **Write-Behind Pattern**: Immediate capture, async embedding generation
5. **Task Lifecycle Automation**: Auto-state transitions with APScheduler (Draft → Ready → Active → Blocked → Completed → Archived)
6. **Multi-Provider Fallback**: Embedding generation with Ollama → Gemini → Perplexity fallback
7. **Chrome Extension Integration**: Real-time conversation capture from multiple AI platforms
8. **Linear Task Management**: Bidirectional sync with Linear for task automation

### Core Components

**Capture Server** (`capture_server.py`, 33KB):
- FastAPI application (port 8765) with lifespan management
- Receives conversations from Chrome extension via `POST /capture`
- Saves to Obsidian vault, creates Neo4j graph relationships
- Background scheduler for task lifecycle management (every 5 minutes)
- Embedding worker initialization

**Chrome Extension** (`chrome-extension/`):
- Manifest V3 extension
- Captures conversations from supported AI platforms
- Supported: Claude, ChatGPT, Gemini, Perplexity, DeepSeek, Mistral, Qwen
- Sends data to capture server

**Database Layer** (`database/`):
- **PostgreSQL** (port 5433): Event storage, vector embeddings (pgvector)
- **Neo4j** (ports 7474/7687): Graph relationships (Sessions → Decisions → Tasks → Commits)

**Domain Models** (`domain/linear/`):
- Pydantic models for Linear webhook processing
- Data mapping and processing logic
- Graph writer for Neo4j relationships

### Directory Structure

```
omega_kg/
├── capture_server.py       # FastAPI entry point with lifespan management
├── main.py                 # FastAPI app factory
├── cli.py                  # CLI commands (poetry run omega)
├── settings.py             # Configuration (Bitwarden + env vars)
├── config.py               # Runtime configuration constants
│
├── database/               # Database layer
│   ├── base.py             # SQLAlchemy Base
│   ├── graph.py            # Neo4j async driver
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
│   └── linear.py           # RawLinearEvent model
│
├── routers/                # FastAPI route modules
│   └── linear_receiver.py  # Linear webhook endpoint
│
├── workers/                # Background workers
│   └── embedding_worker.py # Async vector generation
│
├── lifecycle.py            # Task state automation
├── linear_sync.py          # Linear API sync
├── percolation.py          # Insight extraction
├── vector_store.py         # PostgreSQL vector operations (pgvector)
└── obsidian_sync.py        # Vault synchronization
```

### Key Relationships

**Graph Schema** (Neo4j):
- `Session` → contains → `Decision`
- `Decision` → becomes → `Task`
- `Task` → implemented by → `Commit`
- `Session` ↔ related_to ↔ `Session`

### Supported AI Platforms

| Platform     | Status | Auto-Capture |
|--------------|--------|--------------|
| ChatGPT      | ✅ Supported | Yes |
| Claude       | ✅ Supported | Yes |
| Gemini       | ✅ Supported | Yes |
| Perplexity   | ✅ Supported | Yes |
| DeepSeek     | ✅ Supported | Yes |
| Mistral      | ✅ Supported | Yes |
| Qwen         | ✅ Supported | Yes |
| AI Studio    | ✅ Supported | Yes |

### Task Lifecycle Automation

**States**: Draft → Ready → Active → Blocked → Completed → Archived

**Auto-Transitions** (runs every 5 minutes):
- Draft → Archived (inactive for 14 days)
- Ready → Draft (needs more info)
- Active → Blocked (no commits for 30 days)
- Blocked → Archived (stuck too long)
- Completed → Archived (after 90 days)

**Commands**:
```bash
# Preview lifecycle changes
python -m omega_kg.lifecycle --dry-run
```

---

## Configuration

### Environment Variables

**Required in `.env`**:
```env
# Obsidian vault location
OBSIDIAN_VAULT_PATH=D:\path\to\vault

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_PASSWORD=your-password

# PostgreSQL
POSTGRES_SERVER=127.0.0.1
POSTGRES_PORT=5433
POSTGRES_DB=omega_kg
POSTGRES_USER=omega_user
POSTGRES_PASSWORD=your-password

# Server
APP_HOST=0.0.0.0
APP_PORT=8765

# Extension authentication
EXTENSION_API_KEY_PRD=your-api-key
```

### Configuration Sources (Priority Order)
1. **Bitwarden Secrets** (if `BWS_ACCESS_TOKEN` set)
2. **Environment Variables** (`.env`)
3. **Defaults** (in `settings.py`)

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

### Port Reference
| Service | Port | Access |
|---------|------|--------|
| Capture Server | 8765 | http://localhost:8765 |
| Neo4j Browser | 7474 | http://localhost:7474 |
| Neo4j Bolt | 7687 | Database connection |
| PostgreSQL | 5433 | Database connection |
| MkDocs Dev | 8000 | http://localhost:8000 |

---

## Entry Points

### Main Commands
- **`poetry run capture-server`** - Start FastAPI server
- **`poetry run omega`** - Main CLI
- **`python -m omega_kg.lifecycle`** - Task lifecycle management

### API Endpoints
- `GET /health` - Health check with database status
- `POST /capture` - Receives conversations from extension
- `POST /linear/webhook` - Linear webhook receiver
- `GET /docs` - Swagger API documentation

---

## Key Files

- **`pyproject.toml`** - Dependencies, scripts, test config
- **`docker-compose.yml`** - Database services (Neo4j, PostgreSQL)
- **`.env.example`** - Complete environment template (157 lines)
- **`pytest.ini`** - Test markers and configuration
- **`.pre-commit-config.yaml`** - Code quality hooks

---

## Background Workers

### Embedding Worker
- Async worker in `workers/embedding_worker.py`
- Polls PostgreSQL for pending embeddings every 10 seconds
- Batch processing with retry mechanism
- Provider fallback: Ollama → Gemini → Perplexity

### Lifecycle Scheduler
- Runs every 5 minutes (configured in `capture_server.py`)
- Automates task state transitions
- Auto-archives old drafts/completed tasks
- Blocks tasks with no commits

---

## Testing Architecture

### Test Markers
- `unit` - Fast unit tests
- `integration` - Requires live databases
- `slow` - Long-running tests
- `requires_neo4j` - Needs Neo4j instance
- `requires_postgres` - Needs PostgreSQL instance

### Current Test Status
- ~80 tests total
- Coverage: ~46% (81 tests passing)
- Target: 80%+ coverage

---

## External Integrations

### Linear (Task Management)
- Webhook-based sync (`POST /linear/webhook`)
- Creates tasks from decisions automatically
- Tracks state changes in both systems

### Obsidian Vault
- Saves conversations as markdown files
- Bidirectional sync with Neo4j graph
- Frontmatter metadata for indexing

### Embedding Providers
- **Ollama** (local, default) - http://localhost:11434
- **Gemini** (cloud fallback)
- **Perplexity** (cloud fallback)

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
docker compose logs -f omega-kg
```

### Database Issues
```bash
# Check Neo4j connection
docker compose exec neo4j-db cypher-shell -u neo4j -p password "MATCH (n) RETURN count(n)"

# Check PostgreSQL
docker compose exec postgres-db psql -U omega_user -d omega_kg -c "SELECT count(*) FROM raw_linear_events;"
```

---

## See Also

- **[Full Documentation](./docs/index.md)** - Comprehensive guides
- **[Port Mapping](./docs/PORT_MAPPING.md)** - Network configuration
- **[Developer Quickstart](./docs/20251130/DEVELOPER_QUICKSTART.md)** - Detailed setup
- **[Testing Guide](./tests/README.md)** - Test suite documentation
- **[README.md](./README.md)** - Project overview with architecture diagrams
