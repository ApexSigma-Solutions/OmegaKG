# OmegaKG Release Management Guide

## 🚀 Overview

This document provides comprehensive guidance for managing OmegaKG releases, including automated workflows, security practices, and deployment procedures.

## 📋 Release Types

### Core Releases (`vX.Y.Z-core`)
- **Purpose**: Major stable releases with complete feature sets
- **Examples**: `v1.0.0-core`, `v1.1.0-core`
- **Validation**: Full MAR (Manual Approval Required) process
- **Security**: GPG signing mandatory

### Standard Releases (`vX.Y.Z`)
- **Purpose**: Feature updates and bug fixes
- **Examples**: `v1.0.1`, `v1.0.2`
- **Validation**: Automated validation with optional MAR
- **Security**: GPG signing recommended

### Pre-releases (`vX.Y.Z-alpha`, `vX.Y.Z-beta`, `vX.Y.Z-rcX`)
- **Purpose**: Testing and validation releases
- **Examples**: `v1.1.0-alpha`, `v1.1.0-beta`, `v1.1.0-rc1`
- **Validation**: Automated validation only
- **Security**: GPG signing optional

## 🔄 Release Workflow

### 1. Pre-Release Preparation
```bash
# Ensure working tree is clean
git status

# Create and push release tag
git tag -a v1.0.0-core -m "Release: OmegaKG Core v1.0.0"
git push origin v1.0.0-core
```

### 2. Automated Release Pipeline
The release pipeline is automatically triggered when:
- A tag matching `v*.*.*-core` or `v*.*.*` is pushed
- Manual dispatch via GitHub Actions with version parameter

**Pipeline Stages:**
1. **MAR Validation** - Manual approval for production releases
2. **Build & Test** - Multi-platform testing and quality checks
3. **Docker Build** - Container image creation and security scanning
4. **Release Creation** - GitHub release with artifacts
5. **Health Check** - Post-release validation
6. **OmegaKG Ingestion** - Metadata capture for audit trail

### 3. Manual Release Process
For releases requiring manual intervention:

```bash
# Trigger manual release
gh workflow run release.yml \
  --field version="v1.0.0-core" \
  --field prerelease=false \
  --field draft=false
```

## 🔐 Security Practices

### GPG Signing

#### Setup GPG Key
```bash
# Generate new GPG key (if needed)
gpg --full-generate-key

# List available keys
gpg --list-secret-keys --keyid-format LONG

# Configure Git to use your GPG key
git config --global user.signingkey [KEY_ID]
```

#### Sign Release Artifacts
```bash
# Use the automated signing script
./scripts/sign-release.sh v1.0.0-core [KEY_ID]

# Manual signing
git tag -s v1.0.0-core -m "Release: OmegaKG Core v1.0.0"
gpg --armor --detach-sign dist/omega_kg-1.0.0-py3-none-any.whl
```

#### Verify Signatures
```bash
# Verify tag signature
git tag -v v1.0.0-core

# Verify file signatures
gpg --verify omega_kg-1.0.0-py3-none-any.whl.asc
```

### Environment Variables for CI/CD

Set these secrets in your GitHub repository:

```yaml
# GPG Signing
GPG_PRIVATE_KEY: "-----BEGIN PGP PRIVATE KEY BLOCK-----..."
GPG_PASSPHRASE: "your-gpg-passphrase"

# Container Registry
GITHUB_TOKEN: "auto-provided"

# OmegaKG Integration
OMEGAKG_API_URL: "https://your-omegakg-instance.com"
OMEGAKG_API_KEY: "your-api-key"

# Code Coverage
CODECOV_TOKEN: "your-codecov-token"
```

## 🏗️ Release Artifacts

### Python Package
- **Format**: Wheel and source distribution
- **Location**: `dist/` directory
- **Upload**: GitHub Releases and PyPI (manual)

### Docker Images
- **Registry**: GitHub Container Registry (ghcr.io)
- **Tags**: 
  - `v1.0.0-core`
  - `sha-{commit-hash}`
  - `latest` (main branch only)
- **Platforms**: linux/amd64, linux/arm64

### Documentation
- **Release Notes**: Auto-generated from commit messages
- **Changelog**: Comprehensive feature documentation
- **Installation Guide**: Updated with each release

## 📊 Quality Gates

### Tier 1: Fast Feedback
- **Linting**: Ruff, MyPy, Bandit
- **Formatting**: Pre-commit hooks
- **Time Limit**: < 5 minutes

### Tier 2: Unit Testing
- **Coverage**: > 80% required
- **Async Tests**: Full test suite validation
- **Time Limit**: < 10 minutes

### Tier 3: Security Scanning
- **Secrets**: TruffleHog scanning
- **Vulnerabilities**: Trivy security scan
- **SAST**: Semgrep static analysis
- **Time Limit**: < 15 minutes

### Tier 4: Integration Testing
- **Database**: Neo4j integration tests
- **Linear Sync**: End-to-end validation
- **Extension**: Chrome extension testing
- **Time Limit**: < 30 minutes

## 🚨 Manual Approval (MAR)

