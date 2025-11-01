import re
from pathlib import Path
from typing import List

from omega_kg.settings import Settings  # Imports your Pydantic class


def test_config_drift() -> None:
    """
    Ensures .env.example and Pydantic Settings are in sync.
    """
    # 1. Load all keys from the .env.example
    template_path = Path(".env.example")
    with open(template_path, "r", encoding="utf-8") as f:
        template_content = f.read()

    # 2. Use regex to find all variable names (e.g., "NEO4J_URI=")
    template_keys = set(
        re.findall(r"^\s*([A-Z_][A-Z0-9_]*)=", template_content, re.MULTILINE)
    )

    # 3. Load all keys from the Pydantic Settings model
    #    (Pydantic v2 uses .model_fields)
    settings_keys = set(Settings.model_fields.keys())

    # 4. Convert Pydantic keys to UPPER_SNAKE_CASE
    def to_env_var(key: str) -> str:
        # Convert camelCase to snake_case, then to upper
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', key)
        s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1)
        return s2.upper()

    settings_keys_upper = {to_env_var(s) for s in settings_keys}

    # 5. Compare the two sets
    missing_in_template = settings_keys_upper - template_keys
    missing_in_settings = template_keys - settings_keys_upper

    error_messages: List[str] = []
    if missing_in_template:
        error_messages.append(
            f"Keys in Settings but NOT in .env.example: "
            f"{missing_in_template}"
        )
    if missing_in_settings:
        error_messages.append(
            f"Keys in .env.example but NOT in Settings: "
            f"{missing_in_settings}"
        )

    if error_messages:
        error_text = "\n".join(error_messages)
        hint = (
            "Hint: Check both omega_kg/settings.py (Settings) and "
            ".env.example for mismatches."
        )
        assert False, f"\n\nConfig Drift Detected:\n{error_text}\n\n{hint}"