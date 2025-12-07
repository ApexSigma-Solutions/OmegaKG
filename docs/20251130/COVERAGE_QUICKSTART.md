# Coverage Quick Start Guide

Get up and running with code coverage in under 2 minutes!

## What Was Configured

✅ **pytest-cov** - Python coverage tool for pytest
✅ **Coverage reports** - Terminal, HTML, and XML formats
✅ **70% threshold** - Tests fail if coverage drops below 70%
✅ **VSCode integration** - Pre-configured launch configs and tasks
✅ **Helper scripts** - Convenient commands for common tasks
✅ **Documentation** - Comprehensive guides and references

## Quick Start (30 seconds)

### Option 1: Command Line (Recommended)

```bash
# Run tests with coverage
poetry run pytest

# View HTML report
open htmlcov/index.html
```

### Option 2: Using Helper Script

```bash
# Generate full report
python scripts/coverage-report.py full

# Open in browser
python scripts/coverage-report.py view
```

### Option 3: VSCode Run Panel

1. Press `Ctrl+Shift+D` (Run and Debug panel)
2. Select "**Pytest: Run all tests with coverage**"
3. Click the green play button ▶️
4. Open `htmlcov/index.html` to view report

## Coverage Reports Explained

### Terminal Report
Shows coverage percentage and missing lines:
```
Name                           Stmts   Miss  Cover   Missing
--------------------------------------------------------------
omega_kg/auth_utils.py          143     12    92%   45, 67, 89-90
omega_kg/lifecycle.py           185     15    92%   123-145
--------------------------------------------------------------
TOTAL                           3421    287    92%
```

### HTML Report (Best for Finding Gaps)
- Interactive file browser
- Click files to see coverage
- Red highlighting shows uncovered lines
- Click any file to see exactly what's missing

### XML Report (CI/CD)
- Machine-readable format
- Used by GitHub Actions, Jenkins, Codecov
- Generated at `coverage.xml`

## Common Commands

| Task | Command |
|------|---------|
| Run all tests | `poetry run pytest` |
| Run with coverage | `poetry run pytest --cov=omega_kg` |
| Quick unit test coverage | `python scripts/coverage-report.py quick` |
| Full coverage + HTML | `python scripts/coverage-report.py full` |
| View HTML report | `python scripts/coverage-report.py view` |
| Check threshold only | `python scripts/coverage-report.py minimal` |
| Run unit tests only | `poetry run pytest -m "not requires_neo4j"` |
| Format code | `poetry run black .` |
| Lint code | `poetry run ruff check .` |

## Coverage Goals

- **Minimum threshold**: 70% (enforced)
- **Target for new code**: 85%
- **Critical modules**: 95%+

## Understanding Coverage

### What 92% Coverage Means
- 92% of your code is executed by tests
- 8% is not covered (might be OK for error handling, etc.)
- Look at the "Missing" column to see which lines need tests

### Focus Areas (High Impact)
1. **Authentication** (`auth_utils.py`)
2. **Task lifecycle** (`lifecycle.py`)
3. **Core sync logic** (`percolation.py`, `obsidian_sync.py`)
4. **Business logic** - not just getters/setters

### What's NOT Critical
- Simple `__repr__` methods
- Raise `NotImplementedError` in stubs
- `if TYPE_CHECKING:` imports
- Mock-based unit tests (shows 0% but that's expected)

## Fixing Low Coverage

### Step 1: See What's Missing
```bash
python scripts/coverage-report.py full
open htmlcov/index.html
```

### Step 2: Find the Gaps
- Click on files with low coverage
- Red lines in HTML report are not covered
- Focus on critical business logic first

### Step 3: Write Tests
```python
def test_new_feature():
    """Test the new feature."""
    result = my_function()
    assert result == expected
```

### Step 4: Verify
```bash
python scripts/coverage-report.py quick
```

## VSCode Tips

### Running Tests
- **Run Panel** (`Ctrl+Shift+D`): Select launch config → Click play
- **Task Menu** (`Ctrl+Shift+P` → "Tasks: Run Task"): Pre-configured tasks
- **Test Explorer** (`Ctrl+Shift+,`): Browse and run individual tests
- **Terminal** (`` Ctrl+` ``): Any of the commands above

### Shortcuts
- `Ctrl+Shift+D`: Run and Debug panel
- `Ctrl+Shift+P`: Command palette
- `` Ctrl+` ``: Toggle terminal

### Auto-Format on Save
Configured in `.vscode/settings.json`:
- Formats with black
- Organizes imports
- Runs on every save

## Best Practices

### Before Writing Code
```bash
python scripts/coverage-report.py quick
```
Quick check shows current state before you add code

### After Adding Code
```bash
python scripts/coverage-report.py full
```
Generate full report to see exactly what's missing

### Before Committing
```bash
python scripts/coverage-report.py minimal
```
Check if coverage meets 70% threshold

### Regular Maintenance
- Run quick coverage weekly
- Review HTML report monthly
- Aim to increase coverage gradually
- Don't chase 100% at the expense of test quality

## Troubleshooting

### "No module named pytest"
**Solution**: VSCode not using Poetry's Python
- Restart VSCode (settings.json is configured)
- Or: `Ctrl+Shift+P` → "Python: Select Interpreter" → Choose Poetry environment

### "Coverage below threshold"
**Solution**: Write more tests
- Run `python scripts/coverage-report.py full`
- Open HTML report to see missing lines
- Focus on critical paths first

### "Tests pass but coverage is 0%"
**Normal**: Unit tests with mocked imports show 0% coverage
- This is expected behavior
- Integration tests (with `-m requires_neo4j`) show actual coverage
- Both types of tests are valuable

### Can't see test results
**Solution**: Check test output
- In Run panel, select "Debug Console" tab
- Or check integrated terminal output

## File Locations

### Configuration Files
- `pyproject.toml` - pytest and coverage configuration
- `.vscode/settings.json` - VSCode Python interpreter and settings
- `.vscode/launch.json` - Run configurations
- `.vscode/tasks.json` - Pre-configured tasks
- `.gitignore` - Coverage report files ignored

### Generated Files
- `htmlcov/index.html` - HTML coverage report
- `coverage.xml` - XML coverage report (for CI/CD)
- `.coverage` - Coverage data file

### Documentation
- `COVERAGE.md` - Comprehensive coverage guide
- `COVERAGE_VSCODE.md` - VSCode-specific instructions
- `CLAUDE.md` - Project overview and commands

## Next Steps

1. **Run a quick test**: `python scripts/coverage-report.py quick`
2. **View the HTML report**: `python scripts/coverage-report.py view`
3. **Explore uncovered code**: Click through files in the HTML report
4. **Write tests for gaps**: Focus on critical business logic
5. **Set up pre-commit**: Optional: Add coverage check to git hooks

## Need Help?

- 📖 **Comprehensive guide**: See `COVERAGE.md`
- 💻 **VSCode-specific help**: See `COVERAGE_VSCODE.md`
- 🔍 **Test marker info**: `poetry run pytest --markers`
- ❓ **Pytest help**: `poetry run pytest --help`

---

**Happy testing!** 🧪

Run `python scripts/coverage-report.py --help` for all available commands.
