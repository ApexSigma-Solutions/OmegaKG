# Quick Capture Test

## Current Status

✅ **Capture-server is NOW RUNNING** on http://localhost:8765

Your extension can now capture conversations!

## Test It Now

1. **In Chrome on Gemini** (or ChatGPT):
   - Make sure you have the extension loaded
   - Send a new message
   - Wait for a response (2-3 seconds)

2. **Check the console** (F12 → Console):
   Look for one of these messages:
   - ✅ `[Omega_KG] ✅ Captured X messages from gemini`
   - ✅ `[Omega_KG] Started capturing: gemini`

3. **If you see capture messages, it's working!**

## Important: Keep Server Running

The capture-server needs to stay running for the extension to work.

### Option 1: Use Auto-Start System (Recommended)

This is what we built to solve exactly this problem!

```powershell
# Register capture-server to auto-start when you open AI web apps
.\scripts\register-capture-monitor.ps1
```

Then reboot, and the system will:
- Automatically detect when you open Gemini/ChatGPT/Claude
- Automatically start capture-server
- Automatically stop it when you close all AI apps

### Option 2: Keep Server Window Open

For now, keep the terminal window open where capture-server is running:

```
🚀 Starting Omega_KG Capture Server
Listening on: http://localhost:8765
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8765 (Press CTRL+C to quit)
```

### Option 3: Use PowerShell Script

You can start it anytime with:

```powershell
cd "C:\Users\steyn\OneDrive\ApexSigma\Omega_KG"
poetry run capture-server
```

---

## Why This Stopped Working Yesterday

The capture-server process wasn't running. The extension needs:

1. ✅ Extension loaded in Chrome (working)
2. ✅ Content script capturing messages (working)
3. ❌ **Capture-server receiving data** (was missing)

Now that the server is running, everything should work!

---

## Next Steps

1. **Test capture** with a message in Gemini
2. **Check console** for success message
3. **Set up auto-start** using: `.\scripts\register-capture-monitor.ps1`
4. **Done!** - From now on, captures happen automatically

---

**Server Status**: 🟢 RUNNING on localhost:8765
