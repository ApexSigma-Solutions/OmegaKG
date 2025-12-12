# Suggested Commands — Omega_KG (Windows / PowerShell)

Quick reference of commands you will use daily when developing and testing Omega_KG.

## Setup
```powershell
git clone https://github.com/ApexSigma-Solutions/omega_kg.git
cd omega_kg
poetry install --with dev
cp .env.example .env  # Edit .env with local secrets
```

## Development server
```powershell
# Start capture server (FastAPI + Uvicorn)
poetry run capture-server
# or
poetry run python -m omega_kg.capture_server
```

## Tests
```powershell
# Run all tests
poetry run pytest
# Quick unit-only tests
poetry run pytest -m "not requires_neo4j"
# Run a single test file with coverage
poetry run pytest --cov=omega_kg tests/test_filename.py::test_function_name -v
```

## Linters & Type Checking
```powershell
poetry run ruff check .
poetry run mypy omega_kg/
poetry run black omega_kg/ tests/ --check
poetry run pre-commit run --all-files
```

## Useful scripts & utilities
```powershell
# Lifecycle dry-run to preview automated transitions
poetry run python -m omega_kg.lifecycle --dry-run

# Run CLI entrypoint
poetry run omega <command>

# Coverage / reporting helpers
python scripts/coverage-report.py quick
python scripts/coverage-report.py full
python scripts/coverage-report.py view
```

## Chrome extension
- Load the `chrome-extension/` folder via `chrome://extensions` → Developer mode → Load unpacked
- Ensure `EXTENSION_API_KEY_PRD` or `EXTENSION_API_KEY_PRD` is set in `.env`

## Notes
- On Windows, prefer PowerShell; commands above are PowerShell-ready.
- Keep `origin/alpha` as the base branch for merges and ensure CI passes before merge.
