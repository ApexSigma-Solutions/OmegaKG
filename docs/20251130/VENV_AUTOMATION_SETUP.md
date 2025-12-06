# Virtual Environment Automation - Setup Complete ✅

## Summary

I've created automated virtual environment activation for the Omega_KG project. Here's what was done:

### Files Created

1. **`scripts/omega-venv.ps1`** - PowerShell script with automation functions
   - `Activate-OmegaVenv` function to activate the .venv
   - `Deactivate-OmegaVenv` function to deactivate
   - Convenient aliases: `activate-omega` and `deactivate-omega`
   - Auto-activates when in Omega_KG directory
   - Adds Poetry to PATH automatically

2. **`scripts/VENV_SETUP.md`** - Setup instructions and troubleshooting

### Current Status ✅

- ✅ Python 3.13.6 is active in `.venv`
- ✅ Virtual environment created at `C:\Users\steyn\OneDrive\ApexSigma\Omega_KG\.venv`
- ✅ Poetry installed (system-wide at `$env:APPDATA\Python\Scripts`)
- ✅ Script tested and working

### How to Use

#### Option 1: One-Time Manual Activation

```powershell
# From any directory, run:
. "C:\Users\steyn\OneDrive\ApexSigma\Omega_KG\scripts\omega-venv.ps1"

# Then use:
activate-omega
```

#### Option 2: Auto-Activation (Recommended)

Add this line to your PowerShell profile:

```powershell
. "C:\Users\steyn\OneDrive\ApexSigma\Omega_KG\scripts\omega-venv.ps1"
```

To edit profile:
```powershell
notepad $PROFILE
```

Restart PowerShell or run:
```powershell
. $PROFILE
```

### Available Commands

Once the script is loaded, you'll have:

```powershell
activate-omega      # Activate .venv + add Poetry to PATH
deactivate-omega    # Deactivate .venv
```

### What Gets Automated

✅ Activates `.venv` virtual environment
✅ Adds Poetry to PATH
✅ Displays Python version
✅ Auto-activates when entering Omega_KG directory
✅ Provides convenient command aliases
✅ Shows setup instructions on load

### Next Steps

1. **Option A**: Load manually:
   ```powershell
   . "C:\Users\steyn\OneDrive\ApexSigma\Omega_KG\scripts\omega-venv.ps1"
   ```

2. **Option B**: Add to profile for auto-loading (recommended):
   ```powershell
   # Edit your profile
   notepad $PROFILE

   # Add this line:
   . "C:\Users\steyn\OneDrive\ApexSigma\Omega_KG\scripts\omega-venv.ps1"
   ```

That's it! You now have automated `.venv` activation for Omega_KG.
