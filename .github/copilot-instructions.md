# Omega_KG: AI Coding Agent Instructions

## Project Architecture & Conventions

- **Single Python package**: All code is under `src/`. Main config is in `src/settings.py` using Pydantic `BaseSettings` for all environment/config management.
- **Environment variables**: Reference `.env.example` for required variables. Keep it in sync with `Settings` fields.
- **Dependency management**: Use Poetry (`pyproject.toml`). Install with `poetry install --with dev` for development, `poetry install --with docs` for docs.
- **Testing**: Add new tests under `tests/` (directory exists but is empty). Use `pytest` for all testing.
- **Documentation**: Built with MkDocs Material (`mkdocs.yml`, `docs/`). API docs are auto-generated from code docstrings via mkdocstrings.

## Workflows & Tooling

- **Linting/Formatting**: Use Trunk (`trunk check`, `trunk fmt`, `trunk lint`) for all lint, format, and security checks. Trunk is installed via `install-trunk.sh` or CI. Black, Ruff, Flake8, and others are run via Trunk and pre-commit.
- **CI/CD**: GitHub Actions run Trunk, Semgrep, Trivy, Snyk, ZAP, and pytest with coverage. See `.github/workflows/ci.yml` for details.
- **Pre-commit**: Enforced via `.pre-commit-config.yaml` (Black, Ruff, Flake8, Semgrep, Trivy, Snyk, ZAP, pytest, etc.).
- **MkDocs deploy**: Docs are deployed via GitHub Actions (`.github/workflows/mkdocs.yml`).

## Patterns & Examples

- **Settings pattern**: All config must extend `src/settings.py:Settings` (Pydantic). Example usage:
  ```python
  from src.settings import Settings
  settings = Settings()
  print(settings.database_url)
  ```
- **Adding dependencies**: Use `poetry add <package>` and update `pyproject.toml`.
- **Adding environment variables**: Update both `src/settings.py` and `.env.example`.
- **Testing**: Add tests to `tests/`, run with `poetry run pytest`.
- **Docs**: Add docstrings to all public classes/functions for mkdocstrings.

## Key Files

- `src/settings.py`: Central config (Pydantic BaseSettings)
- `.env.example`: Reference for all required env vars
- `pyproject.toml`: Poetry config
- `.pre-commit-config.yaml`: Lint/test hooks
- `.trunk/trunk.yaml`: Trunk lint/format/check config
- `.github/workflows/ci.yml`: CI pipeline
- `docs/`, `mkdocs.yml`: Documentation

## AI Agent Guidance

- Always keep `.env.example` and `src/settings.py` in sync for env vars
- Use Trunk and pre-commit for all lint/format/security checks
- Prefer Poetry for all dependency management
- Follow the Pydantic settings/config pattern for all new config
- Add/maintain docstrings for API docs

---
