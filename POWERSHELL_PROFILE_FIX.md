# PowerShell Profile Integration - Diagnostic & Fix

## 🔍 Root Cause Analysis

### Problem
Terminal session logs are NOT being captured to the Sessions folder because the PowerShell profile is configured with an **incorrect vault path**.

### Configuration Mismatch

| Component | Current Value | Should Be |
|-----------|---------------|-----------|
| **Profile Location** | `C:\Users\steyn\OneDrive\Documents\PowerShell\Microsoft.PowerShell_profile.ps1` | ✅ Correct |
| **Configured Vault Path** | `C:\Users\steyn\OneDrive\Apps\remotely-save\Omega.as Vault` | ❌ **WRONG** |
| **Actual Vault Path** | `C:\Users\steyn\OneDrive\ApexSigma\omegavault.as\omegavault.as` | ✅ **CORRECT** |
| **Session Directory** | Should be: `...omegavault.as\omegavault.as\Sessions` | Currently pointing to wrong path |

### Impact

Because of the path mismatch:
- ✗ Session log files are being created in: `C:\Users\steyn\OneDrive\Apps\remotely-save\Omega.as Vault\Sessions\`
- ✗ But the actual vault is in: `C:\Users\steyn\OneDrive\ApexSigma\omegavault.as\omegavault.as\Sessions\`
- ✗ The session files at `omegavault.as\Sessions\` are NOT being updated by the integration
- ✗ Commands are being logged to a vault that doesn't contain your Omega_KG project

## 🔧 How to Fix

### Step 1: Edit the PowerShell Profile

Run this command in PowerShell:

```powershell
notepad $PROFILE
```

### Step 2: Update the Vault Path

Find this line (should be around line 5):

```powershell
# CURRENT (WRONG):
$env:OMEGA_VAULT = "C:\Users\steyn\OneDrive\Apps\remotely-save\Omega.as Vault"
```

Replace it with:

```powershell
# NEW (CORRECT):
$env:OMEGA_VAULT = "C:\Users\steyn\OneDrive\ApexSigma\omegavault.as\omegavault.as"
```

### Step 3: Reload the Profile

Close your PowerShell terminal and open a new one, or run:

```powershell
& $PROFILE
```

### Step 4: Verify

Test the fix:

```powershell
Get-OmegaStats
```

Should output:
```
📊 Session Statistics
━━━━━━━━━━━━━━━━━━━━━
Total Commands: X
Success: Y
Errors: Z
Session Log: C:\Users\steyn\OneDrive\ApexSigma\omegavault.as\omegavault.as\Sessions\2025-10-29.md
```

## 📊 Current Session Log Status

### Existing Files
- `Sessions\2025-10-25.md` - Contains old captures from wrong path
- `Sessions\2025-10-26.md` - Contains old captures from wrong path

### What Will Happen After Fix
- New commands will be logged to: `Sessions\2025-10-29.md` (correct path)
- Old session files can be migrated/merged if needed

## 🐛 Secondary Issues Detected

The profile implementation has a few potential issues that may be worth addressing later:

### Issue 1: PreCommandLookupAction Hook Reliability
**Problem**: The command capture hook may not work in all PowerShell contexts
```powershell
# Current approach (unreliable):
$ExecutionContext.InvokeCommand.PreCommandLookupAction = {
    param($CommandName, $CommandLookupEventArgs)
    $global:OmegaLastCommand = $CommandName
}
```

**Better approach**: Use EnterValidationAttributeValue or rely directly on history

### Issue 2: Prompt Override
**Problem**: The custom prompt function may be overridden by VS Code or other shells
```powershell
# Current:
$function:prompt = { ... }

# Better:
function prompt {
    $history = Get-History -Count 1
    if ($history) {
        Add-OmegaCommand -Command $history.CommandLine -ExitCode $LASTEXITCODE
    }
    "PS $($executionContext.SessionState.Path.CurrentLocation)$('>' * ($nestedPromptLevel + 1)) "
}
```

### Issue 3: Trivial Command Filtering
The profile skips commands like 'ls', 'cd', 'pwd' which is good, but it might also skip important diagnostic commands.

## 📋 Recommended Profile Updates (Optional Enhancement)

For a more robust implementation, consider updating to this improved version:

```powershell
# Omega_KG Shell Integration - Enhanced
# Automatically logs commands to Obsidian session notes

# Configuration
$env:OMEGA_VAULT = "C:\Users\steyn\OneDrive\ApexSigma\omegavault.as\omegavault.as"
$env:OMEGA_SESSION_DIR = "$env:OMEGA_VAULT\Sessions"
$env:OMEGA_SESSION_LOG = "$env:OMEGA_SESSION_DIR\$(Get-Date -Format yyyy-MM-dd).md"

