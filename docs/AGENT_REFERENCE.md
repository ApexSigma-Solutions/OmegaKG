# Agent Reference — omega_kg

Purpose
-------
This document is a concise, persistent reference for agents onboarding into the `omega_kg` codebase. It highlights entry points, critical architecture patterns, common developer tasks, and commands to run and test the project locally.

Quick Start
-----------
- Environment: copy `.env.example` → `.env` and fill required values. Pydantic settings fail fast on missing vars.
- Install deps (project uses Poetry):

```powershell
poetry install
```

- Run capture server locally (default port 8765):

```powershell
poetry run python -m omega_kg.capture_server
```

- Run CLI: `poetry run omega` (entry: `omega_kg.cli:cli`).

Run & Test
-----------
- Run a single test with coverage:

```powershell
poetry run pytest --cov=omega_kg tests/test_filename.py::test_function_name -v
```

- Coverage helper scripts:

```powershell
python scripts/coverage-report.py quick
python scripts/coverage-report.py full
python scripts/coverage-report.py view
python scripts/coverage-report.py minimal
```

Key Entry Points
----------------
- Capture server: `omega_kg.capture_server` — main web/capture logic; embedding worker, percolation scheduler, health endpoints.
- CLI: `omega_kg.cli` — project command entry.
- Lifecycle enforcement: `omega_kg.lifecycle` — task lifecycle rules and background enforcement (supports `--dry-run`).
- Vector store: `omega_kg.vector_store` and embedding worker in `capture_server`.
- Neo4j-related code: `omega_kg.neo4j_schema`, Neo4j usage in `capture_server.py` and `lifecycle.py` (async driver pattern).

Project Layout (high level)
---------------------------
- `omega_kg/` — main package: capture_server, lifecycle, percolation, sync modules, utils and workers.
- `scripts/` — helpers: test scripts, setup and CI utilities.
- `docs/` — documentation and guides.
- `tests/` — unit/integration tests and fixtures.

Critical Patterns & Gotchas
--------------------------
- Dual persistence: Tasks are stored in Neo4j and mirrored to Obsidian markdown frontmatter; updates must keep both in sync (see `lifecycle.py`).
- Task file discovery uses glob `Tasks/**/{uid}*.md`.
- Mock mode: system auto-falls back to mock behavior when Neo4j is unavailable; many components accept `mock_mode=True`.
- Vector/embedding worker polls every 10s; vector store must be initialized before the worker starts.
- Config: environment-driven using `.env` and `.env.example` — no hardcoded secrets.
- Security: Chrome extension exchanges static API key for JWTs; CORS origin checks require exact extension ID.
- Payload limits: capture endpoint caps payloads at 500KB.
- Neo4j operations follow `with driver.session() as session:` and health-checks with `RETURN 1`.
- Linear webhooks require HMAC-SHA256 verification.

Percolation & Parsing Notes
---------------------------
- Decision extraction uses `settings.decision_keywords` and looks for `## Decision` headers.
- Task references use `[[PROJ-123]]` style patterns.
- Commit extraction looks for `#### Git Commit [repo]: hash` blocks.

Task Lifecycle Rules (summary)
-----------------------------
- Draft → Archived: 14 days (10 days warning) unless pinned.
- Active → Blocked: 30 days without commits.
- Completed → Archived: 90 days.

Testing & CI
------------
- Use pytest markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.requires_neo4j`.
- Tests create a `./test_vault` automatically for vault-related tests.
- Coverage threshold is enforced at 70% (see `pyproject.toml`).

Developer Tips
--------------
- Use `encoding="utf-8"` for all file IO.
- Use `datetime.now().isoformat()` for timestamps.
- Follow import order: standard, third-party, local.
- Logging: `logger = logging.getLogger(__name__)`.

Files to inspect first
----------------------
- `omega_kg/capture_server.py` — primary runtime for capture, embedding worker, and health endpoints.
- `omega_kg/lifecycle.py` — task lifecycle rules and dual-persistence logic.
- `omega_kg/percolation.py` and `omega_kg/parsers.py` — extraction and parsing logic.
- `omega_kg/settings.py` — environment variable definitions and validation.

Next Steps
----------
- Review this file and tell me if you want a shorter quick-start README or a PR-ready onboarding checklist. I can also add editor/IDE tips and common debugging commands.

---

Persisted at `docs/AGENT_REFERENCE.md`.
