# Omega_KG

**Neo4j-powered knowledge management system with Obsidian sync and task lifecycle enforcement**

[![Tests](https://github.com/ApexSigma-Solutions/omega_kg/actions/workflows/ci.yml/badge.svg)](https://github.com/ApexSigma-Solutions/omega_kg/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Poetry](https://img.shields.io/endpoint?url=https://python-poetry.org/badge/v0.json)](https://python-poetry.org/)

## Overview

Omega_KG bridges Obsidian vaults, Linear tasks, and Git commits in a Neo4j knowledge graph with intelligent task lifecycle enforcement.

### Key Features

- 🔄 **Bidirectional Sync**: Obsidian ↔ Neo4j ↔ Linear integration
- 🌡️ **Lifecycle Rules**: Time-based task state transitions with configurable thresholds
- 🔗 **Knowledge Graph**: Tasks, decisions, and commits as interconnected nodes
- 📧 **Email Reports**: Automated lifecycle reports via SMTP
- 🎯 **Mock Mode**: Graceful fallback when database unavailable
- 🛠️ **CLI Tools**: Complete command-line interface for all operations

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/ApexSigma-Solutions/omega_kg.git
cd omega_kg

# Install with Poetry
poetry install

# Configure environment
cp .env.example .env
# Edit .env with your settings
```

### Basic Commands

```bash
# Initialize schema
poetry run omega init

# Check status
poetry run omega status

# Sync vault
poetry run omega sync

# Enforce lifecycle (dry-run)
poetry run omega lifecycle --dry-run

# Generate report
poetry run omega report
```

## Configuration

Required environment variables in `.env`:

```env
# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password

# Obsidian
OBSIDIAN_VAULT_PATH=/path/to/vault

# Email (Optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-password
EMAIL_TO=recipient@example.com

# Linear (Optional)
LINEAR_API_KEY=your-api-key
LINEAR_WEBHOOK_SECRET=your-webhook-secret
```

## Task Lifecycle

Tasks transition through states with automatic enforcement:

```
draft → ready → active → blocked → completed → archived
```

**Rules:**
- Draft tasks auto-archive after 14 days (warn at 10 days)
- Active tasks without commits for 30+ days → blocked
- Completed tasks archive after 90 days
- Pinned tasks are exempt from auto-archival

## Development

### Running Tests

```bash
poetry run pytest              # Run all tests
poetry run pytest --cov        # With coverage
poetry run pytest -v           # Verbose output
```

### Code Quality

```bash
poetry run black .             # Format code
poetry run ruff check .        # Lint
poetry run mypy omega_kg       # Type check
```

## Documentation

Full documentation available at: https://apexsigma-solutions.github.io/omega_kg/

## CLI Reference

| Command | Description |
|---------|-------------|
| `omega init` | Initialize Neo4j schema |
| `omega sync` | Sync Obsidian vault to Neo4j |
| `omega lifecycle` | Enforce lifecycle rules |
| `omega status` | Check connection status |
| `omega report` | Generate lifecycle report |
| `omega stats` | Display task statistics |
| `omega stale` | List stale tasks |

## Architecture

### Data Model

**Nodes:**
- **Task**: Work items with status and lifecycle metadata
- **ChatSession**: Decision-making sessions
- **Decision**: Individual decisions
- **Commit**: Git commits linked to tasks

**Relationships:**
- `ChatSession -[:CONTAINS]-> Decision`
- `Task -[:IMPLEMENTS]-> Decision`
- `Commit -[:IMPLEMENTS]-> Task`

## License

Copyright © 2025 ApexSigma Solutions

## Support

For issues and questions, please open an issue on GitHub.

