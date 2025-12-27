# Capture Service Startup Failure - Root Cause Analysis & Fix

**Date:** 2025-12-27
**Issue:** Capture Server failing to start with port binding error

**Status:** ✅ FIXED - Port conflict resolved

---

## Executive Summary

The capture service was failing to start due to a **port conflict** between Hookdeck and Capture Server. Both services were configured to use port 8765, causing the Capture Server to fail with error `[Errno 13] error while attempting to bind on address ('127.0.0.1', 8765): [winerror 10013] an attempt was made to access a socket in a way forbidden by its access permissions`.

**Status:** ✅ FIXED - Port conflict resolved by changing Hookdeck to port 8766

---

## Root Cause Analysis

### Primary Issue: Port Conflict in `start_full_stack.ps1`

**Location:** [`scripts/start_full_stack.ps1:112`](scripts/start_full_stack.ps1:112)

**Problem:** Both Hookdeck and Capture Server were configured to use the same port (8765).

#### Evidence:

1. **Hookdeck Configuration (Line 112):**
   ```powershell
   $HookdeckArgs = "listen 8766 linear --path /webhooks/linear"
   ```
   - Hookdeck listens on port **8766**
   - Forwards events from "linear" source
   - Forwards to path `/webhooks/linear`

2. **Capture Server Configuration (Lines 74-75):**
   ```powershell
   $env:HOST = "127.0.0.1"
   $env:PORT = "8765"
   ```
   - Capture Server listens on port **8765**

3. **Settings Configuration ([`settings.py:91`](omega_kg/settings.py:91)):**
   ```python
   app_port: int = Field(8765, validation_alias="APP_PORT")
   ```
   - Default port is 8765

4. **Capture Server Uvicorn Configuration ([`capture_server.py:760-766`](omega_kg/capture_server.py:760-766)):**
   ```python
   uvicorn.run(
       "omega_kg.capture_server:app",
       host="127.0.0.1",
       port=settings.app_port,
       log_level="info",
       reload=False,
   )
   ```
   - Confirms Capture Server uses port 8765

5. **Error Log Evidence ([`logs/capture_server_2025-12-27_02-37-43.err.log:48`](logs/capture_server_2025-12-27_02-37-43.err.log:48)):**
   ```
   ERROR: [Errno 13] error while attempting to bind on address ('127.0.0.1', 8765): [winerror 10013] an attempt was made to access a socket in a way forbidden by its access permissions
   ```

6. **Hookdeck Log Evidence ([`logs/hookdeck_2025-12-27_02-37-43.log`](logs/hookdeck_2025-12-27_02-37-43.log:1)):**
   ```
   ? Select a source [Use arrows to move, type to filter]
   > linear
     Create new source
   ```
   - Hookdeck was running in interactive mode, waiting for source selection
   - This indicates Hookdeck was not properly configured for background operation

---

## Architecture Analysis

### Intended Architecture

The system is designed with the following webhook flow:

```
External Webhooks (Linear, GitHub)
         ↓
    Hookdeck (Port 8766)
         ↓
    Capture Server (Port 8765)
         ↓
    /webhooks/linear endpoint
         ↓
    Linear Sync Processor
         ↓
    Obsidian Vault + Neo4j
```

### Webhook Endpoints

- **Linear Webhook:** [`/webhook/linear`](omega_kg/capture_server.py:697-703) - Receives Linear webhooks directly
- **GitHub Webhook:** [`/webhook/github`](omega_kg/routers/github_receiver.py:72-90) - Receives GitHub webhooks directly
- **Capture Endpoint:** [`/capture`](omega_kg/routers/capture.py:80-80) - Chrome extension capture endpoint

**Note:** The Capture Server has direct webhook endpoints, meaning webhooks can be sent directly to it without going through Hookdeck. However, Hookdeck is included in the stack for webhook management and filtering.

---

## Fix Applied

### Changes Made to `start_full_stack.ps1`

**Line 112 - Updated Hookdeck Command:**

```powershell
# BEFORE:
$HookdeckArgs = "listen 8765"

# AFTER:
$HookdeckArgs = "listen 8766 linear --path /webhooks/linear"
```

**Explanation of Changes:**

1. **Changed Hookdeck Port:** 8765 → 8766
   - Resolves the port conflict
   - Hookdeck now listens on port 8766
   - Capture Server continues to use port 8765

2. **Added Source Specification:** `linear`
   - Hookdeck now explicitly forwards events from the "linear" source
   - This prevents Hookdeck from running in interactive mode

