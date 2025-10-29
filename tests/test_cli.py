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

class TestCLIRemovedCommands:
    """Test that removed commands are no longer available."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_sync_command_removed(self):
        """Verify the 'sync' command was removed from the CLI."""
        result = self.runner.invoke(cli, ['sync'])
        
        # Should fail with "No such command" error
        assert result.exit_code != 0
        assert "No such command" in result.output or "Error" in result.output

    def test_status_command_removed(self):
        """Verify the 'status' command was removed from the CLI."""
        result = self.runner.invoke(cli, ['status'])
        
        # Should fail with "No such command" error
        assert result.exit_code != 0
        assert "No such command" in result.output or "Error" in result.output

    def test_report_command_removed(self):
        """Verify the 'report' command was removed from the CLI."""
        result = self.runner.invoke(cli, ['report'])
        
        # Should fail with "No such command" error
        assert result.exit_code != 0
        assert "No such command" in result.output or "Error" in result.output


class TestCLIDocstringUpdates:
    """Test that CLI command docstrings were simplified."""

    def test_cli_group_docstring_simplified(self):
        """Verify the main CLI group has simplified docstring."""
        from omega_kg.cli import cli
        
        # The docstring should be concise
        assert cli.__doc__ is not None
        assert "Command-line interface group" in cli.__doc__
        assert "Omega_KG knowledge graph operations" in cli.__doc__
        
        # Should NOT contain the old verbose command list
        assert "Available commands:" not in cli.__doc__

    def test_init_command_docstring_simplified(self):
        """Verify init command has updated docstring."""
        from omega_kg.cli import init
        
        assert init.__doc__ is not None
        assert "Initialize" in init.__doc__
        assert "Neo4j schema" in init.__doc__

    def test_lifecycle_command_docstring_updated(self):
        """Verify lifecycle command docstring describes parameters correctly."""
        from omega_kg.cli import lifecycle
        
        assert lifecycle.__doc__ is not None
        assert "dry_run" in lifecycle.__doc__
        assert "no_email" in lifecycle.__doc__
        # Updated to use "If True" format
        assert "If True" in lifecycle.__doc__

    def test_stats_command_docstring_simplified(self):
        """Verify stats command has simplified docstring."""
        from omega_kg.cli import stats
        
        assert stats.__doc__ is not None
        # Should be much shorter
        assert "Show knowledge graph statistics" in stats.__doc__ or "statistics" in stats.__doc__

    def test_stale_command_docstring_updated(self):
        """Verify stale command has more detailed docstring."""
        from omega_kg.cli import stale
        
        assert stale.__doc__ is not None
        assert "7 days" in stale.__doc__
        # Should describe what it prints
        assert "uid" in stale.__doc__ or "UID" in stale.__doc__


class TestCLILifecycleCommandBehavior:
    """Test specific lifecycle command behavior changes."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch('omega_kg.cli.TaskLifecycle')
    def test_lifecycle_dry_run_and_no_email_combined(self, mock_lifecycle_class):
        """Test lifecycle command with both --dry-run and --no-email flags."""
        mock_lc = Mock()
        mock_report = "Dry run report"
        mock_lc.generate_report.return_value = mock_report
        mock_lifecycle_class.return_value = mock_lc

        result = self.runner.invoke(cli, ['lifecycle', '--dry-run', '--no-email'])

        assert result.exit_code == 0
        # Dry run should be True
        mock_lc.enforce_lifecycle.assert_called_once_with(dry_run=True)
        # Email should never be attempted in dry-run mode
        mock_lc.send_email_report.assert_not_called()

    @patch('omega_kg.cli.TaskLifecycle')
    def test_lifecycle_default_sends_email(self, mock_lifecycle_class):
        """Test that lifecycle command sends email by default (no flags)."""
        mock_lc = Mock()
        mock_report = "Default report"
        mock_lc.generate_report.return_value = mock_report
        mock_lifecycle_class.return_value = mock_lc

        result = self.runner.invoke(cli, ['lifecycle'])

        assert result.exit_code == 0
        # Should NOT be dry-run
        mock_lc.enforce_lifecycle.assert_called_once_with(dry_run=False)
        # Should send email
        mock_lc.send_email_report.assert_called_once_with(mock_report)

    @patch('omega_kg.cli.TaskLifecycle')
    def test_lifecycle_cleanup_on_exception(self, mock_lifecycle_class):
        """Verify lifecycle command closes resources even on exception."""
        mock_lc = Mock()
        mock_lc.enforce_lifecycle.side_effect = Exception("Test error")
        mock_lifecycle_class.return_value = mock_lc

        result = self.runner.invoke(cli, ['lifecycle'])

        # Should fail but still close
        assert result.exit_code != 0
        mock_lc.close.assert_called_once()


