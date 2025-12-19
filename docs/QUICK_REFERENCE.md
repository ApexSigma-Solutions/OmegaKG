# Omega KG - Quick Reference Card

## One-Liner Commands

### Start Services
```powershell
.\start-all.ps1          # Start everything (databases + server)
.\start-database.ps1     # Start only databases
.\start-server.ps1       # Start only capture server
```

### Stop Services
```powershell
.\stop-all.ps1           # Stop everything
```

### Check Status
```powershell
.\status.ps1             # System status
poetry run python validate-config.py  # Validate configuration
```

## Service URLs

| Service | URL | Purpose |
|---------|-----|---------|
| Capture Server | http://localhost:8765 | Main API endpoint |
| Neo4j Browser | http://localhost:7474 | Graph database UI |
| Neo4j Bolt | bolt://localhost:7687 | Graph database connection |
| PostgreSQL | localhost:5433 | Relational database |

## Key Files

| File | Purpose |
|------|---------|
| `.env` | **YOUR SECURE CONFIG** (DO NOT commit to git) |
| `.env.example` | Template/documentation for .env |
| `SETUP_COMPLETE.md` | Full setup documentation |
| `.omega_kg_setup_complete` | Setup completion marker |

## Common Tasks

### Test Capture Server
```powershell
# After starting server
Invoke-WebRequest -Uri http://localhost:8765/health
```

### View Logs
```powershell
docker-compose logs neo4j-db      # Neo4j logs
docker-compose logs postgres-db   # PostgreSQL logs
```

### Reset Databases (DANGER!)
```powershell
docker-compose down -v  # Removes all data!
```

### Chrome Extension Setup
1. `chrome://extensions`
2. Enable Developer mode
3. Load unpacked → `d:\projects\Omega_KG_stable\chrome-extension`
4. Configure options:
   - Server: `http://localhost:8765`
   - API Key: Get from `.env` (`EXTENSION_API_KEY_PRD`)

## Vault Locations

- **Vault Root**: `d:\projects\omegavault.as`
- **AI Conversations**: `d:\projects\omegavault.as\AI_Conversations`
- **Tasks**: `d:\projects\omegavault.as\Tasks`

## Troubleshooting

### Services won't start
```powershell
docker ps                          # Check Docker
docker-compose up -d               # Start manually
.\status.ps1                       # Verify status
```

### Configuration issues
```powershell
.\complete-setup.ps1               # Re-run setup
poetry run python validate-config.py  # Validate
```

### Dependency issues
```powershell
poetry install                     # Reinstall packages
poetry show                        # List installed
```

## Emergency Reset
```powershell
# Stop everything
.\stop-all.ps1

# Reset databases (WARNING: DATA LOSS!)
docker-compose down -v

# Re-run complete setup
.\complete-setup.ps1

# Start fresh
.\start-all.ps1
```

## Environment Variables (from .env)

Critical variables you configured:
- `NEO4J_PASSWORD` - Neo4j database password
- `POSTGRES_PASSWORD` - PostgreSQL password
- `EXTENSION_API_KEY_PRD` - Chrome extension auth key
- `JWT_SECRET_KEY` - JWT token signing key
- `OBSIDIAN_VAULT_PATH` - Path to Obsidian vault

## Support Commands

```powershell
# Poetry
poetry --version                   # Check Poetry version
poetry show                        # List installed packages
poetry run python --version        # Check Python version

# Docker
docker --version                   # Check Docker version
docker ps                          # List running containers
docker-compose ps                  # List compose services

# Python
poetry run python -c "from omega_kg.settings import Settings; s = Settings(); print(f'Vault: {s.obsidian_vault_path}')"
```

## Next Steps After Setup

1. ✅ Services running? → Run `.\status.ps1`
2. ✅ Chrome extension installed? → Visit `chrome://extensions`
3. ✅ Test a capture? → Chat with ChatGPT/Claude
4. ✅ Check captures → Look in vault's `AI_Conversations/`
5. ✅ View graph → Open `http://localhost:7474`

---
**Configuration Status**: ✅ Persistent & Ready  
**Last Setup**: 2025-12-16  
**Version**: 1.0.0
