# Omega_KG PowerShell Profile & Smart Start Script - Quick Reference Guide

## Implementation Summary

Two comprehensive automation scripts have been created and deployed:

### 1. PowerShell Profile
**Location:** `C:\Users\steyn\OneDrive\Documents\PowerShell\Microsoft.PowerShell_profile.ps1`

- **Size:** 11.4 KB
- **Status:** ✓ Deployed
- **Features:** Idempotent initialization, environment detection, dependency checks, service management

### 2. Smart Start Scripts
**Locations:**
- `d:\projects\Omega_KG_dev\scripts\Start-OmegaServer.ps1` (22.3 KB)
- `d:\projects\Omega_KG_stable\scripts\Start-OmegaServer.ps1` (22.3 KB)

- **Status:** ✓ Deployed
- **Features:** Multi-mode launch, pre-flight checks, port conflict detection, graceful shutdown

---

## Quick Start

### First Time Setup (After restarting PowerShell)

The profile loads automatically on startup. On first load, you'll see:

```
Omega_KG Profile Loaded! Quick Commands:

  omega-dev              → Switch to dev environment
  omega-stable           → Switch to stable environment
  Get-OmegaStatus        → Show service status
  Test-OmegaKGDependencies → Verify requirements
  Start-OmegaServices    → Start Docker services
  omega-start            → Start capture server
  omega-start-term       → Start server in new terminal
  omega-code dev         → Open dev in VS Code
```

### Most Common Commands

```powershell
# Switch environments
omega-dev                          # → Go to dev, activate venv, load .env
omega-stable                       # → Go to stable, activate venv, load .env

# Check everything is ready
Test-OmegaKGDependencies          # → Verify Python, Poetry, Docker, containers

# Start services (Docker containers)
Start-OmegaServices               # → Start Neo4j + PostgreSQL

# Start the capture server
omega-start                        # → Foreground (blocking, Ctrl+C to stop)
omega-start-term                   # → New terminal (observable)
omega-start-bg                     # → Background (returns immediately)

# View status
Get-OmegaStatus                   # → Show all service statuses
```

---

## Detailed Usage

### PowerShell Profile Commands

#### Environment Switching
```powershell
# Switch to dev environment
Enter-OmegaKG dev
omega-dev                  # Shorter alias

# Switch to stable environment
Enter-OmegaKG stable
omega-stable               # Shorter alias

# Get current active environment
Get-ActiveOmegaEnvironment
```

**What this does:**
- Changes directory to the project folder
- Activates the `.venv` virtual environment
- Loads `.env` file (sets environment variables)
- Sets `$env:OMEGA_KG_ENV` marker

#### Dependency Verification
```powershell
# Full dependency check
Test-OmegaKGDependencies

# Guide to install missing dependencies
Install-OmegaKGDependencies
```

**Checks:**
- Python 3.12+ ✓/✗
- Poetry ✓/✗
- Docker running ✓/✗
- Neo4j container ✓/✗
- PostgreSQL container ✓/✗

#### Service Management
```powershell
# Start Docker services (Neo4j + PostgreSQL)
Start-OmegaServices

# Stop all services gracefully
Stop-OmegaServices

# Check service status
Get-OmegaStatus
```

#### Server Launch (Quick)
```powershell
# Foreground mode (blocking terminal)
omega-start
Start-OmegaCaptureServer                    # Full name
Start-OmegaCaptureServer -Mode foreground   # Explicit

# Background mode (returns immediately)
omega-start-bg
Start-OmegaCaptureServer -Mode background

# New terminal mode (observable in separate window)
omega-start-term
Start-OmegaCaptureServer -Mode terminal
```

#### Logging & Utilities
```powershell
# View recent profile logs
Get-OmegaLog                 # Last 20 entries
Get-OmegaLog -Lines 50       # Last 50 entries

# Clear profile log
Clear-OmegaLog

# Open project in VS Code
Open-OmegaProject dev
Open-OmegaProject stable
omega-code dev
omega-code stable
```

---

### Smart Start Script - Advanced Usage

The scripts are located in:
- `d:\projects\Omega_KG_dev\scripts\Start-OmegaServer.ps1`
- `d:\projects\Omega_KG_stable\scripts\Start-OmegaServer.ps1`

#### Basic Usage
```powershell
cd d:\projects\Omega_KG_dev
.\scripts\Start-OmegaServer.ps1              # Start in foreground

# Or from profile
omega-start                                   # Quick alias
```

#### Launch Modes

