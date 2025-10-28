from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    WARNING: Sensitive default values are provided for development only and
    MUST be overridden in production via environment variables or a .env file.
    Sensitive fields: neo4j_password, smtp_password, smtp_user, email_to,
    linear_api_key, linear_webhook_secret, github_token, nanogpt_api_key,
    openrouter_api_key, perplexity_api_key, gemini_api_key

    app_env: Application environment. Allowed values: "development" or
    "production".
    """

    # App environment
    app_env: str = "development"

    # Neo4j connection
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "please-change-this-password"

    # Obsidian vault path
    obsidian_vault_path: str = "/path/to/your/obsidian/vault"

    # Email settings for lifecycle reports
    smtp_host: Optional[str] = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    email_to: Optional[str] = None

    # Linear integration
    linear_api_key: Optional[str] = None
    linear_webhook_secret: Optional[str] = None
    linear_team_id: Optional[str] = None
    linear_workspace_id: Optional[str] = None
    linear_project_id: Optional[str] = None

    # GitHub integration
    github_token: Optional[str] = None

    # AI/LLM API keys
    nanogpt_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    perplexity_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()


def validate_settings() -> None:
    """
    Validate critical settings for production use.

    Raises:
        ValueError: If required settings are missing in production mode.
    """
    if settings.app_env == "production":
        required_fields = [
            "neo4j_password",
            "obsidian_vault_path"
        ]

        missing = []
        for field in required_fields:
            value = getattr(settings, field)
            if (not value or
                    (isinstance(value, str) and
                     value.startswith("please-change"))):
                missing.append(field)

        if missing:
            raise ValueError(
                f"Missing required production settings: {', '.join(missing)}. "
                "Please configure these in your .env file."
            )
