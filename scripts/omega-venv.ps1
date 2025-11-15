# ============================================================
# Omega_KG Virtual Environment Auto-Activation Script
# ============================================================
# Source this from your PowerShell profile to enable auto-activation
# Add this line to your profile: . "$PSScriptRoot\..\scripts\omega-venv.ps1"

function Activate-OmegaVenv {
    <#
    .SYNOPSIS
    Activate the Omega_KG virtual environment
    
    .DESCRIPTION
    Activates the .venv for Omega_KG and adds Poetry to PATH
    #>
    $venvPath = "C:\Users\steyn\OneDrive\ApexSigma\Omega_KG\.venv"
    $activateScript = Join-Path $venvPath "Scripts\Activate.ps1"
    
    if (Test-Path $activateScript) {
        & $activateScript
        Write-Host "✅ Activated .venv for Omega_KG" -ForegroundColor Green
        Write-Host "   Python: $(python --version)" -ForegroundColor Gray
        Write-Host "   Poetry: $(poetry --version)" -ForegroundColor Gray
    } else {
        Write-Host "⚠️  Virtual environment not found at: $venvPath" -ForegroundColor Yellow
        Write-Host "   Run: python -m venv .venv" -ForegroundColor Yellow
    }
}

function Deactivate-OmegaVenv {
    <#
    .SYNOPSIS
    Deactivate the Omega_KG virtual environment
    #>
    if ($env:VIRTUAL_ENV) {
        deactivate
        Write-Host "✅ Deactivated virtual environment" -ForegroundColor Yellow
    } else {
        Write-Host "⚠️  No virtual environment is currently active" -ForegroundColor Yellow
    }
}

# Create convenient aliases
Set-Alias -Name activate-omega -Value Activate-OmegaVenv -Force -Scope Global
Set-Alias -Name deactivate-omega -Value Deactivate-OmegaVenv -Force -Scope Global

# Add Poetry to PATH if not already present
if ($env:PATH -notmatch "Python\\Scripts") {
    $env:PATH = "$env:APPDATA\Python\Scripts;$env:PATH"
    Write-Host "✨ Added Poetry to PATH" -ForegroundColor Cyan
}

# Auto-activate if we're in the Omega_KG directory
$currentPath = (Get-Location).Path
if ($currentPath -match "Omega_KG|omega_kg") {
    Activate-OmegaVenv
}

Write-Host "✨ Omega_KG venv automation ready:" -ForegroundColor Green
Write-Host "   activate-omega   - Activate .venv and Poetry" -ForegroundColor Gray
Write-Host "   deactivate-omega - Deactivate .venv" -ForegroundColor Gray
