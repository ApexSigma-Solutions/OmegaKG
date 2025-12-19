#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Configure Windows Task Scheduler to start Omega KG server at login
.DESCRIPTION
    Creates a scheduled task that launches the Omega KG capture server
    in a separate window when you log in.
#>

#Requires -RunAsAdministrator

$ErrorActionPreference = "Stop"
$ProjectRoot = "d:\projects\Omega_KG_stable"

Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║     Omega KG - Auto-Start Configuration                     ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Task details
$TaskName = "Omega_KG_CaptureServer"
$TaskDescription = "Starts Omega KG Capture Server at login"

# Check if task already exists
$ExistingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue

if ($ExistingTask) {
    Write-Host "⚠️  Task '$TaskName' already exists" -ForegroundColor Yellow
    $Response = Read-Host "Do you want to replace it? (y/n)"
    if ($Response -ne 'y') {
        Write-Host "Setup cancelled" -ForegroundColor Gray
        exit 0
    }
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "✓ Removed existing task" -ForegroundColor Green
}

# Create startup script wrapper
$StartupScriptPath = Join-Path $ProjectRoot "start-server-window.ps1"
@"
#!/usr/bin/env pwsh
# Auto-generated startup script for Task Scheduler
`$ErrorActionPreference = "Stop"

# Set window title
`$host.UI.RawUI.WindowTitle = "Omega KG Capture Server"

# Change to project directory
Set-Location "$ProjectRoot"

# Clear Python cache
Get-ChildItem -Path omega_kg -Recurse -Filter "__pycache__" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
Get-ChildItem -Path omega_kg -Recurse -Filter "*.pyc" -ErrorAction SilentlyContinue | Remove-Item -Force

Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║         Omega KG Capture Server - Auto-Started              ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Start databases if not running
`$neo4j = docker ps --filter "name=neo4j.stable" --format "{{.Names}}" | Select-String "neo4j"
`$postgres = docker ps --filter "name=postgres.stable" --format "{{.Names}}" | Select-String "postgres"

if (-not `$neo4j -or -not `$postgres) {
    Write-Host "🐳 Starting databases..." -ForegroundColor Yellow
    docker-compose up -d postgres neo4j
    Write-Host "⏳ Waiting for databases to initialize..." -ForegroundColor Gray
    Start-Sleep -Seconds 8
}

Write-Host "🚀 Starting Omega KG Capture Server..." -ForegroundColor Cyan
Write-Host "   Server URL: http://localhost:8765" -ForegroundColor White
Write-Host "   Press Ctrl+C to stop, or close this window to exit" -ForegroundColor Yellow
Write-Host ""

# Start the server
poetry run python omega_kg/capture_server.py

# Keep window open if server crashes
if (`$LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "❌ Server exited with error code `$LASTEXITCODE" -ForegroundColor Red
    Write-Host "Press any key to close..." -ForegroundColor Yellow
    `$null = `$Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}
"@ | Set-Content $StartupScriptPath -Encoding UTF8

Write-Host "✓ Created startup script: $StartupScriptPath" -ForegroundColor Green

# Create the scheduled task action
$Action = New-ScheduledTaskAction `
    -Execute "pwsh.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Normal -File `"$StartupScriptPath`"" `
    -WorkingDirectory $ProjectRoot

# Create the trigger (at logon)
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

# Create task settings
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

# Create the principal (run as current user, highest privileges)
$Principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Highest

# Register the task
Register-ScheduledTask `
    -TaskName $TaskName `
    -Description $TaskDescription `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Force | Out-Null

Write-Host "✓ Task '$TaskName' created successfully" -ForegroundColor Green
Write-Host ""

# Show task details
Write-Host "Task Configuration:" -ForegroundColor Cyan
Write-Host "  Name:        $TaskName"
Write-Host "  Trigger:     At logon (user: $env:USERNAME)"
Write-Host "  Action:      Start Omega KG server in new window"
Write-Host "  Script:      $StartupScriptPath"
Write-Host "  Auto-Retry:  Yes (3 attempts, 1 minute interval)"
Write-Host ""

# Options
Write-Host "What would you like to do?" -ForegroundColor Yellow
Write-Host "  1. Test the task now (start server)"
Write-Host "  2. Disable auto-start (keep task but disable)"
Write-Host "  3. Remove auto-start completely"
Write-Host "  4. Do nothing (task is ready for next login)"
Write-Host ""

$Choice = Read-Host "Enter choice (1-4)"

switch ($Choice) {
    "1" {
        Write-Host ""
        Write-Host "🚀 Starting task now..." -ForegroundColor Cyan
        Start-ScheduledTask -TaskName $TaskName
        Write-Host "✓ Task started! Check the new window." -ForegroundColor Green
        Write-Host "   (The server window should appear in a moment)" -ForegroundColor Gray
    }
    "2" {
        Disable-ScheduledTask -TaskName $TaskName | Out-Null
        Write-Host "✓ Auto-start disabled (task still exists)" -ForegroundColor Yellow
        Write-Host "   To re-enable: Enable-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Gray
    }
    "3" {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Remove-Item $StartupScriptPath -Force -ErrorAction SilentlyContinue
        Write-Host "✓ Auto-start removed completely" -ForegroundColor Green
    }
    default {
        Write-Host "✓ Configuration complete!" -ForegroundColor Green
        Write-Host "   Server will auto-start at next login" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "Management Commands:" -ForegroundColor Cyan
Write-Host "  Start now:     Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "  Stop:          Stop-ScheduledTask -TaskName '$TaskName'"
Write-Host "  Disable:       Disable-ScheduledTask -TaskName '$TaskName'"
Write-Host "  Enable:        Enable-ScheduledTask -TaskName '$TaskName'"
Write-Host "  Remove:        Unregister-ScheduledTask -TaskName '$TaskName'"
Write-Host "  View status:   Get-ScheduledTask -TaskName '$TaskName'"
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
