import re
from pathlib import Path

from omega_kg.settings import Settings  # Imports your Pydantic class


def get_settings_keys() -> set:
    """
    Returns the set of environment variable keys defined in the Settings class,
    supporting both Pydantic v1 and v2.
    """
    try:
        # Pydantic v1: __fields__ is a dict of FieldInfo
        return set(Settings.__fields__.keys())
    except AttributeError:
        # Pydantic v2: model_fields is a dict of FieldInfo
        return set(Settings.model_fields.keys())


def test_config_drift() -> None:
    """
    Ensures .env.example and Pydantic Settings are in sync.
    """
    template_path = Path(".env.example")
    with open(template_path, "r", encoding="utf-8") as f:
        template_content = f.read()

    # 2. Use regex to find all variable names (e.g., "NEO4J_URI=")
    # This regex now supports lowercase and mixed-case variable names.
    template_keys = set(
        re.findall(r"^\s*([A-Za-z_][A-Za-z0-9_]*)=", template_content, re.MULTILINE)
    )
    settings_keys = get_settings_keys()

    missing_in_template = settings_keys - template_keys
    missing_in_settings = template_keys - settings_keys
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
        hint = "Hint: Check both omega_kg/settings.py (Settings) and .env.example for mismatches."
        assert False, f"Config Drift Detected:\n{error_text}\n\n{hint}"