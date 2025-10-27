# Start capture server in background

# Check if already running
$existing = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" |
    Where-Object { $_.CommandLine -match "omega_kg.capture_server" }

if ($existing) {
    Write-Host "⚠ Capture server already running (PID: $($existing.Id))"
    exit 0
}

# Start in background
$job = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    poetry run python -m omega_kg.capture_server
}

Write-Host "✓ Capture server started (Job ID: $($job.Id))"
Write-Host "  Test: http://localhost:8765/health"
Write-Host ""
Write-Host "To stop:"
Write-Host "  Stop-Job -Id $($job.Id); Remove-Job -Id $($job.Id)"