# Omega_KG Project Overview

## Purpose
Omega_KG is a **Neo4j-powered knowledge management system** that bridges:
- **Obsidian vaults** (markdown storage)
- **Linear tasks** (team task management)
- **Git commits** (implementation tracking)
- **AI conversations** (Chrome extension captures from Claude, ChatGPT, Gemini, Perplexity, GitHub Copilot, Qwen, Microsoft Copilot)

The system creates an intelligent knowledge graph that links decisions, tasks, commits, and sessions.

## Key Objectives
1. Capture AI conversations via Chrome extension
2. Sync conversations & tasks bidirectionally with Linear
3. Track implementation through Git commits
4. Enforce automated task lifecycle (draft → ready → active → blocked → completed → archived)
5. Send email notifications before auto-transitions and for stale tasks

## Tech Stack
- **Language**: Python 3.12+ (requires >=3.12, recommended 3.13+)
- **Package manager**: Poetry
- **Database**: Neo4j (local or cloud)
- **API**: FastAPI + Uvicorn
- **Storage/Sync**: Markdown (Obsidian), Chrome extension
- **Task scheduling**: APScheduler
- **Testing**: pytest, pytest-cov, pytest-asyncio
- **Code quality**: Ruff, MyPy, Black, pre-commit
- **Docs**: MkDocs + mkdocstrings

## Core Modules
- `settings.py` — Pydantic BaseSettings for config (NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, OBSIDIAN_VAULT_PATH, email config)
- `capture_server.py` — FastAPI server for receiving conversation captures (http://localhost:8765)
- `lifecycle.py` — Task state management & automated transitions
- `linear_sync.py` — Bidirectional Linear ↔ Obsidian sync
- `obsidian_sync.py` — Markdown sync & frontmatter handling
- `percolation.py` — Extract commits/tasks from markdown into Neo4j
- `neo4j_schema.py` — Graph schema definitions
- `cli.py` — CLI entrypoint
- `poc_okg.py` — Proof-of-concept Neo4j integration

## Data Model
**Nodes**:
- ChatSession (date, topic)
- Decision (content, implements decisions from sessions)
- Task (uid, title, filepath, status, linear_id, linear_status, linear_priority, created, transitioned_at, pinned, warned)
- Commit (hash, message, repo, timestamp)

**Relationships**:
- ChatSession -[:CONTAINS]-> Decision
- Task -[:IMPLEMENTS]-> Decision
- Commit -[:IMPLEMENTS]-> Task
- Session -[:CONTAINS_COMMIT]-> Commit

## Branching Strategy
- **alpha** — default/primary branch
- **beta** — development branch (created for new work)
- **feature/*** — feature branches open PRs to alpha
- All PRs must pass tests and pre-commit checks before merge