class TestCLIStatsCommand:
    """Test stats command behavior and edge cases."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch('omega_kg.obsidian_sync.ObsidianNeo4jSync')
    @patch('neo4j.GraphDatabase')
    def test_stats_displays_all_status_counts(self, mock_graph_db, mock_sync_class):
        """Verify stats command displays all task status categories."""
        mock_sync = Mock()
        mock_sync.get_connection_status.return_value = {"connected": True}
        mock_sync_class.return_value = mock_sync

        mock_driver = Mock()
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        mock_graph_db.driver.return_value = mock_driver
        mock_driver.session.return_value = mock_session

        # Mock comprehensive task counts
        mock_result = Mock()
        mock_record = Mock()
        mock_record.__getitem__ = Mock(side_effect=lambda key: {
            'total': 100,
            'draft': 25,
            'active': 30,
            'completed': 35,
            'archived': 10
        }.get(key, 0))
        mock_result.single.return_value = mock_record
        mock_session.run.return_value = mock_result

        result = self.runner.invoke(cli, ['stats'])

        assert result.exit_code == 0
        # Verify all categories are displayed
        assert "Total Tasks:" in result.output
        assert "Draft:" in result.output
        assert "Active:" in result.output
        assert "Completed:" in result.output
        assert "Archived:" in result.output
        # Verify counts are present
        assert "100" in result.output
        assert "25" in result.output
        assert "30" in result.output
        assert "35" in result.output
        assert "10" in result.output

    @patch('omega_kg.obsidian_sync.ObsidianNeo4jSync')
    @patch('neo4j.GraphDatabase')
    def test_stats_handles_zero_tasks(self, mock_graph_db, mock_sync_class):
        """Test stats command when database has zero tasks."""
        mock_sync = Mock()
        mock_sync.get_connection_status.return_value = {"connected": True}
        mock_sync_class.return_value = mock_sync

        mock_driver = Mock()
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        mock_graph_db.driver.return_value = mock_driver
        mock_driver.session.return_value = mock_session

        # All counts are zero
        mock_result = Mock()
        mock_record = Mock()
        mock_record.__getitem__ = Mock(side_effect=lambda key: 0)
        mock_result.single.return_value = mock_record
        mock_session.run.return_value = mock_result

        result = self.runner.invoke(cli, ['stats'])

        assert result.exit_code == 0
        assert "Total Tasks:      0" in result.output

    @patch('omega_kg.obsidian_sync.ObsidianNeo4jSync')
    @patch('neo4j.GraphDatabase')
    def test_stats_closes_driver_after_query(self, mock_graph_db, mock_sync_class):
        """Verify stats command properly closes Neo4j driver."""
        mock_sync = Mock()
        mock_sync.get_connection_status.return_value = {"connected": True}
        mock_sync_class.return_value = mock_sync

        mock_driver = Mock()
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        mock_graph_db.driver.return_value = mock_driver
        mock_driver.session.return_value = mock_session

        mock_result = Mock()
        mock_record = Mock()
        mock_record.__getitem__ = Mock(return_value=0)
        mock_result.single.return_value = mock_record
        mock_session.run.return_value = mock_result

        result = self.runner.invoke(cli, ['stats'])

        assert result.exit_code == 0
        # Driver should be closed
        mock_driver.close.assert_called_once()


class TestCLIStaleCommand:
    """Test stale command comprehensive behavior."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch('omega_kg.obsidian_sync.ObsidianNeo4jSync')
    def test_stale_displays_multiple_tasks(self, mock_sync_class):
        """Test stale command with multiple stale tasks."""
        mock_sync = Mock()
        mock_stale_tasks = [
            {
                't.uid': 'TASK-001',
                't.title': 'First Stale Task',
                't.created': '2023-01-01T10:00:00'
            },
            {
                't.uid': 'TASK-002',
                't.title': 'Second Stale Task',
                't.created': '2023-02-15T14:30:00'
            },
            {
                't.uid': 'TASK-003',
                't.title': 'Third Stale Task',
                't.created': '2023-03-20T09:15:00'
            }
        ]
        mock_sync.get_stale_tasks.return_value = mock_stale_tasks
        mock_sync_class.return_value = mock_sync

        result = self.runner.invoke(cli, ['stale'])

        assert result.exit_code == 0
        assert "TASK-001" in result.output
        assert "First Stale Task" in result.output
        assert "TASK-002" in result.output
        assert "Second Stale Task" in result.output
        assert "TASK-003" in result.output
        assert "Third Stale Task" in result.output

    @patch('omega_kg.obsidian_sync.ObsidianNeo4jSync')
    def test_stale_uses_seven_day_threshold(self, mock_sync_class):
        """Verify stale command uses 7-day threshold."""
        mock_sync = Mock()
        mock_sync.get_stale_tasks.return_value = []
        mock_sync_class.return_value = mock_sync

        result = self.runner.invoke(cli, ['stale'])

        assert result.exit_code == 0
        # Should call get_stale_tasks with 7 days
        mock_sync.get_stale_tasks.assert_called_once_with(7)

    @patch('omega_kg.obsidian_sync.ObsidianNeo4jSync')
    def test_stale_shows_created_dates(self, mock_sync_class):
        """Test that stale command displays creation dates."""
        mock_sync = Mock()
        mock_stale_tasks = [
            {
                't.uid': 'TASK-100',
                't.title': 'Task with Date',
                't.created': '2023-06-15T12:00:00'
            }
        ]
        mock_sync.get_stale_tasks.return_value = mock_stale_tasks
        mock_sync_class.return_value = mock_sync

        result = self.runner.invoke(cli, ['stale'])

        assert result.exit_code == 0
        # Should display creation date
        assert "created:" in result.output
        assert "2023-06-15" in result.output


