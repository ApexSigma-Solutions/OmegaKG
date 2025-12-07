import re
from pathlib import Path
from typing import List

from omega_kg.settings import Settings  # Imports your Pydantic class


def get_settings_keys() -> set:
    """
    Returns the set of environment variable keys defined in the Settings class,
    using the validation_alias if defined, otherwise the field name.
    Supports Pydantic v2.
    """
    keys = set()
    for field_name, field_info in Settings.model_fields.items():
        # Get validation_alias if it exists, otherwise use field name
        if hasattr(field_info, "validation_alias") and field_info.validation_alias:
            keys.add(str(field_info.validation_alias).upper())
        else:
            keys.add(field_name.upper())
    return keys


def get_exempted_keys() -> set:
    """
    Get list of keys that are exempted from the drift check.
    These are typically Bitwarden mapping IDs that don't directly map to Settings fields.
    """
    return {
        # Bitwarden Secret IDs (not settings fields, used for secret injection)
        "BWS_ACCESS_TOKEN",
        "LINEAR_WEBHOOK_SECRET_PRD_ID",
        "POSTGRES_PASSWORD_PRD_ID",
        "NEO4J_PASSWORD_PRD_ID",
        "EXTENSION_API_KEY_PRD_ID",
        "LINEAR_API_KEY_PRD_ID",
        "PERPLEXITY_API_KEY_PRD_ID",
        "GEMINI_API_KEY_PRD_ID",
        "JWT_SECRET_KEY_ID",
        # Legacy Bitwarden IDs (may still exist in some .env.example files)
        "LINEAR_WEBHOOK_SECRET_ID",
        "POSTGRES_PASSWORD_ID",
        "NEO4J_PASSWORD_ID",
        "LINEAR_API_KEY_ID",
        "PERPLEXITY_API_KEY_ID",
        "GEMINI_API_KEY_ID",
        "NGROK_API_KEY_ID",
        "NANOGPT_DEV_API_KEY_ID",
        "EXTENSION_API_KEY_ID",
        # Optional parsing configs (not in Settings class)
        "LINEAR_USER_MAP_JSON",
        "LINEAR_LABEL_MAP_JSON",
    }


def test_config_drift() -> None:
    """
    Ensures .env.example and Pydantic Settings are in sync.
    Exempts Bitwarden ID keys and optional parsing configs.
    """
    template_path = Path(".env.example")
    with open(template_path, "r", encoding="utf-8") as f:
        template_content = f.read()

    # Use regex to find all variable names (e.g., "NEO4J_URI=")
    # This regex supports lowercase and mixed-case variable names.
    template_keys = set(
        re.findall(r"^\s*([A-Za-z_][A-Za-z0-9_]*)=", template_content, re.MULTILINE)
    )
    settings_keys = get_settings_keys()
    exempted_keys = get_exempted_keys()

    missing_in_template = settings_keys - template_keys
    missing_in_settings = (template_keys - settings_keys) - exempted_keys
    error_messages: List[str] = []

    if missing_in_template:
        error_messages.append(
            f"Keys in Settings but NOT in .env.example: {missing_in_template}"
        )
    if missing_in_settings:
        error_messages.append(
            f"Keys in .env.example but NOT in Settings (and not exempted): {missing_in_settings}"
        )

    if error_messages:
        error_text = "\n".join(error_messages)
        hint = "Hint: Check both omega_kg/settings.py (Settings) and .env.example for mismatches."
        assert False, f"Config Drift Detected:\n{error_text}\n\n{hint}"
