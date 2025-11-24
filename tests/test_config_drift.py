"""
Configuration Drift Detection Test

This test ensures that all settings in omega_kg.settings.Settings 
match the .env.example file, preventing configuration drift.
"""

import os
import re
import pytest
from pathlib import Path
from omega_kg.settings import Settings


def parse_env_example() -> set[str]:
    """
    Parse .env.example and extract all non-comment, non-empty keys.
    
    Returns:
        Set of environment variable keys found in .env.example
    """
    env_example_path = Path(__file__).parent.parent / ".env.example"
    
    if not env_example_path.exists():
        pytest.fail(f".env.example not found at {env_example_path}")
    
    keys = set()
    with open(env_example_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            # Extract key before '=' sign
            if '=' in line:
                key = line.split('=')[0].strip()
                if key:
                    keys.add(key)
    
    return keys


def get_settings_fields() -> dict[str, str]:
    """
    Get all fields from Settings model with their validation_alias.
    
    Returns:
        Dict mapping field_name to validation_alias (or field_name if no alias)
    """
    field_mappings = {}
    for field_name, field_info in Settings.model_fields.items():
        # Get validation_alias if it exists, otherwise use field_name
        alias = field_info.validation_alias or field_name.upper()
        field_mappings[field_name] = alias
    
    return field_mappings


def get_exempted_keys() -> set[str]:
    """
    Get list of keys that are exempted from the drift check.
    These are typically Bitwarden mapping IDs that don't directly map to Settings fields.
    
    Returns:
        Set of exempted keys
    """
    return {
        'BWS_ACCESS_TOKEN',  # Bitwarden token, not a setting field
        'LINEAR_WEBHOOK_SECRET_ID',
        'POSTGRES_PASSWORD_ID',
        'NEO4J_PASSWORD_ID',
        'LINEAR_API_KEY_ID',
        'PERPLEXITY_API_KEY_ID',
        'GEMINI_API_KEY_ID',
        'NGROK_API_KEY_ID',
        'NANOGPT_DEV_API_KEY_ID',
        'EXTENSION_API_KEY_ID',
        'JWT_SECRET_KEY_ID',
    }


def test_settings_have_env_example_entries():
    """
    Verify all Settings fields have corresponding .env.example entries.
    """
    env_keys = parse_env_example()
    settings_fields = get_settings_fields()
    
    missing_in_env = []
    for field_name, alias in settings_fields.items():
        if alias not in env_keys:
            missing_in_env.append(f"{field_name} (expects {alias})")
    
    if missing_in_env:
        pytest.fail(
            f"Settings fields missing from .env.example:\n" +
            "\n".join(f"  - {item}" for item in missing_in_env) +
            "\n\nAdd these to .env.example to prevent configuration drift."
        )


def test_env_example_keys_exist_in_settings():
    """
    Verify all non-exempted .env.example keys exist in Settings.
    """
    env_keys = parse_env_example()
    settings_fields = get_settings_fields()
    exempted = get_exempted_keys()
    
    # Get all valid aliases from Settings
    valid_aliases = set(settings_fields.values())
    
    # Find keys in .env.example that are not in Settings and not exempted
    orphaned_keys = []
    for key in env_keys:
        if key not in valid_aliases and key not in exempted:
            orphaned_keys.append(key)
    
    if orphaned_keys:
        pytest.fail(
            f"Keys in .env.example not mapped to Settings fields:\n" +
            "\n".join(f"  - {key}" for key in orphaned_keys) +
            "\n\nEither add these to Settings or add to exemption list if they are Bitwarden mappings."
        )


def test_bitwarden_id_keys_are_exempted():
    """
    Verify all *_ID keys in .env.example are properly exempted.
    """
    env_keys = parse_env_example()
    exempted = get_exempted_keys()
    settings_fields = get_settings_fields()
    valid_aliases = set(settings_fields.values())
    
    # Find ID keys that are not exempted and not in settings
    id_keys = {key for key in env_keys if key.endswith('_ID')}
    unexempted_ids = []
    
    for key in id_keys:
        if key not in exempted and key not in valid_aliases:
            unexempted_ids.append(key)
    
    if unexempted_ids:
        pytest.fail(
            f"ID keys found that are not exempted:\n" +
            "\n".join(f"  - {key}" for key in unexempted_ids) +
            "\n\nAdd these to get_exempted_keys() in test_config_drift.py"
        )


def test_env_example_exists():
    """
    Sanity check: Verify .env.example file exists.
    """
    env_example_path = Path(__file__).parent.parent / ".env.example"
    assert env_example_path.exists(), f".env.example not found at {env_example_path}"


def test_settings_can_be_instantiated():
    """
    Verify Settings can be instantiated (catches Pydantic validation errors).
    """
    try:
        # This will use env vars or defaults
        Settings()
    except Exception as e:
        pytest.fail(f"Failed to instantiate Settings: {e}")
