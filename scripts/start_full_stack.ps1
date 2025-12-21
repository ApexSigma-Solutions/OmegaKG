# Omega Full Stack Launcher
# -------------------------
# Purpose: Orchestrates the Capture Server (Uvicorn) and Webhook Gateway (Hookdeck).
# Context: Designed for Task Scheduler / Non-Interactive Execution.

param (
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$EnvFile = ".env"
)

$ErrorActionPreference = "Stop"

# --- 1. LOGGING CONFIG ---
$LogDir = Join-Path $ProjectRoot "logs"
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }

$Time = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$CaptureLog = Join-Path $LogDir "capture_server_$Time.log"
$CaptureErrLog = Join-Path $LogDir "capture_server_$Time.err.log"
$HookdeckLog = Join-Path $LogDir "hookdeck_$Time.log"
$HookdeckErrLog = Join-Path $LogDir "hookdeck_$Time.err.log"

Write-Output "[$Time] Starting Omega Stack..."
Write-Output "[$Time] Logs will be written to: $LogDir"

# --- 2. SECRET INJECTION (ZERO-TRUST) ---
# Attempt to load .env file manually to avoid external dependencies
$EnvPath = Join-Path $ProjectRoot $EnvFile
if (Test-Path $EnvPath) {
    Write-Output "[$Time] Loading environment variables from $EnvFile..."
    Get-Content $EnvPath | Where-Object { $_ -match '=' -and $_ -notmatch '^#' } | ForEach-Object {
        $key, $value = $_ -split '=', 2
        [Environment]::SetEnvironmentVariable($key.Trim(), $value.Trim(), "Process")
    }
} else {
    Write-Warning "[$Time] .env file not found at $EnvPath. Relying on system environment variables."
}

# CRITICAL FIX: Verify Hookdeck Key exists to prevent Interactive Browser Hang
if (-not $env:HOOKDECK_API_KEY) {
    Write-Error "FATAL: HOOKDECK_API_KEY is missing. CLI will hang in Session 0. Aborting."
    exit 1
}

# --- 3. START CAPTURE SERVER (UVICORN) ---
Write-Output "[$Time] Launching Capture Server (Port 8765)..."
$PoetryPath = "C:\Users\steyn\AppData\Roaming\Python\Python312\Scripts\poetry.exe"
$PoetryRunArgs = "run python -m omega_kg.capture_server"
try {
    # Use Start-Process with explicit path, capturing output to separate files
    Start-Process -FilePath $PoetryPath -ArgumentList $PoetryRunArgs -RedirectStandardOutput $CaptureLog -RedirectStandardError $CaptureErrLog -WindowStyle Hidden -PassThru
    Write-Output "   [+] Capture Server started."
} catch {
    Write-Error "   [-] Failed to start Capture Server. Error: $($_.Exception.Message)"
}

# --- 4. START HOOKDECK GATEWAY ---
Write-Output "[$Time] Launching Hookdeck (Port 8765 -> Internet)..."
# Note: We pass the API key via the environment variable set above, so no --api-key arg is needed here.
$HookdeckPath = "C:\Users\steyn\AppData\Roaming\npm\hookdeck"
$HookdeckArgs = "listen 8765"

try {
    # Use Start-Process with explicit path to Node.js script
    Start-Process -FilePath "node" -ArgumentList $HookdeckPath, $HookdeckArgs -RedirectStandardOutput $HookdeckLog -RedirectStandardError $HookdeckErrLog -WindowStyle Hidden -PassThru
    Write-Output "   [+] Hookdeck started."
} catch {
    Write-Error "   [-] Failed to start Hookdeck. Error: $($_.Exception.Message)"
}

Write-Output "[$Time] Stack launch sequence complete."