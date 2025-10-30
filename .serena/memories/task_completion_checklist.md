# Task Completion Checklist — Omega_KG

When you complete a task or before opening a PR, ensure the following:

## Code Quality & Testing
- [ ] All new/modified Python code passes `poetry run mypy omega_kg/` (type check)
- [ ] No linting errors: `poetry run ruff check .` (passes without --fix)
- [ ] Code is formatted: `poetry run black omega_kg/ tests/` (or verified with Black)
- [ ] Existing tests still pass: `poetry run pytest -m "not requires_neo4j"` (fast tests)
- [ ] If touching Neo4j code, also run: `poetry run pytest -m requires_neo4j` (requires running Neo4j)
- [ ] Add/update tests for new functionality (aim for ≥80% coverage)
- [ ] Docstrings are updated (Google-style for mkdocstrings)

## Pre-commit & Git
- [ ] Run full pre-commit: `poetry run pre-commit run --all-files` (all checks pass)
- [ ] No `.env` secrets or local config committed (`.gitignore` covers `.env`)
- [ ] Commit message is clear & descriptive
- [ ] Branch is up-to-date with `origin/alpha`: `git pull origin alpha`

## Chrome Extension (if modified)
- [ ] Reload extension in Chrome (Extensions → Reload)
- [ ] Test on target sites (Gemini, ChatGPT, etc.)
- [ ] Check DevTools Console for errors
- [ ] Verify selectors match current DOM (if selectors were updated)
- [ ] `manifest.json` permissions are correct (host_permissions include target sites)

## Documentation
- [ ] README.md updated (if behavior changed)
- [ ] Code docstrings added/updated (Google-style)
- [ ] Complex logic has inline comments
- [ ] `docs/` updated if it's a significant feature

## Before Opening PR
1. Ensure local branch is up-to-date: `git fetch origin && git rebase origin/alpha`
2. Run complete check suite:
   ```powershell
   poetry run ruff check .
   poetry run mypy omega_kg/
   poetry run black omega_kg/ tests/ --check
   poetry run pytest
   poetry run pre-commit run --all-files
   ```
3. Push to remote: `git push origin feature/my-feature`
4. Open PR on GitHub with clear description of changes
5. Wait for CI to pass (GitHub Actions)

## For Lifecycle/Automation Tasks
- [ ] Test with `--dry-run` flag first (shows what would happen)
- [ ] Verify email config if notifications are involved
- [ ] Check Neo4j connection & schema before running live

## For Extension/Capture Tasks
- [ ] Test selector updates on real pages (Gemini, ChatGPT, etc.)
- [ ] Verify no "Access to storage is not allowed" errors (CSP issues)
- [ ] Confirm "messagesFound > 0" when capturing
- [ ] Test with capture-server running: `poetry run capture-server`
