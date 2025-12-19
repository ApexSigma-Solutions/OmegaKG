# Capture Server Troubleshooting Guide

## Issue: Server Won't Start

### Quick Diagnosis Steps

1. **Check if dependencies are installed:**
   ```powershell
   poetry install
   ```

2. **Verify environment configuration:**
   ```powershell
   .\diagnose-capture-config.ps1
   ```

3. **Test settings loading:**
   ```powershell
   poetry run python -c "from omega_kg.settings import settings; print('OK')"
   ```

4. **Check for port conflicts:**
   ```powershell
   Get-NetTCPConnection -LocalPort 8765 -State Listen
   ```

## Common Issues & Solutions

### Zero-Trust Authentication Error

**Error:**
```
ValidationError: BWS_ACCESS_TOKEN is required to enforce zero_trust secret loading
```

**Solution:**
Add to `.env`:
```bash
ZERO_TRUST_REQUIRED=false
```

**Explanation:** This allows local development using plain-text .env credentials instead of requiring Bitwarden.

### Module Not Found Errors

**Error:**
```
ModuleNotFoundError: No module named 'click'
```

**Solution:**
```powershell
poetry install
```

### Port Already in Use

**Error:**
```
OSError: [Errno 48] Address already in use
```

**Solution:**
```powershell
# Find the process
Get-NetTCPConnection -LocalPort 8765 | ForEach-Object {
    Get-Process -Id $_.OwningProcess
}

# Kill it
Stop-Process -Id <PID> -Force
```

### Neo4j Connection Failed

**Warning:**
```
Neo4j does not appear to be running on port 7687
```

**Solution:**
- Start Neo4j: `neo4j start` or use Docker
- The server will run in mock mode if Neo4j is unavailable
- Check AGENTS.md: System auto-falls back to mock mode

### PostgreSQL Connection Failed

**Warning:**
```
PostgreSQL is not running on port 5433
```

**Solution:**
- Start PostgreSQL service
- Or use Docker: `docker-compose up postgres-db`

## After Fixing Issues

1. **Restart the server:**
   ```powershell
   .\start-capture-server-window.ps1
   ```

2. **Verify it's running:**
   ```powershell
   Invoke-WebRequest http://localhost:8765/health
   ```

3. **Check the monitoring window** for startup logs

## Authentication Configuration

### Chrome Extension Setup

1. **Get your API key from .env:**
   ```powershell
   Select-String -Path .env -Pattern "EXTENSION_API_KEY"
   ```

2. **Configure extension:**
   - Open `chrome://extensions`
   - Click "Extension options" on Omega_KG
   - Enter:
     - Server URL: `http://localhost:8765`
     - API Key: (from step 1)

3. **Test authentication:**
   ```powershell
   $apiKey = "your_key_here"
   Invoke-RestMethod -Uri "http://localhost:8765/auth/token" `
       -Method POST -Headers @{"X-API-Key"=$apiKey}
   ```

## Manual Server Start (Debugging)

If the launcher script fails, run manually:

```powershell
cd D:\projects\Omega_KG_stable
poetry run uvicorn omega_kg.capture_server:app --host 127.0.0.1 --port 8765 --reload
```

This shows all errors directly in your terminal.

## Log Files

Check these locations for detailed errors:
- Server monitoring window (PowerShell)
- Neo4j logs: `data/neo4j/logs/`
- PostgreSQL logs: Check Docker logs if using Docker

## Still Not Working?

Run full diagnostic:
```powershell
.\diagnose-capture-config.ps1 > diagnostic-report.txt
cat diagnostic-report.txt
```

Share the diagnostic report for further assistance.
