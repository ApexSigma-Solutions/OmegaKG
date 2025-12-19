# Automated Housekeeping Utility

## Overview

The `scripts/housekeeping.py` script automates routine maintenance tasks for the Omega KG repository root directory. It helps maintain a clean, organized codebase by automatically moving diagnostic reports, cleaning temporary files, and managing git changes.

## Features

- **Diagnostic Report Organization**: Automatically moves diagnostic reports (JSON files) from root to `docs/` folder
- **Temporary Directory Cleaning**: Cleans `.omegakg_temp/` and other temp directories while preserving structure
- **Git Integration**: Optionally stages and commits changes with standardized commit messages
- **Dry-Run Mode**: Preview actions without making changes
- **Safe Operation**: Checks for conflicts and preserves existing files

## Usage

### Basic Commands

```bash
# Preview what would be done (dry-run)
python scripts/housekeeping.py --dry-run

# Perform housekeeping and commit changes
python scripts/housekeeping.py --commit

# Perform housekeeping, commit, and push to remote
python scripts/housekeeping.py --push
```

### Command Line Options

| Option | Description |
|--------|-------------|
| `--dry-run` | Show what would be done without making changes |
| `--commit` | Stage and commit changes to git |
| `--push` | Push changes to remote repository (implies `--commit`) |
| `--help` | Show help message |

### Examples

**Preview housekeeping actions:**
```bash
python scripts/housekeeping.py --dry-run
```

**Perform cleanup and commit:**
```bash
python scripts/housekeeping.py --commit
```

**Full cleanup, commit, and push:**
```bash
python scripts/housekeeping.py --push
```

## What It Does

### 1. Diagnostic File Organization
Automatically detects and moves files matching these patterns from root to `docs/`:
- `diagnostic_health_report.json`
- `*_diagnostic_*.json`
- `*_health_*.json`
- `*_audit_*.json`
- `*_report.md`

### 2. Temporary Directory Cleaning
Cleans these directories while preserving structure:
- `.omegakg_temp/` - Omega KG development files
- `.temp/` - Temporary files

After cleaning, creates a `.gitkeep` file to preserve the directory.

### 3. Git Operations
When `--commit` is enabled:
- Stages all changes (`git add -A`)
- Creates a standardized commit message
- Includes timestamp and description

When `--push` is enabled:
- Pushes changes to `origin/beta`

## Example Output

```
================================================================================
OMEGA KG ROOT DIRECTORY HOUSEKEEPING
================================================================================

=== Checking for diagnostic files in root directory ===
[SKIP] Source file does not exist: d:\projects\Omega_KG_stable\diagnostic_health_report.json

=== Cleaning temporary directories ===
Cleaned: d:\projects\Omega_KG_stable\.omegakg_temp (Omega KG development)

=== Git Operations ===
Staged changes
Committed changes to git

================================================================================
HOUSEKEEPING REPORT
================================================================================
Mode: LIVE
Timestamp: 2025-12-20 00:15:30
Working Directory: d:\projects\Omega_KG_stable

Actions Performed (1):
  1. Cleaned: d:\projects\Omega_KG_stable\.omegakg_temp (Omega KG development)

[OK] Changes were made to the repository
================================================================================
```

## Integration

### Pre-Commit Hook (Optional)
You can integrate this into your workflow by adding it to a pre-commit hook:

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Run housekeeping before commit
python scripts/housekeeping.py --dry-run
if [ $? -ne 0 ]; then
    echo "Housekeeping check failed"
    exit 1
fi
```

### Scheduled Maintenance
Run periodically via cron or task scheduler:

```bash
# Daily at 2 AM
0 2 * * * cd /path/to/Omega_KG_stable && python scripts/housekeeping.py --commit
```

## Safety Features

- **Dry-Run Mode**: Always test with `--dry-run` first
- **Conflict Detection**: Skips files that already exist at destination
- **Preserve Structure**: Maintains directory hierarchies
- **Git Integration**: Only commits when changes are made
- **Detailed Logging**: Reports all actions taken

## Troubleshooting

### No Changes Detected
If the script reports no changes, this means:
- No diagnostic files found in root
- Temp directories already clean
- All files already organized

### Git Push Fails
If pushing fails:
- Check remote branch name (`origin/beta`)
- Verify git credentials
- Ensure branch is not protected

### Permission Errors
If you encounter permission errors:
```bash
chmod +x scripts/housekeeping.py
```

## Customization

The script can be easily extended by modifying the `HousekeepingManager` class:

1. **Add new file patterns** in `check_and_move_diagnostics()`
2. **Add new temp directories** in `organize_temp_directories()`
3. **Modify git behavior** in `stage_and_commit()`

## Requirements

- Python 3.12+
- Git (for commit/push operations)
- Access to repository root directory

## Related Scripts

- `diagnostic_phase1_config_check.py` - Environment validation
- `diagnostic_phase2_code_review.py` - Code structure review
- `diagnostic_phase3_e2e_test.py` - End-to-end testing
- `diagnostic_phase4_failure_recovery.py` - Error handling tests
- `diagnostic_phase5_ollama_check.py` - Ollama service validation
- `diagnostic_phase6_health_report.py` - System health reporting

---

**Note**: Always run with `--dry-run` first to preview actions before committing changes.