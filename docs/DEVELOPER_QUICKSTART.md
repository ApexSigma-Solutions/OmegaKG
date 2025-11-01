# Omega_KG Developer Quick Start Guide

**Last Updated:** October 30, 2025  
**Status:** ✅ All systems operational (81 tests passing, 46.87% coverage)

## What is Omega_KG?

A Neo4j-powered knowledge management system that captures AI conversations, syncs with Linear tasks, and tracks implementation through Git commits. Built with Python, FastAPI, and a Chrome extension.

---

## 1️⃣ Setup (5 minutes)

### Prerequisites
- Python 3.12+ (tested on 3.13)
- Poetry (package manager)
- Neo4j instance (local or cloud; we use `localhost:7474` in a Docker container)
- Git

### Install & Configure

```powershell
# Clone (if not done)
git clone https://github.com/ApexSigma-Solutions/omega_kg.git
cd omega_kg

# Install dependencies (with dev tools)
poetry install --with dev --with docs

# Copy and edit environment config
cp .env.example .env
code .env  # Edit NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, OBSIDIAN_VAULT_PATH, etc.

# Test config loads correctly
poetry run python -c "from omega_kg.settings import settings; print('✓ Settings loaded')"
```

---

## 2️⃣ Running the Application

### Start Capture Server (Message Capture API)
```powershell
poetry run capture-server
# Runs on http://localhost:8765
# Health check endpoint: GET /health
# Capture endpoint: POST /capture (JSON payload with messages)
```

### Task Lifecycle Management
```powershell
# Dry-run (preview what would happen)
poetry run python -m omega_kg.lifecycle --dry-run

# Live enforcement (applies state transitions)
poetry run python -m omega_kg.lifecycle

# Via CLI
poetry run omega lifecycle --help
poetry run omega stats
poetry run omega stale
poetry run omega sync
```

### View Documentation
```powershell
poetry run mkdocs serve
# View at http://localhost:8000
```

---

## 3️⃣ Chrome Extension Setup

### Load Extension into Chrome

**Option A: Automatic (PowerShell script)**
```powershell
.\scripts\load-extension.ps1
# Validates manifest, checks selectors, opens Chrome to extensions page
```

**Option B: Manual**
1. Open `chrome://extensions`
2. Toggle "Developer mode" **ON** (top right)
3. Click "Load unpacked"
4. Select the `chrome-extension/` folder from this repo
5. Open DevTools (F12) on any supported site

### Supported Sites
- 🟢 **Gemini** (`gemini.google.com`)
- 🟢 **ChatGPT** (`chat.openai.com`)
- 🟢 **Claude** (`claude.ai`)
- 🟢 **Perplexity** (`perplexity.ai`)
- 🟢 **GitHub Copilot** (`github.com`)
- 🟢 **Qwen** (`chat.qwen.ai`)
- 🟢 **Microsoft Copilot** (`copilot.microsoft.com`, `copilot.com`)

### Test the Extension
1. Ensure capture-server is running: `poetry run capture-server`
2. Open a supported site (e.g., Gemini)
3. Open DevTools Console (F12 → Console tab)
4. Look for `[Omega_KG]` log messages
5. Start a conversation and check if messages appear in Neo4j

### Troubleshooting
| Problem | Solution |
|---------|----------|
| "Access to storage not allowed" | Confirm manifest has `"storage"` permission; use background worker for storage access |
| No messages captured (messagesFound: 0) | Check selectors in DevTools; verify `run_at: document_idle` in manifest |
| "Unchecked runtime.lastError" | Check background service worker console (`chrome://extensions` → Service worker) |
| Extension not injecting on page | Reload extension icon on `chrome://extensions` |
| Capture-server not accepting messages | Ensure server running on port 8765; check firewall |

---

## 4️⃣ Testing

### Run Tests
```powershell
# All tests (fast + Neo4j)
poetry run pytest

# Fast tests only (skip Neo4j)
poetry run pytest -m "not requires_neo4j"

# Specific test file
poetry run pytest tests/test_lifecycle.py -v

# With coverage report
poetry run pytest --cov=omega_kg --cov-report=html

# Specific markers
poetry run pytest -m unit
poetry run pytest -m slow
poetry run pytest -m requires_neo4j
```

### Current Test Coverage
```
Module                  Coverage   Status
─────────────────────────────────────────
check_nodes.py          96.00%     ✅ Excellent
cli.py                  97.22%     ✅ Excellent
percolation.py          90.52%     ✅ Very Good
linear_sync.py          69.57%     ✅ Good
obsidian_sync.py        47.95%     ⚠️  Medium
lifecycle.py            41.05%     ⚠️  Medium
neo4j_schema.py         44.87%     ⚠️  Medium (needs Neo4j)
capture_server.py        0.00%     ⏭️  (functions not implemented)
───────────────────────────────────────
TOTAL                   46.87%     ✓ Healthy
```

**Status:** 81 tests passing ✅ | 3 skipped | 0 failures

---

