# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Omega_KG** is a Neo4j-powered knowledge management system that bridges Obsidian vaults, Linear tasks, and Git commits. It captures AI conversations through a Chrome extension, manages task lifecycles with automated state transitions, and maintains a comprehensive knowledge graph.

## Development Commands

### Environment Setup
```bash
# Install dependencies
poetry install --with dev

# Copy environment template and configure required secrets
cp .env.example .env
# Edit .env with NEO4J_PASSWORD, OBSIDIAN_VAULT_PATH, EXTENSION_API_KEY,
# LINEAR_WEBHOOK_SECRET, CHROME_EXTENSION_ID, JWT_SECRET_KEY (all required)
```

### Running the System
```bash
# Initialize Neo4j schema (run once)
poetry run omega init

# Start capture server (FastAPI on port 8765)
poetry run capture-server

# Sync Obsidian vault to Neo4j
poetry run omega sync [--mock]

# Enforce task lifecycle rules
poetry run omega lifecycle [--dry-run] [--no-email]

# System health check
poetry run omega status

# View task statistics
poetry run omega stats

# List stale tasks
poetry run omega stale
```

### Testing
```bash
# Run all tests
poetry run pytest

# Run specific test markers
poetry run pytest -m unit
poetry run pytest -m integration
poetry run pytest -m requires_neo4j
poetry run pytest -m "not requires_neo4j"

# Run single test file
poetry run pytest tests/test_lifecycle.py

# Run with coverage (generates terminal, HTML, and XML reports)
poetry run pytest --cov=omega_kg --cov-report=html

# Coverage with specific formats
poetry run pytest --cov=omega_kg --cov-report=term-missing
poetry run pytest --cov=omega_kg --cov-report=xml:coverage.xml

# Coverage helper script (recommended)
python scripts/coverage-report.py quick   # Quick unit test coverage
python scripts/coverage-report.py full    # Full coverage with HTML report
python scripts/coverage-report.py view    # Open HTML report in browser
python scripts/coverage-report.py minimal # Check threshold only (70%)

# Smoke test capture server
poetry run python scripts/smoke-test-capture-server.py
```

**Coverage Documentation:** See [COVERAGE.md](COVERAGE.md) for detailed coverage guide.

### Code Quality
```bash
# Linting
poetry run ruff check .

# Type checking
poetry run mypy omega_kg/

# Code formatting
poetry run black .

# Run pre-commit hooks
poetry run pre-commit install
poetry run pre-commit run --all-files
```

### Documentation
```bash
# Serve docs locally
poetry run mkdocs serve
# View at http://localhost:8000
```

## Architecture Overview

### Core Data Flow

**Capture Flow**: Chrome Extension → FastAPI (`/capture`) → Markdown File (Obsidian vault) → Percolation → Neo4j (ChatSession + Decision nodes)

**Task Lifecycle Flow**: Neo4j Query (find violations) → Update Node → Update Obsidian Frontmatter → Email Report (optional)

**Linear Webhook Flow**: Linear → FastAPI (`/webhook/linear`) → HMAC Verification → Update Neo4j Task → Update Obsidian Frontmatter

