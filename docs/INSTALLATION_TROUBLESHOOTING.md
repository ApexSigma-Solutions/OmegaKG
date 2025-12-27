# Installation Troubleshooting Guide

## "Package not installed" Error

### Root Cause
The `omega_kg` package is not installed in the active virtual environment or not in edit mode.

### Resolution Steps

#### Windows (PowerShell)
```powershell
# Option 1: Automated setup
.\scripts\setup_omega_kg.ps1 -Environment stable

# Option 2: Manual install
.venv\Scripts\Activate.ps1
pip install -e .

# Option 3: Verify installation
python scripts\verify_installation.py
```

#### Linux/Mac (Bash)

```bash
# Option 1: Automated setup
./scripts/setup_omega_kg.sh -Environment stable

# Option 2: Manual install
source .venv/bin/activate
pip install -e .

# Option 3: Verify installation
python scripts/verify_installation.py
```

### Prevention

Always run the automated setup script when setting up a new environment. This script:

- Creates virtual environment if missing
- Installs dependencies in edit mode
- Verifies installation automatically

### Additional Resources

- [Installation Guide](docs/20251130/OMEGA_KG_SETUP_GUIDE.md)
- [Pre-flight Checks](omega_kg/pre_flight.py:11)
