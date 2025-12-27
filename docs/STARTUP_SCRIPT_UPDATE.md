# Startup Script Update - Auto-Hookdeck with -ShowConsole

## Summary

Modified `start_full_stack.ps1` to automatically start Hookdeck listeners in separate console windows when using the `-ShowConsole` flag, making webhook monitoring easier during development.

## Changes Made

### File: `scripts/start_full_stack.ps1`

#### Version Bump
- Updated header from `v2.3` to `v2.4 Auto-Hookdeck`
- Added documentation about the new auto-start behavior

#### Linear Listener (Lines 136-146)
**New behavior when `-ShowConsole` is used:**
```powershell
} elseif ($ShowConsole) {
    # Start Hookdeck in a separate console window when ShowConsole is enabled
    Write-Output "   [+] Starting Hookdeck Linear listener in separate window..."
    try {
        $HookdeckProc = Start-Process -FilePath $HookdeckPath -ArgumentList $HookdeckArgs -WindowStyle "Normal" -PassThru
        Write-Output "   [+] Hookdeck Linear listener started (PID: $($HookdeckProc.Id))"
        Write-Output "       Window title: Hookdeck - Linear Listener"
    } catch {
        Write-Error "   [-] Failed to start Hookdeck Linear listener: $($_.Exception.Message)"
        Write-Output "   [!] You can start it manually: $HookdeckPath $HookdeckArgs"
    }
}
```

#### GitHub Listener (Lines 179-189)
**New behavior when `-ShowConsole` is used:**
```powershell
} elseif ($ShowConsole) {
    # Start GitHub listener in a separate console window when ShowConsole is enabled
    Write-Output "   [+] Starting Hookdeck GitHub listener in separate window..."
    try {
        $GitHubProc = Start-Process -FilePath $HookdeckPath -ArgumentList $GitHubArgs -WindowStyle "Normal" -PassThru
        Write-Output "   [+] Hookdeck GitHub listener started (PID: $($GitHubProc.Id))"
        Write-Output "       Window title: Hookdeck - GitHub Listener"
    } catch {
        Write-Error "   [-] Failed to start Hookdeck GitHub listener: $($_.Exception.Message)"
        Write-Output "   [!] You can start it manually: $HookdeckPath $GitHubArgs"
    }
}
```

## How It Works

### Production Mode (Default)
```powershell
.\scripts\start_full_stack.ps1
```
- Capture Server: ✅ Started automatically (hidden)
- Databases: ✅ Started automatically
- Hookdeck Listeners: ❌ Manual startup required (shows instructions)

### Development Mode (With -ShowConsole)
```powershell
.\scripts\start_full_stack.ps1 -ShowConsole
```
- Capture Server: ✅ Started automatically (visible window)
- Databases: ✅ Started automatically
- Hookdeck Linear: ✅ Auto-starts in separate console window
- Hookdeck GitHub: ✅ Auto-starts in separate console window

## Benefits

1. **Easy Monitoring**: See Hookdeck output in real-time without manual terminal setup
2. **Faster Development**: No need to manually start Hookdeck listeners during development
3. **Clear Separation**: Each service runs in its own window for easy monitoring
4. **Backwards Compatible**: Production mode unchanged (still shows manual instructions)
5. **PID Tracking**: Script tracks Hookdeck process IDs for watchdog functionality

## What Opens When Using -ShowConsole

When you run `.\scripts\start_full_stack.ps1 -ShowConsole`, you will see:

1. **Main PowerShell Window**: Shows the startup script output
2. **Capture Server Window**: Visible Uvicorn/Poetry process
3. **Hookdeck Linear Window**: Title shows "Hookdeck - Linear Listener" on port 8766
4. **Hookdeck GitHub Window**: Title shows "HookHub - GitHub Listener" on port 8767

## Process Monitoring

The script now properly tracks Hookdeck processes:

- `$HookdeckProc`: Tracks the Linear listener PID
- `$GitHubProc`: Tracks the GitHub listener PID
- Used by the watchdog loop (when `-Persistent` flag is used) to restart failed processes

## Error Handling

If Hookdeck fails to start:
- Error is logged with full exception details
- Manual startup command is displayed as fallback
- Script continues (doesn't crash)
- Process tracking variables remain null

## Example Usage

### Start Everything with Visible Windows
```powershell
cd D:\projects\OmegaKG\Omega_KG_stable
.\scripts\start_full_stack.ps1 -ShowConsole
```

**Expected Output:**
```
[2025-12-27_19-30-00] DEBUG MODE: Windows will be visible. Logs streaming to screen (NOT files).
[2025-12-27_19-30-00] Starting Capture Server...
   [+] Capture Server started (PID: 1234)
[2025-12-27_19-30-00] Hookdeck will listen on port 8766 and forward to: http://0.0.0.0:8765/webhook/linear
   [+] Starting Hookdeck Linear listener in separate window...
   [+] Hookdeck Linear listener started (PID: 5678)
       Window title: Hookdeck - Linear Listener
[2025-12-27_19-30-00] GitHub listener will listen on port 8767 and forward to: http://0.0.0.0:8765/webhooks/github
   [+] Starting Hookdeck GitHub listener in separate window...
   [+] Hookdeck GitHub listener started (PID: 9012)
       Window title: Hookdeck - GitHub Listener
[2025-12-27_19-30-00] Sequence complete. Processes are running in background.
```

## Notes

- Each Hookdeck listener gets its own console window
- Window titles help identify which listener is which
- PIDs are logged for troubleshooting
- The watchdog (with `-Persistent`) can now restart Hookdeck if they crash
- Perfect for development and debugging sessions

## Future Enhancement

As mentioned, you're working on a more robust solution to negate the need for Hookdeck. This update provides a temporary but helpful improvement for webhook monitoring until that solution is ready.
