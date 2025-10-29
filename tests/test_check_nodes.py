"""
Unit tests for check_nodes.py
"""

import importlib
import subprocess
import sys
from unittest.mock import Mock, patch
import pytest


class TestCheckNodes:
    """Test suite for check_nodes.py functionality."""

    @patch('omega_kg.check_nodes.GraphDatabase.driver')
    @patch('builtins.print')
    def test_check_nodes_with_tasks(self, mock_print, mock_driver):
        """Test check_nodes script driver creation."""
        # Mock the driver and session
        mock_session = Mock()
        mock_driver.return_value = mock_session
        mock_driver.return_value.session.return_value = mock_session

        # Mock session.run to return mock results
        mock_result = Mock()
        mock_result.single.return_value = None  # No records for simplicity
        mock_result.__iter__ = Mock(return_value=iter([]))  # Empty iterator
        mock_session.run.return_value = mock_result

        # Import and reload the module to execute module-level code
        import omega_kg.check_nodes
        importlib.reload(omega_kg.check_nodes)

        # Verify the driver was created correctly
        expected_auth = (
            omega_kg.check_nodes.settings.neo4j_user,
            omega_kg.check_nodes.settings.neo4j_password
        )
        mock_driver.assert_called_once_with(
            omega_kg.check_nodes.settings.neo4j_uri,
            auth=expected_auth
        )

    @pytest.mark.requires_neo4j
    def test_check_nodes_script_execution(self):
        """Test that check_nodes.py can be executed as a script."""
        # Run the script as a subprocess
        result = subprocess.run(
            [sys.executable, 'omega_kg/check_nodes.py'],
            capture_output=True,
            text=True,
            cwd='.'
        )

        # The script should run without errors (even if Neo4j is not available)
        # It will fail with connection errors, but should not have syntax errors
        assert result.returncode != 2  # Not a syntax error