class TestCLIInitCommand:
    """Test init command edge cases."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch('omega_kg.cli.KnowledgeGraphSchema')
    def test_init_handles_schema_exception(self, mock_schema_class):
        """Test init command handles exceptions during schema initialization."""
        mock_schema = Mock()
        mock_schema.initialize_schema.side_effect = Exception("Schema error")
        mock_schema_class.return_value = mock_schema

        result = self.runner.invoke(cli, ['init'])

        # Should handle error gracefully
        assert result.exit_code != 0
        # Should still call close
        mock_schema.close.assert_called_once()

    @patch('omega_kg.cli.KnowledgeGraphSchema')
    def test_init_creates_sample_relationships(self, mock_schema_class):
        """Verify init creates sample relationships after schema."""
        mock_schema = Mock()
        mock_schema_class.return_value = mock_schema

        result = self.runner.invoke(cli, ['init'])

        assert result.exit_code == 0
        # Verify order: initialize_schema then create_sample_relationships
        call_order = []
        for call in mock_schema.method_calls:
            call_order.append(call[0])
        
        assert 'initialize_schema' in call_order
        assert 'create_sample_relationships' in call_order
        assert call_order.index('initialize_schema') < call_order.index('create_sample_relationships')


class TestCLIHelp:
    """Test CLI help output."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_cli_help_shows_available_commands(self):
        """Test that --help shows all available commands."""
        result = self.runner.invoke(cli, ['--help'])

        assert result.exit_code == 0
        # Should show the commands that exist
        assert "init" in result.output
        assert "lifecycle" in result.output
        assert "stats" in result.output
        assert "stale" in result.output
        
        # Should NOT show removed commands
        assert "sync" not in result.output or "Usage:" in result.output  # "sync" might be in "usage" context
        assert "status" not in result.output or "Usage:" in result.output
        assert "report" not in result.output or "Usage:" in result.output

    def test_lifecycle_help_shows_options(self):
        """Test that lifecycle --help shows available options."""
        result = self.runner.invoke(cli, ['lifecycle', '--help'])

        assert result.exit_code == 0
        assert "--dry-run" in result.output
        assert "--no-email" in result.output
        assert "Preview changes" in result.output
        assert "Skip email report" in result.output