**Sync Flow**: Obsidian Tasks/*.md Files → Parse Frontmatter → MERGE Task Nodes in Neo4j

### Key Modules

**`capture_server.py`** (FastAPI Server, Port 8765)
- Authentication: Static API key (X-API-Key) → JWT token (Bearer)
- Endpoints: `/auth/token`, `/capture`, `/webhook/linear`, `/health`
- Background scheduler: Batch percolates session logs every 5 minutes
- Dependencies: FastAPI, Uvicorn, APScheduler

**`lifecycle.py`** (Task State Machine)
- Task states: `draft → ready → active → blocked → completed → archived`
- Lifecycle rules: Draft decay (14d), stale active (30d), completion archive (90d)
- Enforcement: Updates Neo4j properties + Obsidian frontmatter + markdown body
- Reporting: Human-readable summary, optional email via SMTP

**`obsidian_sync.py`** (Vault ↔ Neo4j Sync)
- Scans `Tasks/*.md` files, parses YAML frontmatter
- MERGE Task nodes (creates if missing, updates if exists)
- Graceful degradation: Falls back to mock mode on connection failure

**`percolation.py`** (Markdown → Graph Extraction)
- Extracts structured data from markdown using regex patterns
- Task patterns: `[[PROJ-123]]`
- Commit patterns: `#### Git Commit [repo]: hash`
- Decision patterns: `## Decision` headers
- Creates Task, Commit, and Decision nodes with relationships

**`linear_sync.py`** (Linear Webhook Handler)
- Verifies HMAC-SHA256 signature (constant-time comparison)
- Routes webhook actions: `update` → sync issue, `remove` → handle deletion
- Updates Neo4j Task properties: `linear_status`, `linear_priority`, `linear_updated`
- Updates corresponding Obsidian file frontmatter

**`linear_client.py`** (Linear GraphQL Adapter)
- Creates Linear issues via GraphQL mutation (`issueCreate`)
- Returns issue ID and identifier (e.g., "APX-123")

**`smart_parser.py`** (Obsidian → Linear Creator)
- Parses Obsidian notes: `@assignee/username`, `@label/label-name`, `@priority/[0-4]`
- Creates Linear issues from markdown
- Uses JSON maps for user/label lookups

**`vault_utils.py`** (Filesystem Adapter)
- Safe read/write operations on Obsidian vault
- Methods: `read_note_frontmatter()`, `update_note_frontmatter()`, `resolve_path()`
- UTF-8 encoding, graceful error handling

**`ai_import.py`** (Conversation Bulk Importer)
- Imports exported conversations from Claude/ChatGPT
- Formats as markdown with frontmatter
- Percolates to Neo4j: ChatSession nodes with timestamps

**`neo4j_schema.py`** (Database Schema Manager)
- Initializes constraints: `task_uid` (unique), `plan_id` (unique)
- Initializes indexes: `task_status`, `task_created`
- Health checks with graceful fallback to mock mode

**`auth_utils.py`** (Authentication & Authorization)
- Bootstrap auth: `get_static_api_key()` validates X-API-Key header
- Dynamic auth: `create_access_token()` generates JWT, `validate_access_token()` validates
- Token lifetime: `JWT_EXPIRATION_MINUTES` (default 24 hours)
- Algorithm: HS256 (HMAC-SHA256)

**`cli.py`** (Click CLI)
- Entry point: `poetry run omega`
- Commands: `init`, `sync`, `lifecycle`, `status`, `stats`, `stale`, `report`

### Neo4j Data Model

**Node Types**:
- `ChatSession`: Conversation sessions (properties: `conversation_hash`, `date`, `platform`, `url`, `message_count`)
- `Decision`: Key decisions extracted from conversations (properties: `decision_id`, `content`, `extracted_at`)
- `Task`: Tasks with lifecycle states (properties: `uid` [unique], `title`, `status` [indexed], `created` [indexed], `linear_id`, `pinned`, `warned`, `transition_reason`)
- `Commit`: Git commits (properties: `hash` [unique], `message`, `repo`, `timestamp`)
- `Plan`: Parent planning containers (properties: `plan_id` [unique])

**Relationships**:
- `ChatSession -[:CONTAINS]-> Decision`
- `Task -[:IMPLEMENTS]-> Decision`
- `Commit -[:IMPLEMENTS]-> Task`
- `Session -[:CONTAINS]-> Decision`

### Obsidian Vault Structure

Convention-based directory layout:
```
vault/
├── Tasks/                    # Task notes (synced to Neo4j)
├── AI_Conversations/         # Captured conversations by platform
│   ├── Claude/
│   ├── ChatGPT/
│   ├── Gemini/
│   └── Perplexity/
└── Sessions/                 # Session logs for percolation
```

Files are markdown with YAML frontmatter containing metadata (uid, status, created, linear_id, etc.)

### Configuration (settings.py)

Uses Pydantic BaseSettings with environment variables. All secrets are **required** (fail-fast on missing):

**Required Secrets**:
- `NEO4J_PASSWORD` - Neo4j database password
- `OBSIDIAN_VAULT_PATH` - Path to Obsidian vault
- `EXTENSION_API_KEY` - Chrome extension authentication
- `LINEAR_WEBHOOK_SECRET` - Linear webhook HMAC verification
- `CHROME_EXTENSION_ID` - CORS allowlist for extension
- `JWT_SECRET_KEY` - JWT token signing (generate with `openssl rand -hex 32`)
- `JWT_ALGORITHM` - JWT algorithm (default: HS256)

**Optional Integrations**:
- Linear API: `LINEAR_API_KEY`, `LINEAR_TEAM_ID`, `LINEAR_WORKSPACE_ID`, `LINEAR_PROJECT_ID`
- Email: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_TO`
- GitHub: `GITHUB_TOKEN`
- AI Services: `NANOGPT_API_KEY`, `OPENROUTER_API_KEY`, `PERPLEXITY_API_KEY`, `GEMINI_API_KEY`

### Testing Patterns

**Shared Fixtures** (`tests/conftest.py`):
- `mock_env_vars` - Monkeypatch environment variables
- `test_vault_path` - Temporary vault directory
- `mock_neo4j_driver` - Mocked Neo4j driver (context manager)
- `mock_neo4j_session` - Mock session for queries
- `sample_*_data` - Predefined test data objects

**Test Markers**:
- `@pytest.mark.unit` - Unit tests (no external dependencies)
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.requires_neo4j` - Tests requiring live Neo4j instance
- `@pytest.mark.not_requires_neo4j` - Tests that work without Neo4j
- `@pytest.mark.slow` - Long-running tests

**Mock Pattern**: All modules support graceful degradation to `mock_mode=True` when Neo4j is unavailable.

## Critical Design Patterns

### 1. Graceful Degradation (Mock Mode)
All major components fall back to mock mode on Neo4j connection failure. This prevents system crashes and enables testing without a live database.

### 2. Connection Health Checks
Before operations, modules run simple queries (`RETURN 1`) to verify Neo4j connectivity. Raises exception on failure, triggering mock mode.

### 3. Security via Constants
- Static API key for bootstrap authentication (X-API-Key header)
- JWT bearer tokens for ongoing authentication (Authorization: Bearer header)
- HMAC-SHA256 signature verification for webhooks
- Constant-time comparison (`hmac.compare_digest()`) prevents timing attacks

### 4. Frontmatter as Contract
Markdown files carry metadata in YAML frontmatter. This is the source of truth for properties synced to Neo4j. Status field is indexed, UID field has unique constraint.

### 5. Deterministic ID Generation
- Task UIDs: Filename stem or frontmatter `uid`
- Decision IDs: Hash of first 3 words → "DEC-XXXX" format
- Conversation hash: MD5 of platform + URL + message count (8 chars)

### 6. Cypher Query Parameterization
All Neo4j queries use parameterized placeholders (`$variable`) to prevent injection and enable query optimization.

## Important Development Notes

### Environment First
Always verify `.env` configuration before debugging. Missing required secrets cause immediate failure on import. Test with `poetry run omega status`.

### Frontmatter Convention
The YAML frontmatter in markdown files is the contract between Obsidian and Neo4j. Changes to files flow back to Neo4j via sync commands. The `status` field is indexed, `uid` is unique.

### Authentication Flow
Chrome extension authenticates in two steps:
1. Bootstrap: Send X-API-Key header → Receive JWT token
2. Ongoing: Send Authorization: Bearer {token} header for all subsequent requests

### Percolation Scheduler
The capture server runs a background scheduler (APScheduler) every 5 minutes to batch percolate session logs from the `Sessions/` directory. This extracts tasks, commits, and decision links.

### CLI vs Server
CLI commands are synchronous (Click, no asyncio). Capture server is async (FastAPI). Both use the same Neo4j driver but cannot share connections across event loops.

### Testing Without Neo4j
Most tests use mocked Neo4j drivers. Use `@pytest.mark.requires_neo4j` for integration tests that need a live database. Run `pytest -m "not requires_neo4j"` to skip integration tests.

### Lifecycle Enforcement
The lifecycle module enforces time-based task state transitions:
- Draft decay: 14 days (with warning at 10 days)
- Stale active: 30 days with no commits
- Completion archive: 90 days

Always run with `--dry-run` first to preview changes before applying.

### Linear Webhook Security
Linear webhooks must include valid HMAC-SHA256 signature in `X-Linear-Signature` header. Signature is computed from request body and `LINEAR_WEBHOOK_SECRET`. Verification uses constant-time comparison.

## Git Workflow

- **Main branch**: `alpha`
- **Current branch**: `beta`
- Create PRs targeting `alpha` branch
- Commit messages follow conventional format: "feat:", "fix:", "chore:", etc.
- Pre-commit hooks enforce code quality (black, ruff, mypy)
