# Schedule capture server to start at login

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-WindowStyle Hidden -Command `"cd `"$env:USERPROFILE\OneDrive\ApexSigma\Omega_KG`"; poetry run python -m omega_kg.capture_server`""

$trigger = New-ScheduledTaskTrigger -AtLogOn

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0)  # Run indefinitely

Register-ScheduledTask `
    -TaskName "Omega_KG_Capture_Server" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Omega_KG AI conversation capture server"

Write-Host "✓ Capture server scheduled to start at login"