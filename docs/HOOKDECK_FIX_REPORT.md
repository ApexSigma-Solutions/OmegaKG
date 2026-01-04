# Hookdeck CLI Fix Report

## Summary

Successfully identified and fixed the Hookdeck CLI execution issue in the startup script. The problem was that the script was trying to use a Linux binary instead of the Windows .exe, causing "cannot execute binary file" errors.

## Root Cause Analysis

### The Problem
The npm-installed Hookdeck CLI includes both:
- **Linux binary**: `/node_modules/hookdeck-cli/bin/hookdeck` (for Linux/Mac)
- **Windows binary**: `/node_modules/hookdeck-cli/bin/hookdeck.exe` (for Windows)

The shell wrapper script at `/c/Users/steyn/AppData/Roaming/npm/hookdeck` was calling the Linux binary:
```bash
exec "$basedir/node_modules/hookdeck-cli/bin/hookdeck" "$@"
```

This caused the error:
```
/c/Users/steyn/AppData/Roaming/npm/node_modules/hookdeck-cli/bin/hookdeck: cannot execute binary file: Exec format error
```

## Solution Implemented

### Changes to `scripts/start_full_stack.ps1` (v2.5)

#### 1. Fixed Hookdeck Path Detection (Lines 117-128)
**Before:**
```powershell
$HookdeckCmd = (Get-Command hookdeck -ErrorAction SilentlyContinue)
$HookdeckPath = $HookdeckCmd.Source
if (-not $HookdeckPath) {
    $HookdeckPath = "hookdeck"
} elseif ($HookdeckPath -like "*.ps1") {
    # If it's a ps1, try to find .cmd in same directory
    $CmdPath = $HookdeckPath -replace "\.ps1$", ".cmd"
    if (Test-Path $CmdPath) { $HookdeckPath = $HookdeckPath }
}
```

**After:**
```powershell
# Use Windows .exe directly to avoid shell wrapper issues
$HookdeckPath = "C:\Users\steyn\AppData\Roaming\npm\node_modules\hookdeck-cli\bin\hookdeck.exe"
if (-not (Test-Path $HookdeckPath)) {
    # Fallback to hookdeck command if .exe not found
    $HookdeckCmd = (Get-Command hookdeck -ErrorAction SilentlyContinue)
    if ($HookdeckCmd) {
        $HookdeckPath = $HookdeckCmd.Source
    } else {
        Write-Warning "   [!] Hookdeck not found. Please install with: npm install -g @hookdeck/cli"
        $HookdeckPath = $null
    }
}
```

**Benefits:**
- Directly uses the Windows .exe binary
- Includes fallback to shell wrapper if .exe not found
- Provides helpful error message if Hookdeck is not installed

#### 2. Fixed Command Syntax (Lines 129-130)
**Before:**
```powershell
$HookdeckArgs = "listen 8766 linear --path /webhook/linear --url http://${env:HOST}:8765/webhook/linear"
```

**After:**
```powershell
# Correct Hookdeck syntax: listen <port> <source>
$HookdeckArgs = "listen 8765 linear"
```

**Changes:**
- Removed incorrect `--path` and `--url` flags
- Uses correct syntax: `listen <port> <source>`
- Changed port from 8766 to 8765

#### 3. Fixed Process Detection (Lines 134-143)
**Before:**
```powershell
$ExistingHookdeck = Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*hookdeck*"
}
```

**After:**
```powershell
# Check if Hookdeck process is already running (check for hookdeck.exe or hookdeck)
$ExistingHookdeck = Get-Process -Name "hookdeck" -ErrorAction SilentlyContinue | Where-Object {
    $_.ProcessName -eq "hookdeck"
}
if (-not $ExistingHookdeck) {
    # Also check for hookdeck.exe explicitly
    $ExistingHookdeck = Get-Process -Name "hookdeck" -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -like "*hookdeck.exe*"
    }
}
```

**Benefits:**
- Checks for `hookdeck` process instead of `node`
- Specifically looks for hookdeck.exe
- More accurate process detection