# Initialize session log
function Initialize-OmegaSession {
    if (-not (Test-Path $env:OMEGA_SESSION_DIR)) {
        New-Item -ItemType Directory -Force -Path $env:OMEGA_SESSION_DIR | Out-Null
    }

    if (-not (Test-Path $env:OMEGA_SESSION_LOG)) {
        $timestamp = Get-Date -Format "HH:mm:ss"
        $content = @"
---
type: session
date: $(Get-Date -Format yyyy-MM-dd)
start: $timestamp
tags: [session, terminal]
---

# Terminal Session $(Get-Date -Format yyyy-MM-dd)

Started: $timestamp

## Commands

"@
        Set-Content -Path $env:OMEGA_SESSION_LOG -Value $content
    }
}

# Log command to session note
function Add-OmegaCommand {
    param(
        [string]$Command,
        [int]$ExitCode = 0,
        [string]$WorkingDirectory = (Get-Location).Path
    )

    # Skip trivial commands
    $trivialCommands = @('ls', 'dir', 'cd', 'pwd', 'echo', 'cls', 'clear', '.', '..')
    $commandName = ($Command -split ' ')[0].TrimStart('&', '.', '\')
    if ($trivialCommands -contains $commandName) { return }
    if ($Command.Length -lt 3) { return }
    if ($Command -match '^\s*#') { return }  # Skip comments

    $timestamp = Get-Date -Format "HH:mm:ss"
    $statusEmoji = if ($ExitCode -eq 0) { "✅" } else { "❌" }

    # Detect command type
    $commandType = switch -Regex ($Command) {
        '^git '      { 'git' }
        '^poetry '   { 'poetry' }
        '^docker '   { 'docker' }
        '^python '   { 'python' }
        '^npm '      { 'node' }
        '^cargo '    { 'rust' }
        '^dotnet '   { 'dotnet' }
        '^terraform '{ 'terraform' }
        default      { 'shell' }
    }

    $entry = @"

### [$timestamp] $statusEmoji \`$Command\`
**Type:** $commandType | **Exit:** $ExitCode | **Path:** \`$WorkingDirectory\`

"@

    # NOTE: The backticks above are literal backticks for markdown code formatting
    # They should NOT have dollar signs escaped with them

    Add-Content -Path $env:OMEGA_SESSION_LOG -Value $entry
}

# Enhanced prompt with reliable command logging
function prompt {
    # Log previous command if it exists
    $history = Get-History -Count 1 -ErrorAction SilentlyContinue
    if ($history -and $history.ExecutionStatus -eq 'Completed') {
        $lastLoggedCommand = Get-Content $env:OMEGA_SESSION_LOG -Tail 1 -ErrorAction SilentlyContinue
        if ($lastLoggedCommand -notmatch [regex]::Escape($history.CommandLine)) {
            Add-OmegaCommand -Command $history.CommandLine -ExitCode $LASTEXITCODE -WorkingDirectory (Get-Location).Path
        }
    }

    # Return prompt
    "PS $($executionContext.SessionState.Path.CurrentLocation)$('>' * ($nestedPromptLevel + 1)) "
}

# Initialize on profile load
Initialize-OmegaSession

# Helper functions
function Get-OmegaSessionLog {
    <#
    .SYNOPSIS
    Open today's session log in default editor
    #>
    if (Test-Path $env:OMEGA_SESSION_LOG) {
        & $env:OMEGA_SESSION_LOG
    } else {
        Write-Host "No session log for today" -ForegroundColor Yellow
    }
}

function Get-OmegaStats {
    <#
    .SYNOPSIS
    Show session statistics
    #>
    if (-not (Test-Path $env:OMEGA_SESSION_LOG)) {
        Write-Host "No session log for today" -ForegroundColor Yellow
        return
    }

    $content = Get-Content $env:OMEGA_SESSION_LOG -Raw
    $commands = ([regex]::Matches($content, '###')).Count
    $errors = ([regex]::Matches($content, '❌')).Count
    $success = $commands - $errors

    Write-Host "`n📊 Session Statistics" -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
    Write-Host "Total Commands: $commands" -ForegroundColor White
    Write-Host "Success: $success" -ForegroundColor Green
    Write-Host "Errors: $errors" -ForegroundColor Red
    Write-Host "Success Rate: $([math]::Round(($success/$commands)*100))%" -ForegroundColor Cyan
    Write-Host "Session Log: $env:OMEGA_SESSION_LOG" -ForegroundColor Gray
}

Write-Host "✨ Omega_KG shell integration loaded" -ForegroundColor Green
Write-Host "   Vault: $env:OMEGA_VAULT" -ForegroundColor Gray
Write-Host "   Session: $env:OMEGA_SESSION_LOG" -ForegroundColor Gray
```

## 📝 Summary

**Immediate Action Required:**
1. Edit PowerShell profile: `notepad $PROFILE`
2. Change vault path from wrong location to: `C:\Users\steyn\OneDrive\ApexSigma\omegavault.as\omegavault.as`
3. Save and reload the profile
4. Verify with: `Get-OmegaStats`

After this fix, all new terminal commands will be properly logged to the Sessions folder in your actual vault!
