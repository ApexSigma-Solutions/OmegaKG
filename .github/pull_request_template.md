## Description

<!-- Provide a brief description of the changes in this PR -->

## Type of Change

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Security fix
- [ ] Performance improvement
- [ ] Code refactoring

## Related Issues

<!-- Link to related issues using #issue_number -->

Fixes #
Related to #

## Changes Made

<!-- List the main changes made in this PR -->

-
-
-

## Testing

<!-- Describe the tests you ran to verify your changes -->

- [ ] Existing tests pass
- [ ] New tests added (if applicable)
- [ ] Manual testing completed

### Test Commands

```bash
poetry run pytest
poetry run ruff check .
poetry run mypy omega_kg/
```

## Security Checklist

**Please review our [Security Policy](../SECURITY.md) before submitting**

- [ ] No hardcoded credentials, API keys, or tokens
- [ ] No private keys or certificates (*.pem, *.key, *.crt)
- [ ] Sensitive configuration uses environment variables (not committed)
- [ ] Pre-commit hooks pass (`poetry run pre-commit run --all-files`)
- [ ] No sensitive data in logs or error messages
- [ ] Dependencies are up-to-date and vulnerability-free (`poetry run safety check`)
- [ ] Input validation on all user-supplied data
- [ ] Authentication and authorization properly implemented

## Documentation

- [ ] README updated (if needed)
- [ ] Documentation updated (if needed)
- [ ] AGENTS.md updated (if build/test commands changed)
- [ ] Comments added for complex logic

## Checklist

- [ ] My code follows the project's style guidelines
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] Any dependent changes have been merged and published

## Screenshots (if applicable)

<!-- Add screenshots to show UI changes or new features -->

## Additional Notes

<!-- Any additional information that reviewers should know -->
