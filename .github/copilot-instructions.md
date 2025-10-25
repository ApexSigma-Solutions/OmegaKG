# Omega_KG: AI Coding Agent Instructions

## Project Architecture & Core Concepts

**Knowledge Graph System**: Omega_KG is a Neo4j-powered knowledge management system that bridges Obsidian vaults, Linear tasks, and Git commits. The core architecture involves:

- **Package location**: All code is under `omega_kg/` (not `src/`). Main config is in `omega_kg/settings.py`.
- **Data flow**: Obsidian markdown → Neo4j graph → Linear sync → Git tracking
- **Core modules**:
  - `lifecycle.py`: Task state transitions with time-based rules and email notifications
  - `linear_sync.py`: Bidirectional sync between Linear and Obsidian via Neo4j
  - `percolation.py`: Extract commits/tasks from markdown content into database
  - `poc_okg.py`: Neo4j connection and data ingestion proof-of-concept

## Environment & Configuration

**Settings Pattern**: All config via Pydantic BaseSettings in `omega_kg/settings.py`:
```python
from omega_kg.settings import settings
# Access: settings.neo4j_uri, settings.obsidian_vault_path, etc.
```

**Required Environment Variables** (use `.env` file with values from `.env.example`):
- Neo4j: `NEO4J_URI` (e.g., `bolt://localhost:7687`), `NEO4J_USER`, `NEO4J_PASSWORD`
- Obsidian: `OBSIDIAN_VAULT_PATH` (path to vault directory)
- Email (optional): `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_TO`
- App: `APP_ENV` (development|production)

⚠️ **NOTE**: `.env.example` has been corrected to match actual Neo4j usage (was out of sync with PostgreSQL references)

## Neo4j Data Schema & Integration Patterns

**Connection Pattern** (used in `lifecycle.py`, `linear_sync.py`):
```python
from omega_kg.settings import settings
from neo4j import GraphDatabase

driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))
with driver.session() as session:
    result = session.run("MATCH (n) RETURN n LIMIT 1")
```

**Node Types & Properties**:
- **ChatSession**: `date`, `topic` - Represents decision-making sessions
- **Decision**: `content` - Decisions made within sessions
- **Task**: `uid`, `title`, `filepath`, `status`, `linear_id`, `linear_status`, `linear_priority`, `created`, `transitioned_at`, `pinned`, `warned`
- **Commit**: `hash`, `message`, `repo`, `timestamp`

**Relationships**:
- `ChatSession -[:CONTAINS]-> Decision`
- `Task -[:IMPLEMENTS]-> Decision`
- `Commit -[:IMPLEMENTS]-> Task`
- `Session -[:CONTAINS_COMMIT]-> Commit`

**Task Lifecycle States** (`lifecycle.py:TaskStatus` enum):
- `draft` → `ready` → `active` → `blocked` → `completed` → `archived`
- Rules enforce auto-transitions based on age and conditions (see `TaskLifecycle.RULES`)

**Example Cypher Query** (from `lifecycle.py`):
```cypher
MATCH (t:Task)
WHERE t.status = 'draft'
  AND duration.between(t.created, datetime()).days > 14
  AND NOT t.pinned = true
RETURN t.uid, t.title, t.filepath
ORDER BY t.created DESC
```

**Obsidian ↔ Neo4j Sync** (`linear_sync.py`):
- Markdown frontmatter is parsed via `python-frontmatter`
- Linear webhook updates trigger Neo4j queries and Obsidian file updates
- Status mapping: `Backlog→draft`, `Todo→ready`, `In Progress→active`, `Done→completed`, `Canceled→archived`

## Development Workflow

**Dependency Management**: Poetry with Python 3.14+ requirement
```bash
poetry install --with dev    # Development dependencies (Black, Ruff, Pytest-Cov, Pre-Commit)
poetry install --with docs   # Documentation (MkDocs, mkdocstrings)
poetry run python -m omega_kg.lifecycle  # Run lifecycle enforcement directly
```

**Quality Assurance Pipeline**:
- **Local pre-commit** (`.pre-commit-config.yaml`): Ruff, MyPy, Bandit (Windows-compatible subset)
- **Trunk** (`trunk check --all`, `trunk fmt`): Full lint/format/security suite
- **CI** (`.github/workflows/ci.yml`): Semgrep, Trivy, Snyk, ZAP + pytest coverage on Ubuntu
- **Pre-commit difference**: Windows uses lightweight checks; full security suite runs in CI

**Task Automation** (Windows PowerShell in `scripts/`):
- `schedule-lifecycle.ps1`: Creates Windows scheduled task (runs daily at 9 AM)
  ```powershell
  poetry run python -m omega_kg.lifecycle
  ```
- `install-hooks.ps1`: Pre-commit hook setup
- `pre-commit-full.ps1`: Run complete CI-like checks locally

## Documentation & API

- **MkDocs Material** with `mkdocstrings` for auto-generated API docs from Google-style docstrings
- **Deployment**: GitHub Actions builds and deploys docs automatically (`.github/workflows/mkdocs.yml`)
- **Structure**: `docs/index.md` (overview), `docs/reference.md` (API reference)
- **Docstring style**: Google-style for mkdocstrings extraction

## Key Integration Points & Patterns

1. **Obsidian → Neo4j**:
   - Parse markdown with `python-frontmatter`
   - Extract commit/task metadata from frontmatter
   - Link to decisions via Linear ID matching

2. **Linear ↔ Neo4j** (via webhooks):
   - Receive webhook payload in `LinearSync.handle_linear_webhook()`
   - Update Task nodes with Linear status/priority
   - Sync changes back to Obsidian files via frontmatter

3. **Git → Knowledge Graph**:
   - Parse commit messages for Linear IDs and task links
   - Create Commit nodes with message, hash, repo, timestamp
   - Link to Task nodes via `IMPLEMENTS` relationship

4. **Task Lifecycle Enforcement**:
   - Time-based state transitions (draft auto-archives after 14 days unless pinned)
   - Stale detection (active tasks → blocked after 30 days without commits)
   - Email notifications and warning states before auto-transitions
   - Dry-run mode available for testing

## Critical Fixes Applied

- ✅ Import paths corrected: `src.settings` → `omega_kg.settings` (in `linear_sync.py`)
- ✅ `.env.example` aligned with actual Neo4j configuration (was PostgreSQL)
- ✅ PowerShell script updated to use module-based execution: `python -m omega_kg.lifecycle`

---
