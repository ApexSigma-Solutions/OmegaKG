# Omega_KG Shell Integration - CORRECTED
# Automatically logs commands to Obsidian session notes
# Copy this entire content into: C:\Users\steyn\OneDrive\Documents\PowerShell\Microsoft.PowerShell_profile.ps1

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
    if ($Command -match '^\s*#') { return }

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

### [$timestamp] $statusEmoji ``$Command``
**Type:** $commandType | **Exit:** $ExitCode | **Path:** ``$WorkingDirectory``

"@

    Add-Content -Path $env:OMEGA_SESSION_LOG -Value $entry
}

# Prompt with command logging
function prompt {
    $history = Get-History -Count 1 -ErrorAction SilentlyContinue
    if ($history -and $history.ExecutionStatus -eq 'Completed') {
        $lastLoggedCommand = Get-Content $env:OMEGA_SESSION_LOG -Tail 1 -ErrorAction SilentlyContinue
        if ($lastLoggedCommand -notmatch [regex]::Escape($history.CommandLine)) {
            Add-OmegaCommand -Command $history.CommandLine -ExitCode $LASTEXITCODE -WorkingDirectory (Get-Location).Path
        }
    }

    "PS $($executionContext.SessionState.Path.CurrentLocation)$('>' * ($nestedPromptLevel + 1)) "
}

Initialize-OmegaSession

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
