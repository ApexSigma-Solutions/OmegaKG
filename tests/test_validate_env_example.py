import sys
from pathlib import Path

from scripts.validate_env_example import parse_settings_for_env_vars, parse_env_example, compare


def test_validate_env_example_matches_settings():
    repo_root = Path(__file__).resolve().parent.parent
    settings_py = repo_root / "omega_kg" / "settings.py"
    env_example = repo_root / ".env.example"

    settings_map = parse_settings_for_env_vars(settings_py)
    env_keys = parse_env_example(env_example)

    missing_required, extra_keys = compare(settings_map, env_keys)

    assert missing_required == [], f"Missing required env vars: {missing_required}"