## 5️⃣ Code Quality

### Pre-commit Hooks (runs automatically before commits)
```powershell
# Install hooks
poetry run pre-commit install

# Run manually (all checks)
poetry run pre-commit run --all-files
```

### Manual Checks
```powershell
# Linting (code style)
poetry run ruff check .
poetry run ruff check . --fix  # Auto-fix

# Type checking
poetry run mypy omega_kg/

# Formatting
poetry run black omega_kg/ tests/
poetry run black omega_kg/ tests/ --check  # Check without changing
```

---

## 6️⃣ Key Commands Reference

| Command | Purpose |
|---------|---------|
| `poetry install --with dev` | Install all dependencies |
| `poetry run capture-server` | Start message capture API |
| `poetry run omega lifecycle --dry-run` | Preview lifecycle changes |
| `poetry run pytest` | Run all tests |
| `poetry run ruff check .` | Check for lint errors |
| `poetry run mypy omega_kg/` | Check type hints |
| `poetry run mkdocs serve` | Build docs locally |
| `poetry run pre-commit run --all-files` | Run all pre-commit checks |
| `.\scripts\load-extension.ps1` | Load/validate Chrome extension |
| `git checkout -b feature/name` | Create feature branch |

---

## 7️⃣ Before Opening a PR

### Checklist
- [ ] Code passes all tests: `poetry run pytest`
- [ ] No linting errors: `poetry run ruff check .`
- [ ] Type hints valid: `poetry run mypy omega_kg/`
- [ ] Pre-commit passes: `poetry run pre-commit run --all-files`
- [ ] Docstrings updated (Google-style)
- [ ] Branch updated: `git pull origin alpha`
- [ ] `.env` secrets not committed
- [ ] If modified extension: tested on 2+ sites and selectors verified

### Push & Open PR
```powershell
git push origin feature/my-feature
# Open PR on GitHub → target branch: alpha
# Wait for CI (GitHub Actions) to pass
```

---

## 8️⃣ Architecture Quick Reference

### Main Modules
- **`settings.py`** — Configuration via Pydantic (loads from `.env`)
- **`capture_server.py`** — FastAPI server for message ingestion
- **`lifecycle.py`** — Automated task state transitions
- **`linear_sync.py`** — Bidirectional Linear ↔ Obsidian sync
- **`obsidian_sync.py`** — Markdown storage & frontmatter handling
- **`percolation.py`** — Extract commits/tasks from markdown
- **`neo4j_schema.py`** — Graph schema & initialization
- **`cli.py`** — Command-line interface

### Neo4j Data Model
```
ChatSession -[:CONTAINS]-> Decision
Task -[:IMPLEMENTS]-> Decision
Commit -[:IMPLEMENTS]-> Task
Session -[:CONTAINS_COMMIT]-> Commit
```

### Extension Files
- **`manifest.json`** — Permissions, host_permissions, service worker
- **`content.js`** — Injects into pages, extracts messages, sends to background
- **`background.js`** — Service worker, handles retry logic, forwards to capture-server

---

## 9️⃣ Common Issues & Solutions

### "Module not found" Error
```powershell
# Reinstall dependencies
poetry install --with dev
poetry run python -c "import omega_kg; print('OK')"
```

### Neo4j Connection Error
```
ERROR: Unable to connect to bolt://localhost:7687

Solution:
1. Verify Neo4j is running: http://localhost:7474/browser/
2. Check .env: NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
3. Test: poetry run python -c "from neo4j import GraphDatabase; ..."
```

### Extension Stops Capturing
```
Solution:
1. Reload extension: chrome://extensions → Reload button
2. Check DevTools Console for [Omega_KG] errors
3. Verify capture-server running: poetry run capture-server
4. Check if selectors match page DOM (use DevTools Inspector)
```

### Pre-commit Failures
```powershell
# See all failures
poetry run pre-commit run --all-files

# Auto-fix (Ruff + Black)
poetry run ruff check . --fix
poetry run black omega_kg/ tests/

# Commit again
git add . && git commit -m "Fix linting"
```

---

## 🔟 Useful Resources

- **Neo4j Browser**: http://localhost:7474/browser/
- **Capture-Server API Docs**: http://localhost:8765/docs (when running)
- **MkDocs**: http://localhost:8000 (when serving)
- **GitHub Repo**: https://github.com/ApexSigma-Solutions/omega_kg
- **GitHub Issues**: https://github.com/ApexSigma-Solutions/omega_kg/issues

---

## 📞 Quick Help

**Tests failing?**
```powershell
poetry run pytest tests/test_name.py -vv --tb=long
```

**Extension not working?**
```powershell
# Reload extension in Chrome
chrome://extensions  # Find Omega_KG → Reload

# Check background worker logs
chrome://extensions  # Find Omega_KG → Service worker (click "inspect")
```

**Need to update selectors?**
Edit `chrome-extension/content.js` → search for `extractMessages()` function → update selector objects under `const selectors = {...}`

---

**Happy coding!** 🚀
