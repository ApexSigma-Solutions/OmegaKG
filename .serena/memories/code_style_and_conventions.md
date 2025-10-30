# Code Style & Conventions — Omega_KG

## Python Style
- **Formatter**: Black (configured in pyproject.toml)
- **Linter**: Ruff (configured in pyproject.toml)
- **Type checker**: MyPy (configured in pyproject.toml)
- **Line length**: Default Black (~88 chars)
- **Naming**: 
  - Classes: PascalCase (e.g., TaskLifecycle, Settings)
  - Functions/methods: snake_case (e.g., validate_settings, extract_messages)
  - Constants: UPPER_SNAKE_CASE
  - Private: Leading underscore (e.g., _internal_method)

## Type Hints
- All functions and methods should have type hints
- Use `from typing import ...` or built-in types (list, dict, etc. in Python 3.9+)
- Return types explicitly annotated

## Docstrings
- **Style**: Google-style docstrings (for mkdocstrings extraction)
- **Format**: 
  ```python
  def function_name(param1: str, param2: int) -> bool:
      """Short description on one line.
      
      Longer description if needed.
      
      Args:
          param1: Description of param1
          param2: Description of param2
      
      Returns:
          Description of return value
      
      Raises:
          ValueError: When something is invalid
      """
  ```

## Imports
- Organize: standard library → third-party → local imports
- One import per line for clarity
- Sort alphabetically (pre-commit will enforce via ruff)

## Neo4j Integration Pattern
```python
from omega_kg.settings import settings
from neo4j import GraphDatabase

driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))
with driver.session() as session:
    result = session.run("MATCH (n) RETURN n LIMIT 1")
```

## Configuration
- All config via `omega_kg/settings.py` (Pydantic BaseSettings)
- Environment variables from `.env` file (see `.env.example`)
- Access: `from omega_kg.settings import settings` then `settings.neo4j_uri`, etc.

## Testing
- Test files in `tests/` with `test_*.py` naming
- Markers: `@pytest.mark.unit`, `@pytest.mark.requires_neo4j`, `@pytest.mark.slow`
- Fixtures in `tests/conftest.py`
- Coverage target: >=80% (configured in pyproject.toml)

## Pre-commit Hooks
- `.pre-commit-config.yaml` defines checks: Ruff, MyPy, Bandit, etc.
- Run locally: `poetry run pre-commit run --all-files`
- Runs automatically on commit (after `poetry run pre-commit install`)

## Comment Style
- Use `#` for inline comments
- Use docstrings for function/class documentation
- Avoid commented-out code; use git history instead
