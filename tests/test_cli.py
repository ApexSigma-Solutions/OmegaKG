"""
Unit tests for cli.py
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner
from omega_kg.cli import cli


class TestCLI:
    """Test suite for CLI commands."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch('omega_kg.cli.KnowledgeGraphSchema')
    def test_init_command(self, mock_schema_class):
        """Test the init command."""
        mock_schema = Mock()
        mock_schema_class.return_value = mock_schema

        result = self.runner.invoke(cli, ['init'])

        assert result.exit_code == 0
        assert "🔧 Initializing Neo4j schema..." in result.output
        assert "✓ Schema initialized" in result.output

        # Verify schema methods were called
        mock_schema.initialize_schema.assert_called_once()
        mock_schema.create_sample_relationships.assert_called_once()
        mock_schema.close.assert_called_once()

    @patch('omega_kg.cli.TaskLifecycle')
    def test_lifecycle_command_dry_run(self, mock_lifecycle_class):
        """Test the lifecycle command with dry-run flag."""
        mock_lc = Mock()
        mock_report = "Test lifecycle report"
        mock_lc.generate_report.return_value = mock_report
        mock_lifecycle_class.return_value = mock_lc

        result = self.runner.invoke(cli, ['lifecycle', '--dry-run'])

        assert result.exit_code == 0
        assert "🔄 Running lifecycle enforcement..." in result.output
        assert mock_report in result.output

        # Verify lifecycle methods were called correctly
        mock_lc.enforce_lifecycle.assert_called_once_with(dry_run=True)
        mock_lc.generate_report.assert_called_once()
        mock_lc.send_email_report.assert_not_called()
        mock_lc.close.assert_called_once()

    @patch('omega_kg.cli.TaskLifecycle')
    def test_lifecycle_command_with_email(self, mock_lifecycle_class):
        """Test the lifecycle command with email sending."""
        mock_lc = Mock()
        mock_report = "Test lifecycle report"
        mock_lc.generate_report.return_value = mock_report
        mock_lifecycle_class.return_value = mock_lc

        result = self.runner.invoke(cli, ['lifecycle'])

        assert result.exit_code == 0
        assert mock_report in result.output

        # Verify email was sent
        mock_lc.enforce_lifecycle.assert_called_once_with(dry_run=False)
        mock_lc.send_email_report.assert_called_once_with(mock_report)

    @patch('omega_kg.obsidian_sync.ObsidianNeo4jSync')
    @patch('neo4j.GraphDatabase')
    @patch('omega_kg.settings')
    def test_stats_command_connected(self, mock_settings, mock_graph_db, mock_sync_class):
        """Test the stats command when connected to Neo4j."""
        # Mock sync
        mock_sync = Mock()
        mock_sync.get_connection_status.return_value = {"connected": True}
        mock_sync_class.return_value = mock_sync

        # Mock Neo4j driver and session
        mock_driver = Mock()
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        mock_graph_db.driver.return_value = mock_driver
        mock_driver.session.return_value = mock_session

        # Mock query result
        mock_result = Mock()
        mock_record = Mock()
        mock_record.__getitem__ = Mock(side_effect=lambda key: {
            'total': 10,
            'draft': 3,
            'active': 4,
            'completed': 2,
            'archived': 1
        }.get(key, 0))
        mock_result.single.return_value = mock_record
        mock_session.run.return_value = mock_result

        result = self.runner.invoke(cli, ['stats'])

        assert result.exit_code == 0
        assert "✓ Neo4j connection established" in result.output
        assert "📊 Knowledge Graph Statistics" in result.output
        assert "Total Tasks:      10" in result.output
        assert "Draft:            3" in result.output
        assert "Active:           4" in result.output
        assert "Completed:        2" in result.output
        assert "Archived:         1" in result.output

        mock_sync.close.assert_called_once()

    @patch('omega_kg.obsidian_sync.ObsidianNeo4jSync')
    def test_stats_command_mock_mode(self, mock_sync_class):
        """Test the stats command in mock mode."""
        mock_sync = Mock()
        mock_sync.get_connection_status.return_value = {"connected": False}
        mock_sync_class.return_value = mock_sync

        result = self.runner.invoke(cli, ['stats'])

        assert result.exit_code == 0
        assert "[WARN] Running in mock mode" in result.output
        mock_sync.close.assert_called_once()

    @patch('omega_kg.obsidian_sync.ObsidianNeo4jSync')
    def test_stale_command(self, mock_sync_class):
        """Test the stale command."""
        mock_sync = Mock()
        mock_stale_tasks = [
            {'t.uid': 'TASK-001', 't.title': 'Old Task',
             't.created': '2023-01-01'}
        ]
        mock_sync.get_stale_tasks.return_value = mock_stale_tasks
        mock_sync_class.return_value = mock_sync

        result = self.runner.invoke(cli, ['stale'])

        assert result.exit_code == 0
        assert "--- Stale Tasks (>7 days) ---" in result.output
        assert "TASK-001: Old Task" in result.output
        mock_sync.get_stale_tasks.assert_called_once_with(7)
        mock_sync.close.assert_called_once()

    @patch('omega_kg.obsidian_sync.ObsidianNeo4jSync')
    def test_stale_command_no_stale_tasks(self, mock_sync_class):
        """Test the stale command when no stale tasks exist."""
        mock_sync = Mock()
        mock_sync.get_stale_tasks.return_value = []
        mock_sync_class.return_value = mock_sync

        result = self.runner.invoke(cli, ['stale'])

        assert result.exit_code == 0
        assert "(none)" in result.output
        mock_sync.close.assert_called_once()
    @patch('omega_kg.cli.TaskLifecycle')
    def test_lifecycle_command_no_email(self, mock_lifecycle_class):
        """Test the lifecycle command with --no-email flag (no email should be sent)."""
        mock_lc = Mock()
        mock_report = "Report without email"
        mock_lc.generate_report.return_value = mock_report
        mock_lifecycle_class.return_value = mock_lc

        result = self.runner.invoke(cli, ['lifecycle', '--no-email'])

        assert result.exit_code == 0
        # Should run lifecycle normally (not dry-run)
        mock_lc.enforce_lifecycle.assert_called_once_with(dry_run=False)
        # But must not send email due to --no-email
        mock_lc.send_email_report.assert_not_called()
        mock_lc.close.assert_called_once()

