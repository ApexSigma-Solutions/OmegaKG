# Bitwarden Secrets Manager Integration Guide

## Overview

Omega KG uses [Bitwarden Secrets Manager SDK](https://github.com/bitwarden/sdk-sm/tree/main/languages/python) for zero-trust secret management in production environments.

## How It Works

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Settings Loading Flow                     │
├─────────────────────────────────────────────────────────────┤
│  1. Load .env file (dotenv.load_dotenv(override=True))     │
│  2. Check ZERO_TRUST_REQUIRED environment variable          │
│  3. If true AND BWS_ACCESS_TOKEN exists:                    │
│     → Use BitwardenSettingsSource to fetch secrets          │
│  4. If false OR no BWS_ACCESS_TOKEN:                        │
│     → Use local .env values                                 │
└─────────────────────────────────────────────────────────────┘
```

### Hybrid Mode

The system supports **hybrid mode** - automatic fallback between Bitwarden and local secrets:

- **Production**: Use Bitwarden Secrets Manager (zero-trust)
- **Development**: Use local `.env` file values
- **CI/CD**: Can use either depending on configuration

## Development Setup (Current Configuration)

### Current State ✅

Your `.env` is configured for **development mode**:

```bash
# Development Mode Configuration
OMEGA_ENV=dev
APP_ENV=development
ZERO_TRUST_REQUIRED=false

# BWS_ACCESS_TOKEN is commented out (no Bitwarden in dev)
# BWS_ACCESS_TOKEN=<your-token-here>
```

This is the **correct** setup for local development.

## Production Setup

### Prerequisites

1. **Bitwarden Organization** with Secrets Manager enabled
2. **Machine Account** created in Bitwarden
3. **Access Token** generated for the machine account

### Step 1: Get Bitwarden Access Token

1. Log into your Bitwarden web vault
2. Navigate to **Organizations** → **Your Org** → **Secrets Manager**
3. Go to **Machine Accounts**
4. Create a new machine account (e.g., "omega-kg-production")
5. Generate an **Access Token** and save it securely

### Step 2: Create Secrets in Bitwarden

Create the following secrets in your Bitwarden Secrets Manager:

| Secret Name | Description | Example ID |
|-------------|-------------|------------|
| `LINEAR_WEBHOOK_SECRET_PRD` | Linear webhook signing secret | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `POSTGRES_PASSWORD_PRD` | PostgreSQL database password | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `NEO4J_PASSWORD_PRD` | Neo4j database password | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `EXTENSION_API_KEY_PRD` | Chrome extension API key | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `JWT_SECRET_KEY` | JWT token signing key | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `LINEAR_API_KEY_PRD` | Linear API key | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `PERPLEXITY_API_KEY_PRD` | Perplexity AI API key | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `GEMINI_API_KEY_PRD` | Google Gemini API key | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `NANOGPT_OMEGAKG_API_KEY` | NanoGPT API key | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `OLLAMA_OKG_API_KEY_PRD` | Ollama API key | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |

### Step 3: Configure `.env` for Production

```bash
# Production Mode Configuration
OMEGA_ENV=stable
APP_ENV=production
ZERO_TRUST_REQUIRED=true

# Bitwarden Access Token
BWS_ACCESS_TOKEN=<your-machine-account-token>

# Bitwarden Secret IDs (UUIDs from Bitwarden)
LINEAR_WEBHOOK_SECRET_PRD_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
POSTGRES_PASSWORD_PRD_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
NEO4J_PASSWORD_PRD_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
EXTENSION_API_KEY_PRD_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
JWT_SECRET_KEY_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
LINEAR_API_KEY_PRD_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
PERPLEXITY_API_KEY_PRD_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
GEMINI_API_KEY_PRD_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
NANOGPT_OMEGAKG_API_KEY=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
OLLAMA_OKG_API_KEY_PRD_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# Local fallback values (NOT USED in production when Bitwarden is active)
# These are ignored when BWS_ACCESS_TOKEN is set
NEO4J_PASSWORD=ignored_in_production
POSTGRES_PASSWORD=ignored_in_production
EXTENSION_API_KEY_PRD=ignored_in_production
JWT_SECRET_KEY=ignored_in_production
```

## How to Get Secret IDs from Bitwarden

### Option 1: Web UI
1. Log into Bitwarden web vault
2. Navigate to Secrets Manager → Secrets
3. Click on a secret
4. Copy the **Secret ID** (UUID format)

### Option 2: Using the SDK (Python)

```python
from bitwarden_sdk import BitwardenClient
from bitwarden_sdk.schemas import ClientSettings, DeviceType

# Initialize client
client = BitwardenClient(
    settings=ClientSettings(device_type=DeviceType.SDK)
)

# Login with access token
client.auth().login_access_token("your-access-token-here")

# List all secrets
secrets = client.secrets().list("your-organization-id")
for secret in secrets.data:
    print(f"{secret.key}: {secret.id}")
```

## Environment Variable Priority

The system loads configuration in this order (highest to lowest priority):

1. **Bitwarden Secrets** (if `BWS_ACCESS_TOKEN` is set)
2. **Environment Variables** (shell/system)
3. **`.env` file** (local configuration)
4. **Default Values** (in code)

## Testing Bitwarden Integration

### Test Script

Create `test_bitwarden.py`:

```python
#!/usr/bin/env python3
"""Test Bitwarden Secrets Manager integration"""

import os
from dotenv import load_dotenv
from bitwarden_sdk import BitwardenClient
from bitwarden_sdk.schemas import ClientSettings, DeviceType

load_dotenv()

# Get access token
access_token = os.getenv("BWS_ACCESS_TOKEN")
if not access_token:
    print("❌ BWS_ACCESS_TOKEN not set")
    exit(1)

print(f"✓ Access token found: {access_token[:20]}...")

# Initialize client
try:
    client = BitwardenClient(
        settings=ClientSettings(
            device_type=DeviceType.SDK,
            user_agent="OmegaKG-Test/1.0"
        )
    )
    print("✓ Client initialized")
    
    # Login
    client.auth().login_access_token(access_token)
    print("✓ Successfully authenticated with Bitwarden")
    
    # Test fetching a secret
    secret_id = os.getenv("NEO4J_PASSWORD_PRD_ID")
    if secret_id:
        import uuid
        response = client.secrets().get(uuid.UUID(secret_id))
        print(f"✓ Successfully fetched secret: {response.key}")
        print(f"  Value length: {len(response.value)} characters")
    else:
        print("⚠ NEO4J_PASSWORD_PRD_ID not set, skipping secret fetch test")
    
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)

