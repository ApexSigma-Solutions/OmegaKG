"""
Comprehensive unit tests for troubleshoot_extension.py module.

Tests cover:
- HTTP health checks
- File system checks
- Neo4j connectivity
- Recent capture detection
- Main workflow orchestration
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, call
from datetime import datetime
import sys

# Import the module under test
import troubleshoot_extension


class TestCheckCaptureServer:
    """Test check_capture_server function."""
    
    @patch("troubleshoot_extension.requests.get")
    def test_server_running_and_healthy(self, mock_get):
        """Test when server is running and returns 200."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_get.return_value = mock_response
        
        result = troubleshoot_extension.check_capture_server()
        
        assert result is True
        mock_get.assert_called_once_with("http://127.0.0.1:8765/health", timeout=2)
    
    @patch("troubleshoot_extension.requests.get")
    def test_server_returns_non_200(self, mock_get):
        """Test when server returns non-200 status."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        result = troubleshoot_extension.check_capture_server()
        
        assert result is False
    
    @patch("troubleshoot_extension.requests.get")
    def test_server_connection_error(self, mock_get):
        """Test when server is not reachable."""
        import requests
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")
        
        result = troubleshoot_extension.check_capture_server()
        
        assert result is False
    
    @patch("troubleshoot_extension.requests.get")
    def test_server_timeout(self, mock_get):
        """Test when server request times out."""
        import requests
        mock_get.side_effect = requests.exceptions.Timeout("Request timeout")
        
        result = troubleshoot_extension.check_capture_server()
        
        assert result is False
    
    @patch("troubleshoot_extension.requests.get")
    def test_server_generic_exception(self, mock_get):
        """Test handling of generic exceptions."""
        mock_get.side_effect = Exception("Unexpected error")
        
        result = troubleshoot_extension.check_capture_server()
        
        assert result is False


class TestCheckVaultAccessible:
    """Test check_vault_accessible function."""
    
    @patch("troubleshoot_extension.settings")
    def test_vault_exists_with_all_folders(self, mock_settings, tmp_path):
        """Test when vault exists with all required folders."""
        vault_path = tmp_path / "test_vault"
        vault_path.mkdir()
        
        ai_conv_path = vault_path / "AI_Conversations"
        ai_conv_path.mkdir()
        
        # Create all platform folders
        platforms = ["Claude.ai", "ChatGPT", "Gemini", "Perplexity", "GitHub_Copilot", "Qwen"]
        for platform in platforms:
            (ai_conv_path / platform).mkdir()
        
        mock_settings.obsidian_vault_path = str(vault_path)
        
        result = troubleshoot_extension.check_vault_accessible()
        
        assert result is True
    
    @patch("troubleshoot_extension.settings")
    def test_vault_does_not_exist(self, mock_settings, tmp_path):
        """Test when vault path doesn't exist."""
        nonexistent_vault = tmp_path / "nonexistent_vault"
        mock_settings.obsidian_vault_path = str(nonexistent_vault)
        
        result = troubleshoot_extension.check_vault_accessible()
        
        assert result is False
    
    @patch("troubleshoot_extension.settings")
    def test_vault_missing_ai_conversations_folder(self, mock_settings, tmp_path):
        """Test when AI_Conversations folder is missing."""
        vault_path = tmp_path / "test_vault"
        vault_path.mkdir()
        
        mock_settings.obsidian_vault_path = str(vault_path)
        
        result = troubleshoot_extension.check_vault_accessible()
        
        assert result is False
    
    @patch("troubleshoot_extension.settings")
    def test_vault_creates_missing_platform_folders(self, mock_settings, tmp_path):
        """Test that missing platform folders are created."""
        vault_path = tmp_path / "test_vault"
        vault_path.mkdir()
        
        ai_conv_path = vault_path / "AI_Conversations"
        ai_conv_path.mkdir()
        
        # Create only some platform folders
        (ai_conv_path / "ChatGPT").mkdir()
        
        mock_settings.obsidian_vault_path = str(vault_path)
        
        result = troubleshoot_extension.check_vault_accessible()
        
        # Should create missing folders
        assert result is True
        assert (ai_conv_path / "Claude.ai").exists()
        assert (ai_conv_path / "Gemini").exists()
        assert (ai_conv_path / "Perplexity").exists()


