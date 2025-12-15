# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Build & Test Commands
- Run single test with coverage: `poetry run pytest --cov=omega_kg tests/test_filename.py::test_function_name -v`
- Coverage threshold: 70% minimum enforced (pyproject.toml:95-108)

## Code Style Guidelines
- Type hints required for all functions (mypy configured with `check_untyped_defs = true`)
- Google-style docstrings with parameter descriptions
- Specific exception types for error handling
- Always use `encoding="utf-8"` for file operations

## Testing Requirements
- Test markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.requires_neo4j`
- Mock fixtures: `mock_env_vars`, `mock_neo4j_driver`, `task_lifecycle_mock` from conftest.py

## Critical Gotchas
- Settings validation fails fast on missing required env vars (settings.py:108-119)
- Dual persistence sync: Update both Neo4j and Obsidian frontmatter when updating tasks (lifecycle.py:318)
- Vector store initialization must be done before starting the worker (capture_server.py:66-71)
- Embedding worker must be started and stopped gracefully (capture_server.py:74-78, 102-106)