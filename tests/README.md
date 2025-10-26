# Omega_KG Test Suite

This directory contains comprehensive unit tests for the Omega_KG project, using pytest and pytest-cov for test execution and coverage analysis.

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── test_settings.py         # Settings module tests
├── test_lifecycle.py        # Task lifecycle enforcement tests
├── test_linear_sync.py      # Linear webhook sync tests
└── test_poc.py              # Proof-of-concept integration tests
```

## Running Tests

### Run all tests
```bash
poetry run pytest
```

### Run tests with coverage report
```bash
poetry run pytest --cov=omega_kg --cov-report=html
```

### Run specific test file
```bash
poetry run pytest tests/test_lifecycle.py -v
```

### Run tests matching pattern
```bash
poetry run pytest -k "test_task_status" -v
```

### Run with different report formats
```bash
# Terminal report
poetry run pytest --cov=omega_kg --cov-report=term-missing

# XML report (for CI/CD)
poetry run pytest --cov=omega_kg --cov-report=xml

# HTML report
poetry run pytest --cov=omega_kg --cov-report=html
```

## Test Categories

Tests are organized by functionality:

### Settings Tests (`test_settings.py`)
- Environment variable loading
- Default configuration values
- Settings singleton behavior

### Lifecycle Tests (`test_lifecycle.py`)
- TaskStatus enum validation
- LifecycleRule data structure
- TaskLifecycle enforcement logic
- Rule execution and state transitions

### Linear Sync Tests (`test_linear_sync.py`)
- LinearSync initialization
- Webhook payload handling
- Issue update synchronization
- Issue deletion handling

### POC Tests (`test_poc.py`)
- Neo4j connection verification
- Session management
- Cypher query execution
- Data ingestion

## Coverage Goals

Target coverage: **80%+** across all modules

- `omega_kg/settings.py`: 95%+
- `omega_kg/lifecycle.py`: 85%+
- `omega_kg/linear_sync.py`: 85%+
- `omega_kg/poc_okg.py`: 80%+

## Fixtures

Common test fixtures are defined in `conftest.py`:

- `mock_env_vars`: Mock environment variables
- `test_vault_path`: Temporary vault directory
- `mock_neo4j_driver`: Mock Neo4j driver
- `sample_task_data`: Sample task for testing
- `sample_lifecycle_rule_data`: Sample rule
- `sample_linear_webhook_payload`: Sample webhook
- `sample_chat_session_data`: Sample session

## Markers

Tests can be marked with categories:

```python
@pytest.mark.unit
def test_something():
    pass

@pytest.mark.integration
def test_database_sync():
    pass

@pytest.mark.slow
def test_heavy_computation():
    pass
```

Run marked tests:
```bash
poetry run pytest -m unit     # Only unit tests
poetry run pytest -m integration  # Only integration tests
poetry run pytest -m "not slow"   # Exclude slow tests
```

## Continuous Integration

Tests are automatically run in CI/CD pipeline on:
- Pull requests to `alpha` branch
- Commits to `alpha` branch

Coverage reports are uploaded to coverage tracking service.

## Best Practices

1. **Isolation**: Each test should be independent and not rely on others
2. **Mocking**: Use mocks for external dependencies (Neo4j, file system)
3. **Clarity**: Test names should describe what is being tested
4. **Coverage**: Aim for high coverage of critical paths
5. **Performance**: Keep unit tests fast (< 100ms per test)
6. **Documentation**: Add docstrings explaining complex test logic

## Adding New Tests

When adding new functionality:

1. Create test file: `tests/test_<module_name>.py`
2. Import fixtures from `conftest.py`
3. Write test classes/functions following pattern
4. Add appropriate markers
5. Run tests locally: `poetry run pytest -v`
6. Check coverage: `poetry run pytest --cov=omega_kg`

## Troubleshooting

### Tests not found
```bash
poetry run pytest --collect-only
```

### MyPy errors in tests
Tests may have looser type annotations than production code. This is acceptable for test fixtures.

### Mock not working
Ensure you're patching at the location where the object is *used*, not where it's defined.

```python
# Correct - patch where it's used
@patch("omega_kg.lifecycle.GraphDatabase.driver")

# Wrong - patch where it's defined
@patch("neo4j.GraphDatabase.driver")
```

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
- [unittest.mock documentation](https://docs.python.org/3/library/unittest.mock.html)
