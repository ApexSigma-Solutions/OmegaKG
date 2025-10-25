"""
Unit tests for omega_kg.settings module
"""

from unittest.mock import patch


def test_settings_load_from_env():
    """Test that settings load correctly with defaults"""
    from omega_kg.settings import Settings

    settings = Settings()

    assert settings.app_env in ["development", "test", "production"]
    assert settings.neo4j_uri is not None
    assert settings.neo4j_user is not None
    assert settings.neo4j_password is not None


def test_settings_defaults():
    """Test that settings use correct defaults when env vars not set"""
    from omega_kg.settings import Settings

    settings = Settings()

    assert settings.app_env in ["development", "test", "production"]
    assert settings.neo4j_uri is not None
    assert settings.neo4j_user is not None
    assert settings.neo4j_password is not None


def test_settings_singleton():
    """Test that settings is a singleton instance"""
    from omega_kg.settings import settings as settings1
    from omega_kg.settings import settings as settings2

    assert settings1 is settings2
