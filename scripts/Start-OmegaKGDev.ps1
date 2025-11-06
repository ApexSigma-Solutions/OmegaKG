# -----------------------------------------------------------------------------
# Omega_KG Development Environment Pre-Flight Check
#
# This script verifies that all dependencies (Docker, Neo4j, Poetry, Tools)
# are correctly configured and running *before* starting the server.
#
# It is designed to be called by the $PROFILE hook.
# -----------------------------------------------------------------------------

# --- UTILITY FUNCTIONS ---
function Write-Check {
    param([string]$Message)
    Write-Host "Checking: $Message" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "  [✓] SUCCESS: $Message" -ForegroundColor Green
}

function Write-Failure {
    param([string]$Message)
    Write-Host "  [X] FAILURE: $Message" -ForegroundColor Red
    # --- FIX ---
    # Set the global flag to prevent server start
    $global:allChecksPassed = $false
}

function Write-Warning {
    param([string]$Message)
    Write-Host "  [!] WARNING: $Message" -ForegroundColor Yellow
}

function Write-Info {
    param([string]$Message)
    Write-Host "  [i] INFO: $Message" -ForegroundColor Gray
}

# --- SCRIPT START ---
Write-Host "--- OMEGA_KG PRE-FLIGHT CHECKS ---" -ForegroundColor Yellow

# --- FIX ---
# Initialize the global failure flag
$global:allChecksPassed = $true

# ---------------------------------
# 1. NEO4J DOCKER CHECKS
# ---------------------------------
Write-Check "Neo4j Docker container (apexsigma.neo4j.db)..."
$containerName = "apexsigma.neo4j.db"
$neo4jNetwork = "apexsigma.net"
$neo4jBoltPort = 7687

# Check 1: Is container running?
$containerID = docker ps -q -f "name=$containerName" -f "status=running"
if (-not $containerID) {
    Write-Failure "Container '$containerName' is not running. (Try: docker start $containerName)"
} else {
    Write-Success "Container '$containerName' is running (ID: $($containerID.Substring(0,12)))."

    # Check 2: Is it on the correct network?
    $networkCheck = docker inspect $containerID -f '{{.NetworkSettings.Networks}}'
    if ($networkCheck -notlike "*$neo4jNetwork*") {
        Write-Failure "Container is not attached to the '$neo4jNetwork' network."
    } else {
        Write-Success "Container is on the '$neo4jNetwork' network."
    }

    # Check 3: Is Bolt port mapped?
    $portMapping = docker port $containerID "$neo4jBoltPort/tcp"
    if (-not $portMapping) {
        Write-Failure "Neo4j Bolt port ($neo4jBoltPort) is not mapped. (Check 'docker ps' port bindings)"
    } else {
        if ($portMapping -notmatch "127\.0\.0\.1|\[::1\]|0\.0\.0\.0|\[::\]") {
            Write-Warning "Neo4j Bolt port ($neo4jBoltPort) is not mapped to localhost. Remote access may be required."
        }
        Write-Success "Neo4j container is networked and Bolt port is mapped (interface: $portMapping)."
    }

    # Check 4: Health check
    $health = docker inspect $containerID -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}not-configured{{end}}'
    switch ($health) {
        "healthy" { Write-Success "Neo4j container is healthy." }
        "unhealthy" { Write-Failure "Neo4j container is running but 'unhealthy'." }
        "starting" { Write-Warning "Neo4j container is still 'starting'." }
        "not-configured" {
            Write-Warning "Container does not have a health check configured. To add one, update your Docker Compose or Docker run config with: 
            healthcheck:
              test: ['CMD', 'cypher-shell', '-u', 'neo4j', '-p', '<password>', 'RETURN 1']
              interval: 30s
              timeout: 10s
              retries: 5
            (Replace <password> with your Neo4j password.)"
        }
    }
}

# ---------------------------------
# 2. POETRY ENVIRONMENT CHECKS
# ---------------------------------
Write-Check "Poetry virtual environment..."
if (-not $env:VIRTUAL_ENV) {
    Write-Failure "'.venv' is not active. This script should be run *after* sourcing 'activate-omega'.`n(Tip: Run '. scripts\activate-omega.ps1' from the repo root. If missing, see CONTRIBUTING.md.)"
} else {
    Write-Success "'.venv' is active: $env:VIRTUAL_ENV"
}

