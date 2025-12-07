# Omega_KG Environment Setup - Implementation Complete ✓

## Deployment Status

| Component | Location | Size | Status |
|-----------|----------|------|--------|
| PowerShell Profile | `C:\Users\steyn\OneDrive\Documents\PowerShell\Microsoft.PowerShell_profile.ps1` | 11.4 KB | ✓ Deployed |
| Smart Start Script (Dev) | `d:\projects\Omega_KG_dev\scripts\Start-OmegaServer.ps1` | 22.3 KB | ✓ Deployed |
| Smart Start Script (Stable) | `d:\projects\Omega_KG_stable\scripts\Start-OmegaServer.ps1` | 22.3 KB | ✓ Deployed |
| Setup Guide | `d:\projects\Omega_KG_dev\OMEGA_KG_SETUP_GUIDE.md` | 14 KB | ✓ Created |

---

## What Was Implemented

### 1. **Comprehensive PowerShell Profile**
- **Idempotent initialization** - Guards against duplicate loading with `$global:OmegaKGProfileLoaded`
- **Environment detection** - Auto-detects dev/stable from current directory
- **Dependency verification** - Checks Python 3.12+, Poetry, Docker, containers
- **Service management** - Commands to start/stop Neo4j, PostgreSQL, capture server
- **Logging** - Timestamps all events, auto-rotates at 1MB
- **Convenient aliases** - `omega-dev`, `omega-start`, `omega-start-term`, etc.

### 2. **Smart Start Script (Multi-Mode)**
- **6 launch modes**: foreground, background, terminal, status, stop, restart
- **Pre-flight checks** - Validates all dependencies before launch
- **Port conflict detection** - Identifies and can kill blocking processes
- **Graceful shutdown** - 5-second timeout for clean exits, falls back to force kill
- **Background job support** - Proper job naming and management
- **Comprehensive logging** - Detailed startup logs with auto-rotation

### 3. **Robust Error Handling**
- All scripts are defensive with proper error catching
- Clear error messages with actionable guidance
- Timeout handling for graceful shutdowns
- Process verification after startup

### 4. **Documentation**
- Complete setup guide with usage examples
- Quick reference for common commands
- Troubleshooting section with solutions
- Performance notes and configuration reference

---

## Immediate Next Steps

### 1. First Time Use
```powershell
# Restart PowerShell to load the profile
# Or manually: & $PROFILE

# Should see welcome banner with quick commands
```

### 2. Verify Everything Works
```powershell
# Check dependencies
Test-OmegaKGDependencies

# View service status
Get-OmegaStatus

# Start services if needed
Start-OmegaServices
```

### 3. Start the Server
```powershell
# Option A: Foreground (blocking, see logs)
omega-start

# Option B: New terminal (observable in separate window)
omega-start-term

# Option C: Background (returns immediately)
omega-start-bg
```

---

## Key Features

### ✓ **Idempotency**
- Profile loads safely multiple times
- No duplicate initialization
- Functions are reentrant

### ✓ **Environment Isolation**
- Dev and stable never interfere
- Separate ports: 8765 (dev) vs 8002 (stable)
- Auto-detection from current directory
- Environment variable tracking

### ✓ **Safety & Robustness**
- Pre-flight checks prevent startup errors
- Graceful shutdown with timeouts
- Port conflict detection
- Backup on profile update

### ✓ **Developer Friendly**
- Minimal commands needed (`omega-dev`, `omega-start`)
- Auto-activation of virtual environments
- Auto-loading of `.env` files
- Status commands to troubleshoot issues

### ✓ **Logging & Debugging**
- All events logged with timestamps
- Log rotation to prevent disk bloat
- Multiple verbosity levels
- Quick access to recent logs

---

## File Locations

```
C:\Users\steyn\OneDrive\Documents\PowerShell\
├── Microsoft.PowerShell_profile.ps1                    [Main profile]
└── Microsoft.PowerShell_profile.ps1.backup_*           [Auto-backups]

d:\projects\Omega_KG_dev\
└── scripts\
    └── Start-OmegaServer.ps1                           [Smart launcher]

d:\projects\Omega_KG_stable\
└── scripts\
    └── Start-OmegaServer.ps1                           [Smart launcher]

$env:TEMP\
├── Omega_KG_profile.log                                [Profile logs]
├── Omega_KG_profile.log_backup_*                       [Rotated logs]
├── Omega_KG_server.log                                 [Server logs]
└── Omega_KG_server.log_*                               [Rotated logs]
```

---

## Essential Commands Reference

### Environment Switching
```powershell
omega-dev                           # Switch to dev
omega-stable                        # Switch to stable
Get-ActiveOmegaEnvironment          # Show current
```

### Pre-Flight Checks
```powershell
Test-OmegaKGDependencies           # Verify all requirements
Install-OmegaKGDependencies        # Installation guide
```

### Service Management
```powershell
Get-OmegaStatus                     # Show all service status
Start-OmegaServices                 # Start Docker services
Stop-OmegaServices                  # Stop all services
```

### Server Launch
```powershell
omega-start                         # Foreground (blocking)
omega-start-term                    # New terminal (observable)
omega-start-bg                      # Background job
```

### Server Control
```powershell
# Using profile shortcuts
.\scripts\Start-OmegaServer.ps1 -Mode status    # View status
.\scripts\Start-OmegaServer.ps1 -Mode stop      # Stop server
.\scripts\Start-OmegaServer.ps1 -Mode restart   # Restart
```

### Logging
```powershell
Get-OmegaLog                        # View recent logs
Get-OmegaLog -Lines 100             # View 100 lines
Clear-OmegaLog                      # Clear log
```

---

## Configuration

### Default Ports
- **Dev Capture Server**: 8765
- **Stable Capture Server**: 8002
- **Neo4j HTTP**: 7474
- **Neo4j Bolt**: 7687
- **PostgreSQL**: 5433

### Docker Containers Required
- `apexsigma.neo4j.db` - Neo4j database
- `apexsigma.postgres.db` - PostgreSQL database

### Environment Variables
Auto-loaded from `.env` file in project root:
- Database credentials (Neo4j, PostgreSQL)
- JWT secrets
- API keys (Linear, Bitwarden, AI services)
- SMTP settings
- Vault paths

---

## Troubleshooting

### "Profile not loaded"
```powershell
# Reload profile
& $PROFILE

# Verify
$global:OmegaKGProfileLoaded
```

### "Port already in use"
```powershell
# Check what's using it
.\scripts\Start-OmegaServer.ps1 -Mode status

# Force stop
.\scripts\Start-OmegaServer.ps1 -Mode stop -Force
```

### "Docker not running"
- Start Docker Desktop
- Or: `docker-compose up -d neo4j-db`

### "Virtual environment not activated"
```powershell
# Manually activate in project directory
cd d:\projects\Omega_KG_dev
.\.venv\Scripts\Activate.ps1
```

### See Full Documentation
```
d:\projects\Omega_KG_dev\OMEGA_KG_SETUP_GUIDE.md
```

---

## Version Information

- **Profile Version**: 1.0.0
- **Script Version**: 2.0.0
- **Deployed**: 2025-11-30
- **PowerShell Required**: 7.0+
- **Python Required**: 3.12+

---

## Support

All logs are stored with timestamps and auto-rotated:
- Profile logs: `$env:TEMP\Omega_KG_profile.log`
- Server logs: `$env:TEMP\Omega_KG_server.log`

For detailed troubleshooting, see: `d:\projects\Omega_KG_dev\OMEGA_KG_SETUP_GUIDE.md`

---

✓ **Implementation Complete** - Ready to use!
