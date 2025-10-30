# Quick Fix: Extension Not Loading

**Issue**: "Manifest file is missing or unreadable"

**Root Cause**: Extension files are on OneDrive, which has permission restrictions that interfere with Chrome loading

**Quick Solution**: Copy extension to local disk (1 minute fix)

---

## ⚡ Quick Start (Copy & Paste)

```powershell
# Copy extension to local folder (no admin needed)
$source = "C:\Users\steyn\OneDrive\ApexSigma\Omega_KG\chrome-extension"
$target = "C:\Omega_KG_Extension"

New-Item -ItemType Directory -Path $target -Force | Out-Null
Copy-Item "$source\*" -Destination $target -Recurse -Force

Write-Host "✅ Copied to: $target" -ForegroundColor Green
Write-Host "Now open chrome://extensions/ and load unpacked from: $target" -ForegroundColor Yellow
```

Or use the helper script:

```powershell
cd "C:\Users\steyn\OneDrive\ApexSigma\Omega_KG"
.\scripts\copy-extension-local.ps1 -OpenChrome
```

---

## 📝 Manual Steps (If Script Doesn't Work)

### 1. Create Local Folder
- Create folder: `C:\Omega_KG_Extension`

### 2. Copy Files
Copy these 3 files to `C:\Omega_KG_Extension`:
- `chrome-extension\manifest.json`
- `chrome-extension\content.js`
- `chrome-extension\background.js`

### 3. Load in Chrome
1. Open Chrome
2. Type: `chrome://extensions/`
3. Toggle **Developer mode** ON (top right)
4. Click **Load unpacked**
5. Select: `C:\Omega_KG_Extension`
6. Click **Select Folder**

### 4. Verify
You should see:
```
Omega_KG Chat Capture
Version: 1.0.0
✅ [Enabled]
```

### 5. Test
- Open Gemini (https://gemini.google.com)
- Open DevTools (F12)
- Check Console for: `[Omega_KG] Started capturing: gemini`

---

## 🔧 Troubleshooting

### Still getting "Manifest missing" error?

**Try this**:
1. Right-click `C:\Omega_KG_Extension` → Properties → Security
2. Click Advanced
3. Click "Change" next to Owner
4. Type your username (e.g., `steyn`)
5. Click "Check Names" then OK
6. Click Apply → OK

Then reload extension in Chrome.

### Extension loads but not capturing messages?

Check console (F12 → Console):
- Should see: `[Omega_KG] Started capturing: gemini`
- If not, the selectors may have changed

Run selector validation:
```powershell
.\scripts\load-extension.ps1 -ValidateOnly
```

### Can't find chrome://extensions?

Type directly in address bar:
1. Click address bar (or Ctrl+L)
2. Type: `chrome://extensions/`
3. Press Enter

---

## 📂 File Structure

After copying, your `C:\Omega_KG_Extension` should have:

```
C:\Omega_KG_Extension\
├── manifest.json       (tells Chrome how to load extension)
├── content.js          (runs on AI websites)
└── background.js       (runs in background)
```

**That's all you need** - the other files in chrome-extension/ are optional.

---

## ⚙️ Advanced: Keep in Sync

If you want changes in the OneDrive folder to auto-sync to the local copy:

```powershell
# Use watch mode (optional)
.\scripts\copy-extension-local.ps1 -Watch

# This monitors OneDrive folder and copies changes every 2 seconds
# Press Ctrl+C to stop
```

---

## 🎯 Summary

| Step | Action |
|------|--------|
| 1 | Copy extension to `C:\Omega_KG_Extension` |
| 2 | Open `chrome://extensions/` |
| 3 | Enable Developer mode |
| 4 | Click Load unpacked |
| 5 | Select `C:\Omega_KG_Extension` |
| 6 | Test on Gemini/ChatGPT |

**That's it!** The extension should now work.

---

**Still having issues?**

Run the diagnostic:
```powershell
.\scripts\diagnose-extension.ps1
```

Then check:
- `docs/EXTENSION_LOADING_TROUBLESHOOTING.md` (detailed guide)
- `docs/DEVELOPER_QUICKSTART.md` (full setup)
- `chrome-extension/RELOAD_EXTENSION.md` (extension-specific help)
