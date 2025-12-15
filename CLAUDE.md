# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is Omega_KG?

Omega_KG is an **AI conversation capture and knowledge graph system** that automatically transforms your AI conversations into a searchable, connected knowledge base. It captures conversations from ChatGPT, Claude, Gemini, Perplexity, DeepSeek, Mistral, AI Studio, and Qwen, then stores them across multiple data stores to create meaningful connections between ideas.

**System Architecture:**
```
Chrome Extension → Capture Server (FastAPI) → Dual Persistence
                                              ↓
                                         Linear Sync
```

The system uses a **write-behind pattern** with background workers for async processing, maintaining a dual-database architecture for optimal query performance.

## Technology Stack

- **Python 3.12+** with Poetry for dependency management
- **FastAPI** for REST API services
- **PostgreSQL + pgvector** for vector embeddings and event logging (1024-dim BGE-M3)
- **Neo4j** for graph database (relationships, decisions, tasks)
- **Chrome Extension** for real-time conversation capture
- **Ollama/NanoGPT/Gemini** for multi-provider embedding generation (with fallback chain)
- **Bitwarden SDK** for Zero Trust secret management
- **Docker Compose** for local services (Neo4j, PostgreSQL, Ollama)

## Common Commands

### Installation & Setup
```bash
# Install all dependencies (including dev)
poetry install --with dev

# Start development environment (PowerShell)
.\scripts\start-dev.ps1

# Copy environment template
cp .env.example .env
# Then edit .env with your configuration
```

### Running the Application
```bash
# Start capture server (main service on port 8765)
poetry run capture-server

# Start CLI
poetry run omega-kg serve

# With specific host/port
poetry run run omega-kg serve --host 0.0.0.0 --port 8765

# Lifecycle management (dry-run)
poetry run python -m omega_kg.lifecycle --dry-run
```

### Testing
```bash
# All tests (requires running services)
poetry run pytest

# Unit tests only (fast, no external dependencies)
poetry run pytest -m "unit"

# Integration tests (requires PostgreSQL, Neo4j)
poetry run pytest -m "integration"

# Skip slow tests
poetry run pytest -m "not slow"

# Run specific test file
poetry run pytest tests/test_capture_server.py

# Run specific test function
poetry run pytest tests/test_capture_server.py::test_function_name

# Run with coverage report
poetry run pytest --cov=omega_kg --cov-report=html
```

### Code Quality
```bash
# Run all pre-commit hooks
poetry run pre-commit run --all-files

# Ruff linting and formatting
poetry run ruff check .
poetry run ruff format .

# Type checking
poetry run mypy omega_kg/

# Security scanning
poetry run bandit -c pyproject.toml -r .
```

### Docker Services
```bash
# Start all services
docker-compose up --build

# Start databases only
docker-compose up neo4j postgres

# Start in detached mode
docker-compose up -d

# Start with dev profile
docker-compose --profile dev up -d
```

## Core Architecture

### Module Organization

| Module | Responsibility |
|--------|----------------|
| **capture_server.py** | FastAPI server (port 8765) - Main entry point for Chrome extension webhooks |
| **percolation.py** | Knowledge graph engine - Converts conversations to Neo4j nodes/relationships |
| **lifecycle.py** | Task state machine - Manages Draft → Ready → Active → Blocked/Completed → Archived |
| **linear_sync.py** | Linear.app integration - Bi-directional task synchronization |
| **vector_store.py** | PostgreSQL + pgvector integration - Vector storage for semantic search |
| **workers/embedding_worker.py** | Background worker - Async embedding generation from conversations |
| **settings.py** | Pydantic Settings + Bitwarden SDK - Configuration and secrets management |
| **database/graph.py** | Neo4j driver and schema management |
| **database/session.py** | PostgreSQL async sessions |
| **vault_utils.py** | Obsidian vault operations - Saves markdown files |
| **quipu_ollama_heartbeat.py** | Ollama health monitoring |

### Data Flow

1. **Chrome Extension** captures conversations in real-time from AI platforms
2. **capture_server.py** receives data via `/capture` endpoint (JWT authenticated)
3. **Dual Persistence**:
   - Raw events → PostgreSQL (with `pending_embedding` status)
   - Markdown → Obsidian vault
   - Graph extraction → Neo4j via `percolation.py`
