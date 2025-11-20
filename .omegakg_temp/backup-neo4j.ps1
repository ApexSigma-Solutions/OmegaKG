# === VALHALLA SHIELD: OMEGA_KG BACKUP SCRIPT (v7.1 - DUMP + ENV LOADER) ===
#
# Runs an *online* DUMP of the neo4j-db-stable container.
# This version uses the Community-safe `neo4j-admin database dump` command
# as the `backup` command is Enterprise-only and was failing.
#
# v7.1: Added .env loader block to make script portable and scheduler-safe.
#
# To be run by Windows Task Scheduler or manually.
# ===================================================

# --- START: .env LOADER ---
# Get the directory where the script itself is located
$ScriptDir = $PSScriptRoot 

# Assume the project root is one level up from the 'scripts' directory
# If your script is in the root, change this to: $ProjectRoot = $PSScriptRoot
$ProjectRoot = (Get-Item $ScriptDir).Parent.FullName
$EnvFile = Join-Path $ProjectRoot ".env"

if (Test-Path $EnvFile) {
    Write-Host "Found .env file at '$EnvFile'. Loading environment variables..."
    Get-Content $EnvFile | ForEach-Object {
        $line = $_.Trim()
        # Skip empty lines and comments
        if ($line -and $line -notmatch '^\s*#') {
            $parts = $line.Split('=', 2)
            if ($parts.Length -eq 2) {
                $key = $parts[0].Trim()
                $value = $parts[1].Trim()
                
                # Remove surrounding quotes (single or double) from the value
                $value = $value -replace '^"|"$' -replace "^'|'$"
                
                # Set the environment variable for this script's session
                Set-Item -Path "env:$key" -Value $value
            }
        }
    }
} else {
    Write-Warning "!!! .env file not found at '$EnvFile'. Script will use defaults. !!!"
}
# --- END: .env LOADER ---


# --- 1. CONFIGURATION ---
# Allow overriding important paths via environment variables (or .env loaded into the shell).
# If an env var is not present, fall back to a sensible default.

# Container and database names
$ContainerName = $env:NEO4J_CONTAINER_NAME
if (-not $ContainerName) { $ContainerName = "neo4j-db-stable" }
$DatabaseName = $env:NEO4J_DATABASE_NAME
if (-not $DatabaseName) { $DatabaseName = "neo4j" }

# Timestamped dump directory name
$DumpTimestamp = (Get-Date).ToString('yyyyMMdd-HHmmss')
$DumpDir_Name = "$DatabaseName-$DumpTimestamp.backup"

# Paths inside the container (must match docker-compose mounts)
$BackupDir_Container = "/backups"
$DumpDir_Container  = "$BackupDir_Container/$DumpDir_Name"

# Host-side paths (can be provided via env). If not provided, infer from NEO4J_HOST_DATA_PATH
$DataDir_Local = $env:NEO4J_HOST_DATA_PATH
if (-not $DataDir_Local) { $DataDir_Local = "D:\docker-data\omega_kg_stable\neo4j" }

$BackupDir_Local = $env:NEO4J_BACKUPS_PATH
if (-not $BackupDir_Local) {
    # assume backups live alongside the data dir (parent/backups)
    $BackupDir_Local = Join-Path (Split-Path $DataDir_Local -Parent) 'backups'
}

$DumpDir_Local = Join-Path $BackupDir_Local $DumpDir_Name

# Rclone / logging (also overridable)
$RcloneRemote = $env:RCLONE_REMOTE
if (-not $RcloneRemote) { $RcloneRemote = "neo4j.omega.as.bu:Backups" }
$LogFile = $env:BACKUP_LOG_FILE
if (-not $LogFile) { $LogFile = Join-Path $BackupDir_Local 'backup_log.txt' }

# Ensure host backup directory exists
if (-not (Test-Path -LiteralPath $BackupDir_Local)) {
    New-Item -Path $BackupDir_Local -ItemType Directory -Force | Out-Null
}

# Log chosen configuration
Write-Host "Using configuration: Container='$ContainerName' Database='$DatabaseName' DataDir='$DataDir_Local' Backups='$BackupDir_Local' Rclone='$RcloneRemote'"

# --- Function for logging ---
function Write-Log {
    param (
        [string]$Message,
        [switch]$IsError
    )
    $Timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $LogEntry = "$Timestamp - $Message"
    
    Write-Host $LogEntry # Also write to console
    Add-Content -Path $LogFile -Value $LogEntry
    
    if ($IsError) {
        Write-Error $Message
    }
}

# --- 2. START BACKUP ---
Write-Log -Message "===== Valhalla Shield Backup Started (v7.1 - DUMP Command) ====="

