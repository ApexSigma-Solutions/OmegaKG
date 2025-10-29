"""
Comprehensive unit tests for omega_kg.settings module covering edge cases and validation.
"""

import pytest
from pydantic import ValidationError
from omega_kg.settings import Settings


class TestSettingsEdgeCases:
    """Test edge cases and boundary conditions for Settings."""
    
    def test_settings_with_empty_strings(self, monkeypatch):
        """Test that empty strings are handled correctly."""
        monkeypatch.setenv("NEO4J_URI", "")
        monkeypatch.setenv("NEO4J_USER", "")
        
        settings = Settings()
        
        # Empty strings should be accepted (may be invalid but pydantic allows it)
        assert settings.neo4j_uri == ""
        assert settings.neo4j_user == ""
    
    def test_settings_optional_fields_none(self, monkeypatch):
        """Test that optional fields can be None."""
        # Clear optional fields
        for key in ["SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", 
                    "EMAIL_TO", "LINEAR_API_KEY"]:
            monkeypatch.delenv(key, raising=False)
        
        settings = Settings()
        
        # Optional fields should be None or have defaults
        assert settings.smtp_user is None or isinstance(settings.smtp_user, str)
        assert settings.email_to is None or isinstance(settings.email_to, str)
    
    def test_settings_with_special_characters_in_password(self, monkeypatch):
        """Test that passwords with special characters work correctly."""
        special_password = "P@ssw0rd!#$%^&*()_+-=[]{}|;:,.<>?"
        monkeypatch.setenv("NEO4J_PASSWORD", special_password)
        
        settings = Settings()
        
        assert settings.neo4j_password == special_password
    
    def test_settings_with_unicode_vault_path(self, monkeypatch):
        """Test that vault paths with unicode characters are handled."""
        unicode_path = "/path/to/测试/vault"
        monkeypatch.setenv("OBSIDIAN_VAULT_PATH", unicode_path)
        
        settings = Settings()
        
        assert settings.obsidian_vault_path == unicode_path
    
    def test_settings_smtp_port_as_integer(self, monkeypatch):
        """Test that SMTP port is correctly parsed as integer."""
        monkeypatch.setenv("SMTP_PORT", "465")
        
        settings = Settings()
        
        assert settings.smtp_port == 465
        assert isinstance(settings.smtp_port, int)
    
    def test_settings_environment_precedence(self, monkeypatch):
        """Test that environment variables take precedence over defaults."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("NEO4J_URI", "bolt://prod-server:7687")
        
        settings = Settings()
        
        assert settings.app_env == "production"
        assert settings.neo4j_uri == "bolt://prod-server:7687"
    
    def test_settings_multiple_instances_share_state(self, monkeypatch):
        """Test that multiple Settings instances reflect environment changes."""
        monkeypatch.setenv("APP_ENV", "test1")
        settings1 = Settings()
        
        monkeypatch.setenv("APP_ENV", "test2")
        settings2 = Settings()
        
        # Each instance should read from env at creation time
        assert settings1.app_env == "test1"
        assert settings2.app_env == "test2"
    
    def test_settings_case_sensitivity(self, monkeypatch):
        """Test that environment variable names are case-sensitive."""
        monkeypatch.setenv("neo4j_uri", "bolt://lowercase:7687")
        monkeypatch.setenv("NEO4J_URI", "bolt://uppercase:7687")
        
        settings = Settings()
        
        # Should use uppercase version (Pydantic convention)
        assert settings.neo4j_uri == "bolt://uppercase:7687"


class TestSettingsIntegration:
    """Test Settings integration with other components."""
    
    def test_settings_used_in_neo4j_driver_config(self, monkeypatch):
        """Test that settings provide valid Neo4j driver configuration."""
        monkeypatch.setenv("NEO4J_URI", "bolt://localhost:7687")
        monkeypatch.setenv("NEO4J_USER", "neo4j")
        monkeypatch.setenv("NEO4J_PASSWORD", "password")
        
        settings = Settings()
        
        # Verify all required driver params are present
        assert settings.neo4j_uri.startswith("bolt://")
        assert len(settings.neo4j_user) > 0
        assert len(settings.neo4j_password) > 0
    
    def test_settings_obsidian_vault_path_is_string(self, monkeypatch):
        """Test that vault path is always a string."""
        monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/home/user/vault")
        
        settings = Settings()
        
        assert isinstance(settings.obsidian_vault_path, str)
        assert settings.obsidian_vault_path == "/home/user/vault"
    
    def test_settings_email_configuration_complete(self, monkeypatch):
        """Test that all email settings can be configured together."""
        monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
        monkeypatch.setenv("SMTP_PORT", "587")
        monkeypatch.setenv("SMTP_USER", "user@example.com")
        monkeypatch.setenv("SMTP_PASSWORD", "secret")
        monkeypatch.setenv("EMAIL_TO", "recipient@example.com")
        
        settings = Settings()
        
        assert settings.smtp_host == "smtp.example.com"
        assert settings.smtp_port == 587
        assert settings.smtp_user == "user@example.com"
        assert settings.smtp_password == "secret"
        assert settings.email_to == "recipient@example.com"


class TestSettingsDocstringAccuracy:
    """Test that docstrings accurately describe behavior."""
    
    def test_settings_has_class_docstring(self):
        """Test that Settings class has a docstring."""
        assert Settings.__doc__ is not None
        assert "environment variables" in Settings.__doc__.lower()
    
    def test_settings_warns_about_sensitive_defaults(self):
        """Test that docstring warns about sensitive defaults."""
        assert "WARNING" in Settings.__doc__
        assert "sensitive" in Settings.__doc__.lower() or "production" in Settings.__doc__.lower()