### When MAR is Required
- Core releases (`v*.*.*-core`)
- Production deployments
- Security-sensitive changes
- First release of a major version

### MAR Approval Process
1. **Issue Creation**: Automated approval issue created
2. **Review Period**: Minimum 24 hours for review
3. **Approvers**: Designated team members
4. **Approval**: Comment with `/approve` or use GitHub interface
5. **Timeout**: Auto-reject after 7 days

### Approvers Configuration
```yaml
# .github/workflows/release.yml
approvers: 'sigmaDev11,apexsigma-admin'
minimum-approvals: 1
```

## 🏥 Health Monitoring

### Post-Release Health Checks
Automated validation includes:
- **Release Artifacts**: Verification of uploaded files
- **Docker Images**: Container registry availability
- **Security Scans**: Vulnerability assessment
- **Documentation**: Release notes and changelog validation

### Monitoring Setup
```yaml
# Health check endpoints
HEALTH_CHECK_URL: "https://api.github.com/repos/${{ github.repository }}/releases/tags/${{ version }}"

# Alerting
SLACK_WEBHOOK: "your-slack-webhook"
EMAIL_ALERTS: "release-team@apexsigma-solutions.com"
```

### Health Check Report
Generated reports include:
- Release status and artifact availability
- Security scan results
- Deployment validation
- Next steps and recommendations

## 🧠 OmegaKG Integration

### Metadata Capture
Each release automatically ingests:
- **Release Information**: Version, date, commit SHA
- **Validation Results**: Test results and quality metrics
- **Security Status**: Scan results and vulnerability assessment
- **Deployment Status**: Artifact availability and health checks

### Knowledge Graph Structure
```cypher
(:Release {version: "v1.0.0-core"})-[:CONTAINS]->(:Feature)
(:Release)-[:VALIDATED_BY]->(:TestSuite)
(:Release)-[:SECURED_BY]->(:SecurityScan)
(:Release)-[:DEPLOYED_AS]->(:Artifact)
```

### Audit Trail
Complete traceability includes:
- **Change History**: Commit lineage and authorship
- **Approval Records**: MAR approval workflow
- **Quality Metrics**: Test coverage and scan results
- **Deployment Records**: Artifact distribution and usage

## 📅 Release Schedule

### Core Releases
- **Frequency**: Quarterly (January, April, July, October)
- **Support**: 12 months from release date
- **LTS**: Every 4th core release (v1.0.0, v1.4.0, v1.8.0)

### Standard Releases
- **Frequency**: Monthly or as needed
- **Support**: 6 months from release date
- **Patch**: Critical security fixes only

### Pre-releases
- **Alpha**: Feature validation (2-4 weeks)
- **Beta**: Integration testing (1-2 weeks)
- **Release Candidate**: Final validation (3-7 days)

## 🔧 Release Tools

### Scripts Directory
```
scripts/
├── sign-release.sh          # GPG signing automation
├── graceful-shutdown.ps1    # Power failure protection
├── startup-with-recovery.ps1 # Database recovery
├── percolate-conversations.ps1 # Data processing
└── sync_linear.py          # Linear integration
```

### Configuration Files
```
.github/
├── workflows/
│   ├── ci.yml              # Continuous integration
│   ├── release.yml         # Release automation
│   └── mkdocs.yml          # Documentation building
├── .gpg-key                # Public key for verification
└── .release-template.md    # Release note template
```

## 🚀 Deployment Checklist

### Pre-Release
- [ ] All tests passing
- [ ] Security scans completed
- [ ] Documentation updated
- [ ] GPG key configured
- [ ] MAR approvers identified

### Release Creation
- [ ] Tag created and signed
- [ ] CI/CD pipeline triggered
- [ ] Manual approval obtained (if required)
- [ ] Artifacts built and uploaded
- [ ] Release published

### Post-Release
- [ ] Health checks completed
- [ ] Monitoring alerts configured
- [ ] Stakeholders notified
- [ ] Documentation published
- [ ] OmegaKG metadata ingested

## 📞 Support & Escalation

### Release Team
- **Primary**: sigmaDev11 (Lead Developer)
- **Secondary**: apexsigma-admin (DevOps Lead)
- **Escalation**: CTO Office (Critical issues only)

### Communication Channels
- **Slack**: #omega-release-alerts
- **Email**: release-team@apexsigma-solutions.com
- **Emergency**: +27 123 456 7890

### Issue Templates
```yaml
# Release Blocker
severity: critical
response-time: 15-minutes
escalation: immediate

# Release Delay
severity: high
response-time: 2-hours
escalation: 4-hours

# Release Information
severity: medium
response-time: 24-hours
escalation: 72-hours
```

## 📚 Additional Resources

- [OmegaKG Documentation](./README.md)
- [CI/CD Pipeline Guide](./docs/CI_CD_GUIDE.md)
- [Security Best Practices](./docs/SECURITY.md)
- [Troubleshooting Guide](./docs/TROUBLESHOOTING.md)
- [Contributing Guidelines](./docs/CONTRIBUTING.md)

---

**Last Updated**: November 29, 2025  
**Version**: v1.0.0-core  
**Maintainer**: OmegaKG Release Team