print("\n✓ All tests passed!")
```

Run with:
```bash
poetry run python test_bitwarden.py
```

## Security Best Practices

### DO ✅

- Store `BWS_ACCESS_TOKEN` in environment variables or secure vaults
- Use different machine accounts for dev/staging/production
- Rotate access tokens regularly
- Set `ZERO_TRUST_REQUIRED=true` in production
- Use Bitwarden Secret IDs (UUIDs) in `.env`, not the actual secrets
- Keep `.env` file in `.gitignore`

### DON'T ❌

- Commit `BWS_ACCESS_TOKEN` to version control
- Share access tokens between environments
- Use development mode (`ZERO_TRUST_REQUIRED=false`) in production
- Store production secrets in `.env` file
- Hardcode secrets in code

## Troubleshooting

### Error: "BWS_ACCESS_TOKEN is required to enforce zero_trust secret loading"

**Cause**: `ZERO_TRUST_REQUIRED=true` but `BWS_ACCESS_TOKEN` is not set

**Solutions**:
1. **Development**: Set `ZERO_TRUST_REQUIRED=false` in `.env`
2. **Production**: Set valid `BWS_ACCESS_TOKEN` in environment

### Error: "Failed to fetch secret for key 'xxx' from Bitwarden"

**Causes**:
- Secret ID (UUID) is incorrect
- Machine account doesn't have access to the secret
- Secret doesn't exist in Bitwarden

**Solutions**:
1. Verify the secret exists in Bitwarden Secrets Manager
2. Check the Secret ID matches the UUID in `.env`
3. Ensure machine account has read access to the secret
4. Check organization ID is correct

### Settings load successfully but uses wrong values

**Cause**: Environment variable priority or caching

**Solutions**:
1. Clear Python cache: `Remove-Item -Recurse omega_kg/__pycache__`
2. Restart terminal/shell session
3. Check `dotenv.load_dotenv(override=True)` is at top of `settings.py`

## Current Configuration Summary

```
┌─────────────────────────────────────────────────┐
│         Your Current Setup (Development)         │
├─────────────────────────────────────────────────┤
│ Mode: Development                               │
│ ZERO_TRUST_REQUIRED: false                      │
│ BWS_ACCESS_TOKEN: Commented out (disabled)      │
│ Secret Source: Local .env file                  │
│ Status: ✅ Correctly configured for dev work    │
└─────────────────────────────────────────────────┘
```

## Switching Modes

### From Development → Production

1. Set `OMEGA_ENV=stable`
2. Set `APP_ENV=production`
3. Set `ZERO_TRUST_REQUIRED=true`
4. Uncomment and set `BWS_ACCESS_TOKEN`
5. Set all `*_PRD_ID` variables with Bitwarden secret UUIDs

### From Production → Development

1. Set `OMEGA_ENV=dev`
2. Set `APP_ENV=development`
3. Set `ZERO_TRUST_REQUIRED=false`
4. Comment out `BWS_ACCESS_TOKEN` (add `#` at start of line)
5. Ensure local secret values are set in `.env`

---

**Documentation Version**: 1.0.0  
**Last Updated**: 2025-12-16  
**Bitwarden SDK Version**: 1.0.0
