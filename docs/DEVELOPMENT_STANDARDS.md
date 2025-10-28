# ApexSigma Development Standards & Best Practices

**Last Updated**: October 28, 2025  
**Version**: 1.0  
**Status**: Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [Environment Setup](#environment-setup)
3. [Dependency Management (Poetry)](#dependency-management-poetry)
4. [Configuration Management (Pydantic)](#configuration-management-pydantic)
5. [Code Quality Tools](#code-quality-tools)
6. [Git Hooks & Pre-Commit Checks](#git-hooks--pre-commit-checks)
7. [Docker Containerization](#docker-containerization)
8. [CI/CD Pipeline](#cicd-pipeline)
9. [Secret Management](#secret-management)
10. [Testing & Coverage](#testing--coverage)
11. [Documentation](#documentation)
12. [Workflow Examples](#workflow-examples)

---

## Overview

This document outlines the **complete development standards** implemented across ApexSigma projects. These practices ensure:

- **Code Quality**: Automated linting, type checking, and formatting
- **Security**: Secret management, vulnerability scanning, code scanning
- **Consistency**: Unified standards across all Python projects
- **Automation**: Git hooks prevent bad commits, CI/CD gates enforce standards
- **Visibility**: Dashboard tracking, test coverage reporting, trend analysis
- **Documentation**: Auto-generated API docs, reproducible environments

### Key Technologies

| Tool               | Purpose                            | Platform       |
| ------------------ | ---------------------------------- | -------------- |
| **Poetry**         | Dependency & version management    | Python         |
| **Pydantic**       | Configuration & validation         | Python         |
| **Trunk**          | Unified linting & formatting       | Cross-language |
| **MyPy**           | Static type checking               | Python         |
| **Ruff**           | Fast Python linter                 | Python         |
| **Pytest**         | Testing & coverage                 | Python         |
| **Docker**         | Containerization & reproducibility | All            |
| **GitHub Actions** | CI/CD automation                   | Cloud          |

---

## Environment Setup

### Prerequisites

Before starting any project, ensure you have:

```bash
# System Requirements
- Python 3.12+ (minimum)
- Git 2.40+
- Docker 24.0+ (for containerization)
- curl or wget (for tool installation)

# Windows-specific
- Git Bash (included with Git for Windows)
- WSL2 (optional, for Linux environment)
- PowerShell 7+ (recommended)
```

### Initial Project Setup

#### 1. Clone Repository

```bash
git clone https://github.com/ApexSigma-Solutions/project-name.git
cd project-name
```

#### 2. Install Poetry

```bash
# Linux/macOS
curl -sSL https://install.python-poetry.org | python3 -

# Windows (PowerShell)
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -

# Add to PATH
export PATH="$HOME/.local/bin:$PATH"  # Linux/macOS
$env:PATH += ";$env:APPDATA\Python\Scripts"  # Windows
```

#### 3. Verify Poetry Installation

```bash
poetry --version        # Should be 1.7.0+
poetry config --list    # View configuration
```

#### 4. Install Project Dependencies

```bash
poetry install --with dev      # Development dependencies
poetry install --with docs     # Documentation tools
poetry install                 # Production only
```

#### 5. Set Up Git Hooks

```bash
# Hooks are automatically installed via .git/hooks/
# They run on every commit, blocking commits that fail checks

# To verify hooks are executable (Linux/macOS):
chmod +x .git/hooks/pre-commit
chmod +x .git/hooks/commit-msg

# Windows: Git handles permissions automatically
```

#### 6. Install Trunk CLI

```bash
# Install Trunk
curl -fsSL https://get.trunk.io | bash

# Verify installation
trunk version           # Should be 1.25.0+

# Login to Trunk Cloud (for dashboard)
trunk login            # Opens browser for authentication

# Install tools defined in .trunk/trunk.yaml
trunk install
```

---

## Dependency Management (Poetry)

### Why Poetry?

Poetry provides:

- **Deterministic builds** via `poetry.lock` (like Docker)
- **Virtual environment management** (isolated, reproducible)
- **Dependency resolution** (handles conflicts automatically)
- **Build & publishing** (single tool for package management)
- **Scripts & CLI entry points** (in pyproject.toml)

### pyproject.toml Structure

```toml
[project]
name = "omega_kg"
version = "0.1.0"
description = "Description of project"
authors = [{name = "Your Name", email = "email@company.com"}]
readme = "README.md"
requires-python = ">=3.12,<4.0"

# Core dependencies (production)
dependencies = [
    "neo4j>=6.0.2,<7.0.0",
    "pydantic-settings>=2.11.0,<3.0.0",
    "fastapi>=0.120.0,<0.121.0",
    # ...
]

# CLI entry points
[project.scripts]
myapp = "myapp.cli:main"

# Build system
[build-system]
requires = ["poetry-core>=2.0.0,<3.0.0"]
build-backend = "poetry.core.masonry.api"

# Poetry configuration
[tool.poetry]
packages = [{include = "myapp"}]

# Development dependencies
[tool.poetry.group.dev.dependencies]
pytest-cov = "^7.0.0"
ruff = "^0.14.1"
mypy = "^1.14.1"
black = "^25.9.0"

# Documentation dependencies
[tool.poetry.group.docs.dependencies]
mkdocs = "^1.6.1"
mkdocs-material = "^9.6.22"
mkdocstrings = {extras = ["python"], version = "^0.30.1"}
```

### Version Pinning Strategy

**Use semantic versioning ranges** for stability:

```toml
# GOOD: Allows patch/minor updates, blocks major
"^1.2.3"        # 1.2.3 to <2.0.0

# GOOD: Allows patch updates only
"~1.2.3"        # 1.2.3 to <1.3.0

# AVOID: Accepts any version (risky)
"1.2.3"         # Exact version (freezes everything)
"*"             # Any version (unpredictable)

# ACCEPTABLE: For dev tools only
"^7.0.0"        # Flexible for pytest, ruff, etc.
```

### Common Poetry Commands

```bash
# Dependency Management
poetry add package-name              # Add production dependency
poetry add --group dev package       # Add dev dependency
poetry remove package-name           # Remove dependency
poetry update                        # Update dependencies (respects constraints)
poetry lock                          # Regenerate poetry.lock

# Environment & Execution
poetry install                       # Install all dependencies
poetry shell                         # Enter virtual environment
poetry run python script.py          # Run in virtual environment
poetry run pytest                    # Run tests
poetry run mypy omega_kg/           # Type checking

# Version Management
poetry version                       # Show current version
poetry version minor                 # Bump minor version
poetry build                         # Build distribution packages
poetry publish                       # Publish to PyPI
```

### Dependency Security

**Always keep dependencies updated**:

```bash
# Check for outdated packages
poetry show --outdated

# Check for security vulnerabilities
poetry export --format requirements.txt | pip install safety
safety check -r /dev/stdin

# Update all dependencies to latest (within constraints)
poetry update

# Verify lock file is committed
git add poetry.lock
```

---

## Configuration Management (Pydantic)

### Why Pydantic BaseSettings?

Pydantic provides:

- **Type-safe configuration** (validated at startup)
- **Environment variable loading** (automatic, with defaults)
- **Schema validation** (catches config errors early)
- **Nested configurations** (complex hierarchical settings)
- **Custom validation** (business logic in code)

### Settings Pattern

```python
# omega_kg/settings.py
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App environment
    app_env: str = "development"  # Override with APP_ENV variable

    # Database
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "please-change-this-password"  # ⚠️ Change in .env

    # Optional configurations
    smtp_host: Optional[str] = "smtp.gmail.com"
    smtp_user: Optional[str] = None  # Set in .env if needed

    model_config = SettingsConfigDict(
        env_file=".env",              # Load from .env file
        env_file_encoding="utf-8",
        extra="ignore"                # Ignore unknown fields
    )

# Create singleton instance
settings = Settings()

# Usage in code
from omega_kg.settings import settings
driver = GraphDatabase.driver(settings.neo4j_uri, auth=...)
```

### Environment Variable Convention

**Use UPPER_SNAKE_CASE** for environment variables:

```bash
# .env file
APP_ENV=production
NEO4J_URI=bolt://neo4j-db:7687
NEO4J_PASSWORD=secure-password-here
SMTP_USER=email@gmail.com
LINEAR_API_KEY=lin_xxx_yyy_zzz
```

Pydantic automatically maps:

- `NEO4J_PASSWORD` → `settings.neo4j_password`
- `LINEAR_API_KEY` → `settings.linear_api_key`

### Validation

```python
def validate_settings() -> None:
    """Validate critical settings before application start."""
    if settings.app_env == "production":
        required_fields = ["neo4j_password", "obsidian_vault_path"]
        missing = []

        for field in required_fields:
            value = getattr(settings, field)
            if not value or value.startswith("please-change"):
                missing.append(field)

        if missing:
            raise ValueError(
                f"Production mode requires: {', '.join(missing)}"
            )

# Call on startup
if __name__ == "__main__":
    validate_settings()
    # ... start application
```

### .env File Template

Create `.env.example` with all possible variables (NO SECRETS):

```bash
# .env.example (commit to git)
APP_ENV=development
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=please-change-this-password
OBSIDIAN_VAULT_PATH=/path/to/vault
SMTP_HOST=smtp.gmail.com
SMTP_USER=your-email@gmail.com
LINEAR_API_KEY=your-linear-key
```

Then create `.env` locally (DO NOT commit):

```bash
# .env (git-ignored)
APP_ENV=production
NEO4J_PASSWORD=actual-production-password
LINEAR_API_KEY=actual-api-key-xxx
```

Add to `.gitignore`:

```bash
# .gitignore
.env
.env.local
.env.*.local
*.key
*.pem
secrets/
```

---

## Code Quality Tools

### Trunk - Unified Linter Manager

Trunk manages **all linters** in one tool, running them in parallel with smart caching.

#### Configuration (.trunk/trunk.yaml)

```yaml
version: 0.1
cli:
  version: 1.25.0
lint:
  enabled:
    # Configuration & documentation
    - git-diff-check # Git validation
    - prettier@3.4.2 # Code formatting
    - markdownlint@0.39.0 # Markdown linting
    - yamllint@1.35.1 # YAML validation


    # Note: Python tools via Poetry, not Trunk (Windows compatibility)
    # - ruff@0.8.2         # Use: poetry run ruff check
    # - mypy@1.14.1        # Use: poetry run mypy
```

#### Usage

```bash
# Check all modified files
trunk check

# Auto-fix all issues
trunk fmt

# Check specific file
trunk check path/to/file.py

# CI mode (uploads to dashboard)
trunk check --ci

# View existing issues
trunk check --show-existing

# Update tools to latest
trunk upgrade

# Login to Trunk Cloud dashboard
trunk login
```

#### Dashboard Access

- **URL**: <https://app.trunk.io>
- **Features**: Real-time results, trend analysis, PR integration
- **Benefits**: Historical tracking, team notifications, merge gates

### MyPy - Python Type Checking

Static type analysis for Python. Catches errors without running code.

#### Configuration (pyproject.toml)

```toml
[tool.mypy]
python_version = "3.12"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false      # Allow unannotated definitions
check_untyped_defs = true          # But still check them
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
explicit_package_bases = true
ignore_missing_imports = true      # For untyped dependencies
```

#### Usage

```bash
# Type check entire module
poetry run mypy omega_kg/

# Type check specific file
poetry run mypy omega_kg/settings.py

# Show all errors with context
poetry run mypy omega_kg/ --show-error-context

# Generate HTML report
poetry run mypy omega_kg/ --html report/
```

#### Type Annotations Best Practices

```python
# Good: Explicit type annotations
from typing import Optional, List, Dict

def fetch_tasks(user_id: int) -> List[Dict[str, str]]:
    """Fetch user tasks from database."""
    return db.query(f"SELECT * FROM tasks WHERE user_id = {user_id}")

# Good: Optional types
def get_config(key: str) -> Optional[str]:
    """Get configuration value, or None if not found."""
    return config.get(key)

# Good: Return type hints
async def process_webhook(payload: dict) -> bool:
    """Process webhook payload. Return True if successful."""
    ...

# Avoid: Missing type hints
def calculate(x, y):  # ❌ No types
    return x + y

# Avoid: Using 'Any' unnecessarily
def process_data(data: Any) -> Any:  # ❌ Defeats purpose
    ...
```

### Ruff - Fast Python Linter

Replaces flake8, pycodestyle, pyupgrade, and isort in a single tool.

#### Configuration (pyproject.toml)

```toml
[tool.ruff]
line-length = 79
target-version = "py312"

[tool.ruff.lint]
select = [
    "E",    # PyCodeStyle errors
    "W",    # PyCodeStyle warnings
    "F",    # Pyflakes
    "I",    # isort (imports)
    "B",    # flake8-bugbear
    "C4",   # flake8-comprehensions
    "UP",   # pyupgrade
]

[tool.ruff.lint.isort]
known-first-party = ["omega_kg"]
```

#### Usage

```bash
# Check code style
poetry run ruff check omega_kg/

# Auto-fix issues
poetry run ruff check omega_kg/ --fix

# Format imports
poetry run ruff check omega_kg/ --select I --fix

# Show specific violation
poetry run ruff check omega_kg/ --select E501  # Line too long
```

### Black - Code Formatter

Opinionated code formatting (installed but Trunk's prettier handles it).

```bash
# Format Python files
poetry run black omega_kg/

# Check without modifying
poetry run black omega_kg/ --check
```

---

## Git Hooks & Pre-Commit Checks

### Automated Quality Enforcement

Git hooks run **automatically before commits**, preventing low-quality code from entering the repository.

### Pre-Commit Hook (.git/hooks/pre-commit)

```bash
#!/bin/bash
# Pre-commit hook: Automated code quality checks

set -e

echo "🔍 Running pre-commit quality checks..."

# Run Trunk check on staged files
echo "→ Checking config files, docs, git validation..."
trunk check --index || {
    echo "❌ Trunk check failed"
    echo "Run: trunk fmt"
    exit 1
}

# Run Python linters on staged Python files
echo "→ Checking Python code quality..."

if git diff --cached --name-only --diff-filter=ACM | grep -q '\.py$'; then
    echo "  - Running Ruff..."
    poetry run ruff check omega_kg/ || {
        echo "❌ Ruff style check failed"
        echo "Run: poetry run ruff check omega_kg/ --fix"
        exit 1
    }

    echo "  - Running MyPy..."
    poetry run mypy omega_kg/settings.py omega_kg/lifecycle.py \
        omega_kg/linear_sync.py omega_kg/percolation.py || {
        echo "❌ MyPy type check failed"
        exit 1
    }
fi

echo "✅ All pre-commit checks passed!"
exit 0
```

### Commit Message Hook (.git/hooks/commit-msg)

```bash
#!/bin/bash
# Commit message validation

COMMIT_MSG_FILE=$1

# Minimum length check
COMMIT_MSG=$(cat "$COMMIT_MSG_FILE" | head -1)
if [ ${#COMMIT_MSG} -lt 10 ]; then
    echo "❌ Commit message too short (minimum 10 characters)"
    echo "Current: '$COMMIT_MSG'"
    exit 1
fi

# Conventional commit format recommendation
if ! echo "$COMMIT_MSG" | grep -qE '^(feat|fix|docs|style|refactor|perf|test|chore)(\(.+\))?!?: '; then
    echo "⚠️  Recommend conventional commit format:"
    echo "   feat(scope): description"
fi

exit 0
```

### Workflow Example

```bash
$ git commit -m "add caching"

🔍 Running pre-commit quality checks...
→ Checking config files, docs, git validation...
✓ Trunk passed
→ Checking Python code quality...
  - Running Ruff...
❌ Ruff style check failed
Run: poetry run ruff check omega_kg/ --fix

# Fix issues
$ poetry run ruff check omega_kg/ --fix

# Retry commit
$ git commit -m "add caching"
✅ All pre-commit checks passed!
[feature/add-caching abc1234] add caching
```

### Conventional Commit Format

Use consistent commit messages:

```bash
# Format: <type>(<scope>): <subject>

# Examples:
git commit -m "feat(neo4j): add relationship caching"
git commit -m "fix(settings): validate neo4j password"
git commit -m "docs(readme): update installation steps"
git commit -m "refactor(lifecycle): improve task state logic"
git commit -m "test: add neo4j driver tests"
git commit -m "chore: update dependencies"

# With body (for detailed commits)
git commit -m "feat(api): add webhook validation

- Validate webhook signatures
- Add rate limiting
- Log all requests

Closes #123"
```

**Types**:

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style (formatting, missing semicolons, etc.)
- `refactor`: Code refactoring without behavior change
- `perf`: Performance improvements
- `test`: Adding tests
- `chore`: Build process, dependencies, etc.

---

## Docker Containerization

### Multi-Stage Build Pattern

Reduces image size by separating build and runtime environments.

#### Dockerfile Structure

```dockerfile
# --- Stage 1: Builder ---
# Full image with build tools
FROM python:3.12-slim AS builder

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Copy only dependency files for better caching
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry config virtualenvs.in-project true && \
    poetry install --only main --no-root

# --- Stage 2: Runtime ---
# Clean, minimal image
FROM python:3.12-slim

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd --gid 1000 omega && \
    useradd --uid 1000 --gid omega --shell /bin/bash --create-home omega

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder --chown=omega:omega /app/.venv /app/.venv

# Copy application code
COPY --chown=omega:omega . .

# Set environment
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

# Switch to non-root user
USER omega

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8765/health')" || exit 1

# Default command
CMD ["python", "-m", "omega_kg.cli"]
```

### docker-compose.yml Pattern

```yaml
version: "3.8"

networks:
  apexsigma.net:
    driver: bridge
    name: apexsigma.net

volumes:
  neo4j-data:
    driver: local
    name: apexsigma.neo4j.data

services:
  # Neo4j Database
  neo4j-db:
    image: neo4j:5-community
    container_name: apexsigma.neo4j.db
    restart: unless-stopped
    ports:
      - "7474:7474" # HTTP
      - "7687:7687" # Bolt
    networks:
      - apexsigma.net
    volumes:
      - neo4j-data:/data
    environment:
      NEO4J_AUTH: ${NEO4J_USER}/${NEO4J_PASSWORD}
      NEO4J_dbms_memory_heap_initial__size: 512M
      NEO4J_dbms_memory_heap_max__size: 1G
    healthcheck:
      test: ["CMD", "bash", "-c", "cat < /dev/null > /dev/tcp/localhost/7687"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s

  # Application Service
  omega-kg:
    build: .
    container_name: apexsigma.omega.kg
    restart: "no"
    ports:
      - "8765:8765"
    networks:
      - apexsigma.net
    volumes:
      - "${OBSIDIAN_VAULT_PATH}:/vault:ro"
    env_file:
      - .env
    environment:
      NEO4J_URI: bolt://neo4j-db:7687
    depends_on:
      neo4j-db:
        condition: service_healthy
    profiles:
      - lifecycle
    healthcheck:
      test:
        - "CMD"
        - "python"
        - "-c"
        - >
          import urllib.request;
          urllib.request.urlopen('http://localhost:8765/health')
      interval: 30s
      timeout: 10s
      retries: 3
```

### Running Containers

```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d neo4j-db

# Run lifecycle service (on-demand)
docker-compose run --rm omega-kg

# View logs
docker-compose logs -f neo4j-db

# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

---

## CI/CD Pipeline

### GitHub Actions Workflow

Automated checks on every pull request.

#### .github/workflows/ci.yml

```yaml
name: Code Scanning, Linting, and Testing

on:
  pull_request:
    branches:
      - alpha

jobs:
  # Setup dependencies once, share across jobs
  setup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.14"
      - name: Cache Poetry dependencies
        uses: actions/cache@v4
        with:
          path: ~/.cache/pypoetry
          key: ${{ runner.os }}-poetry-${{ hashFiles('**/poetry.lock') }}
      - name: Install Poetry
        run: pip install poetry
      - name: Install dependencies
        run: poetry install --with dev

  # Code quality checks with Trunk
  trunk:
    needs: setup
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.14"
      - name: Install Poetry
        run: pip install poetry
      - name: Install dependencies
        run: poetry install --with dev
      - name: Install Trunk
        run: curl -fsSL https://get.trunk.io -o install-trunk.sh && bash install-trunk.sh
      - name: Run Trunk check
        run: trunk check --all
      - name: Run Trunk fmt
        run: trunk fmt --all --check

  # Security scanning
  semgrep:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Semgrep
        uses: returntocorp/semgrep-action@v1
        with:
          config: auto

  trivy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Trivy FS scan
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: fs
          format: sarif
          output: trivy-results.sarif
      - name: Upload Trivy results
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: trivy-results.sarif

  # Testing and coverage
  pytest:
    needs: setup
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.14"
      - name: Install Poetry
        run: pip install poetry
      - name: Restore Poetry cache
        uses: actions/cache@v4
        with:
          path: ~/.cache/pypoetry
          key: ${{ runner.os }}-poetry-${{ hashFiles('**/poetry.lock') }}
      - name: Install dependencies
        run: poetry install --with dev
      - name: Run Pytest
        run: poetry run pytest tests/ -v --cov=omega_kg --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
```

### Test Configuration (pyproject.toml)

```toml
[tool.pytest.ini_options]
minversion = "7.0"
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short --strict-markers --junitxml=junit.xml"
markers = [
    "unit: unit tests",
    "integration: integration tests",
    "slow: slow running tests",
]

[tool.coverage.run]
source = ["omega_kg"]
branch = true
omit = ["*/tests/*", "*/__pycache__/*"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
precision = 2
show_missing = true
skip_covered = false
```

---

## Secret Management

### Environment Variables Strategy

**Never** commit secrets to git. Use this pattern:

#### 1. Committed Files (Safe to share)

```bash
# .env.example (commit to git)
APP_ENV=development
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=please-change-this-password  # Placeholder only
SMTP_USER=your-email@gmail.com              # Placeholder only
LINEAR_API_KEY=your-linear-key              # Placeholder only
```

#### 2. Local Files (Never commit)

```bash
# .env (git-ignored)
# Create locally with actual secrets
APP_ENV=production
NEO4J_PASSWORD=actual-secure-password-here
LINEAR_API_KEY=actual-api-key-xxx
GITHUB_TOKEN=ghp_xxx_yyy_zzz
```

#### 3. .gitignore Configuration

```bash
# .gitignore (committed to git)
.env
.env.local
.env.*.local
.env.production.local
*.key
*.pem
secrets/
private/
.aws/credentials
.ssh/
```

### GitHub Secrets (For CI/CD)

Store secrets in GitHub for automated deployments:

1. Go to **Settings → Secrets and variables → Actions**
2. Click **New repository secret**
3. Add each secret:
   - `NEO4J_PASSWORD`
   - `LINEAR_API_KEY`
   - `GITHUB_TOKEN`
   - `DOCKER_REGISTRY_PASSWORD`

Then use in GitHub Actions:

```yaml
- name: Deploy
  env:
    NEO4J_PASSWORD: ${{ secrets.NEO4J_PASSWORD }}
    LINEAR_API_KEY: ${{ secrets.LINEAR_API_KEY }}
  run: |
    poetry run python deploy.py
```

### Best Practices

1. **Never log secrets**: Don't print API keys or passwords
2. **Rotate regularly**: Change passwords and API keys periodically
3. **Least privilege**: Use API keys with minimal required permissions
4. **Use `.env` locally**: Always set up `.env` for local development
5. **Verify on commit**: Pre-commit hook should catch hardcoded secrets

---

## Testing & Coverage

### Testing Strategy

```
Unit Tests (80%)          Integration Tests (15%)     E2E Tests (5%)
├─ Functions              ├─ Database operations      ├─ Full workflows
├─ Classes                ├─ API endpoints            ├─ External services
├─ Edge cases             ├─ File I/O
└─ Mocked dependencies    └─ Inter-service calls
```

### Pytest Structure

```
tests/
├─ __init__.py
├─ conftest.py              # Shared fixtures
├─ test_settings.py         # Unit tests
├─ test_lifecycle.py
├─ test_neo4j.py            # Integration tests
├─ test_api_endpoints.py
└─ fixtures/
   ├─ sample_data.json
   └─ mock_responses.py
```

### Writing Tests

```python
# tests/test_settings.py
import pytest
from omega_kg.settings import Settings, validate_settings

class TestSettingsLoading:
    """Test settings configuration loading."""

    def test_settings_load_from_env(self, monkeypatch):
        """Settings should load from environment variables."""
        monkeypatch.setenv("NEO4J_PASSWORD", "test-password")
        settings = Settings()
        assert settings.neo4j_password == "test-password"

    @pytest.mark.unit
    def test_settings_defaults(self):
        """Settings should have sensible defaults."""
        settings = Settings()
        assert settings.app_env == "development"
        assert settings.neo4j_uri.startswith("bolt://")

    @pytest.mark.unit
    def test_validate_settings_production(self, monkeypatch):
        """Production settings validation should catch missing values."""
        monkeypatch.setenv("APP_ENV", "production")
        with pytest.raises(ValueError) as exc_info:
            validate_settings()
        assert "neo4j_password" in str(exc_info.value)
```

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run specific test file
poetry run pytest tests/test_settings.py

# Run specific test
poetry run pytest tests/test_settings.py::TestSettingsLoading::test_settings_defaults

# Run with markers
poetry run pytest -m unit          # Unit tests only
poetry run pytest -m integration   # Integration tests only

# Run with coverage
poetry run pytest --cov=omega_kg --cov-report=html

# Run in watch mode (requires pytest-watch)
poetry run ptw
```

### Coverage Report

```bash
# Generate HTML coverage report
poetry run pytest --cov=omega_kg --cov-report=html

# View report
open htmlcov/index.html

# Target 80%+ coverage
poetry run pytest --cov=omega_kg --cov-fail-under=80
```

---

## Documentation

### MkDocs Setup

```toml
# pyproject.toml
[tool.poetry.group.docs.dependencies]
mkdocs = "^1.6.1"
mkdocs-material = "^9.6.22"
mkdocstrings = {extras = ["python"], version = "^0.30.1"}
```

### mkdocs.yml Configuration

```yaml
site_name: Omega_KG Documentation
site_url: https://omega-kg.apexsigma.dev
docs_dir: docs
site_dir: site
repo_url: https://github.com/ApexSigma-Solutions/Omega_KG

theme:
  name: material
  palette:
    scheme: slate
    primary: indigo
    accent: indigo
  features:
    - content.code.copy
    - navigation.instant
    - toc.follow

plugins:
  - search
  - mkdocstrings:
      handlers:
        python:
          options:
            show_source: true
            docstring_style: google

nav:
  - Home: index.md
  - Installation: installation.md
  - Configuration: configuration.md
  - API Reference: reference.md
  - Development: development.md
```

### Google-Style Docstrings (for mkdocstrings)

```python
def fetch_tasks(user_id: int, limit: int = 100) -> List[Dict]:
    """
    Fetch user tasks from the database.

    Retrieves a list of tasks assigned to the specified user,
    sorted by creation date in descending order.

    Args:
        user_id: The unique identifier of the user.
        limit: Maximum number of tasks to return (default 100).

    Returns:
        List of task dictionaries with keys: id, title, status, created_at

    Raises:
        ValueError: If user_id is negative or limit exceeds 1000.
        DatabaseError: If database connection fails.

    Example:
        >>> tasks = fetch_tasks(user_id=42, limit=50)
        >>> print(f"Found {len(tasks)} tasks")
        Found 42 tasks
    """
    if user_id < 0:
        raise ValueError("user_id must be non-negative")
    if limit > 1000:
        raise ValueError("limit cannot exceed 1000")

    return db.query(f"SELECT * FROM tasks WHERE user_id = {user_id} LIMIT {limit}")
```

### Building & Serving Docs

```bash
# Build static site
poetry run mkdocs build

# Serve locally (auto-reload on changes)
poetry run mkdocs serve

# Publish to GitHub Pages
poetry run mkdocs gh-deploy
```

---

## Workflow Examples

### Daily Development Workflow

```bash
# 1. Start your day
cd project-name
poetry shell              # Enter virtual environment
trunk check              # Verify code quality
poetry run pytest        # Run tests

# 2. Make changes
code omega_kg/module.py

# 3. Test locally
poetry run pytest tests/test_module.py

# 4. Check quality before commit
trunk check              # Checks config/docs/git
poetry run ruff check omega_kg/module.py
poetry run mypy omega_kg/module.py

# 5. Commit (hooks run automatically)
git add omega_kg/module.py
git commit -m "feat(module): add new functionality"

# Automatic checks run:
# ✓ Trunk check passed
# ✓ Ruff style check passed
# ✓ MyPy type check passed
# [feature/add-functionality abc1234] feat(module): add new functionality
```

### Adding a New Dependency

```bash
# 1. Research and verify the package
# Check: security, maintenance, documentation, popularity

# 2. Add dependency
poetry add package-name

# 3. Update lock file
poetry lock

# 4. Verify import works
poetry run python -c "import package_name; print(package_name.__version__)"

# 5. Commit
git add pyproject.toml poetry.lock
git commit -m "chore(deps): add package-name for feature X"
```

### Setting Up a New Project

```bash
# 1. Create repository
git clone https://github.com/ApexSigma-Solutions/new-project
cd new-project

# 2. Install toolchain
poetry install --with dev --with docs
trunk install

# 3. Verify setup
poetry run pytest
trunk check
poetry run mypy

# 4. Create .env
cp .env.example .env
# Edit .env with local values

# 5. Test hooks
git add .
git commit -m "initial: project scaffold"
```

### Preparing for Production Release

```bash
# 1. Update version
poetry version minor  # or major/patch

# 2. Update CHANGELOG
# Summarize changes since last release

# 3. Final checks
poetry run pytest --cov=project --cov-fail-under=80
trunk check --all
poetry run mypy project/

# 4. Build documentation
poetry run mkdocs build

# 5. Build package
poetry build

# 6. Tag release
git tag v0.2.0
git push origin v0.2.0

# 7. Publish (if using PyPI)
poetry publish
```

---

## Troubleshooting

### Common Issues

#### Poetry: "No module named poetry"

```bash
# Reinstall Poetry
curl -sSL https://install.python-poetry.org | python3 -
export PATH="$HOME/.local/bin:$PATH"
```

#### Git hooks not running

```bash
# Make hooks executable (Linux/macOS)
chmod +x .git/hooks/pre-commit
chmod +x .git/hooks/commit-msg

# Windows: Should work automatically
# If not, reinstall Trunk:
trunk install
```

#### Trunk check hangs on Windows

```bash
# Kill background processes
# Restart terminal or:
pkill -f trunk

# Update to latest
trunk upgrade
```

#### MyPy errors with untyped libraries

```python
# Add to ignore_errors for that library
# In pyproject.toml:
[tool.mypy]
ignore_missing_imports = true

# Or per-file:
# type: ignore
import untyped_library
```

#### Tests fail locally but pass in CI

```bash
# Ensure same Python version
poetry env info

# Reinstall exact lock file versions
poetry install --no-cache

# Clear cache
rm -rf .pytest_cache __pycache__
poetry cache clear . --all
```

---

## Appendix: Quick Reference

### Essential Commands

```bash
# Development
poetry install --with dev
poetry shell
poetry run pytest
trunk check
poetry run mypy omega_kg/

# Formatting
trunk fmt
poetry run ruff check --fix omega_kg/

# Committing
git add .
git commit -m "type(scope): description"

# Docker
docker-compose up -d
docker-compose logs -f

# Documentation
poetry run mkdocs serve
```

### File Checklist for New Projects

```
new-project/
├─ .github/workflows/
│  ├─ ci.yml              # GitHub Actions CI/CD
│  └─ mkdocs.yml          # Documentation deployment
├─ .trunk/
│  └─ trunk.yaml          # Trunk configuration
├─ .git/hooks/
│  ├─ pre-commit          # Auto-run linters
│  └─ commit-msg          # Validate messages
├─ .gitignore             # Exclude .env, __pycache__, etc.
├─ .env.example           # Template (commit to git)
├─ pyproject.toml         # Poetry + Tool configuration
├─ poetry.lock            # Dependency lock file
├─ dockerfile             # Multi-stage build
├─ docker-compose.yml     # Service orchestration
├─ mkdocs.yml             # Documentation config
├─ README.md              # Project overview
├─ docs/
│  ├─ index.md
│  ├─ installation.md
│  ├─ configuration.md
│  └─ reference.md
├─ tests/
│  ├─ conftest.py
│  ├─ test_*.py
│  └─ fixtures/
├─ src/ (or project_name/)
│  ├─ __init__.py
│  ├─ settings.py         # Pydantic settings
│  ├─ cli.py              # CLI entry point
│  └─ ...
└─ scripts/               # Utility scripts
   ├─ setup.sh            # Local setup
   └─ deploy.sh           # Deployment
```

---

## Document History

| Version | Date       | Author     | Changes                                  |
| ------- | ---------- | ---------- | ---------------------------------------- |
| 1.0     | 2025-10-28 | Sean Steyn | Initial comprehensive standards document |

---

**For questions or updates**: Contact the development team  
**Last reviewed**: October 28, 2025  
**Status**: Active and maintained
