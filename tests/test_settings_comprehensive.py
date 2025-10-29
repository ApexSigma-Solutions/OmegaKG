"""
Comprehensive unit tests for omega_kg.settings module.

Tests cover:
- Settings class initialization
- Environment variable loading
- Default values
- Optional field handling
- Config model validation
- Integration with pydantic-settings
"""

import pytest
from unittest.mock import patch, MagicMock
from omega_kg.settings import Settings, settings


class TestSettingsInitialization:
    """Test Settings class initialization and defaults."""
    
    def test_settings_default_values(self):
        """Test that Settings has expected default values."""
        s = Settings()
        assert s.app_env == "development"
        assert s.neo4j_uri == "bolt://localhost:7687"
        assert s.neo4j_user == "neo4j"
        assert s.neo4j_password == "please-change-this-password"
        assert s.obsidian_vault_path == "/path/to/your/obsidian/vault"
    
    def test_settings_smtp_defaults(self):
        """Test SMTP default configuration."""
        s = Settings()
        assert s.smtp_host == "smtp.gmail.com"
        assert s.smtp_port == 587
        assert s.smtp_user is None
        assert s.smtp_password is None
        assert s.email_to is None
    
    def test_settings_linear_defaults(self):
        """Test Linear integration defaults are None."""
        s = Settings()
        assert s.linear_api_key is None
        assert s.linear_webhook_secret is None
        assert s.linear_team_id is None
        assert s.linear_workspace_id is None
        assert s.linear_project_id is None
    
    def test_settings_ai_api_defaults(self):
        """Test AI/LLM API key defaults are None."""
        s = Settings()
        assert s.nanogpt_api_key is None
        assert s.openrouter_api_key is None
        assert s.perplexity_api_key is None
        assert s.gemini_api_key is None
    
    def test_settings_github_default(self):
        """Test GitHub token default is None."""
        s = Settings()
        assert s.github_token is None


class TestSettingsEnvironmentVariables:
    """Test Settings loading from environment variables."""
    
    def test_settings_loads_from_env_neo4j(self, monkeypatch):
        """Test Neo4j settings load from environment."""
        monkeypatch.setenv("NEO4J_URI", "bolt://test-host:7687")
        monkeypatch.setenv("NEO4J_USER", "test_user")
        monkeypatch.setenv("NEO4J_PASSWORD", "test_password")
        
        s = Settings()
        assert s.neo4j_uri == "bolt://test-host:7687"
        assert s.neo4j_user == "test_user"
        assert s.neo4j_password == "test_password"
    
    def test_settings_loads_from_env_vault(self, monkeypatch):
        """Test Obsidian vault path loads from environment."""
        monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/custom/vault/path")
        
        s = Settings()
        assert s.obsidian_vault_path == "/custom/vault/path"
    
    def test_settings_loads_from_env_smtp(self, monkeypatch):
        """Test SMTP settings load from environment."""
        monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
        monkeypatch.setenv("SMTP_PORT", "465")
        monkeypatch.setenv("SMTP_USER", "user@example.com")
        monkeypatch.setenv("SMTP_PASSWORD", "smtp_pass")
        monkeypatch.setenv("EMAIL_TO", "recipient@example.com")
        
        s = Settings()
        assert s.smtp_host == "smtp.example.com"
        assert s.smtp_port == 465
        assert s.smtp_user == "user@example.com"
        assert s.smtp_password == "smtp_pass"
        assert s.email_to == "recipient@example.com"
    
    def test_settings_loads_from_env_linear(self, monkeypatch):
        """Test Linear integration settings load from environment."""
        monkeypatch.setenv("LINEAR_API_KEY", "lin_test_key")
        monkeypatch.setenv("LINEAR_WEBHOOK_SECRET", "webhook_secret")
        monkeypatch.setenv("LINEAR_TEAM_ID", "team_123")
        monkeypatch.setenv("LINEAR_WORKSPACE_ID", "workspace_456")
        monkeypatch.setenv("LINEAR_PROJECT_ID", "project_789")
        
        s = Settings()
        assert s.linear_api_key == "lin_test_key"
        assert s.linear_webhook_secret == "webhook_secret"
        assert s.linear_team_id == "team_123"
        assert s.linear_workspace_id == "workspace_456"
        assert s.linear_project_id == "project_789"
    
    def test_settings_loads_from_env_github(self, monkeypatch):
        """Test GitHub token loads from environment."""
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token")
        
        s = Settings()
        assert s.github_token == "ghp_test_token"
    
    def test_settings_loads_from_env_ai_keys(self, monkeypatch):
        """Test AI API keys load from environment."""
        monkeypatch.setenv("NANOGPT_API_KEY", "nano_key")
        monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter_key")
        monkeypatch.setenv("PERPLEXITY_API_KEY", "perplexity_key")
        monkeypatch.setenv("GEMINI_API_KEY", "gemini_key")
        
        s = Settings()
        assert s.nanogpt_api_key == "nano_key"
        assert s.openrouter_api_key == "openrouter_key"
        assert s.perplexity_api_key == "perplexity_key"
        assert s.gemini_api_key == "gemini_key"


class TestSettingsConfigModel:
    """Test Settings model configuration."""
    
    def test_settings_has_model_config(self):
        """Test that Settings has proper model_config."""
        s = Settings()
        assert hasattr(s, 'model_config')
    
    def test_settings_ignores_extra_fields(self, monkeypatch):
        """Test that extra environment variables are ignored."""
        monkeypatch.setenv("UNKNOWN_FIELD", "some_value")
        monkeypatch.setenv("RANDOM_CONFIG", "random")
        
        # Should not raise error
        s = Settings()
        assert not hasattr(s, 'unknown_field')
        assert not hasattr(s, 'random_config')


class TestSettingsIntegration:
    """Integration tests for Settings with pydantic."""
    
    def test_settings_can_be_serialized(self):
        """Test Settings can be dumped to dict."""
        s = Settings()
        data = s.model_dump()
        assert isinstance(data, dict)
        assert 'neo4j_uri' in data
        assert 'app_env' in data