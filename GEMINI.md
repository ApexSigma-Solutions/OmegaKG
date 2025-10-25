# Omega_KG: AI Coding Agent Instructions

## Project Overview

This is a general-purpose Python project managed with Poetry. The main application logic resides in the `src/` directory.

## Project Architecture & Conventions

- **Single Python package**: All code is under `src/`. Main config is in `src/settings.py` using Pydantic `BaseSettings` for all environment/config management.
- **Environment variables**: Reference `.env.example` for required variables. Keep it in sync with `Settings` fields.
- **Dependency management**: Use Poetry (`pyproject.toml`).
  - For development: `poetry install --with dev`
  - For documentation: `poetry install --with docs`
- **Testing**: Tests are located under `tests/`. Use `pytest` for all testing.
- **Documentation**: Built with MkDocs Material (`mkdocs.yml`, `docs/`). API docs are auto-generated from code docstrings via `mkdocstrings`.

## Workflows & Tooling

- **Linting/Formatting**: Use Trunk (`trunk check`, `trunk fmt`, `trunk lint`) for all lint, format, and security checks. Trunk is installed via `install-trunk.sh` or CI. Black, Ruff, Flake8, and others are run via Trunk and pre-commit.
- **CI/CD**: GitHub Actions run Trunk, Semgrep, Trivy, Snyk, and pytest with coverage. See `.github/workflows/ci.yml` for details.
- **Pre-commit**: Enforced via `.pre-commit-config.yaml` (Black, Ruff, Flake8, Semgrep, Trivy, Snyk, ZAP, pytest, etc.).
- **MkDocs deploy**: Docs are deployed via GitHub Actions (`.github/workflows/mkdocs.yml`).

## Key Commands

- **Install dependencies**: `poetry install --with dev,docs`
- **Run tests**: `poetry run pytest`
- **Run linting and formatting**: `trunk check --all`, `trunk fmt --all`
- **Build documentation**: `mkdocs build`
- **Serve documentation locally**: `mkdocs serve`

## Patterns & Examples

- **Settings pattern**: All config must extend `src/settings.py:Settings` (Pydantic). Example usage:
  ```python
  from src.settings import Settings
  settings = Settings()
  print(settings.database_url)
  ```
- **Adding dependencies**: Use `poetry add <package>` and update `pyproject.toml`.
- **Adding environment variables**: Update both `src/settings.py` and `.env.example`.
- **Adding Tests**: Add new tests to the `tests/` directory.
- **Adding Docs**: Add docstrings to all public classes/functions for `mkdocstrings`.

## Key Files

- `src/settings.py`: Central config (Pydantic BaseSettings)
- `.env.example`: Reference for all required env vars
- `pyproject.toml`: Poetry config
- `.pre-commit-config.yaml`: Lint/test hooks
- `.trunk/trunk.yaml`: Trunk lint/format/check config
- `.github/workflows/ci.yml`: CI pipeline
- `docs/`, `mkdocs.yml`: Documentation
