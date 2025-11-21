from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from functools import lru_cache
import sys
import traceback


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Fails fast if required secrets are missing.
    """

    # --- Pydantic Config (Moved to top as per best practice) ---
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- App Environment ---
    app_env: str = Field("development", validation_alias="APP_ENV")

    # --- Server Configuration ---
    # Default to localhost if not set
    app_host: str = Field("127.0.0.1", validation_alias="APP_HOST")
    # Default to 8000 (standard FastAPI) if not set
    app_port: int = Field(8000, validation_alias="APP_PORT")
    
    # --- Core Required Settings (Fail-fast) ---
    neo4j_uri: str = Field("bolt://localhost:7687", validation_alias="NEO4J_URI")
    neo4j_user: str = Field("neo4j", validation_alias="NEO4J_USER")
    neo4j_password: str = Field(
        ..., validation_alias="NEO4J_PASSWORD"  # <-- CHANGED: Now required
    )
    obsidian_vault_path: str = Field(
        ..., validation_alias="OBSIDIAN_VAULT_PATH"  # <-- CHANGED: Now required
    )

    # --- Security Settings (REQUIRED) ---
    extension_api_key: str = Field(
        ..., validation_alias="EXTENSION_API_KEY"
    )  # API key for browser extension authentication

    linear_webhook_secret: str = Field(
        ..., validation_alias="LINEAR_WEBHOOK_SECRET"
    )  # Secret for verifying Linear webhook payloads

    chrome_extension_id: str = Field(
        ..., validation_alias="CHROME_EXTENSION_ID"
    )  # Chrome extension ID for CORS configuration

    # --- JWT Authentication Settings (REQUIRED) ---
    jwt_secret_key: str = Field(
        ..., validation_alias="JWT_SECRET_KEY"
    )  # Secret key for signing JWT tokens
    jwt_algorithm: str = Field(
        "HS256", validation_alias="JWT_ALGORITHM"
    )  # Algorithm for JWT token signing
    jwt_expiration_minutes: int = Field(
        1440, validation_alias="JWT_EXPIRATION_MINUTES"
    )  # JWT token expiration time in minutes (default: 24 hours)

    # --- Optional Integrations ---

    # Email settings for lifecycle reports
    smtp_host: Optional[str] = Field("smtp.gmail.com", validation_alias="SMTP_HOST")
    smtp_port: int = Field(587, validation_alias="SMTP_PORT")
    smtp_user: Optional[str] = Field(None, validation_alias="SMTP_USER")
    smtp_password: Optional[str] = Field(None, validation_alias="SMTP_PASSWORD")
    email_to: Optional[str] = Field(None, validation_alias="EMAIL_TO")

    # Linear integration
    linear_api_key: Optional[str] = Field(None, validation_alias="LINEAR_API_KEY")
    linear_team_id: Optional[str] = Field(None, validation_alias="LINEAR_TEAM_ID")
    linear_workspace_id: Optional[str] = Field(
        None, validation_alias="LINEAR_WORKSPACE_ID"
    )
    linear_project_id: Optional[str] = Field(None, validation_alias="LINEAR_PROJECT_ID")
    
    # JSON maps for parsing
    linear_user_map_json: Optional[str] = Field(None, validation_alias="LINEAR_USER_MAP_JSON")
    linear_label_map_json: Optional[str] = Field(None, validation_alias="LINEAR_LABEL_MAP_JSON")
    linear_status_map_json: Optional[str] = Field(None, validation_alias="LINEAR_STATUS_MAP_JSON")

    # Keywords for decision extraction
    decision_keywords: List[str] = Field(
        default_factory=lambda: [
            "decided to",
            "will use",
            "going to",
            "plan is",
            "approach is",
            "solution is",
        ],
        validation_alias="DECISION_KEYWORDS",
    )

    # GitHub integration
    github_token: Optional[str] = Field(None, validation_alias="GITHUB_TOKEN")

    # AI/LLM API keys
    nanogpt_api_key: Optional[str] = Field(None, validation_alias="NANOGPT_API_KEY")
    openrouter_api_key: Optional[str] = Field(
        None, validation_alias="OPENROUTER_API_KEY"
    )
    perplexity_api_key: Optional[str] = Field(
        None, validation_alias="PERPLEXITY_API_KEY"
    )
    gemini_api_key: Optional[str] = Field(None, validation_alias="GEMINI_API_KEY")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Lazily load and cache Settings instance.
    This prevents import-time errors if env vars are missing.
    """
    try:
        settings_instance = Settings()
        # Validation is now handled by Pydantic's constructor
        return settings_instance
    except Exception as e:
        # --- CHANGED: Use traceback for richer error logging ---
        print(
            f"FATAL ERROR: Failed to load settings. {e} - settings.py:103",
            file=sys.stderr,
        )
        traceback.print_exc(file=sys.stderr)
        # Re-raise the exception to stop the application
        raise


# --- REMOVED: validate_settings() is no longer needed as fields are
# --- required by Pydantic, providing a cleaner fail-fast mechanism.

# Create the global settings instance using the lazy-loader.
# This ensures Settings() is only called once and is cached.
settings = get_settings()
