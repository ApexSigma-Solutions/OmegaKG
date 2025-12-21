# D:\projects\OmegaKG\Omega_KG_stable\start_stack.ps1
# ==============================================================================
# OMEGAKG STACK ORCHESTRATOR
# Launches Hookdeck (Background) and Capture Server (Foreground)
# ==============================================================================

$ErrorActionPreference = "Stop"

function Check-Command ($cmd) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Error "❌ Command '$cmd' not found. Please install it or check PATH."
    }
}

try {
    # 1. Pre-flight Checks
    Check-Command "hookdeck"
    Check-Command "python"

    # 2. Start Hookdeck
    # We use -WindowStyle Hidden so it doesn't clutter your taskbar, 
    # but it runs as a background process.
    Write-Host "🚀 Launching Hookdeck Tunnel..." -ForegroundColor Cyan
    $hookdeck = Start-Process hookdeck -ArgumentList "listen", "8765", "linear-source" -WindowStyle Hidden -PassThru
    
    if ($hookdeck.Id) {
        Write-Host "   ✅ Hookdeck running (PID: $($hookdeck.Id))"
    }

    # 3. Environment Config
    # Enforce NO Ngrok to prevent conflicts
    $env:ENABLE_NGROK = "false"
    Write-Host "   ⚙️  Enforced ENABLE_NGROK=false" -ForegroundColor DarkGray

    # 4. Give Hookdeck a moment to handshake
    Start-Sleep -Seconds 2

    # 5. Start Capture Server
    Write-Host "`n⚡ Starting OmegaKG Capture Server..." -ForegroundColor Green
    Write-Host "   (Press Ctrl+C to stop server)" -ForegroundColor Gray
    Write-Host "==================================================`n"
    
    python -m omega_kg.capture_server

} catch {
    Write-Error $_.Exception.Message
    Read-Host "Press Enter to exit..."
} finally {
    # Optional: Kill Hookdeck when Python exits
    if ($hookdeck -and -not $hookdeck.HasExited) {
        Stop-Process -Id $hookdeck.Id -Force
        Write-Host "`n🛑 Hookdeck tunnel closed." -ForegroundColor Yellow
    }
}