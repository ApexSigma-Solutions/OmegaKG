# Suggested Commands — Omega_KG Development

## Setup & Dependencies
```powershell
# Install dependencies (with dev & docs extras)
poetry install --with dev --with docs

# Create .env from template
cp .env.example .env
# Edit .env with your Neo4j credentials, Obsidian path, etc.
code .env
```

## Running the Application

### Capture Server (FastAPI)
```powershell
# Start capture server (listens on http://localhost:8765)
poetry run capture-server
# or
poetry run python -m omega_kg.capture_server
```

### Lifecycle Enforcement
```powershell
# Run task lifecycle enforcement (dry-run, safe to test)
poetry run python -m omega_kg.lifecycle --dry-run

# Run live (applies state transitions)
poetry run python -m omega_kg.lifecycle
```

### CLI Entrypoint
```powershell
# Show help
poetry run omega --help
```

## Testing & Code Quality

### Run Tests
```powershell
# Run all tests
poetry run pytest

# Run fast tests only (skip Neo4j-dependent)
poetry run pytest -m "not requires_neo4j"

# Run specific test file
poetry run pytest tests/test_lifecycle.py

# Run with coverage
poetry run pytest --cov=omega_kg --cov-report=html

# Run only marked tests
poetry run pytest -m requires_neo4j
poetry run pytest -m unit
poetry run pytest -m slow
```

### Linting & Formatting
```powershell
# Check code with Ruff
poetry run ruff check .

# Auto-fix with Ruff
poetry run ruff check . --fix

# Type check with MyPy
poetry run mypy omega_kg/

# Format with Black (usually called by pre-commit)
poetry run black omega_kg/ tests/

# Run all pre-commit checks
poetry run pre-commit run --all-files
```

### Install Pre-commit Hooks
```powershell
# Install git hooks (auto-runs checks before commit)
poetry run pre-commit install
```

## Documentation
```powershell
# Serve docs locally (MkDocs)
poetry run mkdocs serve
# View at http://localhost:8000

# Build docs
poetry run mkdocs build
```

## Chrome Extension

### Load Unpacked in Chrome
1. Open `chrome://extensions`
2. Toggle "Developer mode" ON
3. Click "Load unpacked"
4. Select the `chrome-extension/` directory

### Test & Debug
- Open DevTools (F12) on target page (Gemini, ChatGPT, etc.)
- Check Console for errors (storage, runtime.lastError, selector mismatches)
- Verify selectors in Console:
  - Gemini container: `document.querySelector('[role="main"]')`
  - Gemini user messages: `document.querySelectorAll('[data-blocks-role="message"][data-message-role="user"]')`

## Git & Branches
```powershell
# Fetch latest remote branches
git fetch --all

# Create feature branch from alpha
git checkout -b feature/my-feature origin/alpha

# Push feature branch
git push -u origin feature/my-feature

# List all branches (local & remote)
git branch -a
```

## Troubleshooting

### "Module not found" errors
```powershell
# Reinstall dependencies
poetry install --with dev
```

### Neo4j connection errors
- Verify NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD in .env
- Ensure Neo4j instance is running
- Test: `poetry run python -c "from neo4j import GraphDatabase; print('OK')"`

### Extension not capturing messages
- Reload extension: `chrome://extensions` → Find Omega_KG → Reload button
- Check selectors in DevTools Console (see above)
- Verify host_permissions in `manifest.json` includes target site

### Pre-commit hook failures
- Run `poetry run pre-commit run --all-files` to see all failures
- Auto-fix with Ruff: `poetry run ruff check . --fix`
- Format with Black: `poetry run black omega_kg/ tests/`
- Then commit again
