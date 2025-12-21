# OmegaKG Scripts - Quick Reference

**Environment:** Stable | **Port:** 8765 | **Architecture:** Hookdeck-based

---

## 🚀 Daily Operations

### Start the Stack
```powershell
cd d:\projects\OmegaKG\Omega_KG_stable\scripts
.\cleanup_before_start.ps1          # Clean slate
.\start_full_stack.ps1              # Start services
.\verify_stack.ps1                  # Verify health
```

### Stop the Stack
```powershell
.\cleanup_before_start.ps1
```

### Check Status
```powershell
.\status.ps1                        # Quick overview
.\verify_stack.ps1                  # Detailed verification
```

---

## 🔧 Common Tasks

| Task | Command |
|------|---------|
| **Load Chrome Extension** | `.\load-extension.ps1` |
| **Reload Extension Tabs** | `.\reload-extension-tabs.ps1` |
| **Start Databases Only** | `.\start-database.ps1` |
| **Check Task Scheduler** | `.\check_existing_tasks.ps1` |
| **Verify Secrets** | `.\verify_bitwarden_secrets.ps1` |
| **View Logs** | `Get-Content .\logs\capture_server_*.err.log -Tail 50` |

---

## 🛠️ Setup Tasks (One-time)

### Initial Setup
```powershell
.\enable_poetry_path.ps1            # Add Poetry to PATH
.\omega-venv.ps1                    # Create/update venv
.\install-hooks.ps1                 # Install git hooks
```

### Production Deployment
```powershell
.\setup-autostart.ps1               # Auto-start at login
.\schedule-lifecycle.ps1            # Daily lifecycle task
.\setup-ollama-headless.ps1         # Configure Ollama
```

---

## 🔍 Troubleshooting

### Something Not Working?
```powershell
# 1. Check overall status
.\status.ps1

# 2. Verify configuration
.\diagnose-capture-config.ps1

# 3. Check Bitwarden integration
.\verify_bitwarden_secrets.ps1

# 4. Restart with clean slate
.\cleanup_before_start.ps1
.\start_full_stack.ps1
.\verify_stack.ps1
```

### Extension Issues?
```powershell
.\diagnose-extension.ps1            # Extension loading
.\diagnose-capture-issue.ps1        # Capture functionality
.\reload-extension-tabs.ps1         # Reload tabs
```

---

## 📊 Monitoring

```powershell
.\ollama-heartbeat-monitor.ps1      # Monitor Ollama
.\status.ps1                        # System status
```

---

## 🔄 Workflows

### Development Workflow
```powershell
.\cleanup_before_start.ps1
.\start_full_stack.ps1
.\load-extension.ps1
.\status.ps1
```

### Production Deployment
```powershell
.\enable_poetry_path.ps1
.\setup-autostart.ps1
.\start-database.ps1
.\start_full_stack.ps1
.\verify_stack.ps1
```

### Daily Maintenance
```powershell
.\status.ps1
.\verify_stack.ps1
```

---

## ⚡ PowerShell Aliases (Add to Profile)

Add these to your PowerShell profile for shortcuts:

```powershell
# OmegaKG shortcuts
Set-Alias omega-start .\start_full_stack.ps1
Set-Alias omega-stop .\cleanup_before_start.ps1
Set-Alias omega-status .\status.ps1
Set-Alias omega-verify .\verify_stack.ps1
Set-Alias omega-ext .\load-extension.ps1
```

---

## 🎯 Quick Commands Reference

```powershell
# Start everything
.\start_full_stack.ps1

# Stop everything
.\cleanup_before_start.ps1

# Check health
.\verify_stack.ps1

# Load extension
.\load-extension.ps1

# Check status
.\status.ps1

# Verify Bitwarden
.\verify_bitwarden_secrets.ps1

# Diagnose issues
.\diagnose-capture-config.ps1
```

---

## 📝 Log Files

- **Capture Server:** `logs\capture_server_YYYY-MM-DD_HH-mm-ss.err.log`
- **Hookdeck:** `logs\hookdeck_YYYY-MM-DD_HH-mm-ss.err.log`

**View recent logs:**
```powershell
Get-Content .\logs\capture_server_*.err.log -Tail 100 -Wait
```

---

## 🔗 Important URLs

When stack is running:
- **API Documentation:** http://localhost:8765/docs
- **Health Check:** http://localhost:8765/health
- **Neo4j Browser:** http://localhost:7474/browser/

---

## ⚠️ Important Notes

1. **Run as Administrator** if you get port binding errors
2. **Poetry must be in PATH** - run `.\enable_poetry_path.ps1` first
3. **Start databases first** - run `.\start-database.ps1` if needed
4. **Check logs** if something isn't working

---

## 🆘 Emergency Commands

```powershell
# Kill everything and restart
.\stop-all.ps1
Start-Sleep -Seconds 2
.\start_full_stack.ps1
.\verify_stack.ps1
```

---

**For detailed information, see [SCRIPT_MAP.md](SCRIPT_MAP.md)**