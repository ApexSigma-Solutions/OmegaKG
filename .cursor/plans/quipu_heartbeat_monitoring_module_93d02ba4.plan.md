---
name: Quipu Heartbeat Monitoring Module
overview: Refactor and integrate the Quipu Ollama heartbeat monitoring module into the Omega_KG project architecture, following project patterns for configuration, database access, and service deployment.
todos:
  - id: config-settings
    content: Add Quipu monitoring configuration fields to settings.py (ollama_host_url, heartbeat_interval_sec, quipu_service_name, omega_pg_conn)
    status: completed
  - id: database-module
    content: Create omega_kg/database/quipu.py with init_heartbeat_table() and insert_heartbeat() functions using psycopg2
    status: completed
  - id: refactor-heartbeat
    content: Refactor quipu_ollama_heartbeat.py to use settings.py and database/quipu.py module instead of direct os.getenv() and inline DB code
    status: completed
  - id: update-dependencies
    content: Verify and add psycopg2-binary to pyproject.toml dependencies if missing
    status: completed
  - id: fix-service-script
    content: Update scripts/register_heartbeat.ps1 to use correct path (omega_kg/quipu_ollama_heartbeat.py) and verify working directory
    status: completed
  - id: env-documentation
    content: Update .env.example with Quipu monitoring configuration variables (if file is accessible)
    status: completed
---

# Quipu Heartbeat Monitoring Module Implementation Plan

## Current State Analysis

The project has:

- Existing `omega_kg/quipu_ollama_heartbeat.py` using direct psycopg2 connections
- PowerShell service registration scripts (`register_heartbeat.ps1`)
- Pydantic Settings pattern in `omega_kg/settings.py`
- Async SQLAlchemy patterns in `omega_kg/database/session.py`
- Environment-based configuration with `.env` support

## Implementation Tasks

### 1. Configuration Integration (`omega_kg/settings.py`)

Add Quipu monitoring settings to the Settings class:

- `ollama_host_url`: str (default: "http://localhost:11434")
- `heartbeat_interval_sec`: int (default: 60)
- `quipu_service_name`: str (default: "ollama-server-01")
- `omega_pg_conn`: Optional[str] for direct connection string (legacy support)
- Use existing `postgres_*` fields for connection building

**File**: `omega_kg/settings.py`

- Add fields after line 152 (after `ollama_base_url`)
- Support both new pattern (using `postgres_*` fields) and legacy `OMEGA_PG_CONN` string

### 2. Database Schema Module (`omega_kg/database/quipu.py`)

Create new database module for Quipu operations:

- `init_heartbeat_table()`: Create `system_heartbeats` table if missing
- `insert_heartbeat()`: Insert heartbeat record
- Use sync psycopg2 for compatibility with background service (not async)
- Connection pooling or connection factory pattern

**File**: `omega_kg/database/quipu.py` (new file)

- SQL definitions for table creation and inserts
- Connection management with retry logic
- Error handling for database failures

### 3. Refactor Heartbeat Monitor (`omega_kg/quipu_ollama_heartbeat.py`)

Refactor to use project patterns:

- Import from `omega_kg.settings` instead of direct `os.getenv()`
- Use `omega_kg.database.quipu` for database operations
- Maintain sync pattern (required for Windows service)
- Improve error handling and logging
- Add graceful shutdown handling
- Support both direct execution and module import

**File**: `omega_kg/quipu_ollama_heartbeat.py`

- Replace configuration section (lines 10-19) with settings import
- Replace database functions (lines 48-71) with module imports
- Keep `check_ollama_health()` function (lines 73-106)
- Refactor `run_heartbeat_loop()` to use new database module

### 4. Update Dependencies (`pyproject.toml`)

Ensure required dependencies are present:

- `psycopg2-binary` or `psycopg2` (for sync PostgreSQL access)
- `python-dotenv` (already used, verify in dependencies)
- `requests` (already used)

**File**: `pyproject.toml`

- Verify `psycopg2-binary` is in dependencies (add if missing)
- Note: `requests` and `python-dotenv` should already be present

### 5. Update Service Registration Script (`scripts/register_heartbeat.ps1`)

Fix path references and ensure correct working directory:

- Update `$ScriptRelPath` to point to `omega_kg/quipu_ollama_heartbeat.py`
- Ensure working directory is project root for `.env` discovery
- Verify Poetry venv path resolution

**File**: `scripts/register_heartbeat.ps1`

- Line 7: Update path to `omega_kg/quipu_ollama_heartbeat.py`
- Ensure `WorkingDirectory` is set correctly (line 38)

### 6. Environment Configuration

Update `.env.example` template:

- Add `OLLAMA_HOST_URL` (optional, has default)
- Add `HEARTBEAT_INTERVAL_SEC` (optional, has default)
- Add `QUIPU_SERVICE_NAME` (optional, has default)
- Document `OMEGA_PG_CONN` for legacy support

**File**: `.env.example` (if accessible)

- Add Quipu monitoring section with commented examples

### 7. CLI Integration (Optional Enhancement)

Add CLI command for manual heartbeat operations:

- `omega quipu status`: Check current Ollama health
- `omega quipu test`: Run single heartbeat check
- `omega quipu init-db`: Initialize heartbeat table

**File**: `omega_kg/cli.py`

- Add `quipu` command group
- Import and expose heartbeat functions

## Technical Decisions

1. **Sync vs Async**: Keep sync pattern (psycopg2) for Windows service compatibility
2. **Connection String**: Support both new pattern (from settings) and legacy `OMEGA_PG_CONN`
3. **Error Handling**: Graceful degradation - continue monitoring even if DB write fails
4. **Logging**: Use project logging patterns with `[QUIPU]` prefix
5. **Service Name**: Configurable via `QUIPU_SERVICE_NAME` env var

## Testing Considerations

- Unit tests for `check_ollama_health()` with mocked requests
- Integration tests for database operations (requires PostgreSQL)
- Service registration verification (manual/scripted)
- Error handling tests (network failures, DB failures)

## Files to Modify

1. `omega_kg/settings.py` - Add configuration fields
2. `omega_kg/quipu_ollama_heartbeat.py` - Refactor to use settings and database module
3. `omega_kg/database/quipu.py` - New file for database operations
4. `scripts/register_heartbeat.ps1` - Fix path references
5. `pyproject.toml` - Verify dependencies
6. `.env.example` - Add configuration documentation (if accessible)

## Files to Create

1. `omega_kg/database/quipu.py` - Database operations module
2. `tests/test_quipu_heartbeat.py` - Unit and integration tests (optional)

## Dependencies

- `psycopg2-binary` - PostgreSQL sync driver
- `requests` - HTTP client for Ollama health checks
- `python-dotenv` - Environment variable loading