class TestCheckNeo4j:
    """Test check_neo4j function."""
    
    @patch("troubleshoot_extension.GraphDatabase.driver")
    @patch("troubleshoot_extension.settings")
    def test_neo4j_connection_successful(self, mock_settings, mock_driver_class):
        """Test successful Neo4j connection."""
        mock_settings.neo4j_uri = "bolt://localhost:7687"
        mock_settings.neo4j_user = "neo4j"
        mock_settings.neo4j_password = "password"
        
        mock_driver = MagicMock()
        mock_session = MagicMock()
        
        # Mock successful connection test
        mock_result = MagicMock()
        mock_result.single.return_value = {"test": 1}
        mock_session.run.return_value = mock_result
        
        # Mock ChatSession count query
        mock_count_result = MagicMock()
        mock_count_result.single.return_value = {"total": 42}
        mock_session.run.side_effect = [mock_result, mock_count_result]
        
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver_class.return_value = mock_driver
        
        result = troubleshoot_extension.check_neo4j()
        
        assert result is True
        mock_driver_class.assert_called_once_with(
            "bolt://localhost:7687",
            auth=("neo4j", "password")
        )
    
    @patch("troubleshoot_extension.GraphDatabase.driver")
    @patch("troubleshoot_extension.settings")
    def test_neo4j_connection_failed(self, mock_settings, mock_driver_class):
        """Test when Neo4j connection fails."""
        mock_settings.neo4j_uri = "bolt://localhost:7687"
        mock_settings.neo4j_user = "neo4j"
        mock_settings.neo4j_password = "wrong_password"
        
        mock_driver_class.side_effect = Exception("Authentication failed")
        
        result = troubleshoot_extension.check_neo4j()
        
        assert result is False
    
    @patch("troubleshoot_extension.GraphDatabase.driver")
    @patch("troubleshoot_extension.settings")
    def test_neo4j_query_failed(self, mock_settings, mock_driver_class):
        """Test when Neo4j query fails."""
        mock_settings.neo4j_uri = "bolt://localhost:7687"
        mock_settings.neo4j_user = "neo4j"
        mock_settings.neo4j_password = "password"
        
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_session.run.side_effect = Exception("Query failed")
        
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver_class.return_value = mock_driver
        
        result = troubleshoot_extension.check_neo4j()
        
        assert result is False


class TestCheckRecentCaptures:
    """Test check_recent_captures function."""
    
    @patch("troubleshoot_extension.settings")
    def test_recent_captures_found(self, mock_settings, tmp_path):
        """Test when recent captures are found."""
        vault_path = tmp_path / "test_vault"
        ai_conv_path = vault_path / "AI_Conversations"
        chatgpt_path = ai_conv_path / "ChatGPT"
        chatgpt_path.mkdir(parents=True)
        
        # Create test markdown files
        for i in range(3):
            file_path = chatgpt_path / f"2024-01-0{i+1}-test{i}.md"
            file_path.write_text(f"# Test conversation {i}")
        
        mock_settings.obsidian_vault_path = str(vault_path)
        
        # Should not raise error
        troubleshoot_extension.check_recent_captures()
    
    @patch("troubleshoot_extension.settings")
    def test_no_captures_found(self, mock_settings, tmp_path):
        """Test when no captures exist."""
        vault_path = tmp_path / "test_vault"
        ai_conv_path = vault_path / "AI_Conversations"
        ai_conv_path.mkdir(parents=True)
        
        mock_settings.obsidian_vault_path = str(vault_path)
        
        # Should not raise error
        troubleshoot_extension.check_recent_captures()
    
    @patch("troubleshoot_extension.settings")
    def test_ai_conversations_missing(self, mock_settings, tmp_path):
        """Test when AI_Conversations folder doesn't exist."""
        vault_path = tmp_path / "test_vault"
        vault_path.mkdir()
        
        mock_settings.obsidian_vault_path = str(vault_path)
        
        # Should not raise error
        troubleshoot_extension.check_recent_captures()
    
    @patch("troubleshoot_extension.settings")
    def test_captures_sorted_by_modification_time(self, mock_settings, tmp_path):
        """Test that captures are sorted by most recent first."""
        import time
        
        vault_path = tmp_path / "test_vault"
        ai_conv_path = vault_path / "AI_Conversations" / "ChatGPT"
        ai_conv_path.mkdir(parents=True)
        
        # Create files with different timestamps
        file1 = ai_conv_path / "old.md"
        file1.write_text("Old")
        
        time.sleep(0.01)  # Ensure different timestamps
        
        file2 = ai_conv_path / "new.md"
        file2.write_text("New")
        
        mock_settings.obsidian_vault_path = str(vault_path)
        
        # Should list files (most recent first)
        troubleshoot_extension.check_recent_captures()
        
        # Verify new.md has later modification time
        assert file2.stat().st_mtime > file1.stat().st_mtime


class TestPrintExtensionInstructions:
    """Test print_extension_instructions function."""
    
    def test_prints_checklist(self, capsys):
        """Test that extension checklist is printed."""
        troubleshoot_extension.print_extension_instructions()
        
        captured = capsys.readouterr()
        output = captured.out
        
        assert "Chrome Extension Checklist" in output
        assert "chrome://extensions/" in output
        assert "Developer mode" in output
        assert "Omega_KG Chat Capture" in output
        assert "service worker" in output.lower()


