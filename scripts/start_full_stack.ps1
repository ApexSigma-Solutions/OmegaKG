# Omega Full Stack Launcher (v2.1 Configurable)
# -------------------------
# Purpose: Orchestrates the Capture Server (Uvicorn) and Webhook Gateway (Hookdeck).
# Usage: 
#   ./start_full_stack.ps1                -> Production (Hidden Windows, Log to Files)
#   ./start_full_stack.ps1 -ShowConsole   -> Debugging (Visible Windows, Log to Screen)

param (
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$EnvFile = ".env",
    [switch]$ShowConsole,
    [switch]$Persistent
)

$ErrorActionPreference = "Stop"

# --- 1. SETUP LOGGING & WINDOW MODES ---
$LogDir = Join-Path $ProjectRoot "logs"
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }

$Time = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$CaptureLog = Join-Path $LogDir "capture_server_$Time.log"
$CaptureErrLog = Join-Path $LogDir "capture_server_$Time.err.log"
$HookdeckLog = Join-Path $LogDir "hookdeck_$Time.log"
$HookdeckErrLog = Join-Path $LogDir "hookdeck_$Time.err.log"

if ($ShowConsole) {
    Write-Warning "[$Time] DEBUG MODE: Windows will be visible. Logs streaming to screen (NOT files)."
    $WindowStyle = "Normal"
    $LogArgs_Capture = @{}
    $LogArgs_Hookdeck = @{}
} else {
    Write-Output "[$Time] PRODUCTION MODE: Windows hidden. Logs written to $LogDir"
    $WindowStyle = "Hidden"
    $LogArgs_Capture = @{
        RedirectStandardOutput = $CaptureLog
        RedirectStandardError  = $CaptureErrLog
    }
    $LogArgs_Hookdeck = @{
        RedirectStandardOutput = $HookdeckLog
        RedirectStandardError  = $HookdeckErrLog
    }
}

# --- 2. SECRET INJECTION & CLEANUP ---
Write-Output "[$Time] Cleaning up existing processes..."
& (Join-Path $PSScriptRoot "cleanup_before_start.ps1")

Write-Output "[$Time] Ensuring databases are running..."
& (Join-Path $PSScriptRoot "start-database.ps1")

$EnvPath = Join-Path $ProjectRoot $EnvFile
if (Test-Path $EnvPath) {
    Write-Output "[$Time] Loading .env..."
    Get-Content $EnvPath | Where-Object { $_ -match '=' -and $_ -notmatch '^#' } | ForEach-Object {
        $key, $value = $_ -split '=', 2
        [Environment]::SetEnvironmentVariable($key.Trim(), $value.Trim(), "Process")
    }
}

if (-not $env:HOOKDECK_API_KEY) {
    Write-Error "FATAL: HOOKDECK_API_KEY is missing. Aborting."
    exit 1
}

# --- 3. START CAPTURE SERVER (UVICORN) ---
$env:HOST = "127.0.0.1" 
$env:PORT = "8765"

Write-Output "[$Time] Launching Capture Server..."
$PoetryPath = (Get-Command poetry -ErrorAction SilentlyContinue).Source
if (-not $PoetryPath) { $PoetryPath = "poetry" }
$PoetryRunArgs = "run python -m omega_kg.capture_server --host 127.0.0.1"

$CaptureProc = $null
try {
    $CaptureProc = Start-Process -FilePath $PoetryPath -ArgumentList $PoetryRunArgs -WindowStyle $WindowStyle -PassThru @LogArgs_Capture
    Write-Output "   [+] Capture Server started (PID: $($CaptureProc.Id))."
} catch {
    Write-Error "   [-] Failed to start Capture Server: $($_.Exception.Message)"
}

# --- 4. START HOOKDECK GATEWAY ---
Write-Output "[$Time] Launching Hookdeck..."
$HookdeckCmd = (Get-Command hookdeck -ErrorAction SilentlyContinue)
$HookdeckPath = $HookdeckCmd.Source
if (-not $HookdeckPath) { 
    $HookdeckPath = "hookdeck" 
} elseif ($HookdeckPath -like "*.ps1") {
    # If it's a ps1, try to find the .cmd in the same directory
    $CmdPath = $HookdeckPath -replace "\.ps1$", ".cmd"
    if (Test-Path $CmdPath) { $HookdeckPath = $CmdPath }
}
$HookdeckArgs = "listen 8765"

$HookdeckProc = $null
try {
    $HookdeckProc = Start-Process -FilePath $HookdeckPath -ArgumentList $HookdeckArgs -WindowStyle $WindowStyle -PassThru @LogArgs_Hookdeck
    Write-Output "   [+] Hookdeck started (PID: $($HookdeckProc.Id))."
} catch {
    Write-Error "   [-] Failed to start Hookdeck. Ensure 'npm install -g hookdeck-cli' was run."
}

# --- 5. PERSISTENCE LOOP (WATCHDOG) ---
if ($Persistent) {
    Write-Output "[$Time] WATCHDOG ACTIVE: Monitoring processes every 10s. Press Ctrl+C to stop."
    while ($true) {
        Start-Sleep -Seconds 10
        
        # Check Capture Server
        if ($null -eq $CaptureProc -or $CaptureProc.HasExited) {
            $RestartTime = Get-Date -Format "HH:mm:ss"
            Write-Warning "[$RestartTime] Capture Server is down. Restarting..."
            try {
                $CaptureProc = Start-Process -FilePath $PoetryPath -ArgumentList $PoetryRunArgs -WindowStyle $WindowStyle -PassThru @LogArgs_Capture
                Write-Output "   [+] Capture Server restarted (PID: $($CaptureProc.Id))."
            } catch {
                Write-Error "   [-] Failed to restart Capture Server: $($_.Exception.Message)"
            }
        }

        # Check Hookdeck
        if ($null -eq $HookdeckProc -or $HookdeckProc.HasExited) {
            $RestartTime = Get-Date -Format "HH:mm:ss"
            Write-Warning "[$RestartTime] Hookdeck is down. Restarting..."
            try {
                $HookdeckProc = Start-Process -FilePath $HookdeckPath -ArgumentList $HookdeckArgs -WindowStyle $WindowStyle -PassThru @LogArgs_Hookdeck
                Write-Output "   [+] Hookdeck restarted (PID: $($HookdeckProc.Id))."
            } catch {
                Write-Error "   [-] Failed to restart Hookdeck: $($_.Exception.Message)"
            }
        }
    }
} else {
    Write-Output "[$Time] Sequence complete. Processes are running in background."
}