```powershell
# 1. FOREGROUND (Default)
# - Blocks terminal
# - Press Ctrl+C to stop
# - See server logs in real-time
.\scripts\Start-OmegaServer.ps1
.\scripts\Start-OmegaServer.ps1 -Mode foreground

# 2. BACKGROUND
# - Returns immediately to prompt
# - Server runs in PowerShell job
# - Check status with: Get-Job -Name "OmegaKG_*"
.\scripts\Start-OmegaServer.ps1 -Mode background

# 3. NEW TERMINAL
# - Launches dedicated window
# - Shows terminal title with port/environment
# - Clean separation from main terminal
.\scripts\Start-OmegaServer.ps1 -Mode terminal

# 4. STATUS
# - Show current server state
# - List running processes
# - Port availability
# - Docker service status
.\scripts\Start-OmegaServer.ps1 -Mode status

# 5. STOP
# - Gracefully stop running server
# - Clean shutdown (5s timeout)
.\scripts\Start-OmegaServer.ps1 -Mode stop

# 6. RESTART
# - Stop running server
# - Start fresh (foreground by default)
.\scripts\Start-OmegaServer.ps1 -Mode restart
```

#### Advanced Options

```powershell
# Force restart (kill existing process immediately)
.\scripts\Start-OmegaServer.ps1 -Mode restart -Force

# Skip pre-flight checks (faster startup, use carefully)
.\scripts\Start-OmegaServer.ps1 -SkipChecks

# Use custom port (override default)
.\scripts\Start-OmegaServer.ps1 -Port 9000

# Specific environment (auto-detect by default)
.\scripts\Start-OmegaServer.ps1 -Environment stable -Mode terminal

# Verbose output (show all debug info)
.\scripts\Start-OmegaServer.ps1 -Verbose
```

#### Background Job Management

When running in background mode:

```powershell
# List all running Omega jobs
Get-Job -Name "OmegaKG_*"

# View output from a background job
Receive-Job -Id 1                    # Replace 1 with job ID

# Stop a background job
Stop-Job -Id 1
Remove-Job -Id 1

# Or use the script
.\scripts\Start-OmegaServer.ps1 -Mode stop
```

---

## Features & Capabilities

### ✓ Idempotency
- Profile loads only once per session (guard variable prevents re-initialization)
- Functions are reentrant (safe to call multiple times)
- No duplicate initialization overhead

### ✓ Environment Isolation
- Dev and stable environments don't interfere
- Separate ports: 8765 (dev) vs 8002 (stable)
- Auto-detection from current directory
- Explicit environment variable tracking

### ✓ Pre-Flight Checks
Automatically verifies:
- Python 3.12+ installed and accessible
- Poetry installed and working
- Docker running and accessible
- Neo4j container operational
- PostgreSQL container operational
- Target port availability
- Virtual environment status

### ✓ Graceful Shutdown
- Attempts clean shutdown (5s timeout)
- Falls back to forced kill if needed
- Cleans up PID files and background jobs
- Supports Docker container coordination

### ✓ Port Conflict Detection
- Detects processes using target port
- Shows offending process name and PID
- Can force-stop conflicting process with `-Force`
- Prevents port binding errors

### ✓ Comprehensive Logging
- Timestamps on all log entries
- Log levels: INFO, SUCCESS, WARN, ERROR, DEBUG
- Automatic log rotation at 1MB
- Backup files preserved with timestamps
- Log location: `$env:TEMP\Omega_KG_profile.log`

### ✓ Multi-Mode Launch
Choose how to run the server:
| Mode | Use Case | Pros | Cons |
|------|----------|------|------|
| **foreground** | Development/debugging | See logs in real-time | Blocks terminal |
| **background** | Keep working | Doesn't block | No visible output (can check with Get-Job) |
| **terminal** | Monitoring | Separate observable window | Extra window cluttering desktop |
| **status** | Troubleshooting | Non-intrusive status check | Read-only |
| **stop** | Cleanup | Graceful shutdown | Can be slow |
| **restart** | Recovery | Full reset | Kills existing instance |

---

## Error Handling

### Common Issues & Solutions

#### "Profile not loaded" or "Functions not available"
```powershell
# Manually reload profile
& $PROFILE

# Verify it loaded
$global:OmegaKGProfileLoaded
```

#### "Python not found in PATH"
```powershell
# Add Python to PATH or install from https://python.org
# Verify after installation:
python --version
```

