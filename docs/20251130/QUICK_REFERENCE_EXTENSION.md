# 📌 Quick Reference Card - Extension Loading

## 🚀 Quick Load (5 Steps)

```
1. Open Chrome → chrome://extensions/
2. Enable "Developer mode" (toggle, top right)
3. Click "Load unpacked"
4. Select: C:\Omega_KG_Extension
5. Click "Select Folder"
```

✅ **Extension loads successfully!**

---

## 🔧 Quick Commands

```powershell
# Copy extension from OneDrive
.\scripts\copy-extension-local.ps1 -OpenChrome

# Validate extension setup
.\scripts\diagnose-extension.ps1

# Run capture server
poetry run capture-server

# Run auto-start monitor
.\scripts\task-capture-server.ps1
```

---

## 📂 Key Paths

| Item | Path |
|------|------|
| Extension Location | `C:\Omega_KG_Extension` |
| Source (OneDrive) | `C:\Users\steyn\OneDrive\ApexSigma\Omega_KG\chrome-extension` |
| Quick Fix Guide | `docs/QUICK_FIX_EXTENSION_NOT_LOADING.md` |
| Full Troubleshooting | `docs/EXTENSION_LOADING_TROUBLESHOOTING.md` |
| Verification Checklist | `docs/EXTENSION_LOADING_VERIFICATION.md` |

---

## ⚡ Common Issues & Fixes

| Issue | Solution |
|-------|----------|
| "Manifest missing" | Use `C:\Omega_KG_Extension` path, not OneDrive |
| "Invalid manifest" | Run `.\scripts\diagnose-extension.ps1` |
| Extension not capturing | Verify `poetry run capture-server` is running |
| Developer mode hidden | Reload chrome://extensions page |
| Console shows errors | Check `docs/EXTENSION_LOADING_VERIFICATION.md` |

---

## ✅ Verification

After loading, confirm:

```
□ Extension shows "Omega_KG Chat Capture" on chrome://extensions/
□ Extension is enabled (blue toggle on card)
□ Visit https://gemini.google.com
□ Open DevTools (F12)
□ Console shows: [Omega_KG] Started capturing: gemini
□ Send test message without errors
```

---

## 📞 Need Help?

1. **Quick fix**: `docs/QUICK_FIX_EXTENSION_NOT_LOADING.md`
2. **Troubleshooting**: `docs/EXTENSION_LOADING_TROUBLESHOOTING.md`
3. **Step-by-step**: `docs/EXTENSION_LOADING_VERIFICATION.md`
4. **Full report**: `docs/EXTENSION_LOADING_RESOLUTION.md`
5. **Diagnostic**: `.\scripts\diagnose-extension.ps1`

---

## 🎯 Expected Result

✅ Chrome extensions page shows:
```
Omega_KG Chat Capture
Version: 1.0.0
🟢 [Enabled]

Location: C:\Omega_KG_Extension
```

✅ Gemini page console shows:
```
[Omega_KG] Started capturing: gemini
[Omega_KG] Messages found: X
```

---

**Status**: ✅ Ready to Load
**Last Updated**: October 30, 2025
