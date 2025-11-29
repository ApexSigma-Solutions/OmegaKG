import os
import uuid
from typing import Any, Dict, Tuple, Optional
from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)
from bitwarden_sdk import BitwardenClient, DeviceType


class BitwardenSettingsSource(PydanticBaseSettingsSource):
    """
    Hybrid Source: Inject secrets from Bitwarden if BWS_ACCESS_TOKEN is present.
    """

    def get_field_value(self, field: Any, field_name: str) -> Tuple[Any, str, bool]:
        return None, field_name, False

    def __call__(self) -> Dict[str, Any]:
        bws_token = os.getenv("BWS_ACCESS_TOKEN")
        if not bws_token:
            return {}

        fetched_secrets = {}
        try:
            # Standard SDK Pattern
            client = BitwardenClient(
                device_type=DeviceType.SDK, user_agent="OmegaKG/4.4.2"
            )
            client.auth.login_access_token(bws_token)

            # Map internal keys to Env Vars containing UUIDs
            secret_mappings = {
                "linear_webhook_secret": "LINEAR_WEBHOOK_SECRET_ID",
                "postgres_password": "POSTGRES_PASSWORD_ID",
                "neo4j_password": "NEO4J_PASSWORD_ID",
                "extension_api_key": "EXTENSION_API_KEY_ID",
                "linear_api_key": "LINEAR_API_KEY_ID",
                "perplexity_api_key": "PERPLEXITY_API_KEY_ID",
                "gemini_api_key": "GEMINI_API_KEY_ID",
                "nanogpt_api_key": "NANOGPT_DEV_API_KEY_ID",
                "jwt_secret_key": "JWT_SECRET_KEY_ID",
            }

            for config_key, env_var_id in secret_mappings.items():
                secret_uuid = os.getenv(env_var_id)
                if secret_uuid:
                    try:
                        response = client.secrets.get(uuid.UUID(secret_uuid))
                        fetched_secrets[config_key] = response.value
                    except Exception as e:
                        print(
                            f"WARN: Failed to fetch {config_key} (ID: {secret_uuid}): {e}"
                        )
        except Exception as e:
            print(f"CRITICAL: Bitwarden SDK Error: {e}")
            return {}

        return fetched_secrets


class Settings(BaseSettings):
    PROJECT_NAME: str = "Omega KG"
    VERSION: str = "4.4.2"

    # --- Server Settings ---
    app_env: str = Field("development", validation_alias="APP_ENV")
    app_host: str = Field("127.0.0.1", validation_alias="APP_HOST")
    app_port: int = Field(8005, validation_alias="APP_PORT")

    # --- Postgres Infrastructure (New) ---
    postgres_user: str = Field("omega_user", validation_alias="POSTGRES_USER")
    postgres_server: str = Field("127.0.0.1", validation_alias="POSTGRES_SERVER")
    postgres_port: int = Field(5433, validation_alias="POSTGRES_PORT")
    postgres_db: str = Field("omega_kg", validation_alias="POSTGRES_DB")
    postgres_password: str = Field(
        "omega_dev_password", validation_alias="POSTGRES_PASSWORD"
    )

    # --- Neo4j Infrastructure (Legacy) ---
    neo4j_uri: str = Field("bolt://localhost:7687", validation_alias="NEO4J_URI")
    neo4j_user: str = Field("neo4j", validation_alias="NEO4J_USER")
    neo4j_password: str = Field(..., validation_alias="NEO4J_PASSWORD")
    neo4j_heap_size: str = Field("512M", validation_alias="NEO4J_HEAP_SIZE")
    neo4j_host_data_path: str = Field(
        "./data/neo4j", validation_alias="NEO4J_HOST_DATA_PATH"
    )

    # --- Security & Auth (Legacy Restored) ---
    jwt_secret_key: str = Field(
        "legacy_fallback_secret", validation_alias="JWT_SECRET_KEY"
    )
    jwt_algorithm: str = Field("HS256", validation_alias="JWT_ALGORITHM")
    jwt_expiration_minutes: int = Field(60, validation_alias="JWT_EXPIRATION_MINUTES")
    chrome_extension_id: Optional[str] = Field(
        None, validation_alias="CHROME_EXTENSION_ID"
    )
    extension_api_key: Optional[str] = Field(None, validation_alias="EXTENSION_API_KEY")

    # --- Email/SMTP (Legacy Restored) ---
    smtp_host: Optional[str] = Field(None, validation_alias="SMTP_HOST")
    smtp_port: int = Field(587, validation_alias="SMTP_PORT")
    smtp_user: Optional[str] = Field(None, validation_alias="SMTP_USER")
    smtp_password: Optional[str] = Field(None, validation_alias="SMTP_PASSWORD")

    # --- Logic & Keywords (Legacy Restored) ---
    decision_keywords: str = Field(
        "decided to,chose to,agreed to", validation_alias="DECISION_KEYWORDS"
    )
    linear_status_map_json: str = Field("{}", validation_alias="LINEAR_STATUS_MAP_JSON")

    # --- Secrets & Keys ---
    linear_webhook_secret: str = Field(..., validation_alias="LINEAR_WEBHOOK_SECRET")

    # --- External Services ---
    linear_api_key: Optional[str] = Field(None, validation_alias="LINEAR_API_KEY")
    linear_team_id: Optional[str] = Field(None, validation_alias="LINEAR_TEAM_ID")
    linear_workspace_id: Optional[str] = Field(
        None, validation_alias="LINEAR_WORKSPACE_ID"
    )
    linear_project_id: Optional[str] = Field(None, validation_alias="LINEAR_PROJECT_ID")

    github_token: Optional[str] = Field(None, validation_alias="GITHUB_TOKEN")

    # --- AI Services ---
    nanogpt_api_key: Optional[str] = Field(None, validation_alias="NANOGPT_API_KEY")
    openrouter_api_key: Optional[str] = Field(
        None, validation_alias="OPENROUTER_API_KEY"
    )
    perplexity_api_key: Optional[str] = Field(
        None, validation_alias="PERPLEXITY_API_KEY"
    )
    gemini_api_key: Optional[str] = Field(None, validation_alias="GEMINI_API_KEY")

    # --- Paths ---
    obsidian_vault_path: str = Field("./vault", validation_alias="OBSIDIAN_VAULT_PATH")

    model_config = SettingsConfigDict(
        env_file=os.getenv("OMEGA_ENV_FILE", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_server}:{self.postgres_port}/{self.postgres_db}"

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            BitwardenSettingsSource(settings_cls),
            env_settings,
            dotenv_settings,
        )


settings = Settings()