#### "Port 8765 in use"
```powershell
# Check what's using it
.\scripts\Start-OmegaServer.ps1 -Mode status

# Force stop it
.\scripts\Start-OmegaServer.ps1 -Mode stop -Force

# Or kill specific process
Stop-Process -Id <PID> -Force
```

#### "Neo4j container not running"
```powershell
# Start services
Start-OmegaServices

# Or manually
docker-compose up -d neo4j-db
```

#### "Virtual environment not found"
```powershell
# Navigate to project and create it
cd d:\projects\Omega_KG_dev
poetry install
```

---

## Performance Notes

### Log File Rotation
- Automatically rotates when log exceeds 1MB
- Keeps backup with timestamp: `Omega_KG_profile.log_backup_20251130_120000.log`
- Location: `$env:TEMP\Omega_KG_profile.log`

### Startup Performance
- Pre-flight checks: ~2-3 seconds
- Skip with `-SkipChecks` if you want instant startup
- Background job startup: ~3 seconds
- Terminal window launch: ~1 second

### Resource Usage
- Profile overhead: ~2-3 MB memory
- Background job: ~50-100 MB (Python process)
- Docker containers: ~500 MB - 1 GB combined

---

## File Structure

```
C:\Users\steyn\OneDrive\Documents\PowerShell\
├── Microsoft.PowerShell_profile.ps1           (11.4 KB, main profile)
└── Microsoft.PowerShell_profile.ps1.backup_*  (auto-backup on update)

d:\projects\Omega_KG_dev\
└── scripts\
    ├── Start-OmegaServer.ps1                  (22.3 KB, smart launcher)
    ├── omega-venv.ps1                         (existing)
    ├── Start-OmegaKGDev.ps1                   (existing)
    └── ... (other scripts)

d:\projects\Omega_KG_stable\
└── scripts\
    ├── Start-OmegaServer.ps1                  (22.3 KB, smart launcher)
    └── ... (other scripts)

$env:TEMP\
├── Omega_KG_profile.log                       (profile logging)
├── Omega_KG_profile.log_backup_*              (rotated logs)
├── Omega_KG_server.log                        (server startup logging)
└── Omega_KG_server.log_*                      (rotated server logs)
```

---

## Testing Checklist

- [ ] Open new PowerShell terminal
- [ ] Verify profile loads (should see quick commands list)
- [ ] Run `Get-OmegaStatus` - check all services
- [ ] Run `Test-OmegaKGDependencies` - verify requirements
- [ ] Run `omega-dev` - switch to dev environment
- [ ] Run `omega-start-term` - launch server in new terminal
- [ ] Verify server starts: `http://127.0.0.1:8765/health`
- [ ] Stop server with Ctrl+C in new terminal
- [ ] Test background mode: `.\scripts\Start-OmegaServer.ps1 -Mode background`
- [ ] Check background job: `Get-Job -Name "OmegaKG_*"`
- [ ] Stop background job: `.\scripts\Start-OmegaServer.ps1 -Mode stop`
- [ ] Test stable environment: `omega-stable` then `omega-start`

---

## Support & Logs

### View Logs
```powershell
# Profile logs
Get-OmegaLog
Get-OmegaLog -Lines 100

# Server startup logs
Get-Content $env:TEMP\Omega_KG_server.log -Tail 20
```

### Clear Logs
```powershell
Clear-OmegaLog
Remove-Item "$env:TEMP\Omega_KG_server.log*"
```

### Enable Debug Output
```powershell
# Run with verbose flag
.\scripts\Start-OmegaServer.ps1 -Verbose
```

---

## Configuration Reference

### Default Ports
| Service | Dev | Stable | Protocol |
|---------|-----|--------|----------|
| Capture Server | 8765 | 8002 | HTTP |
| Neo4j HTTP | 7474 | 7474 | HTTP |
| Neo4j Bolt | 7687 | 7687 | Bolt |
| PostgreSQL | 5433 | 5433 | TCP |

### Docker Containers
| Name | Status |
|------|--------|
| apexsigma.neo4j.db | Required |
| apexsigma.postgres.db | Required |
| apexsigma.omega.kg | Optional (on-demand) |

### Environment Variables Loaded
From `.env` file:
- `NEO4J_PASSWORD`, `NEO4J_USER`, `NEO4J_URI`
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_SERVER`, `POSTGRES_PORT`
- `JWT_SECRET_KEY`
- `EXTENSION_API_KEY_PRD`, `CHROME_EXTENSION_ID`
- And all other project-specific settings

---

**Version:** 1.0.0  
**Last Updated:** 2025-11-30  
**Author:** Omega_KG Team
