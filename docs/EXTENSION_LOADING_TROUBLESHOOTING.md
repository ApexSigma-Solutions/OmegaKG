# Chrome Extension Loading Guide - Troubleshooting

**Date**: October 30, 2025  
**Issue**: "Manifest file is missing or unreadable" when loading extension

## Root Cause

The extension is stored on OneDrive, which has special file permissions and access restrictions. Chrome may have issues accessing files directly from OneDrive paths, especially if:

1. OneDrive sync is in progress
2. File access permissions are restricted
3. The path contains spaces or special characters
4. Chrome is running with different permissions than the file owner

## Solution: Copy Extension to Local Folder

The most reliable solution is to copy the extension files to a standard local folder (not OneDrive).

### Step 1: Copy Extension to a Local Folder

**Option A: Copy to Program Files (Recommended)**

```powershell
# Run PowerShell as Administrator

# Create extension directory
$ExtDir = "C:\Program Files\Omega_KG_Extension"
New-Item -ItemType Directory -Path $ExtDir -Force

# Copy extension files
Copy-Item "C:\Users\steyn\OneDrive\ApexSigma\Omega_KG\chrome-extension\*" `
          -Destination $ExtDir -Recurse -Force

Write-Host "Extension copied to: $ExtDir" -ForegroundColor Green
```

**Option B: Copy to Local AppData (Alternative)**

```powershell
# No admin needed

# Create extension directory
$ExtDir = "$env:LOCALAPPDATA\Omega_KG_Extension"
New-Item -ItemType Directory -Path $ExtDir -Force

# Copy extension files
Copy-Item "C:\Users\steyn\OneDrive\ApexSigma\Omega_KG\chrome-extension\*" `
          -Destination $ExtDir -Recurse -Force

Write-Host "Extension copied to: $ExtDir" -ForegroundColor Green
```

**Option C: Copy to Root of C: Drive (Simplest)**

```powershell
# No admin needed

$ExtDir = "C:\Omega_KG_Extension"
New-Item -ItemType Directory -Path $ExtDir -Force

# Copy extension files
Copy-Item "C:\Users\steyn\OneDrive\ApexSigma\Omega_KG\chrome-extension\*" `
          -Destination $ExtDir -Recurse -Force

Write-Host "Extension copied to: $ExtDir" -ForegroundColor Green
```

### Step 2: Verify Copied Files

```powershell
# Verify all files were copied
$ExtDir = "C:\Omega_KG_Extension"  # Use your chosen path
Get-ChildItem -Path $ExtDir

# You should see:
# - manifest.json
# - content.js
# - background.js
```

### Step 3: Load Extension in Chrome

1. **Open Chrome**
2. **Navigate to**: `chrome://extensions/`
3. **Enable "Developer mode"** (toggle in top right corner)
4. **Click "Load unpacked"** button
5. **Select the folder** where you copied the extension
   - e.g., `C:\Omega_KG_Extension`
6. **Click "Select Folder"**

### Step 4: Verify Extension is Loaded

After loading, you should see:

```
Omega_KG Chat Capture
Version: 1.0.0
📍 Location: C:\Omega_KG_Extension
🟢 [Enabled]
```

### Step 5: Test the Extension

1. **Open DevTools** (F12) on the extension entry
2. **Click on "Service worker"** link
3. **Navigate to a supported site** (Gemini, ChatGPT, Claude, etc.)
4. **Open DevTools** (F12) on the Gemini page
5. **Check Console** for messages like:
   ```
   [Omega_KG] Started capturing: gemini
   [Omega_KG] Messages found: X
   ```

## Troubleshooting - File Permissions Issue

If you still get "Manifest file is missing or unreadable", try:

### Fix 1: Check OneDrive Status

```powershell
# Check if OneDrive is currently syncing
$OneDrivePath = "$env:USERPROFILE\OneDrive\ApexSigma\Omega_KG"
Get-ItemProperty "$OneDrivePath\chrome-extension\manifest.json" | Select-Object *

# If locked, wait for sync to complete
```

### Fix 2: Disable OneDrive Sync Temporarily

1. Open **OneDrive Settings**
2. Find **ApexSigma** folder
3. Click **Stop sync** (temporary)
4. Try loading extension
5. When done, re-enable sync

### Fix 3: Change Chrome Permissions

```powershell
# Run Chrome as Administrator
& "C:\Program Files\Google\Chrome\Application\chrome.exe" --run-as-admin chrome://extensions/
```

## Automated Copy Script

For convenience, here's a script you can use to copy the extension:

**File**: `scripts/copy-extension-local.ps1`

