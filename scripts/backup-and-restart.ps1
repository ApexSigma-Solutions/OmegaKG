<#
.SYNOPSIS
    Backup Neo4j Docker named volume and restart docker-compose stack safely.

.DESCRIPTION
    Creates a timestamped tar.gz of the named Docker volume `apexsigma.neo4j.data`
    into a `docker_backups` directory in the project. Then brings the compose
    stack down and back up. Includes checks for Docker and Poetry availability.

.PARAMETER DryRun
    When supplied, the script will NOT perform docker stop/start or volume
    backup operations. It will still perform Poetry checks so you can verify
    dependency state without impacting running services.

.EXAMPLE
    .\backup-and-restart.ps1

.EXAMPLE
    .\backup-and-restart.ps1 -DryRun
#>

param(
    [switch]$DryRun
)

Set-StrictMode -Version Latest

function Write-Info { param($m) Write-Host "[INFO] $m" -ForegroundColor Cyan }
function Write-Warn { param($m) Write-Host "[WARN] $m" -ForegroundColor Yellow }
function Write-Err  { param($m) Write-Host "[ERROR] $m" -ForegroundColor Red }

$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Definition)
$backupDir = Join-Path $projectRoot 'docker_backups'

Write-Info "Project root: $projectRoot"
Write-Info "Backup directory: $backupDir"

if (-not (Test-Path $backupDir)) {
    if ($DryRun) { Write-Info "(DryRun) Would create backup dir: $backupDir" } else { New-Item -ItemType Directory -Path $backupDir -Force | Out-Null }
}

# Check Docker
$dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
if (-not $dockerCmd) {
    Write-Err "Docker CLI not found in PATH. Please install Docker Desktop or add docker to PATH."; exit 2
}

# Check Poetry availability (we'll still run checks in DryRun)
$poetryCmd = Get-Command poetry -ErrorAction SilentlyContinue
if (-not $poetryCmd) {
    Write-Warn "Poetry not found in PATH. Poetry checks will be skipped. Install from https://python-poetry.org/docs/"
} else {
    try {
        $poetryVersion = (& poetry --version) -join " `n"
        Write-Info "Poetry version: $poetryVersion"
    } catch {
        Write-Warn "Failed to run 'poetry --version' but Poetry command exists. Continuing. Error: $_"
    }
}

# Function: create backup of named volume
function Backup-Neo4jVolume {
    param(
        [string]$NamedVolume = 'apexsigma.neo4j.data'
    )

    $timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $archiveName = "neo4j_backup_${timestamp}.tar.gz"
    $archivePathHost = Join-Path $backupDir $archiveName

    Write-Info "Backing up named volume '$NamedVolume' to '$archivePathHost'"

    $tarCmd = "tar czf /backup/$archiveName ."

    if ($DryRun) {
        # Use ${} to safely expand variables that are followed by punctuation (colon)
        Write-Info "(DryRun) Would run: docker run --rm -v ${NamedVolume}:/data -v \"${backupDir}:/backup\" alpine sh -c '$tarCmd'"
        return $archivePathHost
    }

    # Run ephemeral container to create the archive
    # Delimit variables with ${} when followed by punctuation
    & docker run --rm -v "${NamedVolume}:/data" -v "${backupDir}:/backup" alpine sh -c $tarCmd
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Backup command failed with exit code $LASTEXITCODE"; exit 3
    }

    if (-not (Test-Path $archivePathHost)) {
        Write-Err "Expected archive was not created: $archivePathHost"; exit 4
    }

    $size = (Get-Item $archivePathHost).Length
    if ($size -lt 1024) {
        Write-Warn "Archive exists but is very small ($size bytes). Verify contents before proceeding."
    } else {
        Write-Info "Backup created: $archivePathHost ($size bytes)"
    }

    return $archivePathHost
}

# Function: restart compose stack
function Restart-ComposeStack {
    Write-Info "Bringing docker-compose stack down (remove orphans)"
    if ($DryRun) { Write-Info "(DryRun) Would run: docker-compose down --remove-orphans" } else { docker-compose down --remove-orphans }

    Write-Info "Bringing docker compose stack up (detached, rebuild)"
    if ($DryRun) { Write-Info "(DryRun) Would run: docker compose up -d --build --remove-orphans" } else { docker compose up -d --build --remove-orphans }

    Write-Info "Showing 'docker compose ps'"
    if ($DryRun) { Write-Info "(DryRun) Would run: docker compose ps" } else { docker compose ps }
}

# Perform actions
try {
    if (-not $DryRun) {
        $null = Backup-Neo4jVolume
    } else {
        Write-Info "DryRun: skipping actual volume backup, but running poetry checks."
    }

    Restart-ComposeStack

    Write-Info "Collecting some logs for verification (last 80 lines)"
    if (-not $DryRun) {
        docker compose logs --tail 80 neo4j-db | Out-Host
        docker compose logs --tail 80 omega-kg | Out-Host
    } else {
        Write-Info "(DryRun) Skipping container logs collection"
    }

    # Poetry dependency checks
    if ($poetryCmd) {
        Write-Info "Running 'poetry install' to ensure dependencies are available (may modify virtualenv)"
        try {
            # Run poetry install in project root
            Push-Location $projectRoot
            if ($DryRun) {
                Write-Info "(DryRun) Would run: poetry install"
            } else {
                poetry install
            }

            Write-Info "Checking for outdated packages (poetry show --outdated)"
            if ($DryRun) {
                Write-Info "(DryRun) Would run: poetry show --outdated"
            } else {
                $outdated = poetry show --outdated
                if ([string]::IsNullOrWhiteSpace($outdated)) { Write-Info "All packages up-to-date according to Poetry." } else { Write-Info "Outdated packages:\n$outdated" }
            }
        } finally { Pop-Location }
    } else {
        Write-Warn "Poetry not available; skipping dependency installation/outdated check."
    }

    Write-Info "Operation completed."; exit 0

} catch {
    Write-Err "Unhandled exception: $_"; exit 10
}
