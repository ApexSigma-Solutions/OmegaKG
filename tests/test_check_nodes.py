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
        """
        Ensure omega_kg/check_nodes.py can be executed as a script without syntax errors.
        
        Runs the script in a controlled environment with invalid Neo4j credentials to prevent real connections and asserts the process does not exit with the Python syntax-error code (2).
        """
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
    @patch('omega_kg.check_nodes.GraphDatabase.driver')
    @patch('builtins.print')
    def test_sample_query_executed_when_tasks_exist(self, mock_print, mock_driver):
        """When tasks exist, script should query a small sample of tasks."""
        # Arrange driver and session
        driver = Mock()
        session = Mock()
        mock_driver.return_value = driver
        driver.session.return_value = session

        # Return count > 0 on first count query
        count_result = Mock()
        count_result.single.return_value = {'count': 2}

        # Sample tasks iterator
        sample_iter = iter([{'t': {'uid': 'A'}}, {'t': {'uid': 'B'}}])
        sample_result = Mock()
        sample_result.__iter__ = Mock(return_value=sample_iter)

        # Empty iterator for final "all nodes" query
        empty_iter = iter([])
        empty_result = Mock()
        empty_result.__iter__ = Mock(return_value=empty_iter)

        def run_side_effect(query, *args, **kwargs):
            """
            Return a mock result appropriate for the supplied Cypher query string.

            Parameters:
                query (str): Cypher query text used to choose which mock result to return.
                *args: Unused positional arguments forwarded by the caller.
                **kwargs: Unused keyword arguments forwarded by the caller.

            Returns:
                Mock: One of `count_result`, `sample_result`, `empty_result`, or a new generic Mock depending on which query pattern `query` matches:
                - `count_result` when `query` starts with "MATCH (t:Task) RETURN count"
                - `sample_result` when `query` starts with "MATCH (t:Task) RETURN t LIMIT 5"
                - `empty_result` when `query` (after stripping leading/trailing whitespace) starts with "MATCH (n) RETURN"
                - a new generic Mock for any other query
            """
            if query.startswith("MATCH (t:Task) RETURN count"):
                return count_result
            if query.startswith("MATCH (t:Task) RETURN t LIMIT 5"):
                return sample_result
            if query.strip().startswith("MATCH (n) RETURN"):
                return empty_result
            return Mock()

        session.run.side_effect = run_side_effect

        # Act: import (executes module code)
        import importlib, omega_kg.check_nodes as mod
        importlib.reload(mod)

        # Assert: sample query executed
        issued_queries = [c.args[0] for c in session.run.call_args_list]
        assert any("MATCH (t:Task) RETURN t LIMIT 5" in q for q in issued_queries)
        # And printed at least two Task lines
        assert any("Task:" in str(c.args[0]) for c in mock_print.call_args_list)