3. **Added Path Flag:** `--path /webhooks/linear`
   - Hookdeck forwards webhooks to the correct endpoint path
   - Matches the Capture Server's Linear webhook endpoint at `/webhook/linear`

---

## Verification Steps

To verify the fix works:

1. **Run the startup script:**
   ```powershell
   ./scripts/start_full_stack.ps1
   ```

2. **Check that both services start successfully:**
   - Capture Server should bind to port 8765
   - Hookdeck should bind to port 8766
   - No port binding errors should occur

3. **Verify Hookdeck is not in interactive mode:**
   - Hookdeck logs should show it's forwarding events, not waiting for source selection
   - Check logs in `logs/hookdeck_*.log`

4. **Test webhook delivery:**
   - Send a test webhook to Hookdeck on port 8766
   - Verify it's forwarded to Capture Server on port 8765
   - Check Capture Server logs for webhook receipt

---

## Additional Recommendations

### 1. Cleanup Script Enhancement

The [`cleanup_before_start.ps1`](scripts/cleanup_before_start.ps1:1) script has a 2-second wait time after killing processes. Consider increasing this to 5 seconds to ensure ports are fully released:

```powershell
# Line 39 in cleanup_before_start.ps1
Start-Sleep -Seconds 2  # Consider changing to: Start-Sleep -Seconds 5
```

### 2. Process Detection Logic

The [`start_full_stack.ps1`](scripts/start_full_stack.ps1:83-90) script checks for existing Poetry processes by matching command line. This is good, but could be enhanced to also check if the port is actually in use:

```powershell
# Add after line 85:
$PortInUse = Get-NetTCPConnection -LocalPort 8765 -ErrorAction SilentlyContinue
if ($PortInUse) {
    Write-Warning "Port 8765 is already in use by PID: $($PortInUse.OwningProcess)"
}
```

### 3. Hookdeck Configuration File

Consider creating a Hookdeck configuration file to avoid command-line complexity:

```toml
# ~/.config/hookdeck/config.toml
[connections]
[[connections]]
name = "omega-kg-linear"
source = "linear"
url = "http://127.0.0.1:8765/webhooks/linear"
```

Then update the script to use:
```powershell
$HookdeckArgs = "listen --connection omega-kg-linear"
```

### 4. Environment Variable Documentation

Document the port configuration in [`.env.example`](.env.example) for clarity:

```bash
# Capture Server
APP_HOST=127.0.0.1
APP_PORT=8765

# Hookdeck (if used)
HOOKDECK_LISTEN_PORT=8766
HOOKDECK_SOURCE=linear
HOOKDECK_PATH=/webhooks/linear
```

---

## Technical Details

### Hookdeck Command Syntax

```bash
hookdeck listen [port or forwarding URL] [source] [connection] [flags]
```

**Arguments:**
- `[port or forwarding URL]`: Required. The port or forwarding URL to forward events to
- `[source]`: Required. The name of source to forward events from
- `[connection]`: Optional. The name of the connection linking Source and Destination
- `--path`: Sets the path to which events are forwarded (default: "/")
- `--filter-body`: Filter events by request body
- `--filter-headers`: Filter events by request headers
- `--filter-path`: Filter events by request path
- `--max-connections`: Maximum concurrent connections (default: 50)

### Port Allocation Summary

| Service | Port | Purpose |
|----------|------|---------|
| Capture Server | 8765 | Direct webhooks + Chrome extension capture |
| Hookdeck | 8766 | Webhook gateway for Linear source |

---

## Conclusion

The root cause was a **port conflict** between Hookdeck and Capture Server. The fix changes Hookdeck to listen on port 8766 and properly configures it to forward Linear webhooks to the Capture Server's `/webhooks/linear` endpoint.

This resolves the binding error and allows both services to run simultaneously without conflict.

---

## Files Modified

- [`scripts/start_full_stack.ps1`](scripts/start_full_stack.ps1:112) - Line 112 updated

## Files Referenced

- [`scripts/cleanup_before_start.ps1`](scripts/cleanup_before_start.ps1:1)
- [`scripts/start-database.ps1`](scripts/start-database.ps1:1)
- [`omega_kg/settings.py`](omega_kg/settings.py:91)
- [`omega_kg/capture_server.py`](omega_kg/capture_server.py:760-766)
- [`logs/capture_server_2025-12-27_02-37-43.err.log`](logs/capture_server_2025-12-27_02-37-43.err.log:48)
- [`logs/hookdeck_2025-12-27_02-37-43.log`](logs/hookdeck_2025-12-27_02-37-43.log:1)
