# Omega_KG Documentation

**Omega_KG** is a Neo4j-powered knowledge management system that bridges Obsidian vaults, Linear tasks, and Git commits with intelligent task lifecycle enforcement.

## Overview

Omega_KG provides a bidirectional synchronization layer between an Obsidian vault and Neo4j graph database, enabling:

- **Knowledge Graph Management**: Represent tasks, decisions, and commits as interconnected nodes
- **Task Lifecycle Enforcement**: Automatic time-based transitions with configurable rules
- **Linear Integration**: Bidirectional sync with Linear issue tracker via webhooks
- **Obsidian Sync**: Parse vault notes and maintain frontmatter-based task metadata
- **Mock Mode Support**: Graceful fallback when database is unavailable
- **CLI Tools**: Comprehensive command-line interface for all operations

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/ApexSigma-Solutions/omega_kg.git
cd omega_kg

# Install dependencies with Poetry
poetry install

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your configuration
```

### Configuration

Create a `.env` file with required settings:

```env
# Neo4j Database
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password

# Obsidian Vault
OBSIDIAN_VAULT_PATH=/path/to/your/vault

# Email (Optional - for lifecycle reports)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_TO=recipient@example.com

# Linear Integration (Optional)
LINEAR_API_KEY=your-linear-api-key
LINEAR_WEBHOOK_SECRET=your-webhook-secret
LINEAR_TEAM_ID=your-team-id
```

### Basic Usage

```bash
# Initialize Neo4j schema
poetry run omega init

# Check system status
poetry run omega status

# Sync Obsidian vault to Neo4j
poetry run omega sync

# Enforce lifecycle rules (dry-run)
poetry run omega lifecycle --dry-run

# Generate lifecycle report
poetry run omega report

# View statistics
poetry run omega stats

# List stale tasks
poetry run omega stale
```

## Architecture

### Data Model

**Node Types:**
- **Task**: Represents work items with status, priority, and lifecycle metadata
- **ChatSession**: Decision-making sessions
- **Decision**: Individual decisions or action items
- **Commit**: Git commits linked to tasks

**Relationships:**
- `ChatSession -[:CONTAINS]-> Decision`
- `Task -[:IMPLEMENTS]-> Decision`
- `Commit -[:IMPLEMENTS]-> Task`
- `Session -[:CONTAINS_COMMIT]-> Commit`

### Task Lifecycle

Tasks flow through the following states with automatic transitions:

```
draft → ready → active → blocked → completed → archived
```

**Lifecycle Rules:**
1. **Draft decay**: Draft tasks auto-archive after 14 days (warns at 10 days)
2. **Stale detection**: Active tasks without commits for 30+ days → blocked
3. **Completed archival**: Completed tasks archive after 90 days
4. **Pinning**: Tasks marked as `pinned: true` are exempt from automatic archival

## Features

### 1. Obsidian Sync

Bidirectional synchronization between Obsidian markdown files and Neo4j:

- Parse frontmatter metadata (status, UID, Linear ID, etc.)
- Create/update Task nodes in Neo4j
- Update vault files when tasks change
- Support for templated UIDs

### 2. Task Lifecycle Enforcement

Automated task lifecycle management:

- Time-based state transitions
- Email notifications for approaching deadlines
- Stale task detection
- Human-readable reports
- Dry-run mode for testing

### 3. Linear Integration

Webhook-based integration with Linear:

- Sync Linear issue updates to Neo4j
- Map Linear states to Obsidian statuses
- Handle issue deletion
- Update vault files with Linear metadata

### 4. Connection Recovery

Graceful handling of database unavailability:

- Automatic fallback to mock mode
- Connection health checks
- No-op operations when disconnected
- Clear status reporting

## CLI Reference

### `omega init`
Initialize the Neo4j schema with required constraints and relationships.

### `omega sync [--mock]`
Synchronize all task notes from Obsidian vault to Neo4j. Use `--mock` flag to test without database.

### `omega lifecycle [--dry-run] [--no-email]`
Enforce lifecycle rules on tasks. Use `--dry-run` to preview changes without applying them.

### `omega status`
Check and display connection status for Neo4j, configuration, and integrations.

### `omega report [--dry-run] [--email]`
Generate a lifecycle report with task statistics. Use `--email` to send via SMTP.

### `omega stats`
Display aggregated task counts by status.

### `omega stale`
List draft tasks older than 7 days.

## Development

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=omega_kg

# Run specific test file
poetry run pytest tests/test_lifecycle.py -v
```

### Code Quality

```bash
# Format code
poetry run black omega_kg tests

# Lint
poetry run ruff check omega_kg tests

# Type checking
poetry run mypy omega_kg
```

## API Reference

See the [API Reference](reference.md) section for detailed module documentation.

## Support

For issues and questions, please visit the [GitHub repository](https://github.com/ApexSigma-Solutions/omega_kg).
