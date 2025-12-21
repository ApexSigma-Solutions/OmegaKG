# OmegaKG Scripts Map

**Version:** 4.4.2
**Last Updated:** 2025-12-21
**Environment:** Stable (d:\projects\OmegaKG\Omega_KG_stable)

---

## 📋 Table of Contents

1. [Quick Reference](#quick-reference)
2. [Active Scripts](#active-scripts)
3. [Deprecated Scripts](#deprecated-scripts)
4. [Workflows](#workflows)
5. [Shell Scripts (.sh)](#shell-scripts)
6. [Troubleshooting](#troubleshooting)

---

## 🚀 Quick Reference

### Most Common Operations

| Operation | Command |
|-----------|---------|
| **Start full stack** | `powershell -ExecutionPolicy Bypass -File scripts\start_full_stack.ps1` |
| **Verify stack** | `powershell -ExecutionPolicy Bypass -File scripts\verify_stack.ps1` |
| **Check status** | `powershell -ExecutionPolicy Bypass -File scripts\status.ps1` |
| **Stop all services** | `powershell -ExecutionPolicy Bypass -File scripts\cleanup_before_start.ps1` |
| **Load Chrome extension** | `powershell -ExecutionPolicy Bypass -File scripts\load-extension.ps1` |
| **Setup autostart** | `powershell -ExecutionPolicy Bypass -File scripts\setup-autostart.ps1` |

---

## 📝 Active Scripts

### Core Orchestration Scripts

#### 1. **start_full_stack.ps1** ⭐ CRITICAL
**Purpose:** Primary launcher for entire OmegaKG stack
**Dependencies:**
- Poetry installed at `C:\Users\steyn\AppData\Roaming\Python\Python312\Scripts\poetry.exe`
- Hookdeck CLI installed
- `.env` file with `HOOKDECK_API_KEY`
- Port 8765 available

**What it does:**
- Loads environment variables from `.env`
- Starts capture server via Poetry (U port 8765vicorn on)
- Starts Hookdeck gateway for webhook tunneling
- Logs to timestamped files in `logs/` directory

**Usage:**
```powershell
cd d:\projects\OmegaKG\Omega_KG_stable\scripts
.\start_full_stack.ps1
```

**Output:**
- Capture logs: `logs\capture_server_YYYY-MM-DD_HH-mm-ss.log` (stdout)
- Capture errors: `logs\capture_server_YYYY-MM-DD_HH-mm-ss.err.log` (stderr)
- Hookdeck logs: `logs\hookdeck_YYYY-MM-DD_HH-mm-ss.log`

---

#### 2. **verify_stack.ps1** ⭐ IMPORTANT
**Purpose:** Diagnostic verification of running stack
**Checks:**
- Python/Poetry processes running
- Hookdeck node process running
- Port 8765 availability
- API health endpoint (http://127.0.0.1:8765/health)
- HOOKDECK_API_KEY presence

**Usage:**
```powershell
.\verify_stack.ps1
```

**Typical Output:**
```
[OK] Poetry process found (PID: 12345)
[OK] Hookdeck process found (PID: 12346)
[OK] Port 8765 is listening
[OK] API health check passed
[OK] HOOKDECK_API_KEY is set
```

---

#### 3. **cleanup_before_start.ps1** ⭐ IMPORTANT
**Purpose:** Kill existing processes before fresh start
**What it does:**
- Stops all Poetry processes
- Kills Hookdeck node processes
- Waits 2 seconds for port release

**Usage:**
```powershell
.\cleanup_before_start.ps1
```

**Note:** Run this before `start_full_stack.ps1` to prevent port conflicts

---

### Setup & Configuration Scripts

#### 4. **enable_poetry_path.ps1** ⭐ IMPORTANT
**Purpose:** Add Poetry to system PATH
**What it does:**
- Adds `C:\Users\steyn\AppData\Roaming\Python\Python312\Scripts` to PATH
- Updates current session PATH
- Verifies Poetry is accessible

**Usage:**
```powershell
.\enable_poetry_path.ps1
```

**Note:** Requires administrator privileges for system PATH update

---

#### 5. **setup-autostart.ps1** ⭐ IMPORTANT
**Purpose:** Configure Windows Task Scheduler for auto-start at login
**What it does:**
- Creates `Omega_KG_CaptureServer` scheduled task
- Trigger: At log on (any user)
- Action: `powershell -ExecutionPolicy Bypass -File "D:\projects\OmegaKG\Omega_KG_stable\scripts\start_full_stack.ps1"`
- Working Directory: `D:\projects\OmegaKG\Omega_KG_stable`

**Usage:**
```powershell
.\setup-autostart.ps1
```

**Note:** Requires administrator privileges

---

#### 6. **schedule-lifecycle.ps1** ⭐ IMPORTANT
**Purpose:** Schedule daily lifecycle task for task state transitions
**What it does:**
- Creates `Omega_KG_Lifecycle` scheduled task
- Trigger: Daily at 9:00 AM
- Action: `python -m omega_kg.lifecycle`

**Usage:**
```powershell
.\schedule-lifecycle.ps1
```

---

### Database Scripts

#### 7. **start-database.ps1** ⭐ IMPORTANT
**Purpose:** Start Docker services (Neo4j + PostgreSQL)
**Dependencies:**
- Docker Desktop running
- `docker-compose.yml` in project root

**What it does:**
- Starts Neo4j container (port 7687)
- Starts PostgreSQL container (port 5800)
- Uses persistent named volumes

**Usage:**
```powershell
.\start-database.ps1
```

**Note:** Run this before starting the capture server

---

#### 8. **stop-all.ps1** ⭐ USEFUL
**Purpose:** Stop all OmegaKG services
**What it does:**
- Stops all Python processes
- Stops all Docker containers
- Stops Hookdeck processes

**Usage:**
```powershell
.\stop-all.ps1
```

---

### Task Scheduler Scripts

#### 9. **check_existing_tasks.ps1** ⭐ USEFUL
**Purpose:** Inspect Windows Task Scheduler configuration
**Checks:**
- All OmegaKG-related scheduled tasks
- Task states (Ready, Running, Disabled)
- Last run time and next run time
- Task triggers and actions
- Poetry PATH configuration

**Usage:**
```powershell
.\check_existing_tasks.ps1
```

---

#### 10. **check_tasks_simple.ps1** ⭐ OPTIONAL
**Purpose:** Simple task listing and test execution
**What it does:**
- Lists OmegaKG scheduled tasks
- Attempts to run `start_full_stack.ps1` for testing

**Usage:**
```powershell
.\check_tasks_simple.ps1
```

---

#### 11. **test_task_scheduler.ps1** ⭐ OPTIONAL
**Purpose:** Test Task Scheduler integration
**Checks:**
- Existing scheduled tasks
- Script availability
- Environment variable loading

**Usage:**
```powershell
.\test_task_scheduler.ps1
```

---

### Chrome Extension Scripts

#### 12. **load-extension.ps1** ⭐ IMPORTANT
**Purpose:** Load Chrome extension with validation
**What it does:**
- Validates extension files (manifest.json, content.js, background.js)
- Checks selectors for supported AI platforms
- Opens Chrome extensions page

**Usage:**
```powershell
.\load-extension.ps1
```

**Manual Steps:**
1. Extension opens in Chrome
2. Enable "Developer mode"
3. Click "Load unpacked"
4. Select `chrome-extension` folder

---

#### 13. **reload-extension-tabs.ps1** ⭐ USEFUL
**Purpose:** Reload extension tabs
**What it does:**
- Sends reload signal to all tabs with extension loaded

**Usage:**
```powershell
.\reload-extension-tabs.ps1
```

---

#### 14. **copy-extension-local.ps1** ⭐ OPTIONAL
**Purpose:** Copy extension files to local directory

**Usage:**
```powershell
.\copy-extension-local.ps1
```

---

### Security & Configuration Scripts

#### 15. **verify_bitwarden_secrets.ps1** ⭐ CRITICAL
**Purpose:** Verify Bitwarden Secret Manager integration
**Tests:**
- BWS_ACCESS_TOKEN presence and validity
- Bitwarden SDK connectivity
- Secret ID resolution from Bitwarden
- Integration with `settings.py`

**Usage:**
```powershell
.\verify_bitwarden_secrets.ps1
```

**Expected Output:**
```
[OK] BWS_ACCESS_TOKEN is set
[OK] Bitwarden SDK connected
[OK] All secret IDs resolved
[OK] Settings integration working
```

---

#### 16. **verify_capture_storage.ps1** ⭐ IMPORTANT
**Purpose:** Verify capture storage functionality
**Checks:**
- Obsidian vault path accessibility
- Database connectivity
- Capture endpoint functionality

**Usage:**
```powershell
.\verify_capture_storage.ps1
```

---

### Diagnostic Scripts

#### 17. **status.ps1** ⭐ USEFUL
**Purpose:** Quick system status check
**Checks:**
- `.env` file exists and is valid
- `.venv` directory exists
- Docker containers status
- Capture server process
- Database services

**Usage:**
```powershell
.\status.ps1
```

**Sample Output:**
```
[OK] .env file exists
[OK] Poetry virtual environment found
[INFO] Docker: 2 containers running
[OK] Capture server running on port 8765
[OK] Neo4j: Connected
[OK] PostgreSQL: Connected
```

---

#### 18. **diagnose-capture-config.ps1** ⭐ USEFUL
**Purpose:** Configuration diagnostic before server start
**Checks:**
- `.env` file configuration
- Extension configuration files
- Port alignment (8765)
- Authentication settings

**Usage:**
```powershell
.\diagnose-capture-config.ps1
```

---

#### 19. **diagnose-capture-issue.ps1** ⭐ USEFUL
**Purpose:** Diagnose why extension stopped capturing
**Checks:**
- Extension files integrity
- Manifest.json validity
- Platform detection
- Selectors for supported sites

**Usage:**
```powershell
.\diagnose-capture-issue.ps1
```

---

#### 20. **diagnose-extension.ps1** ⭐ USEFUL
**Purpose:** Diagnose extension loading issues
**Checks:**
- Extension directory path
- manifest.json syntax
- Required files presence
- File permissions

**Usage:**
```powershell
.\diagnose-extension.ps1
```

---

### Development Scripts

#### 21. **sync_dev_environment.ps1** ⭐ USEFUL
**Purpose:** Sync dev environment with stable

**Usage:**
```powershell
.\sync_dev_environment.ps1
```

---

#### 22. **omega-venv.ps1** ⭐ USEFUL
**Purpose:** Manage Poetry virtual environment
**What it does:**
- Creates/updates Poetry virtual environment
- Installs dependencies from `pyproject.toml`

**Usage:**
```powershell
.\omega-venv.ps1
```

---

#### 23. **install-hooks.ps1** ⭐ USEFUL
**Purpose:** Install git pre-commit hooks

**Usage:**
```powershell
.\install-hooks.ps1
```

---

### Monitoring Scripts

#### 24. **ollama-heartbeat-monitor.ps1** ⭐ USEFUL
**Purpose:** Monitor Ollama service heartbeat
**Checks:**
- Ollama service status
- Heartbeat endpoint
- API connectivity

**Usage:**
```powershell
.\ollama-heartbeat-monitor.ps1
```

---

#### 25. **register_heartbeat.ps1** ⭐ USEFUL
**Purpose:** Register heartbeat service

**Usage:**
```powershell
.\register_heartbeat.ps1
```

---

#### 26. **register-capture-monitor.ps1** ⭐ USEFUL
**Purpose:** Register capture monitor service

**Usage:**
```powershell
.\register-capture-monitor.ps1
```

---

### Other Utilities

#### 27. **commit-and-push.ps1** ⭐ OPTIONAL
**Purpose:** Git operations wrapper

**Usage:**
```powershell
.\commit-and-push.ps1
```

---

#### 28. **complete-setup.ps1** ⭐ OPTIONAL
**Purpose:** Complete setup process

**Usage:**
```powershell
.\complete-setup.ps1
```

---

#### 29. **setup-ollama-headless.ps1** ⭐ OPTIONAL
**Purpose:** Configure Ollama for headless operation

**Usage:**
```powershell
.\setup-ollama-headless.ps1
```

---

#### 30. **setup-project.ps1** ⭐ OPTIONAL
**Purpose:** Initial project setup

**Usage:**
```powershell
.\setup-project.ps1
```

---

#### 31. **percolate-conversations.ps1** ⭐ OPTIONAL
**Purpose:** Process conversations for insights

**Usage:**
```powershell
.\percolate-conversations.ps1
```

---

#### 32. **pre-commit-full.ps1** ⭐ OPTIONAL
**Purpose:** Run full pre-commit checks

**Usage:**
```powershell
.\pre-commit-full.ps1
```

---

#### 33. **start-capture-server.ps1** ⭐ OPTIONAL
**Purpose:** Start capture server only (without Hookdeck)

**Usage:**
```powershell
.\start-capture-server.ps1
```

---

#### 34. **test_capture_auth.ps1** ⭐ OPTIONAL
**Purpose:** Test capture endpoint authentication

**Usage:**
```powershell
.\test_capture_auth.ps1
```

---

## ⚠️ Deprecated Scripts

All deprecated scripts are located in `scripts/depracated/` directory.

### Recently Deprecated (Today)

1. **start-stable-DEPRECATED.ps1**
   - **Reason:** Conflicts with start_full_stack.ps1 (port 8002 vs 8765)
   - **Replaced by:** start_full_stack.ps1

2. **task-capture-server-DEPRECATED.ps1**
   - **Reason:** Hardcoded old paths, not in main workflow
   - **Replaced by:** start_full_stack.ps1

### Legacy Scripts (Previously Deprecated)

- `Start-OmegaServer.ps1` - Old comprehensive server launcher
- `start-all.ps1` - Old all-services starter (no Hookdeck)
- `Start-OmegaKGDev.ps1` - Development environment launcher
- `start-dev.ps1` - Dev environment starter
- `start-tunnel.ps1` - Ngrok tunnel starter (superseded by Hookdeck)
- `backup-and-restart.ps1` - Neo4j backup and restart
- Plus various diagnostic and test scripts

**Note:** These are kept for reference but should not be used.

---

## 🔄 Workflows

### Standard Production Startup

```powershell
# 1. Ensure Poetry is in PATH (one-time setup)
.\enable_poetry_path.ps1

# 2. Start databases (if not running)
.\start-database.ps1

# 3. Clean slate (stop any existing processes)
.\cleanup_before_start.ps1

# 4. Start full stack
.\start_full_stack.ps1

# 5. Verify everything is running
.\verify_stack.ps1

# 6. Load Chrome extension
.\load-extension.ps1
```

### Development Workflow

```powershell
# Quick start for development
.\cleanup_before_start.ps1
.\start_full_stack.ps1

# Check status
.\status.ps1

# Load extension for testing
.\load-extension.ps1
```

### Troubleshooting Workflow

```powershell
# 1. Check overall status
.\status.ps1

# 2. Verify configuration
.\diagnose-capture-config.ps1

# 3. Verify Bitwarden integration
.\verify_bitwarden_secrets.ps1

# 4. Verify storage
.\verify_capture_storage.ps1

# 5. Check detailed logs
Get-Content .\logs\capture_server_*.err.log -Tail 50

# 6. Restart with clean slate
.\cleanup_before_start.ps1
.\start_full_stack.ps1
.\verify_stack.ps1
```

### Task Scheduler Setup

```powershell
# 1. Enable Poetry in PATH
.\enable_poetry_path.ps1

# 2. Setup autostart at login
.\setup-autostart.ps1

# 3. Setup lifecycle task
.\schedule-lifecycle.ps1

# 4. Verify tasks
.\check_existing_tasks.ps1
```

---

## 🐚 Shell Scripts (.sh)

### Shell Scripts in Project

1. **source_env.sh** (Project Root)
   - **Purpose:** Source OmegaKG environment
   - **Usage:** `source ./source_env.sh`
   - **Functionality:** Sets up environment variables and aliases
   - **Equivalent .ps1:** N/A (Bash-specific)

2. **scripts/verify_security.sh** (CRITICAL)
   - **Purpose:** Security verification script
   - **Usage:** `./scripts/verify_security.sh`
   - **Functionality:**
     - Checks for private keys
     - Verifies .env file security
     - Checks gitignore patterns
     - Scans git history for sensitive files
     - Detects hardcoded API keys
     - Validates pre-commit hooks
   - **Equivalent .ps1:** Should create `verify_security.ps1` for Windows users

3. **scripts/start-server.sh** (DEPRECATED)
   - **Purpose:** Old dev server starter
   - **Status:** Deprecated - superseded by start_full_stack.ps1
   - **Issues:** References wrong paths, old architecture

4. **.omegakg_temp/test-*.sh** (Testing)
   - **Purpose:** MCP connection testing
   - **Status:** Development/testing scripts

### Recommendations

✅ **Keep as-is:**
- `source_env.sh` - Already has PowerShell equivalent via `.omega_env`
- `.omegakg_temp/test-*.sh` - MCP testing scripts

⚠️ **Create .ps1 equivalents:**
- `scripts/verify_security.sh` → Create `scripts\verify_security.ps1`

⚠️ **Deprecate:**
- `scripts/start-server.sh` - Move to deprecated (superseded by start_full_stack.ps1)

---

## 🔧 Troubleshooting

### Common Issues

#### Issue: "Poetry not found"
**Solution:**
```powershell
.\enable_poetry_path.ps1
```
If still failing, manually add Poetry to PATH:
```powershell
$env:Path += ";C:\Users\steyn\AppData\Roaming\Python\Python312\Scripts"
```

---

#### Issue: "Port 8765 already in use"
**Solution:**
```powershell
.\cleanup_before_start.ps1
.\start_full_stack.ps1
```

---

#### Issue: "HOOKDECK_API_KEY is missing"
**Solution:**
1. Check `.env` file has the key
2. Verify Bitwarden integration: `.\verify_bitwarden_secrets.ps1`
3. Ensure ZERO_TRUST_REQUIRED=false for local development

---

#### Issue: "Failed to bind to port 8765"
**Cause:** Windows permission error
**Solution:**
1. Run PowerShell as Administrator
2. Or change port in `.env`: `APP_PORT=8766`
3. Check Windows Firewall settings

---

#### Issue: "Extension not capturing"
**Solution:**
1. Reload extension: `.\reload-extension-tabs.ps1`
2. Diagnose: `.\diagnose-capture-issue.ps1`
3. Verify extension: `.\diagnose-extension.ps1`
4. Check logs in Chrome DevTools

---

#### Issue: "Neo4j connection failed"
**Solution:**
```powershell
.\start-database.ps1
```
Or manually start Docker containers:
```powershell
docker-compose up -d neo4j
```

---

#### Issue: "Database pool initialization failed"
**Solution:**
1. Check PostgreSQL: `.\start-database.ps1`
2. Verify credentials in `.env`
3. Check database logs

---

### Log Locations

| Component | Log File |
|-----------|----------|
| Capture Server | `logs\capture_server_YYYY-MM-DD_HH-mm-ss.err.log` |
| Hookdeck | `logs\hookdeck_YYYY-MM-DD_HH-mm-ss.err.log` |
| Docker Containers | `docker-compose logs` |
| Chrome Extension | Chrome DevTools → Console |
| Task Scheduler | Windows Event Viewer |

---

### Useful Commands

```powershell
# Check if port is listening
netstat -ano | findstr :8765

# Check running processes
Get-Process | Where-Object {$_.ProcessName -match "poetry|node"}

# View recent logs
Get-Content .\logs\capture_server_*.err.log -Tail 100

# Check Docker containers
docker ps -a

# Check Task Scheduler tasks
Get-ScheduledTask | Where-Object {$_.TaskName -match "Omega"}
```

---

## 📊 Critical Dependencies

All active scripts depend on:

| Component | Required Version | Installation Path |
|-----------|-----------------|-------------------|
| **Python** | 3.12+ | C:\Program Files\Python312 |
| **Poetry** | Latest | C:\Users\steyn\AppData\Roaming\Python\Python312\Scripts\poetry.exe |
| **PowerShell** | 5.1+ | Built-in Windows |
| **Docker Desktop** | Latest | Docker |
| **Hookdeck CLI** | Latest | npm install -g @hookdeck/cli |
| **Ollama** | Latest | C:\Users\steyn\AppData\Local\Programs\Ollama\ollama.exe |
| **Neo4j** | 5.x | Docker container |
| **PostgreSQL** | 15+ | Docker container |

---

## 🎯 Script Criticality Levels

### ⭐ CRITICAL
Scripts required for core functionality:
- `start_full_stack.ps1` - Main entry point
- `verify_bitwarden_secrets.ps1` - Security validation

### 🔶 IMPORTANT
Scripts required for production deployment:
- `verify_stack.ps1` - Health checks
- `cleanup_before_start.ps1` - Clean startup
- `enable_poetry_path.ps1` - PATH setup
- `setup-autostart.ps1` - Autostart configuration
- `schedule-lifecycle.ps1` - Task automation
- `start-database.ps1` - Database services
- `load-extension.ps1` - Extension deployment
- `verify_capture_storage.ps1` - Storage validation

### 🔸 USEFUL
Scripts for monitoring and diagnostics:
- All diagnostic scripts (diagnose-*.ps1)
- All verification scripts (verify-*.ps1)
- Status scripts (status.ps1)
- Task scheduler scripts (check_*.ps1)

### 🔹 OPTIONAL
Scripts for specific use cases:
- Development utilities
- Testing scripts
- Legacy compatibility

---

## 📚 Additional Resources

- **Project Documentation:** `docs/` directory
- **API Documentation:** http://localhost:8765/docs (when server running)
- **Neo4j Browser:** http://localhost:7474/browser/
- **Architecture Guide:** See project README
- **Security Documentation:** SECURITY.md

---

**End of Script Map**

For updates or issues with this document, refer to the project repository.