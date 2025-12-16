# Pytest Configuration Guide

This document explains the improved pytest configuration and best practices for the Omega_KG project.

## Configuration Overview

The `pytest.ini` file has been enhanced with the following improvements:

### 1. Code Readability and Maintainability

- **Structured Organization**: Configuration is grouped by purpose with clear comments
- **Detailed Documentation**: Each section includes explanations and usage examples
- **Consistent Formatting**: Proper indentation and line breaks for readability
- **Self-Documenting**: Comments explain the purpose of each configuration option

### 2. Performance Optimization

- **Parallel Execution Support**: Configuration ready for `pytest-xdist` plugin
- **Test Timeout**: Prevents hanging tests with configurable timeouts
- **Selective Execution**: Markers allow running only necessary test subsets
- **Filter Warnings**: Reduces noise by filtering non-actionable warnings

### 3. Best Practices and Patterns

- **Strict Validation**: `--strict-markers` and `--strict-config` enforce discipline
- **Comprehensive Markers**: Categorized markers for different test types and dependencies
- **Environment Management**: Support for multiple environment files
- **Logging Configuration**: Structured logging for better debugging

### 4. Error Handling and Edge Cases

- **Warning Management**: Treats important warnings as errors
- **Coverage Integration**: Built-in support for coverage reporting
- **Timeout Protection**: Prevents tests from hanging indefinitely
- **Color Output**: Enhanced visibility of test results

## Usage Examples

### Running Different Test Categories

```bash
# Run only unit tests (fastest)
pytest -m "unit"

# Run integration tests (requires Neo4j)
pytest -m "integration"

# Run tests that don't require Neo4j
pytest -m "not_requires_neo4j"

# Run smoke tests (basic functionality)
pytest -m "smoke"

# Run performance tests
pytest -m "performance"

# Run security tests
pytest -m "security"
```

### Parallel Execution

```bash
# Auto-detect CPU cores
pytest -n auto

# Use specific number of workers
pytest -n 4

# Run with coverage
pytest --cov=omega_kg --cov-report=html -n 2
```

### Filtering and Selection

```bash
# Run tests matching pattern
pytest -k "test_capture"

# Exclude slow tests
pytest -m "not slow"

# Run specific test files
pytest tests/test_capture_server.py

# Run with verbose output
pytest -v
```

### Coverage Reporting

```bash
# Generate HTML coverage report
pytest --cov=omega_kg --cov-report=html

# Generate XML coverage for CI/CD
pytest --cov=omega_kg --cov-report=xml

# Fail if coverage below threshold
pytest --cov=omega_kg --cov-fail-under=80
```

## Test Markers Reference

### Categorization Markers
- `unit`: Isolated tests, no external dependencies
- `integration`: Tests requiring external services
- `slow`: Long-running tests

### Dependency Markers
- `requires_neo4j`: Needs Neo4j database connection
- `not_requires_neo4j`: No Neo4j dependency
- `requires_linear`: Requires Linear API integration
- `requires_obsidian`: Requires Obsidian vault access
- `requires_ollama`: Requires Ollama service

### Type Markers
- `smoke`: Basic functionality verification
- `regression`: Comprehensive coverage tests
- `performance`: Benchmarks and load tests
- `security`: Security compliance tests

### Workflow Markers
- `e2e`: End-to-end tests
- `mock`: Tests using mocked dependencies
- `live`: Tests requiring live services

## Development Workflow Integration

### Pre-commit Hooks

Add to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: pytest
        name: Run pytest
        entry: pytest -m "unit and not slow"
        language: system
        pass_filenames: false
        always_run: true
```

### CI/CD Pipeline

Example GitHub Actions workflow:

```yaml
name: Test
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      neo4j:
        image: neo4j:5
        env:
          NEO4J_AUTH: neo4j/test123
        ports:
          - 7687:7687

    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'

    - name: Install dependencies
      run: |
        pip install -e .
        pip install pytest pytest-cov pytest-xdist

    - name: Run unit tests
      run: pytest -m "unit" --cov=omega_kg

    - name: Run integration tests
      run: pytest -m "integration" --neo4j-uri="bolt://localhost:7687"
      env:
        NEO4J_USER: neo4j
        NEO4J_PASSWORD: test123
```

## Troubleshooting

### Common Issues

1. **Tests hanging**: Use `--timeout=300` to prevent indefinite hangs
2. **Memory issues**: Run with `-n 2` instead of `-n auto` on memory-constrained systems
3. **Database conflicts**: Use `--reuse-db` flag with pytest-django if applicable
4. **Coverage issues**: Ensure `__init__.py` files exist in all directories

### Debug Commands

```bash
# List all available markers
pytest --markers

# Show collected tests without running
pytest --collect-only

# Run with maximum verbosity
pytest -vvv --tb=long

# Run specific test with debugging
pytest -s -v tests/test_example.py::test_specific_function
```

## Best Practices

1. **Use Markers**: Always mark tests appropriately for selective execution
2. **Environment Isolation**: Use separate environment files for different test types
3. **Parallel Execution**: Leverage `pytest-xdist` for faster test runs in CI/CD
4. **Coverage Monitoring**: Maintain coverage thresholds and monitor trends
5. **Warning Management**: Address warnings early to prevent technical debt
6. **Timeout Configuration**: Set appropriate timeouts to prevent hanging tests
7. **Logging**: Use structured logging for better debugging in complex tests

## Plugin Recommendations

Install these plugins for enhanced functionality:

```bash
pip install pytest-xdist          # Parallel execution
pip install pytest-cov            # Coverage reporting
pip install pytest-timeout        # Test timeouts
pip install pytest-mock           # Enhanced mocking
pip install pytest-env            # Environment management
pip install pytest-benchmark      # Performance testing
```

## Migration Guide

If upgrading from the old configuration:

1. **Review Markers**: Update test files to use new marker names
2. **Environment Files**: Move test-specific env vars to `.env.test`
3. **CI/CD Updates**: Update pipeline configurations to use new markers
4. **Documentation**: Update team documentation with new commands
5. **Plugin Installation**: Install recommended plugins for full functionality
