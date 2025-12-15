# PR Merge Checklist - Security & CI Fixes

## ✅ Completed Fixes

### 1. Security Remediation
- ✅ **Private Key Deleted**: `Omega_KG_Capture.pem` removed from working directory
- ✅ **Gitignore Updated**: Security patterns added to prevent future key commits
- ⚠️ **Git History Cleanup**: **REQUIRED** - Key still exists in Git history (see below)

### 2. CI Workflow Fix
- ⚠️ **Duplicate Step**: Still needs manual removal (lines 40-43 in `.github/workflows/ci.yml`)

### 3. Test Fixes
- ✅ **test_config_drift.py**: Added required env vars before Settings import
- ✅ **conftest.py**: Added `LINEAR_WEBHOOK_SECRET` to mock_env_vars fixture

### 4. Code Quality Fixes (from PR #81)
- ✅ Async correctness fixes (AsyncGraphDriver usage)
- ✅ Security hardening (path traversal, API key validation)
- ✅ Data fidelity (timestamp handling)
- ✅ Resource management (driver cleanup)
- ✅ Unicode filename handling
- ✅ Retry logic improvements

## 🔧 Manual Actions Required

### 1. Remove Duplicate CI Step (CRITICAL)
**File**: `.github/workflows/ci.yml`  
**Lines**: 40-43  
**Action**: Delete the duplicate "Run Pre-commit Hooks" step

```yaml
# DELETE THESE LINES (40-43):
      - name: Run Pre-commit Hooks (Ruff, Mypy, Bandit)
        uses: pre-commit/action@v3.0.1
        with:
          extra_args: --all-files
```

### 2. Verify .gitignore Security Patterns
**File**: `.gitignore`  
**Action**: Ensure these patterns are present at the end:

```
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
```

### 3. Git History Cleanup (CRITICAL - Do Before Merge)
The private key still exists in Git history. **DO NOT MERGE** until this is fixed:

```bash
# Option 1: Using git-filter-repo (Recommended)
pip install git-filter-repo
git filter-repo --path Omega_KG_Capture.pem --invert-paths
git push origin --force --all
git push origin --force --tags

# Option 2: Using git filter-branch (Legacy)
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch Omega_KG_Capture.pem" \
  --prune-empty --tag-name-filter cat -- --all
git push origin --force --all
git push origin --force --tags
```

**⚠️ WARNING**: This rewrites history. All collaborators must reclone.

### 4. Key Revocation (URGENT)
- [ ] Revoke `Omega_KG_Capture.pem` in all systems (cloud providers, servers, APIs)
- [ ] Generate new key using secrets management solution
- [ ] Deploy new key to production systems

## 📋 Pre-Merge Verification

Before merging, verify:

```bash
# 1. Check no .pem files exist
find . -name "*.pem" -not -path "./.git/*"

# 2. Verify CI workflow has no duplicates
grep -n "Run Pre-commit Hooks" .github/workflows/ci.yml
# Should show only ONE occurrence

# 3. Check gitignore has security patterns
tail -15 .gitignore | grep -E "\.pem|\.key|\.crt"

# 4. Verify tests pass
poetry run pytest tests/test_config_drift.py -v

# 5. Check git history (should return nothing after cleanup)
git log --all --full-history -- Omega_KG_Capture.pem
```

## 🚀 Merge Steps

1. **Complete Git History Cleanup** (see above)
2. **Remove Duplicate CI Step** (see above)
3. **Verify All Checks Pass** (see verification above)
4. **Revoke and Replace Key** (see above)
5. **Create PR or Merge to Target Branch**
6. **Notify Team** - All collaborators must reclone after history rewrite

## 📝 Files Modified

- `.github/workflows/ci.yml` - Remove duplicate step (manual)
- `.gitignore` - Add security patterns
- `tests/test_config_drift.py` - Fix Settings import
- `tests/conftest.py` - Add LINEAR_WEBHOOK_SECRET
- `omega_kg/capture_server.py` - Async fixes, security, resource management
- `omega_kg/workers/embedding_worker.py` - Async driver usage
- `omega_kg/auth_utils.py` - API key validation
- `omega_kg/domain/linear/graph_writer.py` - Timestamp handling
- `omega_kg/domain/common/embedding_service.py` - Retry logic
- `omega_kg/domain/linear/mapper.py` - Unicode handling
- `omega_kg/vault_utils.py` - File scanning efficiency

---

**Status**: Ready for merge after manual fixes above  
**Priority**: CRITICAL - Security issue must be resolved before merge
