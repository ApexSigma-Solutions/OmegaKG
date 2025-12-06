# ✅ Extension Loading - Verification Checklist

**Date**: October 30, 2025
**Status**: Ready to Load

## 🔍 Pre-Loading Verification

### Files Status
- ✅ Extension files copied to `C:\Omega_KG_Extension`
- ✅ `manifest.json` - Valid and readable
- ✅ `content.js` - Present (401 lines, 15293 bytes)
- ✅ `background.js` - Present (59 lines, 2328 bytes)

### Manifest Validation
- ✅ manifest_version: 3
- ✅ name: "Omega_KG Chat Capture"
- ✅ version: 1.0.0
- ✅ permissions: storage, activeTab, scripting, alarms
- ✅ host_permissions: All 8 AI sites configured
- ✅ background.service_worker: background.js
- ✅ content_scripts: Configured for 8 domains

### Host Permissions Verified
- ✅ claude.ai
- ✅ chat.openai.com
- ✅ gemini.google.com
- ✅ perplexity.ai
- ✅ github.com
- ✅ chat.qwen.ai
- ✅ copilot.microsoft.com
- ✅ copilot.com

---

## 📋 Manual Loading Steps

### Step 1: Open Chrome
Chrome should already be open at `chrome://extensions/`

If not, open a new tab and type: `chrome://extensions/`

### Step 2: Enable Developer Mode
Look in the top-right corner and toggle **Developer mode** ON

You should see a toggle switch that turns blue when enabled

### Step 3: Click "Load Unpacked"
After enabling Developer mode, a new button appears: **Load unpacked**

Click it

### Step 4: Select Extension Folder
A folder picker dialog will open

Navigate to: `C:\Omega_KG_Extension`

Click "Select Folder"

### Step 5: Verify Loading
You should see the extension card appear:

```
┌─────────────────────────────────────────────┐
│ Omega_KG Chat Capture                  v1.0.0
│ 🟢 [Enabled]
├─────────────────────────────────────────────┤
│ Version: 1.0.0
│ Location: C:\Omega_KG_Extension
├─────────────────────────────────────────────┤
│ [Details] [Remove]                          │
│ [⟳ Reload] [Errors] [Service worker]        │
└─────────────────────────────────────────────┘
```

---

## 🧪 Testing After Loading

### Test 1: Check Service Worker Console
1. On the extension card, click **Service worker**
2. Look for any errors (should be mostly empty)
3. Close the DevTools

### Test 2: Open a Supported Site
1. Go to https://gemini.google.com
2. Wait for page to load completely

### Test 3: Check Content Script Console
1. Press F12 to open DevTools
2. Go to Console tab
3. You should see a message like:
   ```
   [Omega_KG] Started capturing: gemini
   ```
4. Check for any red error messages

### Test 4: Send a Message
1. In Gemini, type a test message
2. Send it
3. In the DevTools console, you should see:
   ```
   [Omega_KG] Message captured
   [Omega_KG] Messages found: 1
   ```

### Test 5: Verify Capture Server Connection
1. Make sure capture-server is running:
   ```powershell
   poetry run capture-server
   ```
2. In console, check for messages indicating successful transmission
3. Check that no "Access to storage" errors appear

---

## 🚨 Troubleshooting If Loading Fails

### Error: "Manifest file is missing or unreadable"
**Possible causes**:
1. Wrong folder selected (verify you selected `C:\Omega_KG_Extension`)
2. Files not copied properly
3. Folder permissions issue

**Fix**:
```powershell
# Verify files exist
Get-ChildItem "C:\Omega_KG_Extension"

# If empty, run copy script again
.\scripts\copy-extension-local.ps1 -OpenChrome
```

### Error: "Invalid manifest.json"
**Likely cause**: JSON syntax error in manifest

**Fix**:
```powershell
# Validate manifest
$manifest = Get-Content "C:\Omega_KG_Extension\manifest.json" | ConvertFrom-Json
$manifest | ConvertTo-Json | Write-Host
```

### Extension shows but nothing happens
**Likely causes**:
1. Capture-server not running
2. Extension not enabled

**Fix**:
1. Verify extension is enabled (blue toggle)
2. Start capture-server: `poetry run capture-server`
3. Reload extension (click ↻ button)

### Service Worker console shows errors

**Common errors**:

| Error | Cause | Fix |
|-------|-------|-----|
| "Access to storage not allowed" | Storage API called from wrong context | Check background.js code |
| "Cannot find manifest" | Manifest.json has syntax error | Validate JSON in extension folder |
| "Cannot access host" | Missing host_permissions | Check manifest.json host_permissions |

---

## ✅ Confirmation Checklist

**Before testing, confirm**:

- [ ] Chrome is open and at `chrome://extensions/`
- [ ] Developer mode is enabled (blue toggle in top right)
- [ ] Extension folder is `C:\Omega_KG_Extension`
- [ ] Extension card shows "Omega_KG Chat Capture"
- [ ] Extension is enabled (blue toggle on card)
- [ ] Service worker console shows no critical errors
- [ ] Capture-server is running (or will be started by auto-start)

**After loading, confirm**:

- [ ] Can open Gemini/ChatGPT without errors
- [ ] DevTools console shows `[Omega_KG] Started capturing: ...`
- [ ] No red error messages in console
- [ ] Can send a message without console errors

---

## 🎯 Success Criteria

✅ **Extension successfully loaded when**:
1. Extension appears on `chrome://extensions/`
2. Extension card shows as enabled (blue toggle)
3. No manifest or permission errors
4. Console shows `[Omega_KG] Started capturing:` messages
5. Messages are captured without errors

---

## 📚 Additional Resources

If you need help:

1. **Quick reference**: `docs/QUICK_FIX_EXTENSION_NOT_LOADING.md`
2. **Detailed guide**: `docs/EXTENSION_LOADING_TROUBLESHOOTING.md`
3. **Developer info**: `docs/DEVELOPER_QUICKSTART.md`
4. **Extension notes**: `chrome-extension/RELOAD_EXTENSION.md`

---

## 🔧 Diagnostic Tools Available

```powershell
# Check extension setup
.\scripts\diagnose-extension.ps1

# Copy extension from OneDrive
.\scripts\copy-extension-local.ps1

# Load extension and validate
.\scripts\load-extension.ps1

# Run capture-server
poetry run capture-server

# Run auto-start monitor
.\scripts\task-capture-server.ps1
```

---

**Ready to load?** Follow the steps above and you should have a working extension! 🚀
