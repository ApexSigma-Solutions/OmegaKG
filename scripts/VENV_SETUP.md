# Omega_KG Virtual Environment Automation

## Quick Setup

### Option 1: Manual Activation (One-time)
```powershell
activate-omega
```

### Option 2: Auto-Activation in PowerShell Profile (Recommended)

Add this line to your PowerShell profile:

```powershell
# In: C:\Users\steyn\OneDrive\Documents\PowerShell\Microsoft.PowerShell_profile.ps1
. "C:\Users\steyn\OneDrive\ApexSigma\Omega_KG\scripts\omega-venv.ps1"
```

To open your profile in an editor:
```powershell
notepad $PROFILE
```

Then restart PowerShell or reload the profile:
```powershell
. $PROFILE
```

## Available Commands

Once loaded, you'll have these commands available:

```powershell
# Activate the virtual environment and add Poetry to PATH
activate-omega

# Deactivate the virtual environment
deactivate-omega
```

## What This Automation Does

✅ Activates `.venv` for Omega_KG
✅ Adds Poetry to your PATH automatically
✅ Shows Python and Poetry versions
✅ Auto-activates when you cd into Omega_KG directory
✅ Provides convenient aliases for quick access

## Troubleshooting

If Poetry is not found:
```powershell
# Poetry should be at:
$env:APPDATA\Python\Scripts\poetry.exe

# Check if it exists:
Test-Path "$env:APPDATA\Python\Scripts\poetry.exe"
```

If Python is not found:
```powershell
# Check venv was created properly:
Test-Path "C:\Users\steyn\OneDrive\ApexSigma\Omega_KG\.venv\Scripts\python.exe"

# If missing, create it:
python -m venv .venv
```

## Manual Commands (Without Automation)

If you prefer not to use automation:

```powershell
# Activate venv manually
& "C:\Users\steyn\OneDrive\ApexSigma\Omega_KG\.venv\Scripts\Activate.ps1"

# Add Poetry to PATH manually
$env:PATH = "$env:APPDATA\Python\Scripts;$env:PATH"

# Verify installation
poetry --version
python --version
```
