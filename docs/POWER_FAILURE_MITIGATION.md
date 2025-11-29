# Power Failure Mitigation Guide

## Problem
Frequent power failures were corrupting Neo4j transaction logs, causing database startup failures.

## Solutions Implemented

### 1. Docker Configuration Changes
Modified `docker-compose.yml` to add power-failure-resistant settings:

- **More frequent checkpoints** (every 5 minutes) - reduces data loss window
- **Transaction log pre-allocation** - prevents partial writes
- **Graceful degradation** - allows startup even with corrupted logs (will truncate and recover)
- **Better I/O limits** - prevents write queue buildup

### 2. Graceful Shutdown Script
**Location:** `scripts/graceful-shutdown.ps1`

Forces Neo4j to flush all pending transactions before shutdown.

**Usage:**
```powershell
.\scripts\graceful-shutdown.ps1
```

**Configure with UPS software:**
- APC PowerChute: Set as shutdown script when battery reaches 30%
- CyberPower PowerPanel: Add to "Low Battery Action"
- Windows: Add to Group Policy shutdown scripts

### 3. Recovery-Aware Startup Script
**Location:** `scripts/startup-with-recovery.ps1`

Automatically detects and recovers from corruption.

**Usage:**
```powershell
.\scripts\startup-with-recovery.ps1
```

### 4. Recommended Hardware
**Get a UPS (Uninterruptible Power Supply):**

**Minimum specs for your setup:**
- 1500VA / 900W capacity
- 15-30 minutes runtime
- USB/Network management
- Automatic shutdown software

**Recommended models:**
- **APC Back-UPS Pro 1500VA** (BR1500MS2) - ~$350
  - Smart shutdown via USB
  - PowerChute software included
  
- **CyberPower CP1500PFCLCD** - ~$280
  - Pure sine wave (safer for PSU)
  - PowerPanel software included

## Setup Instructions

### Step 1: Configure UPS Software
1. Install UPS management software (APC PowerChute or CyberPower PowerPanel)
2. Configure low battery threshold: **30%**
3. Add shutdown action: Call `graceful-shutdown.ps1`

### Step 2: Test Graceful Shutdown
```powershell
# Test the shutdown script
.\scripts\graceful-shutdown.ps1

# Verify Neo4j stopped cleanly
docker ps | Select-String "neo4j"
```

### Step 3: Test Recovery Startup
```powershell
# Start with recovery
.\scripts\startup-with-recovery.ps1

# Check logs for any errors
docker logs apexsigma.neo4j.db --tail 20
```

### Step 4: Update Backup Script
Your central backup script at `d:\scripts\backups\backup-neo4j.ps1` should be updated to:

1. **Validate backups** after creation:
```powershell
# Add after line 158 (after dump completes)
Write-Log -Message "Validating backup integrity..."
$testRestore = docker run --rm -v apexsigma.neo4j.data:/data neo4j:5-community `
    neo4j-admin database check --verbose neo4j
if ($LASTEXITCODE -ne 0) {
    Write-Log -Message "Backup validation FAILED!" -IsError
    exit 1
}
```

2. **Keep more backup versions** on rclone (currently only keeps latest locally)

## Additional Recommendations

### 1. Enable Windows Fast Startup Disable
Power failures can corrupt fast startup cache:
```powershell
# Disable fast startup
powercfg /hibernate off
```

### 2. Schedule Regular Consistency Checks
Add to Windows Task Scheduler (weekly):
```powershell
docker exec apexsigma.neo4j.db cypher-shell -u neo4j -p $env:NEO4J_PASSWORD `
    "CALL dbms.checkConsistency();"
```

### 3. Monitor for Corruption
Add to your monitoring:
```powershell
# Check Neo4j logs for corruption warnings
docker logs apexsigma.neo4j.db 2>&1 | Select-String -Pattern "corrupt|recovery|ERROR"
```

## Emergency Recovery Procedure

If Neo4j won't start despite these measures:

1. **Check logs:**
   ```powershell
   docker logs apexsigma.neo4j.db --tail 50
   ```

2. **Try forced recovery:**
   ```powershell
   docker-compose down neo4j-db
   # Temporarily enable aggressive recovery
   docker-compose up -d neo4j-db
   ```

3. **Restore from backup:**
   ```powershell
   .\scripts\percolate-conversations.ps1 -StartDate "2025-11-01"
   ```

## Monitoring Neo4j Health

Add this to a daily check:
```powershell
# Check database health
docker exec apexsigma.neo4j.db cypher-shell -u neo4j -p $env:NEO4J_PASSWORD `
    "CALL dbms.queryJmx('org.neo4j:*') YIELD attributes RETURN attributes;"
```

## Current Status
✅ Neo4j configured for power-failure resilience
✅ Graceful shutdown script created
✅ Recovery startup script created
⚠️ **Action Required:** Purchase and configure UPS
⚠️ **Action Required:** Test UPS automatic shutdown
⚠️ **Action Required:** Update central backup script validation
