# Security Policy

## Reporting Security Vulnerabilities

If you discover a security vulnerability in Omega_KG, please report it to us privately:

- **Email**: [security@apexsigma.solutions](mailto:security@apexsigma.solutions)
- **GitHub Security Advisories**: Use the [GitHub Security tab](https://github.com/ApexSigma-Solutions/omega_kg/security/advisories/new)

Please **do not** create public GitHub issues for security vulnerabilities.

### What to Include

- Description of the vulnerability
- Steps to reproduce the issue
- Potential impact
- Any suggested fixes (optional)

We aim to respond to security reports within 48 hours and will work with you to address the issue promptly.

---

## Security Best Practices

### 1. Private Keys and Certificates

**Never commit private keys, certificates, or credentials to the repository.**

Protected file patterns (automatically blocked by pre-commit hooks):
- `*.pem` - PEM-encoded certificates/keys
- `*.key` - Private key files
- `*.crt` - Certificate files
- `*.p12` / `*.pfx` - PKCS#12 keystores
- `*.jks` - Java keystores
- `*_rsa` / `*_dsa` / `*_ecdsa` / `*_ed25519` - SSH keys
- `id_rsa*` - SSH identity files
- `*.priv` - Private key files

### 2. Environment Variables and Secrets

- Use `.env` files for local development (never commit `.env` to git)
- Use `.env.example` as a template with placeholder values
- Store production secrets in secure secret management systems:
  - GitHub Secrets for CI/CD
  - Azure Key Vault / AWS Secrets Manager for cloud deployments
  - Bitwarden / 1Password for team secrets

### 3. API Keys and Tokens

- Rotate API keys regularly
- Use short-lived tokens where possible
- Implement proper authentication mechanisms (JWT, OAuth2)
- Never log API keys or tokens in application logs

### 4. Chrome Extension Security

The Chrome extension uses a private key (`Omega_KG_Capture.pem`) to maintain a consistent extension ID across versions. This key:

- **Must never be committed to version control**
- Should be stored securely in a password manager
- Must be revoked and regenerated if exposed
- Is used only for local extension packaging

**If the extension signing key is exposed:**
1. Immediately revoke access to any systems using the key
2. Remove the key from git history (see Git History Cleanup below)
3. Generate a new extension key
4. Update the extension ID in the capture server's CORS configuration
5. Notify all team members to update their local copies

### 5. Pre-commit Security Checks

We use `pre-commit` hooks to automatically detect security issues:

```bash
# Install pre-commit hooks
poetry run pre-commit install

# Run manually
poetry run pre-commit run --all-files
```

Security checks include:
- **detect-private-key**: Prevents committing private keys
- **bandit**: Python security linter
- **check-added-large-files**: Prevents large file commits
- **ruff**: Code quality and security patterns

---

## Git History Cleanup

If sensitive data is accidentally committed, follow these steps to remove it from git history:

### Using git-filter-repo (Recommended)

```bash
# Install git-filter-repo
pip install git-filter-repo

# Remove the sensitive file from all commits
git filter-repo --path path/to/sensitive/file.pem --invert-paths

# Force push to remote (WARNING: rewrites history)
git push origin --force --all
git push origin --force --tags
```

### Using BFG Repo-Cleaner (Alternative)

```bash
# Download BFG (https://rtyley.github.io/bfg-repo-cleaner/)
java -jar bfg.jar --delete-files sensitive-file.pem

# Clean up and force push
git reflog expire --expire=now --all
git gc --prune=now --aggressive
git push origin --force --all
```

### Post-Cleanup Steps

1. **Revoke the exposed secret** immediately
2. **Notify all collaborators** to re-clone or rebase
3. **Audit access logs** for any unauthorized use
4. **Update documentation** with incident details
5. **Generate new secrets** and redeploy

---

## Known Security Incidents

### 2024-12: Chrome Extension Private Key Exposure

**Severity**: High  
**Status**: Remediated  
**File**: `Omega_KG_Capture.pem`

#### What Happened

The Chrome extension signing key was accidentally committed to the repository, potentially exposing the extension's identity.

#### Actions Taken

1. ✅ File removed from working directory
2. ✅ Added to `.gitignore` to prevent future commits
3. ✅ Git history cleaned using `git-filter-repo`
4. ✅ Pre-commit hooks configured to detect private keys
5. ⚠️ Key revocation in progress (if applicable)
6. ⚠️ New key generation (if required)

#### Prevention Measures

- Enhanced `.gitignore` patterns for all sensitive file types
- `detect-private-key` pre-commit hook enabled
- Security documentation created (this file)
- Team training on secret management best practices

#### References

- [PR Merge Checklist](./PR_MERGE_CHECKLIST.md)
- [Pre-commit Configuration](./.pre-commit-config.yaml)

---

## Security Tools and Resources

### Static Analysis

- **Bandit**: Python security linter (integrated in pre-commit)
- **Safety**: Dependency vulnerability scanner
- **Trivy**: Container vulnerability scanner

### Dependency Scanning

```bash
# Check for vulnerable dependencies
poetry run safety check

# Update dependencies
poetry update
```

### Secret Scanning

- **git-secrets**: Prevents committing secrets (AWS-focused)
- **truffleHog**: Scans git history for secrets
- **gitleaks**: Detects hardcoded secrets

```bash
# Scan repository for secrets
docker run --rm -v $(pwd):/repo trufflesecurity/trufflehog:latest filesystem /repo
```

---

## Security Checklist for Contributors

Before submitting a PR:

- [ ] No hardcoded credentials, API keys, or tokens
- [ ] No private keys or certificates
- [ ] Sensitive configuration in `.env` (not committed)
- [ ] Pre-commit hooks pass (`poetry run pre-commit run --all-files`)
- [ ] Dependencies are up-to-date and vulnerability-free
- [ ] No sensitive data in logs or error messages
- [ ] Authentication and authorization properly implemented
- [ ] Input validation on all user-supplied data

---

## Supported Versions

We provide security updates for:

| Version | Supported          |
| ------- | ------------------ |
| 2.x     | ✅ Yes             |
| 1.x     | ⚠️ Limited support |
| < 1.0   | ❌ No              |

---

## Contact

For security concerns:
- **Email**: security@apexsigma.solutions
- **GitHub**: [Security Advisories](https://github.com/ApexSigma-Solutions/omega_kg/security/advisories)

For general questions:
- **Issues**: [GitHub Issues](https://github.com/ApexSigma-Solutions/omega_kg/issues)
- **Discussions**: [GitHub Discussions](https://github.com/ApexSigma-Solutions/omega_kg/discussions)
