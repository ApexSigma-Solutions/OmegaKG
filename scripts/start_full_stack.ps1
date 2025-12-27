# Omega Full Stack Launcher (v2.5 Hookdeck-Fixed)
# -------------------------
# Purpose: Orchestrates Capture Server (Uvicorn), Hookdeck Gateway, and GitHub Listener.
# Usage:
#   ./start_full_stack.ps1                      -> Production (Hidden Windows, Log to Files, Manual Hookdeck)
#   ./start_full_stack.ps1 -ShowConsole        -> Debugging (Visible Windows, Auto-starts Hookdeck in separate windows)
#   ./start_full_stack.ps1 -SkipCleanup        -> Skip cleanup (useful if cleanup was already run)
#   ./start_full_stack.ps1 -SkipCleanup -Persistent -> Skip cleanup and keep processes alive with watchdog
#
# With -ShowConsole: Hookdeck listeners automatically start in separate console windows for monitoring
# Without -ShowConsole: Hookdeck listeners must be started manually (production mode)
#
# v2.5 Changes:
# - Fixed to use hookdeck.exe directly (Windows binary) instead of shell wrapper
# - Fixed command syntax to use "listen <port> <source>" format
# - Both Linear and GitHub listeners use port 8765 (Hookdeck limitation)
#

param (
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$EnvFile = ".env",
    [switch]$ShowConsole,
    [switch]$Persistent,
    [switch]$SkipCleanup
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
        RedirectStandardError = $CaptureErrLog
    }
    # For Hookdeck, always use Normal window style to allow manual interaction
    $LogArgs_Hookdeck = @{}
}

# --- 2. SECRET INJECTION & CLEANUP ---
if (-not $SkipCleanup) {
    Write-Output "[$Time] Cleaning up existing processes..."
    & (Join-Path $PSScriptRoot "cleanup_before_start.ps1")
} else {
    Write-Output "[$Time] Skipping cleanup (SkipCleanup flag set)."
}

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
$env:HOST = "0.0.0.0"
$env:PORT = "8765"

Write-Output "[$Time] Checking Capture Server status..."
Write-Output "[$Time] Capture Server will bind to: $env:HOST`:$env:PORT"
$PoetryPath = (Get-Command poetry -ErrorAction SilentlyContinue).Source
if (-not $PoetryPath) { $PoetryPath = "poetry" }

$PoetryRunArgs = "run python -m omega_kg.capture_server --host $env:HOST"

# Check if Poetry process with capture_server is already running
$ExistingPoetry = Get-Process -Name "poetry" -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*capture_server*"
}

$CaptureProc = $null
if ($ExistingPoetry) {
    Write-Output "   [i] Capture Server already running (PID: $($ExistingPoetry.Id)). Skipping start."
    $CaptureProc = $ExistingPoetry
} else {
    Write-Output "[$Time] Launching Capture Server..."
    try {
        $CaptureProc = Start-Process -FilePath $PoetryPath -ArgumentList $PoetryRunArgs -WindowStyle $WindowStyle -PassThru @LogArgs_Capture
        Write-Output "   [+] Capture Server started (PID: $($CaptureProc.Id))."
        Write-Output "[$Time] Waiting 5 seconds for Capture Server to initialize..."
        Start-Sleep -Seconds 5
        
        # Verify process is still running
        if (-not (Get-Process -Id $CaptureProc.Id -ErrorAction SilentlyContinue)) {
            Write-Error "   [-] Capture Server process exited unexpectedly after 5 seconds!"
            $CaptureProc = $null
        } else {
            Write-Output "[$Time] Capture Server is running and ready."
        }
    } catch {
        Write-Error "   [-] Failed to start Capture Server: $($_.Exception.Message)"
    }
}

# --- 4. START HOOKDECK GATEWAY ---
Write-Output "[$Time] Checking Hookdeck status..."
# Use Windows .exe directly to avoid shell wrapper issues
$HookdeckPath = "C:\Users\steyn\AppData\Roaming\npm\node_modules\hookdeck-cli\bin\hookdeck.exe"
if (-not (Test-Path $HookdeckPath)) {
    # Fallback to hookdeck command if .exe not found
    $HookdeckCmd = (Get-Command hookdeck -ErrorAction SilentlyContinue)
    if ($HookdeckCmd) {
        $HookdeckPath = $HookdeckCmd.Source
    } else {
        Write-Warning "   [!] Hookdeck not found. Please install with: npm install -g @hookdeck/cli"
        $HookdeckPath = $null
    }
}
# Correct Hookdeck syntax: listen <port> <source>
$HookdeckArgs = "listen 8765 linear"

Write-Output "[$Time] Hookdeck will listen on port 8765 and forward to: http://${env:HOST}:8765/webhook/linear"

# Check if Hookdeck process is already running (check for hookdeck.exe or hookdeck)
$ExistingHookdeck = Get-Process -Name "hookdeck" -ErrorAction SilentlyContinue | Where-Object {
    $_.ProcessName -eq "hookdeck"
}
if (-not $ExistingHookdeck) {
    # Also check for hookdeck.exe explicitly
    $ExistingHookdeck = Get-Process -Name "hookdeck" -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -like "*hookdeck.exe*"
    }
}

