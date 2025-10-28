"""
Comprehensive unit tests for verify_system.py module.

Tests cover:
- Settings loading
- Neo4j connectivity checks
- Data existence verification
- Task queryability
- Vault structure validation
- Markdown file counting
- Main workflow orchestration
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, call
import sys

# Import the module under test
import verify_system


class TestMainSystemVerification:
    """Test main system verification function."""
    
    @patch("verify_system.GraphDatabase.driver")
    @patch("verify_system.settings")
    def test_check_1_settings_loaded(self, mock_settings, mock_driver_class, capsys):
        """Test that Check 1 (settings loaded) passes."""
        mock_settings.neo4j_uri = "bolt://localhost:7687"
        mock_settings.obsidian_vault_path = "/path/to/vault"
        
        # Mock Neo4j to avoid side effects
        mock_driver = MagicMock()
        mock_driver_class.return_value = mock_driver
        
        verify_system.main()
        
        captured = capsys.readouterr()
        output = captured.out
        
        assert "1️⃣  Settings loaded" in output
        assert "bolt://localhost:7687" in output
        assert "/path/to/vault" in output
    
    @patch("verify_system.GraphDatabase.driver")
    @patch("verify_system.settings")
    def test_check_2_neo4j_connection_success(self, mock_settings, mock_driver_class, capsys):
        """Test successful Neo4j connection check."""
        mock_settings.neo4j_uri = "bolt://localhost:7687"
        mock_settings.neo4j_user = "neo4j"
        mock_settings.neo4j_password = "password"
        mock_settings.obsidian_vault_path = "/path/to/vault"
        
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver_class.return_value = mock_driver
        
        verify_system.main()
        
        captured = capsys.readouterr()
        output = captured.out
        
        assert "2️⃣  Attempting Neo4j connection" in output
        assert "Neo4j connection successful" in output
    
    @patch("verify_system.GraphDatabase.driver")
    @patch("verify_system.settings")
    def test_check_2_neo4j_connection_failure(self, mock_settings, mock_driver_class, capsys):
        """Test Neo4j connection failure handling."""
        mock_settings.neo4j_uri = "bolt://localhost:7687"
        mock_settings.neo4j_user = "neo4j"
        mock_settings.neo4j_password = "wrong_password"
        mock_settings.obsidian_vault_path = "/path/to/vault"
        
        mock_driver_class.side_effect = Exception("Authentication failed")
        
        verify_system.main()
        
        captured = capsys.readouterr()
        output = captured.out
        
        assert "❌ Check 2 failed" in output
        assert "Authentication failed" in output
    
    @patch("verify_system.GraphDatabase.driver")
    @patch("verify_system.settings")
    def test_check_3_data_exists(self, mock_settings, mock_driver_class, capsys):
        """Test data existence check when nodes are found."""
        mock_settings.neo4j_uri = "bolt://localhost:7687"
        mock_settings.neo4j_user = "neo4j"
        mock_settings.neo4j_password = "password"
        mock_settings.obsidian_vault_path = "/path/to/vault"
        
        mock_driver = MagicMock()
        mock_session = MagicMock()
        
        # First call for connection check
        mock_session.run.side_effect = [
            MagicMock(),  # Connection check
            [{"count": 150}],  # Data existence check
        ]
        
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver_class.return_value = mock_driver
        
        verify_system.main()
        
        captured = capsys.readouterr()
        output = captured.out
        
        assert "3️⃣  Checking for data in Neo4j" in output
        assert "Found 150 nodes" in output
    
    @patch("verify_system.GraphDatabase.driver")
    @patch("verify_system.settings")
    def test_check_3_no_data(self, mock_settings, mock_driver_class, capsys):
        """Test when Neo4j has no data."""
        mock_settings.neo4j_uri = "bolt://localhost:7687"
        mock_settings.neo4j_user = "neo4j"
        mock_settings.neo4j_password = "password"
        mock_settings.obsidian_vault_path = "/path/to/vault"
        
        mock_driver = MagicMock()
        mock_session = MagicMock()
        
        mock_session.run.side_effect = [
            MagicMock(),  # Connection check
            [{"count": 0}],  # No data
        ]
        
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver_class.return_value = mock_driver
        
        verify_system.main()
        
        captured = capsys.readouterr()
        output = captured.out
        
        assert "⚠️  Check 3 warning: No data in Neo4j yet" in output
    
    @patch("verify_system.GraphDatabase.driver")
    @patch("verify_system.settings")
    def test_check_4_tasks_queryable(self, mock_settings, mock_driver_class, capsys):
        """Test task queryability check."""
        mock_settings.neo4j_uri = "bolt://localhost:7687"
        mock_settings.neo4j_user = "neo4j"
        mock_settings.neo4j_password = "password"
        mock_settings.obsidian_vault_path = "/path/to/vault"
        
        mock_driver = MagicMock()
        mock_session = MagicMock()
        
        mock_session.run.side_effect = [
            MagicMock(),  # Connection check
            [{"count": 100}],  # Data exists
            [{"count": 25}],  # Task count
        ]
        
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver_class.return_value = mock_driver
        
        verify_system.main()
        
        captured = capsys.readouterr()
        output = captured.out
        
        assert "4️⃣  Checking if tasks can be queried" in output
        assert "Tasks queryable: 25 found" in output
    
    @patch("verify_system.GraphDatabase.driver")
    @patch("verify_system.settings")
    @patch("verify_system.Path")
    def test_check_5_vault_structure(self, mock_path_class, mock_settings, mock_driver_class, capsys, tmp_path):
        """Test vault structure validation."""
        vault_path = tmp_path / "test_vault"
        vault_path.mkdir()
        
        # Create expected folders
        folders = ["Plans", "Tasks", "Archive", "AI_Conversations", "Daily", "Sessions"]
        for folder in folders:
            folder_path = vault_path / folder
            folder_path.mkdir()
            # Add some markdown files
            (folder_path / "test1.md").write_text("# Test 1")
            (folder_path / "test2.md").write_text("# Test 2")
        
        # Create platform folders
        ai_conv = vault_path / "AI_Conversations"
        platforms = ["ChatGPT", "Claude.ai", "Gemini"]
        for platform in platforms:
            (ai_conv / platform).mkdir()
            (ai_conv / platform / "conv.md").write_text("# Conversation")
        
        mock_settings.obsidian_vault_path = str(vault_path)
        mock_settings.neo4j_uri = "bolt://localhost:7687"
        mock_settings.neo4j_user = "neo4j"
        mock_settings.neo4j_password = "password"
        
        # Mock Neo4j
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_session.run.side_effect = [
            MagicMock(),  # Connection check
            [{"count": 0}],  # No data
            [{"count": 0}],  # No tasks
        ]
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver_class.return_value = mock_driver
        
        # Patch Path to return real paths
        mock_path_class.side_effect = lambda x: Path(x)
        
        verify_system.main()
        
        captured = capsys.readouterr()
        output = captured.out
        
        assert "5️⃣  Checking Obsidian vault structure" in output
        assert "Obsidian vault found" in output
        assert "Plans" in output
        assert "Tasks" in output
        assert "ChatGPT" in output
    
    @patch("verify_system.GraphDatabase.driver")
    @patch("verify_system.settings")
    def test_check_5_vault_missing(self, mock_settings, mock_driver_class, capsys, tmp_path):
        """Test when vault doesn't exist."""
        nonexistent_vault = tmp_path / "nonexistent_vault"
        mock_settings.obsidian_vault_path = str(nonexistent_vault)
        mock_settings.neo4j_uri = "bolt://localhost:7687"
        mock_settings.neo4j_user = "neo4j"
        mock_settings.neo4j_password = "password"
        
        # Mock Neo4j
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_session.run.return_value = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver_class.return_value = mock_driver
        
        verify_system.main()
        
        captured = capsys.readouterr()
        output = captured.out
        
        assert "⚠️  Check 5 warning: Obsidian vault not found" in output
    
    @patch("verify_system.GraphDatabase.driver")
    @patch("verify_system.settings")
    def test_check_6_markdown_files(self, mock_settings, mock_driver_class, capsys, tmp_path):
        """Test markdown file counting."""
        vault_path = tmp_path / "test_vault"
        vault_path.mkdir()
        
        # Create markdown files in checked folders
        plans_path = vault_path / "Plans"
        plans_path.mkdir()
        (plans_path / "plan1.md").write_text("# Plan 1")
        (plans_path / "plan2.md").write_text("# Plan 2")
        
        tasks_path = vault_path / "Tasks"
        tasks_path.mkdir()
        (tasks_path / "task1.md").write_text("# Task 1")
        
        sessions_path = vault_path / "Sessions"
        sessions_path.mkdir()
        (sessions_path / "session1.md").write_text("# Session 1")
        
        mock_settings.obsidian_vault_path = str(vault_path)
        mock_settings.neo4j_uri = "bolt://localhost:7687"
        mock_settings.neo4j_user = "neo4j"
        mock_settings.neo4j_password = "password"
        
        # Mock Neo4j
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_session.run.return_value = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver_class.return_value = mock_driver
        
        verify_system.main()
        
        captured = capsys.readouterr()
        output = captured.out
        
        assert "6️⃣  Verifying markdown content" in output
        assert "Found 4 markdown files" in output
    
    @patch("verify_system.GraphDatabase.driver")
    @patch("verify_system.settings")
    def test_summary_all_checks_pass(self, mock_settings, mock_driver_class, capsys, tmp_path):
        """Test summary when all checks pass."""
        vault_path = tmp_path / "test_vault"
        vault_path.mkdir()
        
        # Create all required structure
        for folder in ["Plans", "Tasks", "Sessions"]:
            folder_path = vault_path / folder
            folder_path.mkdir()
            (folder_path / "test.md").write_text("# Test")
        
        mock_settings.obsidian_vault_path = str(vault_path)
        mock_settings.neo4j_uri = "bolt://localhost:7687"
        mock_settings.neo4j_user = "neo4j"
        mock_settings.neo4j_password = "password"
        
        # Mock successful Neo4j
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_session.run.side_effect = [
            MagicMock(),  # Connection
            [{"count": 100}],  # Data exists
            [{"count": 50}],  # Tasks exist
        ]
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver_class.return_value = mock_driver
        
        verify_system.main()
        
        captured = capsys.readouterr()
        output = captured.out
        
        assert "RESULTS:" in output
        assert "System is operational!" in output
    
    @patch("verify_system.GraphDatabase.driver")
    @patch("verify_system.settings")
    def test_summary_partial_configuration(self, mock_settings, mock_driver_class, capsys):
        """Test summary when partially configured."""
        mock_settings.obsidian_vault_path = "/nonexistent"
        mock_settings.neo4j_uri = "bolt://localhost:7687"
        mock_settings.neo4j_user = "neo4j"
        mock_settings.neo4j_password = "password"
        
        # Mock successful Neo4j but no data
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_session.run.side_effect = [
            MagicMock(),  # Connection
            [{"count": 0}],  # No data
        ]
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver_class.return_value = mock_driver
        
        verify_system.main()
        
        captured = capsys.readouterr()
        output = captured.out
        
        assert "System partially configured" in output or "System needs configuration" in output


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    @patch("verify_system.GraphDatabase.driver")
    @patch("verify_system.settings")
    def test_unicode_vault_path(self, mock_settings, mock_driver_class, tmp_path, capsys):
        """Test vault path with Unicode characters."""
        vault_path = tmp_path / "测试_vault"
        vault_path.mkdir()
        
        mock_settings.obsidian_vault_path = str(vault_path)
        mock_settings.neo4j_uri = "bolt://localhost:7687"
        mock_settings.neo4j_user = "neo4j"
        mock_settings.neo4j_password = "password"
        
        mock_driver = MagicMock()
        mock_driver_class.return_value = mock_driver
        
        # Should not crash
        verify_system.main()
    
    @patch("verify_system.GraphDatabase.driver")
    @patch("verify_system.settings")
    def test_very_large_node_count(self, mock_settings, mock_driver_class, capsys):
        """Test handling of very large node counts."""
        mock_settings.obsidian_vault_path = "/path/to/vault"
        mock_settings.neo4j_uri = "bolt://localhost:7687"
        mock_settings.neo4j_user = "neo4j"
        mock_settings.neo4j_password = "password"
        
        mock_driver = MagicMock()
        mock_session = MagicMock()
        
        # Return very large count
        mock_session.run.side_effect = [
            MagicMock(),
            [{"count": 1000000}],
        ]
        
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver_class.return_value = mock_driver
        
        verify_system.main()
        
        captured = capsys.readouterr()
        output = captured.out
        
        assert "1000000" in output


