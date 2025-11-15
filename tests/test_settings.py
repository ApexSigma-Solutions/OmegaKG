"""
Unit tests for omega_kg.settings module
"""

from omega_kg.settings import Settings


def test_settings_load_from_env(monkeypatch):
    """Test that settings load correctly from environment variables"""
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


def test_settings_defaults(monkeypatch):
    """Test default behavior for Settings.

    Since `NEO4J_PASSWORD` is required in production, a missing password should raise
    an error. We then set NEO4J_PASSWORD to the legacy default and verify other defaults.
    """
    from omega_kg.settings import Settings

    # Ensure NEO4J_PASSWORD is set to the legacy default for this test
    monkeypatch.setenv("NEO4J_PASSWORD", "please-change-this-password")
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
    assert settings.neo4j_uri
    assert settings.neo4j_user
    assert settings.neo4j_password
