# Agent Onboarding Checklist — omega_kg

Purpose
-------
Concise, actionable checklist for new agents and contributors to get productive quickly in this repository. Includes editor recommendations, debug steps, and common troubleshooting commands (Windows-focused).

Preliminaries
-------------
- Copy `.env.example` → `.env` and fill in values. The project uses Pydantic and will fail fast on missing required env vars.
- Install dependencies (Poetry recommended):

```powershell
poetry install
```

- Run pre-commit hooks locally before committing:

```powershell
pre-commit run --all-files
```

VS Code / Editor Setup
----------------------
- Recommended extensions:
  - Python (ms-python.python)
  - Pylance (ms-python.vscode-pylance)
  - Ruff (charliermarsh.ruff-vscode) or other linter integration
  - isort/Black integration or the Python extension's formatters
  - GitLens (eamodio.gitlens)
  - EditorConfig (editorconfig.editorconfig)
- Settings suggestions (user or workspace `settings.json`):
  - `python.languageServer`: `Pylance`
  - `editor.formatOnSave`: `true` (if using Black/ruff)
  - `python.formatting.provider`: `black`
  - `python.linting.enabled`: `true`
  - `python.linting.ruffEnabled`: `true`

Formatting & Static Analysis
----------------------------
- Type hints: required for all functions; run `mypy` where configured.
- Linting/formatting: prefer `ruff` + `black` + `isort`. Use pre-commit to enforce rules.

Run / Debug Quick Commands
--------------------------
- Start capture server (dev):

```powershell
poetry run python -m omega_kg.capture_server
```

- Run CLI command:

```powershell
poetry run omega <command>
```

- Run tests (single file):

```powershell
poetry run pytest tests/test_something.py -q
```

- Run single test with coverage:

```powershell
poetry run pytest --cov=omega_kg tests/test_filename.py::test_function_name -v
```

Key Debugging Steps & Checks
----------------------------
- Environment & settings:
  - Ensure `.env` exists and has values from `.env.example` (Pydantic will raise on missing required values).
- Neo4j connectivity:
  - Quick check in code or using `neo4j` client: run `RETURN 1` to validate connectivity.
  - The code uses `with driver.session() as session:` pattern and falls back to mock mode on failure.
- PostgreSQL / Vector store:
  - Ensure vector store/Postgres is initialized before starting the embedding worker.
  - Check `/health/vectors` endpoint in capture server for pending/failed counts.
- Embedding worker & scheduler:
  - Worker polls every 10s for pending embeddings; start capture server to spawn worker in dev.
  - Percolation runs every ~5 minutes in background scheduler; use logs to verify runs.
- Mock mode:
  - When Neo4j is unavailable, many components auto-fallback to `mock_mode=True`. Use this for local dev without DB.
- Logs & Vault:
  - Capture-related files are written into the Obsidian vault under `AI_Conversations/{platform}/` and `Sessions/`.
  - Check `vault/` or configured vault path for session files when debugging capture flows.

Common Troubleshooting Commands (PowerShell)
-------------------------------------------
```powershell
# Show recent git changes
git status
git rev-parse --abbrev-ref HEAD

# Run pytest with verbose output
poetry run pytest -k "pattern" -vv

# Run a script (e.g., coverage quick)
python scripts/coverage-report.py quick

# Check Python executable used by Poetry
poetry run python -c "import sys; print(sys.executable)"
```

Developer Notes & Gotchas
------------------------
- Dual persistence: updates to Neo4j must be mirrored to Obsidian frontmatter (see `lifecycle.py`).
- Task discovery uses glob `Tasks/**/{uid}*.md` — keep this pattern in mind for task-related changes.
- Capture endpoint has a 500KB payload limit; large payloads will be rejected.
- Chrome extension CORS: extension ID must match exactly in allowed origins.
- Linear webhook security: use HMAC-SHA256 verification implemented in `linear_sync.py`.

Where To Look First
-------------------
- `omega_kg/capture_server.py` — primary runtime, workers, and endpoints.
- `omega_kg/lifecycle.py` — lifecycle rules and dual-persistence logic.
- `omega_kg/percolation.py` & `omega_kg/parsers.py` — parsing and extraction logic.
- `omega_kg/settings.py` — environment variables and validation.

## Contributing

For guidance on branch strategy, PR workflows, or development questions, please reach out to the project maintainers or consult the repository's contribution guidelines.