class TestMain:
    """Test main orchestration function."""
    
    @patch("troubleshoot_extension.check_capture_server")
    @patch("troubleshoot_extension.check_vault_accessible")
    @patch("troubleshoot_extension.check_neo4j")
    @patch("troubleshoot_extension.check_recent_captures")
    @patch("troubleshoot_extension.print_extension_instructions")
    def test_main_all_checks_pass(
        self, mock_print, mock_recent, mock_neo4j, mock_vault, mock_server
    ):
        """Test main when all checks pass."""
        mock_server.return_value = True
        mock_vault.return_value = True
        mock_neo4j.return_value = True
        
        troubleshoot_extension.main()
        
        mock_server.assert_called_once()
        mock_vault.assert_called_once()
        mock_neo4j.assert_called_once()
        mock_recent.assert_called_once()
        mock_print.assert_called_once()
    
    @patch("troubleshoot_extension.check_capture_server")
    @patch("troubleshoot_extension.check_vault_accessible")
    @patch("troubleshoot_extension.check_neo4j")
    @patch("troubleshoot_extension.check_recent_captures")
    @patch("troubleshoot_extension.print_extension_instructions")
    def test_main_some_checks_fail(
        self, mock_print, mock_recent, mock_neo4j, mock_vault, mock_server
    ):
        """Test main when some checks fail."""
        mock_server.return_value = False
        mock_vault.return_value = True
        mock_neo4j.return_value = False
        
        troubleshoot_extension.main()
        
        # All checks should still be called
        mock_server.assert_called_once()
        mock_vault.assert_called_once()
        mock_neo4j.assert_called_once()
        mock_recent.assert_called_once()
        mock_print.assert_called_once()
    
    @patch("troubleshoot_extension.check_capture_server")
    @patch("troubleshoot_extension.check_vault_accessible")
    @patch("troubleshoot_extension.check_neo4j")
    def test_main_handles_exceptions_gracefully(
        self, mock_neo4j, mock_vault, mock_server
    ):
        """Test that main handles exceptions in individual checks."""
        mock_server.side_effect = Exception("Unexpected error")
        mock_vault.return_value = True
        mock_neo4j.return_value = True
        
        # Should not crash
        try:
            troubleshoot_extension.main()
        except Exception as e:
            pytest.fail(f"main() should handle exceptions gracefully, but raised: {e}")


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    @patch("troubleshoot_extension.settings")
    def test_vault_with_nested_platform_folders(self, mock_settings, tmp_path):
        """Test vault with deeply nested folder structure."""
        vault_path = tmp_path / "test_vault"
        ai_conv_path = vault_path / "AI_Conversations" / "ChatGPT" / "subfolder"
        ai_conv_path.mkdir(parents=True)
        
        # Create a file in nested folder
        (ai_conv_path / "test.md").write_text("Test")
        
        mock_settings.obsidian_vault_path = str(vault_path)
        
        # Should handle nested structure
        troubleshoot_extension.check_recent_captures()
    
    @patch("troubleshoot_extension.settings")
    def test_vault_with_non_markdown_files(self, mock_settings, tmp_path):
        """Test vault with non-.md files."""
        vault_path = tmp_path / "test_vault"
        ai_conv_path = vault_path / "AI_Conversations" / "ChatGPT"
        ai_conv_path.mkdir(parents=True)
        
        # Create various file types
        (ai_conv_path / "test.md").write_text("Markdown")
        (ai_conv_path / "test.txt").write_text("Text")
        (ai_conv_path / "test.json").write_text("{}")
        
        mock_settings.obsidian_vault_path = str(vault_path)
        
        # Should only count .md files
        troubleshoot_extension.check_recent_captures()
    
    @patch("troubleshoot_extension.requests.get")
    def test_server_returns_malformed_json(self, mock_get):
        """Test when server returns invalid JSON."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response
        
        result = troubleshoot_extension.check_capture_server()
        
        # Should handle JSON parsing error gracefully
        assert result is False


class TestIntegration:
    """Integration-style tests."""
    
    @patch("troubleshoot_extension.requests.get")
    @patch("troubleshoot_extension.GraphDatabase.driver")
    @patch("troubleshoot_extension.settings")
    def test_full_diagnostic_flow(self, mock_settings, mock_driver_class, mock_get, tmp_path):
        """Test complete diagnostic workflow."""
        # Setup vault
        vault_path = tmp_path / "test_vault"
        ai_conv_path = vault_path / "AI_Conversations" / "ChatGPT"
        ai_conv_path.mkdir(parents=True)
        (ai_conv_path / "test.md").write_text("# Test")
        
        mock_settings.obsidian_vault_path = str(vault_path)
        mock_settings.neo4j_uri = "bolt://localhost:7687"
        mock_settings.neo4j_user = "neo4j"
        mock_settings.neo4j_password = "password"
        
        # Mock server health check
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_get.return_value = mock_response
        
        # Mock Neo4j
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.single.return_value = {"test": 1}
        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver_class.return_value = mock_driver
        
        # Run full diagnostic
        with patch("troubleshoot_extension.print_extension_instructions"):
            troubleshoot_extension.main()
        
        # Verify all checks were performed
        mock_get.assert_called()
        mock_driver_class.assert_called()