$HookdeckProc = $null
if ($ExistingHookdeck) {
    Write-Output "   [i] Hookdeck already running (PID: $($ExistingHookdeck.Id)). Skipping start."
    $HookdeckProc = $ExistingHookdeck
} elseif ($ShowConsole -and $HookdeckPath) {
    # Start Hookdeck in a separate console window when ShowConsole is enabled
    Write-Output "   [+] Starting Hookdeck Linear listener in separate window..."
    try {
        $HookdeckProc = Start-Process -FilePath $HookdeckPath -ArgumentList $HookdeckArgs -WindowStyle "Normal" -PassThru
        Write-Output "   [+] Hookdeck Linear listener started (PID: $($HookdeckProc.Id))"
        Write-Output "       Window title: Hookdeck - Linear Listener"
    } catch {
        Write-Error "   [-] Failed to start Hookdeck Linear listener: $($_.Exception.Message)"
        Write-Output "   [!] You can start it manually: $HookdeckPath $HookdeckArgs"
    }
} elseif ($HookdeckPath) {
    # Show instructions for production mode
    Write-Output ""
    Write-Output "=========================================="
    Write-Output "HOOKDECK SETUP INSTRUCTIONS:"
    Write-Output "=========================================="
    Write-Output ""
    Write-Output "Hookdeck CLI requires an interactive terminal and cannot be started via PowerShell script."
    Write-Output "Please run the following command in a NEW terminal window:"
    Write-Output ""
    Write-Output "  $HookdeckPath $HookdeckArgs"
    Write-Output ""
    Write-Output "This will start the Linear webhook listener on port 8765."
    Write-Output "=========================================="
    Write-Output ""
}

# --- 5. START GITHUB WEBHOOK LISTENER ---
Write-Output "[$Time] Checking GitHub Webhook status..."
# Note: Hookdeck can only listen on one port at a time
# For now, we'll use the same port 8765 for GitHub as well
# In production, you would run separate Hookdeck commands for each service
$GitHubArgs = "listen 8765 github"

Write-Output "[$Time] GitHub listener will listen on port 8765 and forward to: http://${env:HOST}:8765/webhooks/github"
Write-Output "   [!] Note: Only one Hookdeck listener can run at a time on the same port"

# Check if GitHub listener process is already running (check for hookdeck.exe)
$ExistingGitHub = Get-Process -Name "hookdeck" -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*github*"
}

$GitHubProc = $null
if ($ExistingGitHub) {
    Write-Output "   [i] GitHub listener already running (PID: $($ExistingGitHub.Id)). Skipping start."
    $GitHubProc = $ExistingGitHub
} elseif ($ShowConsole -and $HookdeckPath) {
    # Start GitHub listener in a separate console window when ShowConsole is enabled
    Write-Output "   [+] Starting Hookdeck GitHub listener in separate window..."
    try {
        $GitHubProc = Start-Process -FilePath $HookdeckPath -ArgumentList $GitHubArgs -WindowStyle "Normal" -PassThru
        Write-Output "   [+] Hookdeck GitHub listener started (PID: $($GitHubProc.Id))"
        Write-Output "       Window title: Hookdeck - GitHub Listener"
    } catch {
        Write-Error "   [-] Failed to start Hookdeck GitHub listener: $($_.Exception.Message)"
        Write-Output "   [!] You can start it manually: $HookdeckPath $GitHubArgs"
    }
} elseif ($HookdeckPath) {
    # Show instructions for production mode
    Write-Output ""
    Write-Output "=========================================="
    Write-Output "GITHUB LISTENER SETUP INSTRUCTIONS:"
    Write-Output "=========================================="
    Write-Output ""
    Write-Output "Hookdeck CLI requires an interactive terminal and cannot be started via PowerShell script."
    Write-Output "Please run the following command in a NEW terminal window:"
    Write-Output ""
    Write-Output "  $HookdeckPath $GitHubArgs"
    Write-Output ""
    Write-Output "This will start the GitHub webhook listener on port 8765."
    Write-Output "=========================================="
    Write-Output ""
}

# --- 6. PERSISTENCE LOOP (WATCHDOG) ---
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
        
        # Check GitHub Listener
        if ($null -eq $GitHubProc -or $GitHubProc.HasExited) {
            $RestartTime = Get-Date -Format "HH:mm:ss"
            Write-Warning "[$RestartTime] GitHub listener is down. Restarting..."
            try {
                $GitHubProc = Start-Process -FilePath $HookdeckPath -ArgumentList $GitHubArgs -WindowStyle $WindowStyle -PassThru @LogArgs_Hookdeck
                Write-Output "   [+] GitHub listener restarted (PID: $($GitHubProc.Id))."
            } catch {
                Write-Error "   [-] Failed to restart GitHub listener: $($_.Exception.Message)"
            }
        }
    }
} else {
    Write-Output "[$Time] Sequence complete. Processes are running in background."
}
