# Ollama Headless Horsemen Setup Guide

This document provides comprehensive instructions for configuring Ollama as a headless service that integrates with ApexSigma and the Omega Knowledge Graph.

## Overview

By default, Ollama binds to `127.0.0.1`, which prevents access from Docker containers, WSL, or other machines on your LAN. This setup configures Ollama to:

1. **Bind to all network interfaces** (`0.0.0.0:11434`)
2. **Run as a headless service** at system startup (no GUI)
3. **Integrate seamlessly** with Omega_KG embedding services
4. **Provide monitoring** for uptime visibility

## Prerequisites

- Windows 10/11 with PowerShell 5.1+
- Administrator privileges
- Ollama installed
- Omega_KG development environment

## Quick Start

### 1. Run the Setup Script (Recommended)

```powershell
# Run as Administrator
.\scripts\setup-ollama-headless.ps1
```

This script will:
- Set `OLLAMA_HOST=0.0.0.0:11434` environment variable
- Open port 11434 in Windows Firewall
- Create `OllamaService` scheduled task (runs as SYSTEM at startup)
- Disable default Ollama Startup app

### 2. Restart Your Computer

**Critical**: Environment variables require a system restart to take effect.

### 3. Verify the Setup

```powershell
# Check if Ollama is running correctly
.\scripts\verify-ollama-service.ps1
```

### 4. Configure Omega_KG Integration

The Omega_KG application automatically reads the `OLLAMA_HOST` environment variable. No additional configuration is needed if:

- `OLLAMA_HOST` is set to `0.0.0.0:11434`
- `OLLAMA_BASE_URL` in `.env` points to the correct IP

## Manual Configuration

If you prefer to configure manually or troubleshoot:

### Phase 1: Environment & Network Configuration

```powershell
# Set the bind address to all interfaces
[System.Environment]::SetEnvironmentVariable('OLLAMA_HOST', '0.0.0.0:11434', 'Machine')

# Open the port in Windows Defender Firewall
New-NetFirewallRule -DisplayName "Ollama Server" -Direction Inbound -LocalPort 11434 -Protocol TCP -Action Allow
```

### Phase 2: Headless Startup Configuration

1. **Disable the default Startup app:**
   - Open Task Manager (`Ctrl+Shift+Esc`) → **Startup Apps**
   - Right-click "Ollama" → **Disable**

2. **Create the Background Task:**
   ```powershell
   $action = New-ScheduledTaskAction -Execute "ollama" -Argument "serve"
   $trigger = New-ScheduledTaskTrigger -AtStartup
   $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -Hidden -ExecutionTimeLimit 0
   
   Register-ScheduledTask -Action $action -Trigger $trigger -Settings $settings -TaskName "OllamaService" -User "SYSTEM" -RunLevel Highest
   ```

### Phase 3: Verification Protocol

1. **Restart your machine**
2. **Local Check:**
   ```powershell
   netstat -an | findstr 11434
   # Should show: 0.0.0.0:11434
   ```
3. **Service Check:**
   ```powershell
   curl http://localhost:11434/
   # Should return: Ollama is running
   ```
4. **Network Check (from WSL/another device):**
   ```bash
   curl http://<YOUR_WINDOWS_IP>:11434/
   # Should return: Ollama is running
   ```

### Phase 4: Omega_KG Integration

Update your `.env` file:

```env
# Embedding Service Configuration
EMBEDDING_PROVIDER=ollama
OLLAMA_BASE_URL=http://0.0.0.0:11434
OLLAMA_HOST=0.0.0.0:11434
```

**Important**: If your code runs in WSL2, use your Windows host IP instead of `localhost`.

## Monitoring

### Heartbeat Monitor

Start continuous monitoring:

```powershell
.\scripts\ollama-heartbeat-monitor.ps1
```

This script:
- Checks Ollama connectivity every 30 seconds
- Logs status to `ollama_heartbeat.log`
- Optionally logs to PostgreSQL datalake
- Provides uptime alerts

### Manual Health Checks

```powershell
# Quick status check
curl http://localhost:11434/

# Test model inference
$testBody = @{
    model = "llama3.2"
    prompt = "System check. Status?"
    stream = $false
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:11434/api/generate" -Method Post -Body $testBody -ContentType "application/json"
```

## Troubleshooting

### Common Issues

1. **Port not listening on 0.0.0.0**
   - Restart your computer after setting `OLLAMA_HOST`
   - Verify environment variable is set at Machine level

2. **Firewall blocking access**
   - Check Windows Firewall rules
   - Ensure rule allows inbound TCP on port 11434

3. **Service not starting**
   - Check Task Scheduler for `OllamaService`
   - Verify task runs as SYSTEM with highest privileges
   - Check Event Viewer for errors

4. **WSL2 connectivity issues**
   - Use Windows host IP instead of `localhost`
   - Check WSL2 networking configuration

### Diagnostic Commands

```powershell
# Check environment variable
[Environment]::GetEnvironmentVariable('OLLAMA_HOST', 'Machine')

# Check firewall rule
Get-NetFirewallRule -DisplayName "Ollama Server"

# Check scheduled task
Get-ScheduledTask -TaskName "OllamaService" | Get-ScheduledTaskInfo

# Check running processes
Get-Process -Name "ollama" -ErrorAction SilentlyContinue
```

### Logs and Monitoring

- **Ollama logs**: Check Windows Event Viewer
- **Heartbeat logs**: `ollama_heartbeat.log`
- **Omega_KG logs**: Application logs for embedding failures

## Integration with Omega_KG

### Embedding Service Configuration

Omega_KG uses a provider hierarchy for embeddings:

1. **Ollama (primary)**: Local `bge-m3:567m` model, 1024 dimensions
2. **Nano-GPT (fallback)**: Hosted BAAI bge-m3, 1024 dimensions
3. **Gemini (secondary)**: Truncated from 3072 to 1024 dimensions
4. **Mock (development)**: Deterministic hash-based vectors

### Configuration Files

- **settings.py**: Embedding provider configuration
- **config.py**: Ollama URL and worker settings
- **embedding_service.py**: Provider implementation and fallback logic

### WSL2 Considerations

If Omega_KG runs in WSL2:

```env
# Use Windows host IP, not localhost
OLLAMA_BASE_URL=http://<WINDOWS_HOST_IP>:11434
```

Find your Windows host IP from WSL2:
```bash
cat /etc/resolv.conf | grep nameserver | awk '{print $2}'
```

## Security Considerations

- **Network exposure**: Binding to `0.0.0.0` exposes Ollama to your network
- **Firewall rules**: Only allow trusted devices/IPs if needed
- **Authentication**: Consider API key authentication for production
- **Model security**: Keep models updated and scan for vulnerabilities

## Performance Optimization

- **Model selection**: Use smaller models (`bge-m3:567m`) for faster inference
- **Resource allocation**: Ensure adequate RAM and CPU for Ollama
- **Network latency**: Minimize network hops for WSL2/Docker access

## Next Steps

1. **Deploy models**: Pull required models
   ```bash
   ollama pull bge-m3:567m
   ollama pull llama3.2
   ```

2. **Test integration**: Run Omega_KG and verify embedding generation

3. **Monitor performance**: Use heartbeat monitor for uptime tracking

4. **Scale as needed**: Consider Docker deployment for production

## Support

For issues or questions:
- Check the troubleshooting section above
- Review Omega_KG logs for embedding errors
- Verify network connectivity between services
- Consult Ollama documentation for model-specific issues