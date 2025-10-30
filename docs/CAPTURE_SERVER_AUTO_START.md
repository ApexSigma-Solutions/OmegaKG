# Omega_KG Capture Server — Auto-Start Monitor

**Setup automation for the capture-server to start/stop based on active AI web apps.**

## Overview

The capture server is a FastAPI application that receives conversation captures from the Chrome extension. Rather than running it continuously (which uses resources), this solution monitors your browser for active AI web apps and:

- ✅ **Starts** capture-server when you open Gemini, ChatGPT, Claude, or other supported AI sites
- ✅ **Stops** capture-server when all supported sites are closed
- ✅ **Monitors** every 5 seconds for active apps (minimal overhead)
- ✅ **Runs in background** as a Windows scheduled task (starts at logon)

## Supported AI Web Apps

The monitor detects activity on these sites:

| App | URL |
|-----|-----|
| **Gemini** | `gemini.google.com` |
| **ChatGPT** | `chat.openai.com` |
| **Claude** | `claude.ai` |
| **Perplexity** | `perplexity.ai` |
| **GitHub Copilot** | `github.com/copilot` |
| **Qwen** | `chat.qwen.ai` |
| **Microsoft Copilot** | `copilot.microsoft.com`, `copilot.com` |

Add/remove sites by editing `$SupportedApps` array in `task-capture-server.ps1`.

## Quick Setup (One-Time)

### Step 1: Run as Administrator

Open **PowerShell as Administrator** (right-click → "Run as administrator").

### Step 2: Register the Monitor

```powershell
cd "C:\Users\[YourUsername]\OneDrive\ApexSigma\Omega_KG\scripts"
.\register-capture-monitor.ps1
```

You should see:

```
✅ Task registered successfully!

Task Details:
  Name: Omega_KG_Capture_Monitor
  Trigger: At user logon
  Script: C:\Users\[YourUsername]\OneDrive\ApexSigma\Omega_KG\scripts\task-capture-server.ps1
  Status: Ready to start at next logon
```

### Step 3: Test (Optional)

To test the monitor immediately without waiting for logon:

```powershell
Start-ScheduledTask -TaskName "Omega_KG_Capture_Monitor"
```

Or run the script directly (in any PowerShell window):

```powershell
.\task-capture-server.ps1
```

You'll see the monitor running and checking for active apps every 5 seconds. Press `Ctrl+C` to stop.

## How It Works

### Flow Diagram

```
┌─────────────────────────────────────────┐
│  Scheduled Task (Runs at logon)         │
│  "Omega_KG_Capture_Monitor"             │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│  task-capture-server.ps1                │
│  (Continuous monitoring loop)           │
└──────────────────┬──────────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
        ▼                     ▼
  Check every 5s     AI app detected?
        │                     │
     NO                      YES
     │                        │
     ├─► Server running?      ├─► Server running?
     │   ├─ YES → Stop it     │   ├─ YES → Do nothing
     │   └─ NO → Idle         │   └─ NO → Start it
     │                        │
     └──────────┬─────────────┘
                │
         Continue loop ◀─────────────────┘
```

### Detection Method

The script detects active AI web apps by:

1. Querying active processes for Chrome, Edge, and Firefox
2. Extracting window titles (which include page titles/URLs)
3. Matching window titles against the list of supported AI sites
4. No file access or system inspection required

### Server Start/Stop

**Start capture-server:**
```powershell
poetry run capture-server
```
- Runs on `http://localhost:8765`
- Receives captures from Chrome extension
- Minimal overhead when not actively capturing

**Stop capture-server:**
- Killed gracefully when no supported apps are active
- Or manually: Press `Ctrl+C` or `Stop-Process -Name python ...`

## Management

### Check if Task is Running

```powershell
Get-ScheduledTask -TaskName "Omega_KG_Capture_Monitor"
```

### View Task Details

```powershell
Get-ScheduledTask -TaskName "Omega_KG_Capture_Monitor" | Select-Object *
```

### Stop the Monitor Temporarily

```powershell
Stop-ScheduledTask -TaskName "Omega_KG_Capture_Monitor"
```

### Start the Monitor

```powershell
Start-ScheduledTask -TaskName "Omega_KG_Capture_Monitor"
```

### Remove the Scheduled Task

Run as Administrator:

```powershell
.\register-capture-monitor.ps1 -Unregister
```

Or manually:

```powershell
Unregister-ScheduledTask -TaskName "Omega_KG_Capture_Monitor" -Confirm:$false
```

## Troubleshooting

### Task doesn't start at logon

1. Open **Task Scheduler** (type `task scheduler` in Windows Start menu)
2. Navigate to **Task Scheduler Library** (or search for "Omega_KG_Capture_Monitor")
3. Right-click the task → **Properties**
4. Check:
   - **General** tab: "Run with highest privileges" is enabled
   - **Triggers** tab: "At log on" is configured for your user
   - **Settings** tab: "If the task is already running..." is set to "Do not start a new instance"

### Capture server doesn't start

1. Ensure **Poetry** is installed and working:
   ```powershell
   poetry --version
   ```

2. Ensure you can manually start capture-server:
   ```powershell
   cd "C:\Users\[YourUsername]\OneDrive\ApexSigma\Omega_KG"
   poetry run capture-server
   ```

3. Check if capture-server is already running:
   ```powershell
   Get-Process -Name python | Where-Object { $_.CommandLine -match "capture" }
   ```

4. Try starting the monitor manually:
   ```powershell
   .\task-capture-server.ps1
   ```
   Look for error messages.

### Monitor stops unexpectedly

The monitor will restart at next logon. To restart immediately:

```powershell
Start-ScheduledTask -TaskName "Omega_KG_Capture_Monitor"
```

### Chrome/Edge not detected

1. Ensure Chrome/Edge processes are visible to PowerShell:
   ```powershell
   Get-Process chrome   # or msedge
   ```

2. If not found, restart PowerShell as Administrator

3. Update window title detection in `task-capture-server.ps1` if browser title format changed

## Advanced Configuration

### Change Check Interval

Edit `task-capture-server.ps1` and modify:

```powershell
$CheckIntervalSeconds = 5  # Change to desired interval
```

Shorter intervals = faster response time but more CPU usage. Longer = vice versa.

### Add Custom AI Sites

Edit `task-capture-server.ps1` and add to `$SupportedApps`:

```powershell
$SupportedApps = @(
    # ...existing apps...
    "myai.example.com",  # Add here
)
```

### Log Server Output

Capture-server output can be logged by modifying the start command. Edit `register-capture-monitor.ps1`:

```powershell
# Change this:
-Argument "-NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`""

# To this (includes logging):
-Argument "-NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`" >> `"$env:USERPROFILE\Omega_KG_Monitor.log`" 2>&1"
```

## Files

- **`task-capture-server.ps1`** — Main monitoring loop (enhanced)
- **`register-capture-monitor.ps1`** — Registers task with Windows Scheduler
- **`capture-server.ps1`** — Helper script to start server (optional)

## Logs

Monitor and server output is not automatically logged. To enable logging, modify the scheduled task action to redirect output to a file (see "Advanced Configuration" above).

## Support

For issues or questions:
1. Check `docs/DEVELOPER_QUICKSTART.md` for general setup
2. Review `docs/DEVELOPMENT_SUMMARY.md` for architecture overview
3. Open an issue on GitHub

---

**Status**: ✅ Ready for production  
**Tested**: October 30, 2025  
**Last Updated**: October 30, 2025
