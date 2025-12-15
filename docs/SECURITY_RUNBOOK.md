# Security Incident Runbook

Quick reference guide for handling security incidents in the Omega_KG repository.

---

## 🚨 Discovered a Leaked Secret?

### Immediate Actions (First 5 Minutes)

1. **DO NOT** push any more commits until the issue is resolved
2. **DO NOT** try to fix it by committing a deletion (the secret stays in history)
3. **DO** notify the team immediately
4. **DO** revoke/rotate the secret in any systems where it's used

---

## 📋 Secret Removal Checklist

### Step 1: Verify the Exposure

```bash
# Check if the file is in current directory
ls -la | grep -E "\.pem|\.key|\.env"

# Check if it exists in git history
git log --all --full-history -- path/to/secret/file

# Search for the secret content (if you know a unique string)
git log -S "secret-string-here" --source --all
```

### Step 2: Remove from Working Directory

```bash
# Remove the file
rm path/to/secret/file

# Add to .gitignore
echo "path/to/secret/file" >> .gitignore
echo "*.pem" >> .gitignore  # or appropriate pattern

# Commit the changes
git add .gitignore
git commit -m "chore(security): add sensitive files to gitignore"
```

### Step 3: Remove from Git History

```bash
# Install git-filter-repo (if not already installed)
pip install git-filter-repo

# IMPORTANT: Create a backup first!
git clone --mirror . ../repo-backup

# Remove the file from history
git filter-repo --path path/to/secret/file --invert-paths

# Or remove all files matching a pattern
git filter-repo --path-glob '*.pem' --invert-paths
```

### Step 4: Force Push (Coordinate with Team!)

```bash
# ⚠️ WARNING: This rewrites history - coordinate first!

# Push to remote
git push origin --force --all
git push origin --force --tags

# Notify all team members to re-clone or rebase
```

### Step 5: Team Re-sync

All team members must update their local clones:

```bash
# Option 1: Re-clone (safest)
cd ..
mv omega_kg omega_kg.old
git clone https://github.com/ApexSigma-Solutions/omega_kg.git

# Option 2: Reset existing clone
git fetch origin
git reset --hard origin/main  # or origin/beta
```

### Step 6: Revoke the Secret

- [ ] Rotate API keys
- [ ] Revoke certificates
- [ ] Change passwords
- [ ] Update CI/CD secrets
- [ ] Notify affected systems

---

## 🔍 Common Secret Types

### Private Keys (PEM files)

```bash
# Pattern: *.pem, *.key, *.crt
git filter-repo --path-glob '*.pem' --invert-paths
```

**Systems to check:**
- Chrome Web Store (extension keys)
- SSL/TLS certificates
- SSH keys
- API signing keys

### Environment Files (.env)

```bash
# Remove .env files (keep .env.example)
git filter-repo --path '.env' --invert-paths
```

**Systems to check:**
- Database credentials
- API keys
- Third-party service tokens
- OAuth secrets

### API Keys in Code

```bash
# Search for common patterns
git log -S "api_key" --source --all
git log -S "secret" --source --all
git log -S "password" --source --all

# Use git-filter-repo with callbacks for complex cases
```

**Systems to check:**
- Cloud providers (AWS, Azure, GCP)
- Third-party APIs
- Authentication services

---

## 🛡️ Prevention Measures

### 1. Enable Pre-commit Hooks

```bash
# Install pre-commit
poetry install --with dev

# Install hooks
poetry run pre-commit install

# Test hooks
poetry run pre-commit run --all-files
```

### 2. Update .gitignore

Add these patterns to `.gitignore`:

```gitignore
# Security - Private keys and certificates
*.pem
*.key
*.crt
*.p12
*.pfx
*.jks
*_rsa
*_dsa
*_ecdsa
*_ed25519
id_rsa*
*.priv

# Environment files
.env
.env.local
.env.*.local

# Secret management
secrets/
*.secret
```

### 3. Use Environment Variables

```python
# ✅ GOOD: Use environment variables
api_key = os.getenv("API_KEY")

# ❌ BAD: Hardcoded secrets
api_key = "sk-1234567890abcdef"
```

### 4. Regular Security Audits

```bash
# Scan for secrets in history
docker run --rm -v $(pwd):/repo trufflesecurity/trufflehog:latest filesystem /repo

# Check dependencies for vulnerabilities
poetry run safety check

# Run security linter
poetry run bandit -r omega_kg/
```

---

## 📞 Escalation

### Low Severity (Internal Development Keys)
- Fix immediately using the runbook
- Document in commit message
- Continue with normal workflow

### Medium Severity (API Keys, Tokens)
- **Stop all work** and assess impact
- Revoke/rotate keys immediately
- Follow full runbook process
- Notify team lead

### High Severity (Production Credentials, Private Keys)
- **Immediately** notify security team
- Revoke access in all systems
- Follow incident response plan
- Document in security incident report

---

## 🔗 Resources

- [SECURITY.md](../SECURITY.md) - Full security policy
- [SECURITY_INCIDENT_PEM.md](./SECURITY_INCIDENT_PEM.md) - PEM file incident details
- [git-filter-repo docs](https://github.com/newren/git-filter-repo)
- [Pre-commit hooks](../.pre-commit-config.yaml)

---

## ⚡ Quick Commands

```bash
# Check for secrets in current directory
find . -name "*.pem" -o -name "*.key" -o -name ".env"

# Check git history for a file
git log --all --full-history -- path/to/file

# Remove file from history (after backup!)
git filter-repo --path path/to/file --invert-paths

# Verify removal
git log --all --full-history -- path/to/file  # Should be empty

# Test pre-commit hooks
poetry run pre-commit run detect-private-key --all-files
```

---

## 📊 Post-Incident Checklist

After resolving an incident:

- [ ] Secret removed from working directory
- [ ] Secret removed from git history
- [ ] Secret revoked/rotated in all systems
- [ ] .gitignore updated
- [ ] Pre-commit hooks verified
- [ ] Team notified and re-synced
- [ ] Incident documented
- [ ] Prevention measures updated
- [ ] Lessons learned recorded

---

**Keep this runbook updated** as we learn from incidents and improve our processes.