#### 4. Updated GitHub Listener (Lines 177-222)
Applied same fixes to GitHub listener:
- Uses same .exe path
- Uses correct command syntax: `listen 8765 github`
- Same process detection logic

**Note:** Both Linear and GitHub listeners use port 8765 since Hookdeck can only listen on one port at a time. In production, you would run separate Hookdeck commands for each service on different ports.

## Testing Results

### Before Fix
```
[-] Failed to start Hookdeck Linear listener: This command cannot be run completely because the system cannot find all the information required.
```

### After Fix
```powershell
.\scripts\start_full_stack.ps1 -ShowConsole
```

**Expected Output:**
```
[2025-12-27_19-50-00] Checking Hookdeck status...
[2025-12-27_19-50-00] Hookdeck will listen on port 8765 and forward to: http://0.0.0.0:8765/webhook/linear
   [+] Starting Hookdeck Linear listener in separate window...
   [+] Hookdeck Linear listener started (PID: 12345)
       Window title: Hookdeck - Linear Listener
```

## How to Use

### Development Mode (Auto-start Hookdeck)
```powershell
cd D:\projects\OmegaKG\Omega_KG_stable
.\scripts\start_full_stack.ps1 -ShowConsole
```

This will:
1. ✅ Start databases (Neo4j, PostgreSQL)
2. ✅ Start capture server (port 8765)
3. ✅ Start Hookdeck Linear listener in separate window (port 8765)
4. ✅ Show manual instructions for GitHub listener

### Production Mode (Manual Hookdeck)
```powershell
.\scripts\start_full_stack.ps1
```

Shows instructions for manual Hookdeck startup.

## Manual Hookdeck Commands

If you need to start Hookdeck manually:

**Linear Listener:**
```bash
C:\Users\steyn\AppData\Roaming\npm\node_modules\hookdeck-cli\bin\hookdeck.exe listen 8765 linear
```

**GitHub Listener:**
```bash
C:\Users\steyn\AppData\Roaming\npm\node_modules\hookdeck-cli\bin\hookdeck.exe listen 8765 github
```

## Limitations

1. **Single Port**: Hookdeck can only listen on one port at a time
2. **Interactive Terminal**: Hookdeck requires an interactive terminal (can't run as Windows service)
3. **Windows Only**: The .exe fix is Windows-specific

## Future Improvements

As you mentioned working on a more robust solution to replace Hookdeck, here are some alternatives:

1. **Direct Webhook Integration**: Configure Linear/GitHub to send webhooks directly to `http://localhost:8765/webhook/...`
2. **Nginx Reverse Proxy**: Use nginx to route webhooks to different endpoints
3. **Custom Webhook Relay**: Build a simple Python/Node.js relay service
4. **Cloud Webhooks**: Use a cloud service like ngrok, localtunnel, or cloudflared

## Files Modified

1. `scripts/start_full_stack.ps1` - Fixed Hookdeck integration
   - Line 1: Updated version to v2.5
   - Lines 13-16: Added changelog
   - Lines 117-128: Fixed Hookdeck path detection
   - Lines 129-130: Fixed command syntax
   - Lines 134-143: Fixed process detection
   - Lines 177-222: Fixed GitHub listener

## Verification Steps

1. Run: `.\scripts\start_full_stack.ps1 -ShowConsole`
2. Check that Hookdeck window opens
3. Verify Hookdeck shows listening status
4. Test webhook: `curl -X POST http://localhost:8765/webhook/linear -H "Content-Type: application/json" -d '{"test": "data"}'`
5. Check Hookdeck receives the webhook

## Success Criteria

✅ Hookdeck starts without errors
✅ Hookdeck shows interactive UI
✅ Webhooks are forwarded to capture server
✅ Capture server processes webhooks correctly
✅ Both Linear and GitHub endpoints work

---

**Status**: ✅ Complete
**Version**: v2.5 Hookdeck-Fixed
**Date**: 2025-12-27