class TestCLIEdgeCases:
    """Test CLI edge cases and error handling."""
    
    @patch('omega_kg.cli.KnowledgeGraphSchema')
    def test_init_command_handles_schema_error(self, mock_schema_class):
        """Test init command handles schema initialization errors gracefully."""
        mock_schema = Mock()
        mock_schema.initialize_schema.side_effect = Exception("Schema error")
        mock_schema_class.return_value = mock_schema
        
        result = self.runner.invoke(cli, ['init'])
        
        # Should not crash, error should be handled
        assert result.exit_code != 0 or "error" in result.output.lower()
    
    @patch('omega_kg.cli.TaskLifecycle')
    def test_lifecycle_command_handles_driver_error(self, mock_lifecycle_class):
        """Test lifecycle command handles database connection errors."""
        mock_lifecycle_class.side_effect = Exception("Connection failed")
        
        result = self.runner.invoke(cli, ['lifecycle'])
        
        # Should handle error gracefully
        assert result.exit_code != 0 or "error" in result.output.lower()
    
    @patch('omega_kg.obsidian_sync.ObsidianNeo4jSync')
    def test_stats_command_handles_query_error(self, mock_sync_class):
        """Test stats command handles query failures."""
        mock_sync = Mock()
        mock_sync.get_connection_status.return_value = {"connected": True}
        mock_sync_class.return_value = mock_sync
        
        with patch('neo4j.GraphDatabase') as mock_gdb:
            mock_driver = Mock()
            mock_session = Mock()
            mock_session.run.side_effect = Exception("Query failed")
            mock_driver.session.return_value.__enter__.return_value = mock_session
            mock_gdb.driver.return_value = mock_driver
            
            result = self.runner.invoke(cli, ['stats'])
            
            # Should handle error gracefully
            assert result.exit_code != 0 or "error" in result.output.lower()
    
    @patch('omega_kg.obsidian_sync.ObsidianNeo4jSync')
    def test_stale_command_handles_exception(self, mock_sync_class):
        """Test stale command handles unexpected exceptions."""
        mock_sync = Mock()
        mock_sync.get_stale_tasks.side_effect = Exception("Unexpected error")
        mock_sync_class.return_value = mock_sync
        
        result = self.runner.invoke(cli, ['stale'])
        
        # Should handle error gracefully
        assert result.exit_code != 0 or "error" in result.output.lower()