try {
    # --- 3. PREPARE REMOTE DIR INSIDE CONTAINER ---
    # Ensure the target directory exists and is owned by the neo4j user so dump can write into it.
    Write-Log -Message "Preparing dump directory inside container: $DumpDir_Container"
    docker exec $ContainerName sh -c "mkdir -p '$DumpDir_Container' && chown -R neo4j:neo4j '$DumpDir_Container'"
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create or chown container dump directory '$DumpDir_Container'."
    }

    # --- 4. CONSTRUCT & RUN DUMP COMMAND ---
    # We use `neo4j-admin database dump` which works on Community Edition and dumps into a directory.
    $Neo4jBinary = "neo4j-admin"
    $Neo4jArg1   = "database"
    $Neo4jArg2   = "dump"
    $Neo4jArg3   = "--to-path=$DumpDir_Container"
    $Neo4jArg4   = $DatabaseName

    Write-Log -Message "Executing command in container '$ContainerName':"
    Write-Log -Message "$Neo4jBinary $Neo4jArg1 $Neo4jArg2 $Neo4jArg3 $Neo4jArg4"

    # Run the dump inside a shell as the neo4j user to avoid ownership problems
    docker exec --user neo4j $ContainerName sh -c "$Neo4jBinary $Neo4jArg1 $Neo4jArg2 $Neo4jArg3 $Neo4jArg4"
    $DumpExit = $LASTEXITCODE
    if ($DumpExit -ne 0) {
        Write-Log -Message "Neo4j dump command failed with exit code $DumpExit. Will attempt cold-snapshot fallback."

        # --- Cold snapshot fallback ---
        Write-Log -Message "Stopping container '$ContainerName' to take a cold snapshot..."
        docker stop $ContainerName
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to stop container '$ContainerName' for cold snapshot. Aborting."
        }

        # Copy host data dir to a temporary partial folder, then rename to final folder
        $TempDir_Local = "$DumpDir_Local.partial"
        if (Test-Path $TempDir_Local) { Remove-Item -LiteralPath $TempDir_Local -Recurse -Force }
        Write-Log -Message "Starting robocopy from '$DataDir_Local' to '$TempDir_Local'..."
        robocopy $DataDir_Local $TempDir_Local /MIR /COPY:DAT /R:2 /W:5 /V /NP
        $RoboExit = $LASTEXITCODE
        if ($RoboExit -gt 3) {
            # robocopy exit codes: 0-3 are generally successful, >=8 indicates failure
            Write-Log -Message "Robocopy reported exit code $RoboExit. Attempting to restart container and abort." -IsError
            docker start $ContainerName | Out-Null
            throw "Robocopy failed with exit code $RoboExit. Cold snapshot aborted."
        }

        # Move partial to final
        Move-Item -LiteralPath $TempDir_Local -Destination $DumpDir_Local
        Write-Log -Message "Cold snapshot completed to '$DumpDir_Local'. Starting container '$ContainerName'..."
        docker start $ContainerName
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to start container '$ContainerName' after cold snapshot."
        }

        Write-Log -Message "Service restarted. Proceeding to upload the cold snapshot directory."
    }

    Write-Log -Message "Neo4j dump command completed successfully."

    # --- 5. VERIFY LATEST DUMP (ON HOST) ---
    Write-Log -Message "Verifying new backup directory on host: $DumpDir_Local"
    if (-not (Test-Path -LiteralPath $DumpDir_Local)) {
        throw "Could not find the new dump directory at '$DumpDir_Local'. Upload failed."
    }

    $LatestBackup = Get-Item -LiteralPath $DumpDir_Local
    Write-Log -Message "Found backup directory: $($LatestBackup.Name). Uploading to rclone remote '$RcloneRemote'..."

    # --- 6. UPLOAD VIA RCLONE ---
    # Upload the entire dump directory. Use `copy` so each run uploads the directory contents.
    rclone copy "$($LatestBackup.FullName)" "$RcloneRemote/$($LatestBackup.Name)" -P

    if ($LASTEXITCODE -ne 0) {
        throw "Rclone upload FAILED with exit code $LASTEXITCODE."
    }

    Write-Log -Message "Rclone upload complete."

    # --- 7. CLEAN UP LOCAL BACKUP ---
    # We keep the local backup directory as a last-known-good copy. If you'd like to remove
    # old backups automatically, we can add retention logic here.
    Write-Log -Message "Local backup directory '$($LatestBackup.Name)' retained as last-known-good."
    Write-Log -Message "===== Valhalla Shield Backup SUCCESSFUL ====="

} catch {
    Write-Log -Message "===== !!! VALHALLA SHIELD BACKUP FAILED !!! =====" -IsError
    Write-Log -Message "ERROR: $_" -IsError
    exit 1
}

exit 0