```powershell
param(
    [string]$TargetPath = "C:\Omega_KG_Extension",
    [switch]$OpenChrome
)

Write-Host "`n🔄 Copying Omega_KG Extension to local folder..." -ForegroundColor Cyan

$SourcePath = "C:\Users\steyn\OneDrive\ApexSigma\Omega_KG\chrome-extension"

# Verify source exists
if (-not (Test-Path $SourcePath)) {
    Write-Host "❌ Source not found: $SourcePath" -ForegroundColor Red
    exit 1
}

# Create target directory
if (Test-Path $TargetPath) {
    Write-Host "⚠️  Target directory already exists, removing..." -ForegroundColor Yellow
    Remove-Item $TargetPath -Recurse -Force
}

New-Item -ItemType Directory -Path $TargetPath -Force | Out-Null
Write-Host "✅ Created: $TargetPath" -ForegroundColor Green

# Copy files
Copy-Item "$SourcePath\*" -Destination $TargetPath -Recurse -Force
Write-Host "✅ Copied extension files" -ForegroundColor Green

# Verify
$files = Get-ChildItem $TargetPath -File | Select-Object -ExpandProperty Name
Write-Host "`n📂 Files in $TargetPath:" -ForegroundColor Yellow
$files | ForEach-Object { Write-Host "   • $_" -ForegroundColor Gray }

# Show extension path
Write-Host "`n🔗 Extension path for Chrome:" -ForegroundColor Yellow
Write-Host "   $TargetPath" -ForegroundColor Cyan

Write-Host "`n📖 Next steps:" -ForegroundColor Yellow
Write-Host "   1. Open Chrome" -ForegroundColor Gray
Write-Host "   2. Go to chrome://extensions/" -ForegroundColor Gray
Write-Host "   3. Enable 'Developer mode'" -ForegroundColor Gray
Write-Host "   4. Click 'Load unpacked'" -ForegroundColor Gray
Write-Host "   5. Select: $TargetPath" -ForegroundColor Gray

if ($OpenChrome) {
    Write-Host "`n🌐 Opening Chrome extensions page..." -ForegroundColor Cyan
    & "C:\Program Files\Google\Chrome\Application\chrome.exe" "chrome://extensions/"
}

Write-Host "`n✅ Extension copy complete!`n" -ForegroundColor Green
```

### Usage

```powershell
# Copy to C:\Omega_KG_Extension and open Chrome
.\scripts\copy-extension-local.ps1 -OpenChrome

# Copy to custom location
.\scripts\copy-extension-local.ps1 -TargetPath "C:\MyExtensions\Omega_KG"
```

## Keeping Extension in Sync

Once copied locally, you have two options:

### Option 1: Auto-Sync (Recommended)

Create a script that keeps the local copy updated:

```powershell
# Watch for changes and copy
$source = "C:\Users\steyn\OneDrive\ApexSigma\Omega_KG\chrome-extension"
$target = "C:\Omega_KG_Extension"

$watcher = New-Object System.IO.FileSystemWatcher
$watcher.Path = $source
$watcher.IncludeSubdirectories = $true
$watcher.EnableRaisingEvents = $true

$action = {
    Write-Host "📝 Change detected, syncing..." -ForegroundColor Yellow
    Copy-Item "$source\*" -Destination $target -Recurse -Force
    Write-Host "✅ Synced" -ForegroundColor Green
}

Register-ObjectEvent -InputObject $watcher -EventName "Changed" -Action $action | Out-Null
Register-ObjectEvent -InputObject $watcher -EventName "Created" -Action $action | Out-Null

Write-Host "👀 Watching for changes in $source..." -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow

while ($true) { Start-Sleep -Seconds 1 }
```

### Option 2: Manual Update

After making changes to the extension, run:

```powershell
.\scripts\copy-extension-local.ps1
```

Then reload the extension in Chrome:
1. Go to `chrome://extensions/`
2. Click the ↻ (reload) icon on the Omega_KG extension card

## Summary

| Method | Pros | Cons |
|--------|------|------|
| **OneDrive Direct** | Single source of truth | Sync conflicts, permission issues |
| **Local Copy** | Reliable, no sync issues | Need to keep in sync |
| **Auto-Sync Script** | Always updated | Extra complexity |

**Recommendation**: Use **Local Copy** method with **Manual Sync** (easiest and most reliable).

---

**Next Steps**:
1. Copy extension to local folder using the PowerShell command above
2. Load unpacked extension in Chrome from new location
3. Test on Gemini or ChatGPT
4. Check console messages for [Omega_KG] logs

**If still issues**:
- Post the console error messages here
- Run diagnostic: `.\scripts\diagnose-extension.ps1`
- Check file permissions: `Get-Acl "C:\Omega_KG_Extension\manifest.json"`