class TestOutputFormatting:
    """Test output formatting and presentation."""
    
    @patch("verify_system.GraphDatabase.driver")
    @patch("verify_system.settings")
    def test_output_contains_separators(self, mock_settings, mock_driver_class, capsys):
        """Test that output contains proper separators."""
        mock_settings.obsidian_vault_path = "/path"
        mock_settings.neo4j_uri = "bolt://localhost:7687"
        mock_settings.neo4j_user = "neo4j"
        mock_settings.neo4j_password = "password"
        
        mock_driver = MagicMock()
        mock_driver_class.return_value = mock_driver
        
        verify_system.main()
        
        captured = capsys.readouterr()
        output = captured.out
        
        assert "=" * 80 in output
        assert "OMEGA_KG SYSTEM VERIFICATION" in output
        assert "RESULTS:" in output
    
    @patch("verify_system.GraphDatabase.driver")
    @patch("verify_system.settings")
    def test_output_contains_emojis(self, mock_settings, mock_driver_class, capsys):
        """Test that output uses emoji indicators."""
        mock_settings.obsidian_vault_path = "/path"
        mock_settings.neo4j_uri = "bolt://localhost:7687"
        mock_settings.neo4j_user = "neo4j"
        mock_settings.neo4j_password = "password"
        
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_session.run.side_effect = [
            MagicMock(),
            [{"count": 100}],
        ]
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver_class.return_value = mock_driver
        
        verify_system.main()
        
        captured = capsys.readouterr()
        output = captured.out
        
        # Check for emoji indicators
        assert any(emoji in output for emoji in ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣"])
        assert any(indicator in output for indicator in ["✅", "⚠️", "❌"])