4. **Background Worker** polls PostgreSQL for pending embeddings
5. **Embedding Generation**: Ollama → NanoGPT → Gemini → Mock (fallback chain)
6. **Vector Update**: Embeddings stored in PostgreSQL pgvector table
7. **Linear Sync**: Decisions/tasks automatically created/updated in Linear

### Service Ports

| Service | Port | Purpose |
|---------|------|---------|
| Capture Server | 8765 | FastAPI server |
| Neo4j Browser | 7474 | Graph visualization UI |
| Neo4j Bolt | 7687/7688 | Database connections |
| PostgreSQL | 5433 (stable) / 5434 (dev) | Vector storage |
| Ollama | 11434 | Local embeddings |

## Configuration

### Environment Variables
Key configuration in `.env`:

```bash
# Required paths
OBSIDIAN_VAULT_PATH=./vault          # Where to save conversations

# Database connections
NEO4J_URI=bolt://localhost:7687
NEO4J_PASSWORD=your_password
POSTGRES_HOST=localhost
POSTGRES_PASSWORD=your_password
POSTGRES_PORT=5433

# Application
APP_PORT=8765
OMEGA_ENV=dev                        # dev or stable
```

### Bitwarden Integration (Zero Trust)

For production, use Bitwarden Secrets instead of plaintext:

```bash
# Set Bitwarden access token
BWS_ACCESS_TOKEN=<machine_account_token>

# Then reference secret IDs in .env
POSTGRES_PASSWORD_PRD_ID=<uuid>
NEO4J_PASSWORD_PRD_ID=<uuid>
LINEAR_WEBHOOK_SECRET_PRD_ID=<uuid>
# ... other secret IDs
```

Settings are managed in `omega_kg/settings.py` via Pydantic Settings with Bitwarden SDK integration.

## Testing Strategy

### Test Organization
- **tests/** - Unit tests (fast, isolated, no external dependencies)
- **tests/integration/** - Integration tests (require live PostgreSQL, Neo4j)

### Test Markers
- `unit`: Unit tests only
- `integration`: Tests requiring live services
- `slow`: Long-running tests (>10s)
- `requires_neo4j`: Needs Neo4j instance
- `requires_postgres`: Needs PostgreSQL instance
- `not_requires_neo4j`: Skip Neo4j-dependent tests

### Running Tests

**Recommended workflow:**
```bash
# 1. Start required services
docker-compose up -d neo4j postgres

# 2. Run unit tests (fast feedback)
poetry run pytest -m "unit"

# 3. Run all tests with coverage
poetry run pytest --cov=omega_kg --cov-report=html

# 4. Run integration tests
poetry run pytest -m "integration"
```

## Development Tips

### Claude Code Permissions

`.claude/settings.local.json` configures:
```json
{
  "permissions": {
    "allow": ["Bash(poetry run pytest:*)"]
  }
}
```
**This allows running pytest commands via `poetry run pytest:*`**

### Key Files to Read First

1. **README.md** - Project overview, architecture diagrams, and quick start
2. **pyproject.toml** - Dependencies, scripts, and configuration
3. **omega_kg/capture_server.py** - Main server implementation
4. **omega_kg/settings.py** - Configuration management approach
5. **omega_kg/lifecycle.py** - Task state machine logic
6. **docs/PORT_MAPPING.md** - Service network configuration

### Common Development Tasks

**Adding a new AI platform:**
1. Update Chrome extension (`chrome-extension/`)
2. Add platform handler in `capture_server.py`
3. Update `percolation.py` for platform-specific parsing

**Adding database fields:**
1. Update SQLAlchemy models in `omega_kg/models/`
2. Create Alembic migration in `alembic/versions/`
3. Update corresponding database drivers

**Debugging:**
- Health check: `curl http://localhost:8765/health`
- Neo4j Browser: http://localhost:7474
- Extension logs: Chrome DevTools → Extensions → Omega_KG
- Check background worker: `poetry run python -m omega_kg.workers.embedding_worker`

### Troubleshooting

**"Failed to fetch" from extension**
→ Ensure `capture-server` is running on port 8765

**Neo4j connection failed**
→ Start services: `docker-compose up neo4j`

**No conversations appearing**
→ Reload extension: chrome://extensions → Reload

**Import errors**
→ Reinstall: `poetry install --with dev`

**Database migration issues**
→ Check Alembic: `poetry run alembic current` and `poetry run alembic upgrade head`
