# OmegaKG Shell Integration Guide

This document describes the shell integration setup for the OmegaKG project.

## Overview

The shell integration provides convenient aliases and environment variables for quick access to OmegaKG functionality. It works by sourcing environment files that configure your shell.

## Files Created

### 1. `/c/Users/steyn/.local/bin/env`
**Global shell environment file** - Sourced by all shell sessions
- Sets up global OmegaKG paths
- Adds Poetry to PATH
- Creates global aliases
- Loaded automatically via `.profile`, `.bashrc`, and `.bash_profile`

### 2. `.omega_env` (in project directories)
**Project-specific environment file** - Must be sourced manually
- Sets up project-specific variables
- Creates project aliases
- Displays welcome banner

### 3. `source_env.sh`
**Helper script** - Makes sourcing easier
- Usage: `source ./source_env.sh`
- Automatically finds and sources `.omega_env`

## Usage

### For Stable Environment (`d:\projects\OmegaKG\Omega_KG_stable`)

```bash
# Load the environment
source ./source_env.sh

# Available commands:
omega-cd           # Go to project root
omega-scripts      # Go to scripts directory
omega-vault        # Go to Obsidian vault
omega-start        # Start full stack
omega-stop         # Stop all services
omega-health       # Check server health
omega-shell        # Activate Poetry shell
```

### For Dev Environment (`d:\projects\omega_kg_stable`)

```bash
# Load the environment
source ./source_env.sh

# Available commands:
omega-cd           # Go to project root
omega-scripts      # Go to scripts directory
omega-vault        # Go to Obsidian vault
omega-health       # Check server health
omega-shell        # Activate Poetry shell
```

## Environment Variables

Both environments set these variables:
- `OMEGA_KG_ROOT` - Project root directory
- `OMEGA_KG_SCRIPTS` - Scripts directory
- `OMEGA_KG_VAULT` - Obsidian vault path
- `OMEGA_KG_ENV` - Environment type (stable/dev)
- `POETRY_VENV` - Poetry virtual environment path
- `PATH` - Updated with Poetry and scripts

## Aliases

### Global Aliases (in `~/.local/bin/env`)
```bash
omega           # Go to OmegaKG root
omega-scripts   # Go to scripts directory
omega-vault     # Go to Obsidian vault
omega-logs      # Go to logs directory
omega-start     # Start full stack
omega-cleanup   # Cleanup processes
omega-test      # Run test script
```

### Project-Specific Aliases (in `.omega_env`)
```bash
omega-cd        # Go to project root
omega-config    # View project configuration
omega-health    # Check server health
omega-verify    # Verify stack setup
omega-poetry    # Run poetry commands
omega-install   # Install dependencies
omega-run       # Run capture server
```

## Adding to Shell Profile (Optional)

To automatically load the project environment when entering a directory, add this to your `.bashrc`:

```bash
# Auto-load OmegaKG environment
cd_to_omega() {
    if [ -f ".omega_env" ] && [ -f "source_env.sh" ]; then
        source ./source_env.sh
    fi
}

# Hook into cd command
PROMPT_COMMAND="cd_to_omega; $PROMPT_COMMAND"
```

Or manually source when needed:

```bash
# Add to .bashrc for convenience
alias load-omega='source ./source_env.sh'
```

## Troubleshooting

### "Command not found" errors
Make sure you've sourced the environment file:
```bash
source ~/.local/bin/env  # Global environment
source ./source_env.sh   # Project environment
```

### Poetry not found
The environment automatically adds Poetry to PATH. If issues persist:
```bash
export PATH="$HOME/AppData/Roaming/Python/Python312/Scripts:$PATH"
```

### Environment not loading
Check if files exist and have correct permissions:
```bash
ls -la ~/.local/bin/env
ls -la .omega_env source_env.sh
```

## Quick Start

1. **Source the global environment** (already done by your shell profile):
   ```bash
   source ~/.local/bin/env
   ```

2. **Navigate to project directory**:
   ```bash
   cd /d/projects/OmegaKG/Omega_KG_stable
   ```

3. **Load project environment**:
   ```bash
   source ./source_env.sh
   ```

4. **Start the stack**:
   ```bash
   omega-start
   ```

5. **Check health**:
   ```bash
   omega-health
   ```

## Notes

- The global environment (`~/.local/bin/env`) is loaded automatically
- Project environments must be sourced manually
- Each environment has its own set of aliases
- The environment is designed to work with both stable and dev setups
- Poetry virtual environments are isolated per project
