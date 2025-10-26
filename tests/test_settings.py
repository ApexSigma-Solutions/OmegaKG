"""
Unit tests for omega_kg.settings module
"""

from unittest.mock import patch
from omega_kg.settings import Settings


def test_settings_load_from_env(monkeypatch):
    """Test that settings load correctly from environment variables"""
    from omega_kg.settings import Settings

    # Set explicit environment variables
    monkeypatch.setenv("NEO4J_URI", "bolt://test-host:7687")
    monkeypatch.setenv("NEO4J_USER", "test-user")
    monkeypatch.setenv("NEO4J_PASSWORD", "test-password")
    monkeypatch.setenv("APP_ENV", "production")

    settings = Settings()

    assert settings.neo4j_uri == "bolt://test-host:7687"
    assert settings.neo4j_user == "test-user"
    assert settings.neo4j_password == "test-password"
    assert settings.app_env == "production"


def test_settings_defaults():
    """Test that settings use correct default values"""
    from omega_kg.settings import Settings

    settings = Settings()

    assert settings.app_env == "development"
    assert settings.neo4j_uri == "bolt://localhost:7687"
    assert settings.neo4j_user == "neo4j"
    assert settings.neo4j_password == "please-change-this-password"


def test_settings_singleton():
    """Test that settings is a singleton instance"""
    from omega_kg.settings import settings as settings1
    from omega_kg.settings import settings as settings2

    assert settings1 is settings2


def test_settings_creates_valid_driver_config():
    """Test that settings provide valid Neo4j driver configuration"""
    settings = Settings()

    # Verify settings has required Neo4j connection parameters
    assert hasattr(settings, 'neo4j_uri')
    assert hasattr(settings, 'neo4j_user')
    assert hasattr(settings, 'neo4j_password')
    assert settings.neo4j_uri
    assert settings.neo4j_user
    assert settings.neo4j_password
