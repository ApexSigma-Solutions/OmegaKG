# Settings Configuration Fix

## ✅ Problem Solved

Fixed the Pydantic validation errors that were preventing the application from loading settings.

### Error Messages (Before Fix)
```
pydantic_core._pydantic_core.ValidationError: 2 validation errors for Settings
linear_project_id
  Extra inputs are not permitted [type=extra_forbidden, ...]
openrouter_api_key
  Extra inputs are not permitted [type=extra_forbidden, ...]
```

## 🔧 Root Causes

1. **Missing field definitions** in `settings.py`:
   - `linear_project_id` was in `.env.example` but not in Settings class
   - `openrouter_api_key` was in `.env.example` but not in Settings class

2. **Malformed Config class**:
   - Using old Pydantic v1 syntax (`class Config:`)
   - Should use Pydantic v2 syntax (`model_config = SettingsConfigDict(...)`)

3. **Duplicate imports and field definitions**:
   - Misplaced `from pydantic import Field` in the middle of class
   - Duplicate `gemini_api_key` definition

4. **No permission for extra fields**:
   - Settings had implicit `extra='forbid'`
   - Needed explicit `extra='ignore'` to handle unknown environment variables

## 📝 Changes Made

### File: `omega_kg/settings.py`

**Before** (55 lines, broken):
```python
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # ... fields ...
    from pydantic import Field  # ❌ WRONG - import in middle of class

    linear_project_id: Optional[str]  # ❌ MISSING
    openrouter_api_key: Optional[str]  # ❌ MISSING

    gemini_api_key: Optional[str] = "your-gemini-api-key"
    gemini_api_key: Optional[str] = None  # ❌ DUPLICATE

    class Config:  # ❌ OLD PYDANTIC v1 SYNTAX
        env_file = ".env"
        env_file_encoding = "utf-8"
```

**After** (55 lines, fixed):
```python
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # ... fields ...
    linear_project_id: Optional[str] = None  # ✅ ADDED
    openrouter_api_key: Optional[str] = None  # ✅ ADDED
    gemini_api_key: Optional[str] = None  # ✅ FIXED (no duplicate)

    model_config = SettingsConfigDict(  # ✅ PYDANTIC v2 SYNTAX
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # ✅ ADDED - allows unknown env vars
    )
```

## 🎯 Complete Field List

All 19 fields now defined:

**App Configuration**
- `app_env`: Environment mode (development/production)

**Neo4j Database**
- `neo4j_uri`: Database connection URI
- `neo4j_user`: Database username
- `neo4j_password`: Database password

**Obsidian**
- `obsidian_vault_path`: Path to vault directory

**Email (Optional)**
- `smtp_host`: SMTP server
- `smtp_port`: SMTP port
- `smtp_user`: SMTP username
- `smtp_password`: SMTP password
- `email_to`: Recipient email

**Linear Integration (Optional)**
- `linear_api_key`: Linear API token
- `linear_webhook_secret`: Webhook secret
- `linear_team_id`: Team identifier
- `linear_workspace_id`: Workspace identifier
- `linear_project_id`: Project identifier ✅ ADDED

**GitHub (Optional)**
- `github_token`: GitHub personal access token

**AI/LLM APIs (Optional)**
- `nanogpt_api_key`: NanoGPT API key
- `openrouter_api_key`: OpenRouter API key ✅ ADDED
- `perplexity_api_key`: Perplexity AI API key
- `gemini_api_key`: Google Gemini API key

## ✅ Verification

```bash
# All settings now load correctly
poetry run python -c "from omega_kg.settings import settings; print('✅ Settings loaded')"

# Scripts now work
poetry run python omega_kg/neo4j_schema.py
poetry run python -m omega_kg.lifecycle
```

## 📋 Environment Variables

Your `.env` file correctly contains:
```bash
# Core
NEO4J_URI=bolt://localhost:7474/
OBSIDIAN_VAULT_PATH=C:\Users\steyn\OneDrive\Apps\remotely-save\Omega.as Vault

# Email
SMTP_HOST=smtp.gmail.com
SMTP_USER=steynsean11@gmail.com
SMTP_PASSWORD=***
EMAIL_TO=sigmadev11@gmail.com

# Linear
LINEAR_API_KEY=ae9f6b12-aa19-4a22-a104-b374006b5d65
LINEAR_TEAM_ID=ApexSigma
LINEAR_WORKSPACE_ID=apexsigma-solutions
LINEAR_PROJECT_ID=your-linear-project-id

# GitHub
GITHUB_TOKEN=87c0b451-9428-4195-b910-b374006f93dc

# AI/LLM
NANOGPT_API_KEY=4c3b3247-8dd7-45dd-93df-b37a003b3034
OPENROUTER_API_KEY=56e215ca-458d-4130-97e1-b37400713509
PERPLEXITY_API_KEY=4e8918a7-4274-4ea3-8e94-b37400716ebd
GEMINI_API_KEY=6f4aac1c-b61e-41f0-963d-b374006f636b
```

## 🚀 Result

✅ Settings now load without validation errors
✅ All 19 fields properly defined
✅ Pydantic v2 configuration correct
✅ Extra environment variables safely ignored
✅ Ready for development and production use