Write-Check "Poetry dependencies..."
$syncOutput = ""
$syncError = ""
$syncProcess = Start-Process poetry -ArgumentList "install", "--dry-run", "--no-root" -NoNewWindow -RedirectStandardOutput "sync_stdout.txt" -RedirectStandardError "sync_stderr.txt" -Wait -PassThru
$syncOutput = Get-Content "sync_stdout.txt" -Raw
$syncError = Get-Content "sync_stderr.txt" -Raw
Remove-Item "sync_stdout.txt","sync_stderr.txt" -ErrorAction SilentlyContinue

if ($syncProcess.ExitCode -ne 0) {
    if ($syncOutput -like "*Dependencies are locked*") {
        Write-Warning "Dependencies are out of sync. Running 'poetry install'..."
        poetry install --no-root | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Dependencies synced."
        } else {
            Write-Failure "Failed to sync dependencies. Run 'poetry install' manually."
        }
    } else {
        Write-Failure "'poetry install --dry-run' failed. Error output:`n$syncError"
    }
} else {
    Write-Success "Dependencies are in sync."
}

# ---------------------------------
# 3. SHELL INTEGRATION CHECK
# ---------------------------------
Write-Check "Shell integration..."
if (-not (Get-Command activate-omega -ErrorAction SilentlyContinue)) {
    Write-Warning "The 'activate-omega' function itself was not found. Shell integration may be broken."
} else {
    Write-Success "'activate-omega' function is loaded."
}

@(
    "pytest",
    "pytest-cov",
    "pydantic",
    "pre-commit"
) | ForEach-Object {
    poetry show $_ --no-interaction > $null 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Failure "$_ is not installed in the venv. (Run: poetry add --group dev $_)"
    }
}
Write-Success "Core Python tooling (pytest, pytest-cov, pydantic, pre-commit) is installed."

# Check for Trunk.io CLI
$trunkCheck = Get-Command trunk -ErrorAction SilentlyContinue
if (-not $trunkCheck) {
    Write-Failure "Trunk.io binary is not available in your PATH. (See: https://trunk.io/)"
} else {
    Write-Success "Trunk.io binary is available."
}


# ---------------------------------
# --- FIX ---
# FINAL DECISION BLOCK
# Only proceed if all checks passed
# ---------------------------------
if ($global:allChecksPassed) {
    Write-Host ""
    Write-Host "--- ALL PRE-FLIGHT CHECKS PASSED ---" -ForegroundColor Green
    Write-Host ""

    # ---------------------------------
    # 5. SERVER START-UP
    # ---------------------------------
    $title = "Omega_KG Server"
    $message = "All checks passed. Start the FastAPI server?"
    $newWindow = [System.Management.Automation.Host.ChoiceDescription]::new("&New Window", "Start uvicorn in a new, separate terminal window.")
    $thisTerminal = [System.Management.Automation.Host.ChoiceDescription]::new("&This Terminal", "Start uvicorn in this terminal (blocks prompt).")
    $no = [System.Management.Automation.Host.ChoiceDescription]::new("&No (Exit)", "Do not start the server.")
    $options = [System.Management.Automation.Host.ChoiceDescription[]]($newWindow, $thisTerminal, $no)
    $default = 0 # Default to New Window

    $result = $host.ui.PromptForChoice($title, $message, $options, $default)

    switch ($result) {
        0 { 
            Write-Info "Starting server in new window..."
            # Manually activate venv in the new shell, as 'activate-omega' is a profile function
            # -NoExit is required to keep the new PowerShell window open after server start, so you can see logs and stop the server with Ctrl+C.
            $command = '.\.venv\Scripts\Activate.ps1; poetry run uvicorn omega_kg.capture_server:app --host 127.0.0.1 --port 8765'
            Start-Process powershell -ArgumentList @("-NoExit", "-Command", $command)
        }
        1 { 
            Write-Info "Starting server in this terminal. (Press Ctrl+C to stop)"
            # We are already activated, just run the command
            poetry run uvicorn omega_kg.capture_server:app --host 127.0.0.1 --port 8765
        }
        2 {
            Write-Info "Server not started."
        }
    }
} else {
    Write-Host ""
    Write-Host "--- PRE-FLIGHT CHECKS FAILED ---" -ForegroundColor Red
    Write-Host "Server start-up aborted. Please fix the errors above." -ForegroundColor Red
    Write-Host "Tip: Run this script with increased verbosity for more details, or consult the TROUBLESHOOTING.md guide in the repository root for further help." -ForegroundColor Yellow
}

