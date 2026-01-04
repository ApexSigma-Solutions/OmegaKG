# Code Coverage Guide

This document explains how to use code coverage in the Omega_KG project.

## Overview

Code coverage helps us understand how much of our codebase is tested. The project uses **pytest-cov** for coverage reporting with multiple output formats.

## Quick Start

### Run All Tests with Coverage

```bash
poetry run pytest
```

This will automatically generate:
- Terminal report showing uncovered lines
- HTML report at `htmlcov/index.html`
- XML report at `coverage.xml` (for CI/CD)

### Coverage Thresholds

The project is configured with a **70% minimum coverage threshold**. Tests will fail if coverage falls below this threshold.

### View HTML Report

```bash
# Using the helper script
python scripts/coverage-report.py view

# Or manually
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

## Coverage Reports

### 1. Terminal Report

Shows coverage percentage and lists uncovered lines:

```
---------- coverage: platform win32, python 3.12.x.x ----------
Name                           Stmts   Miss  Cover   Missing
--------------------------------------------------------------
omega_kg/__init__.py             12      0   100%
omega_kg/auth_utils.py          143     12    92%   45, 67, 89-90, 102, 134, 147, 156, 174, 189
...
--------------------------------------------------------------
TOTAL                           3421    287    92%
```

### 2. HTML Report

Interactive report showing:
- Coverage percentage per file
- Highlighted source code with uncovered lines in red
- Clickable file tree navigation

View: `htmlcov/index.html`

### 3. XML Report

Machine-readable format for CI/CD:
- Location: `coverage.xml`
- Used by GitHub Actions, Jenkins, SonarQube, etc.

## Coverage Commands

### Using pytest Directly

```bash
# Full coverage with all reports
poetry run pytest --cov=omega_kg --cov-report=term-missing --cov-report=html

# Quick check (unit tests only, no integration tests)
poetry run pytest -m "not requires_neo4j" --cov=omega_kg --cov-report=term

# Coverage check only (fail if below threshold)
poetry run pytest --cov=omega_kg --cov-fail-under=70

# Coverage with specific output formats
poetry run pytest --cov=omega_kg --cov-report=json:coverage.json
poetry run pytest --cov=omega_kg --cov-report=xml:custom-coverage.xml
```

### Using Helper Script

We've created a convenient helper script:

```bash
# Quick coverage (unit tests only)
python scripts/coverage-report.py quick

# Full coverage with HTML report
python scripts/coverage-report.py full

# View HTML report in browser
python scripts/coverage-report.py view

# Compare with baseline
python scripts/coverage-report.py compare

# Minimal check (just threshold validation)
python scripts/coverage-report.py minimal
```

## Coverage Configuration

Coverage settings are in `pyproject.toml`:

### Run Configuration

```toml
[tool.coverage.run]
source = ["omega_kg"]      # Source code to measure
branch = true               # Enable branch coverage
omit = [
    "*/tests/*",            # Exclude test files
    "*/__pycache__/*",      # Exclude cache files
    "*/alembic/*",          # Exclude migrations
]
```

### Report Configuration

```toml
[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",      # Skip @pytest.mark.skip
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
precision = 2               # Decimal places
show_missing = true         # Show uncovered lines
skip_covered = false        # Don't skip files with 100% coverage
fail_under = 70             # Fail if below 70%
```

## Coverage Best Practices

### 1. Write Tests for New Features

When adding new code, write tests simultaneously:

```python
def test_new_feature():
    """Test the new feature."""
    result = my_new_function()
    assert result == expected
```

### 2. Use `@pytest.mark.skip` for Code You Don't Want to Cover

```python
# Example: Experimental code
@pytest.mark.skip(reason="Experimental feature")
def test_experimental():
    pass

# Or in production code:
if TYPE_CHECKING:
    # This is excluded automatically
    from typing import Optional
```

### 3. Check Coverage Before Committing

```bash
# Run quick coverage check
python scripts/coverage-report.py quick

# If below threshold, run full report to see what's missing
python scripts/coverage-report.py full
```

### 4. Focus on Critical Paths

Prioritize testing:
- User-facing features
- Business logic
- Error handling
- Edge cases

Less critical:
- Private helper functions (unless complex)
- Simple getters/setters
- Code marked with `pragma: no cover`

### 5. Review HTML Report

The HTML report is the best tool for finding gaps:

1. Open `htmlcov/index.html`
2. Click on files with low coverage
3. Red highlighting shows uncovered lines
4. Review and write tests for missing paths

## Branch Coverage

The project enables **branch coverage**, which checks if all branches of conditional statements are tested:

```python
# Example: Both branches should be tested
if user.is_admin:
    grant_permission()  # Should have test
else:
    deny_permission()   # Should have test
```

## Integration with CI/CD

The XML report can be used in CI/CD:

```yaml
# GitHub Actions example
- name: Run tests with coverage
  run: poetry run pytest --cov=omega_kg --cov-report=xml

- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
```

## Common Issues

### 1. "Coverage below threshold"

**Solution:** Write more tests or lower the threshold (not recommended)

```toml
[tool.coverage.report]
fail_under = 60  # Lower if needed
```

### 2. "Failed to generate HTML report"

**Solution:** Ensure the htmlcov directory exists and is writable

```bash
mkdir -p htmlcov
poetry run pytest --cov=omega_kg --cov-report=html
```

### 3. "Tests take too long with coverage"

**Solution:** Run only unit tests

```bash
poetry run pytest -m "not requires_neo4j" --cov=omega_kg
```

## Excluding Code from Coverage

### Method 1: `pragma: no cover` comment

```python
def experimental_function():  # pragma: no cover
    raise NotImplementedError("Experimental")
```

### Method 2: Configuration

Add patterns to `[tool.coverage.run].omit`:

```toml
[tool.coverage.run]
omit = [
    "*/migrations/*",           # Exclude database migrations
    "*/deprecated/*",          # Exclude deprecated modules
    "*/third_party/*",         # Exclude third-party code
]
```

### Method 3: `@skip` or `@xfail` markers

```python
@pytest.mark.skip(reason="Testing framework limitation")
def test_skip_this():
    pass

@pytest.mark.xfail(reason="Known issue")
def test_expected_failure():
    pass
```

## Coverage Goals

Current project goals:

- **Minimum threshold:** 70%
- **Target for new code:** 85%
- **Critical modules:** 95%+ (auth, lifecycle, sync)

## Useful Commands Reference

```bash
# Quick check (unit tests)
poetry run pytest -m "not requires_neo4j" --cov=omega_kg

# Full coverage with HTML
poetry run pytest --cov=omega_kg --cov-report=html

# View specific file coverage
poetry run pytest --cov=omega_kg.auth_utils --cov-report=term

# Coverage with diff coverage (only changed lines)
poetry run pytest --cov=omega_kg --cov-report=term-missing --cov-branch

# Run with debug output
poetry run pytest --cov=omega_kg --cov-report=term --cov-report=debug-out
```

## Resources

- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [Python Testing 101: Coverage](https://realpython.com/python-testing/#coverage)
