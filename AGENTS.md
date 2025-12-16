# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Dual-Agent Workflow Context
This is a **Pattern A** project with memory bank at `./.kilocode/rules/memory-bank/`. Always read `activeContext.md` before starting tasks and update memory bank files as needed. Follow the dual-agent architecture with Kilo Code as governance layer and Roo Code as execution engine.

## Non-Obvious Project-Specific Patterns

### Critical Hardcoded Conventions
- **AI_Conversations folder**: Capture server writes to hardcoded `AI_Conversations/{platform}/` folder in Obsidian vault (capture_server.py:339)
- **UID-based task files**: Tasks use glob pattern `f"Tasks/**/{uid}*.md"` for file discovery (lifecycle.py:358)
- **Content ID format**: Conversations use `CAP-{YYYYMMDD}-{HASH}` format for frontmatter IDs (capture_server.py:225)

### Auto-Fallback Behaviors
- **Mock mode activation**: System automatically switches to mock mode when Neo4j connection fails (lifecycle.py:118-120)
- **Embedding worker**: Asynchronous worker polls every 10 seconds for pending embeddings (capture_server.py:75-76)
- **Session scheduler**: Batch percolation runs every 5 minutes via APScheduler (capture_server.py:84-88)

### Dual Persistence Architecture
- **Neo4j + Markdown sync**: Tasks stored in both Neo4j AND Obsidian markdown files with frontmatter synchronization (lifecycle.py:317-391)
- **Health validation**: Connection checks use `RETURN 1` query pattern (capture_server.py:667)
- **Vector embedding**: ChatSession nodes queue embeddings via `store_pending()` then process asynchronously (capture_server.py:520-526)

### Security & Authentication
- **Bitwarden hybrid secrets**: Zero-trust configuration using Bitwarden SDK for environment variable injection (settings.py:15-67)
- **JWT exchange flow**: Chrome extension exchanges static API key for short-lived JWT tokens (capture_server.py:695-716)
- **CORS origins**: Chrome extension ID must match exactly in CORS configuration (capture_server.py:138)

### Task Lifecycle Enforcement
- **Draft → Archived**: 14 days (auto), 10 days (warn) unless pinned (lifecycle.py:63-77)
- **Active → Blocked**: 30 days without commits (lifecycle.py:79-85)  
- **Completed → Archived**: 90 days (lifecycle.py:87-92)

### Testing Infrastructure
- **Custom markers**: Use `@pytest.mark.requires_neo4j` for database-dependent tests
- **Mock fixtures**: `mock_env_vars`, `mock_neo4j_driver`, `task_lifecycle_mock` from conftest.py
- **Test vault**: Tests automatically create `./test_vault` directory structure

### Critical Gotchas
- **Settings validation**: Pydantic fails fast on missing required env vars (settings.py:108-119)
- **File encoding**: Always use `encoding="utf-8"` for file operations (capture_server.py:355)
- **Platform sanitization**: Platform names sanitized via regex `r'[<>:"|?*\x00-\x1f]'` before folder creation (capture_server.py:327)
- **Session context**: Neo4j operations MUST use `with driver.session() as session:` pattern or will leak connections

## Entry Points
- **CLI**: `omega` command via `omega_kg.cli:cli`
- **Capture server**: `capture-server` runs on port 8765 with lifespan management
- **Lifecycle enforcement**: `python -m omega_kg.lifecycle --dry-run`

## Neighboring Projects
- **Omega_KG_stable**: Production version with enhanced linear_client and obsidian_sync modules
- **omegavault.as**: Obsidian vault with memory-bank and workflow templates
- All projects share dual-agent architecture and memory bank patterns

## New Contributors
- **Serena**: Added onboarding doc `ONBOARD_SERENA.md`. Follow the steps there and open a PR titled "Onboarding: Serena" when ready.
