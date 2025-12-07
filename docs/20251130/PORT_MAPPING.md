# Port Mapping & Service Configuration

This document defines all network ports used by Omega_KG services across development and production environments.

## Quick Reference

| Service | Production | Development | Protocol | Purpose |
|---------|------------|-------------|----------|---------|
| **Capture Server** | 8765 | 8765 | HTTP | Chrome extension capture endpoint |
| **PostgreSQL** | 5433 | 5433 | TCP | Relational database (sessions, events) |
| **Neo4j Bolt** | 7687 | 7687 | Bolt | Graph database queries |
| **Neo4j HTTP** | 7474 | 7474 | HTTP | Neo4j Browser UI |
| **Ollama** | 11434 | 11434 | HTTP | Local embedding service |

## Service Details

### Capture Server (FastAPI/Uvicorn)

| Environment | Host | Port | URL |
|-------------|------|------|-----|
| Production | 127.0.0.1 | 8765 | `http://localhost:8765` |
| Development | 127.0.0.1 | 8765 | `http://localhost:8765` |
| Docker | 0.0.0.0 | 8765 | `http://host:8765` |

**Endpoints:**
- `GET /health` - Health check
- `POST /auth/token` - JWT token exchange
- `POST /capture` - Conversation capture
- `POST /webhook/linear` - Linear webhook receiver

**Configuration:**
```bash
# .env
APP_HOST=127.0.0.1
APP_PORT=8765
```

### PostgreSQL

| Environment | Host | Port | Database |
|-------------|------|------|----------|
| Production | 127.0.0.1 | 5433 | omega_kg |
| Development | 127.0.0.1 | 5433 | omega_kg |
| Docker | postgres | 5432 | omega_kg |

**Note:** Port 5433 is used to avoid conflicts with system PostgreSQL on port 5432.

**Configuration:**
```bash
# .env
POSTGRES_SERVER=127.0.0.1
POSTGRES_PORT=5433
POSTGRES_USER=omega_user
POSTGRES_DB=omega_kg
```

### Neo4j

| Environment | Bolt Port | HTTP Port | Browser URL |
|-------------|-----------|-----------|-------------|
| Production | 7687 | 7474 | `http://localhost:7474` |
| Development | 7687 | 7474 | `http://localhost:7474` |
| Docker | 7687 | 7474 | `http://localhost:7474` |

**Configuration:**
```bash
# .env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<secure_password>
```

### Ollama (Local Embeddings)

| Environment | Host | Port | URL |
|-------------|------|------|-----|
| All | localhost | 11434 | `http://localhost:11434` |

**Model:** `bge-m3:567m` (1024-dim embeddings)

**Test Command:**
```bash
curl http://localhost:11434/api/embeddings -d '{"model":"bge-m3:567m","prompt":"test"}'
```

## Docker Compose Port Mappings

```yaml
# docker-compose.yml
services:
  omega-kg:
    ports:
      - "8765:8765"  # Capture server

  neo4j:
    ports:
      - "7474:7474"  # Neo4j Browser
      - "7687:7687"  # Bolt protocol

  postgres:
    ports:
      - "5433:5432"  # PostgreSQL (mapped to 5433 on host)
```

## Chrome Extension Configuration

The Chrome extension connects to the capture server:

```javascript
// chrome-extension/config.js
const DEFAULT_CONFIG = {
    SERVER_URL: 'http://localhost:8765',
    ENDPOINTS: {
        AUTH_TOKEN: '/auth/token',
        CAPTURE: '/capture',
        HEALTH: '/health',
    }
};
```

**manifest.json host_permissions:**
```json
{
  "host_permissions": [
    "http://localhost:8765/*"
  ]
}
```

## Firewall Configuration

### Windows
```powershell
# Allow capture server
netsh advfirewall firewall add rule name="Omega_KG Capture" dir=in action=allow protocol=TCP localport=8765

# Allow Neo4j
netsh advfirewall firewall add rule name="Neo4j Bolt" dir=in action=allow protocol=TCP localport=7687
netsh advfirewall firewall add rule name="Neo4j HTTP" dir=in action=allow protocol=TCP localport=7474

# Allow PostgreSQL
netsh advfirewall firewall add rule name="PostgreSQL" dir=in action=allow protocol=TCP localport=5433
```

### Linux/macOS
```bash
# Allow capture server
sudo ufw allow 8765/tcp

# Allow Neo4j
sudo ufw allow 7474/tcp
sudo ufw allow 7687/tcp

# Allow PostgreSQL
sudo ufw allow 5433/tcp
```

## Port Conflict Troubleshooting

### Check what's using a port

**Windows:**
```powershell
netstat -ano | findstr :8765
Get-Process -Id <PID>
```

**Linux/macOS:**
```bash
lsof -i :8765
```

### Kill process on a port

**Windows:**
```powershell
Stop-Process -Id <PID> -Force
```

**Linux/macOS:**
```bash
kill -9 <PID>
```

### Common Port Conflicts

| Port | Common Conflict | Solution |
|------|-----------------|----------|
| 5432 | System PostgreSQL | Use 5433 instead |
| 8000 | Other web apps | Use 8765 |
| 8080 | Proxy servers | Use 8765 |
| 7474 | Other Neo4j instances | Stop conflicting instance |

## Health Check Commands

```bash
# Capture Server
curl http://localhost:8765/health

# PostgreSQL
pg_isready -h localhost -p 5433

# Neo4j
curl http://localhost:7474

# Ollama
curl http://localhost:11434/api/tags
```

## Environment-Specific Notes

### Production (Omega_KG_stable)
- All services run on standard ports
- Capture server on 8765
- PostgreSQL on 5433
- Neo4j on 7687/7474

### Development (Omega_KG_dev)
- Same port configuration as production
- Can run simultaneously if on different machines
- Use Docker network isolation if needed

## Version History

| Date | Change | Author |
|------|--------|--------|
| 2025-11-30 | Unified port 8765 for capture server | System |
| 2025-11-30 | Created PORT_MAPPING.md documentation | System |
