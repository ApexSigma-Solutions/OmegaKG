# Code Style & Conventions — Omega_KG

This document summarizes required code style, patterns, and developer conventions used across Omega_KG.

## General
- Use **Python 3.12+** and Poetry for dependency management.
- Format with **Black** and lint with **Ruff**.
- Type hints are required — `mypy` is enabled in CI with `check_untyped_defs=True`.
- Use `logger = logging.getLogger(__name__)` for module-level loggers.
- All file read/write operations use `encoding="utf-8"`.
- Keep imports ordered: standard library, third-party, local.

## Docstrings & Comments
- Docstrings follow the **Google-style** format (mkdocstrings expects this).
- Add inline comments for complex logic or unusual implementations.

## Error Handling
- Use specific exception types, e.g., `ServiceUnavailable`, `AuthError`, `ConnectionError` rather than broad `Exception`.

## Testing
- Tests are organized under `tests/` with markers including `unit`, `integration`, `requires_neo4j`, `requires_postgres`, `slow`, and `not_requires_neo4j`.
- Use `pytest-asyncio` for async tests when needed.
- Aim for ≥80% coverage for new features; overall coverage threshold 70% is enforced.
- For Neo4j-required tests, use mocks where possible and mark tests with `requires_neo4j`.

## Pre-commit
- Pre-commit hooks enforce formatting, linting, and basic checks before commits. Run `poetry run pre-commit run --all-files`.

## Branching & PRs
- Branch from `alpha` for feature work; open PR to `alpha`.
- Use `beta` for development integration branches.
- Tests and linters must pass before merging.

## Neo4j & Postgres
- Use `neo4j` driver version `>=6.0.2,<7.0.0` as specified in `pyproject.toml`.
- Ensure Neo4j schema changes are managed in `neo4j_schema.py` and tests cover migration points.

## Additional Project Guidelines
- Maintain dual persistence: update both Neo4j schema (graph nodes/relations) and Obsidian frontmatter for tasks.
- Follow `AGENTS.md` and `docs/` for CI, health checks and operational notes.
- Avoid committing `.env` or local secrets; use Bitwarden secret mappings or `.env.example` as template.

---
This memory is derived from `AGENTS.md`, `pyproject.toml`, and `README.md` and is intended to be a short, practical reference for new contributors.