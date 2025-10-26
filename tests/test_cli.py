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