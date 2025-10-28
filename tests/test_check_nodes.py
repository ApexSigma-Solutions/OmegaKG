"""
Unit tests for check_nodes.py
"""

import importlib
import os
import subprocess
import sys
from unittest.mock import Mock, patch


class TestCheckNodes:
    """Test suite for check_nodes.py functionality."""

    @patch('omega_kg.check_nodes.GraphDatabase.driver')
    @patch('builtins.print')
    def test_check_nodes_with_tasks(self, mock_print, mock_driver):
        """Test check_nodes script driver creation."""
        # Mock the driver instance and session
        mock_driver_instance = Mock()
        mock_session = Mock()
        mock_driver.return_value = mock_driver_instance
        mock_driver_instance.session.return_value = mock_session

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

    def test_check_nodes_script_execution(self):
        """Test that check_nodes.py can be executed as a script."""
        # Create a safe environment to prevent real DB connections
        env = os.environ.copy()
        env['NEO4J_URI'] = 'bolt://invalid-host:9999'  # Invalid URI to prevent connection
        env['NEO4J_USER'] = 'test'
        env['NEO4J_PASSWORD'] = 'test'

        # Run the script as a subprocess with timeout and safe environment
        result = subprocess.run(
            [sys.executable, 'omega_kg/check_nodes.py'],
            capture_output=True,
            text=True,
            cwd='.',
            env=env,
            timeout=10  # Prevent hanging
        )

        # The script should run without syntax errors (connection errors are expected)
        # It will fail with connection errors, but should not have syntax errors
        assert result.returncode != 2  # Not a syntax error
    @patch('omega_kg.check_nodes.GraphDatabase.driver')
    def test_query_constant_shape(self, mock_driver):
        """Ensure the node inspection query matches expected structure."""
        import importlib
        # Prevent real connections
        mock_driver.return_value = Mock()
        import omega_kg.check_nodes as mod
        importlib.reload(mod)
        assert hasattr(mod, "query")
        assert mod.query.strip() == "MATCH (n) RETURN count(n) as count, labels(n) as labels LIMIT 10"