class TestCLIIntegration:
    """Integration-style tests for CLI commands."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    @patch('omega_kg.cli.TaskLifecycle')
    def test_lifecycle_dry_run_no_email_combination(self, mock_lifecycle_class):
        """Test lifecycle with both --dry-run and --no-email flags."""
        mock_lc = Mock()
        mock_report = "Test report"
        mock_lc.generate_report.return_value = mock_report
        mock_lifecycle_class.return_value = mock_lc
        
        result = self.runner.invoke(cli, ['lifecycle', '--dry-run', '--no-email'])
        
        assert result.exit_code == 0
        mock_lc.enforce_lifecycle.assert_called_once_with(dry_run=True)
        mock_lc.send_email_report.assert_not_called()
    
    @patch('omega_kg.cli.KnowledgeGraphSchema')
    def test_init_command_closes_schema_on_error(self, mock_schema_class):
        """Test init command ensures schema is closed even on error."""
        mock_schema = Mock()
        mock_schema.create_sample_relationships.side_effect = Exception("Error")
        mock_schema_class.return_value = mock_schema
        
        result = self.runner.invoke(cli, ['init'])
        
        # close() should still be called
        mock_schema.close.assert_called()


class TestCLIEdgeCases:
    """Test CLI edge cases and error handling."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    @patch('omega_kg.cli.KnowledgeGraphSchema')
    def test_init_command_handles_schema_error(self, mock_schema_class):
        """Test init command handles schema initialization errors gracefully."""
        from unittest.mock import Mock
        mock_schema = Mock()
        mock_schema.initialize_schema.side_effect = Exception("Schema error")
        mock_schema_class.return_value = mock_schema
        
        result = self.runner.invoke(cli, ['init'])
        
        # close() should still be called even on error
        mock_schema.close.assert_called()
    
    @patch('omega_kg.cli.TaskLifecycle')
    def test_lifecycle_dry_run_no_email_combination(self, mock_lifecycle_class):
        """Test lifecycle with both --dry-run and --no-email flags."""
        from unittest.mock import Mock
        mock_lc = Mock()
        mock_report = "Test report"
        mock_lc.generate_report.return_value = mock_report
        mock_lifecycle_class.return_value = mock_lc
        
        result = self.runner.invoke(cli, ['lifecycle', '--dry-run', '--no-email'])
        
        assert result.exit_code == 0
        mock_lc.enforce_lifecycle.assert_called_once_with(dry_run=True)
        mock_lc.send_email_report.assert_not_called()
    
    @patch('omega_kg.obsidian_sync.ObsidianNeo4jSync')
    def test_stale_command_with_multiple_stale_tasks(self, mock_sync_class):
        """Test stale command displays multiple stale tasks correctly."""
        from unittest.mock import Mock
        mock_sync = Mock()
        mock_stale_tasks = [
            {'t.uid': 'TASK-001', 't.title': 'Old Task 1', 't.created': '2023-01-01'},
            {'t.uid': 'TASK-002', 't.title': 'Old Task 2', 't.created': '2023-01-02'},
            {'t.uid': 'TASK-003', 't.title': 'Old Task 3', 't.created': '2023-01-03'}
        ]
        mock_sync.get_stale_tasks.return_value = mock_stale_tasks
        mock_sync_class.return_value = mock_sync
        
        result = self.runner.invoke(cli, ['stale'])
        
        assert result.exit_code == 0
        assert "TASK-001" in result.output
        assert "TASK-002" in result.output
        assert "TASK-003" in result.output
        mock_sync.close.assert_called_once()


class TestCLIOutputFormatting:
    """Test CLI output formatting and messages."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    @patch('omega_kg.cli.KnowledgeGraphSchema')
    def test_init_command_output_messages(self, mock_schema_class):
        """Test init command displays appropriate messages."""
        from unittest.mock import Mock
        mock_schema = Mock()
        mock_schema_class.return_value = mock_schema
        
        result = self.runner.invoke(cli, ['init'])
        
        assert result.exit_code == 0
        assert "Initializing Neo4j schema" in result.output or "initialized" in result.output.lower()
    
    @patch('omega_kg.cli.TaskLifecycle')
    def test_lifecycle_command_output_format(self, mock_lifecycle_class):
        """Test lifecycle command displays report correctly."""
        from unittest.mock import Mock
        mock_lc = Mock()
        detailed_report = "LIFECYCLE REPORT\nArchived: 5\nWarned: 3\n"
        mock_lc.generate_report.return_value = detailed_report
        mock_lifecycle_class.return_value = mock_lc
        
        result = self.runner.invoke(cli, ['lifecycle', '--dry-run'])
        
        assert result.exit_code == 0
        assert detailed_report in result.output