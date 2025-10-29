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

class TestCheckNodesQueryModifications:
    """Test the specific query modifications made in the current branch."""

    @patch('omega_kg.check_nodes.GraphDatabase.driver')
    @patch('builtins.print')
    def test_all_nodes_query_without_order_by(self, mock_print, mock_driver):
        """
        Verify that the all-nodes query does not include ORDER BY clause.
        
        The modification removed 'ORDER BY count DESC' from the query to match
        the simplified version: 'MATCH (n) RETURN count(n) as count, labels(n) as labels LIMIT 10'
        """
        # Mock driver and session
        driver = Mock()
        session = Mock()
        mock_driver.return_value = driver
        driver.session.return_value = session
        
        # Mock results
        count_result = Mock()
        count_result.single.return_value = {'count': 0}
        
        all_nodes_result = Mock()
        all_nodes_result.__iter__ = Mock(return_value=iter([
            {'count': 5, 'labels': ['Task']},
            {'count': 2, 'labels': ['Plan']}
        ]))
        
        def run_side_effect(query, *args, **kwargs):
            if "MATCH (t:Task) RETURN count" in query:
                return count_result
            if query.strip().startswith("MATCH (n) RETURN"):
                # Verify query does NOT contain ORDER BY
                assert "ORDER BY" not in query
                return all_nodes_result
            return Mock()
        
        session.run.side_effect = run_side_effect
        
        # Reload module
        import importlib, omega_kg.check_nodes as mod
        importlib.reload(mod)
        
        # Verify the query was executed
        issued_queries = [c.args[0] for c in session.run.call_args_list]
        all_nodes_queries = [q for q in issued_queries if q.strip().startswith("MATCH (n) RETURN")]
        assert len(all_nodes_queries) > 0
        for query in all_nodes_queries:
            assert "ORDER BY" not in query, "Query should not contain ORDER BY clause"

    @patch('omega_kg.check_nodes.GraphDatabase.driver')
    @patch('builtins.print')
    def test_limit_applied_to_all_nodes_query(self, mock_print, mock_driver):
        """Verify LIMIT 10 is present in the all-nodes query."""
        driver = Mock()
        session = Mock()
        mock_driver.return_value = driver
        driver.session.return_value = session
        
        count_result = Mock()
        count_result.single.return_value = None
        
        all_nodes_result = Mock()
        all_nodes_result.__iter__ = Mock(return_value=iter([]))
        
        def run_side_effect(query, *args, **kwargs):
            if "MATCH (t:Task)" in query:
                return count_result
            if query.strip().startswith("MATCH (n) RETURN"):
                assert "LIMIT 10" in query
                return all_nodes_result
            return Mock()
        
        session.run.side_effect = run_side_effect
        
        import importlib, omega_kg.check_nodes as mod
        importlib.reload(mod)
        
        issued_queries = [c.args[0] for c in session.run.call_args_list]
        all_nodes_queries = [q for q in issued_queries if "MATCH (n) RETURN" in q]
        assert any("LIMIT 10" in q for q in all_nodes_queries)

    @patch('omega_kg.check_nodes.GraphDatabase.driver')
    @patch('builtins.print')
    def test_prints_node_counts_with_labels(self, mock_print, mock_driver):
        """Verify that node counts are printed with their labels."""
        driver = Mock()
        session = Mock()
        mock_driver.return_value = driver
        driver.session.return_value = session
        
        # Mock task count query
        count_result = Mock()
        count_result.single.return_value = None
        
        # Mock all nodes query with multiple node types
        all_nodes_result = Mock()
        all_nodes_result.__iter__ = Mock(return_value=iter([
            {'count': 15, 'labels': ['Task']},
            {'count': 8, 'labels': ['Plan']},
            {'count': 3, 'labels': ['Commit']}
        ]))
        
        def run_side_effect(query, *args, **kwargs):
            if "MATCH (t:Task)" in query:
                return count_result
            return all_nodes_result
        
        session.run.side_effect = run_side_effect
        
        import importlib, omega_kg.check_nodes as mod
        importlib.reload(mod)
        
        # Verify prints were made for node counts
        print_calls = [str(c) for c in mock_print.call_args_list]
        assert any("['Task']" in call and "15" in call for call in print_calls)
        assert any("['Plan']" in call and "8" in call for call in print_calls)
        assert any("['Commit']" in call and "3" in call for call in print_calls)

    @patch('omega_kg.check_nodes.GraphDatabase.driver')
    @patch('builtins.print')
    def test_driver_close_called(self, mock_print, mock_driver):
        """Verify the driver.close() is called to clean up resources."""
        driver = Mock()
        session = Mock()
        mock_driver.return_value = driver
        driver.session.return_value = session
        
        # Mock minimal results
        result = Mock()
        result.single.return_value = None
        result.__iter__ = Mock(return_value=iter([]))
        session.run.return_value = result
        
        import importlib, omega_kg.check_nodes as mod
        importlib.reload(mod)
        
        # Verify driver.close() was called
        driver.close.assert_called_once()

    @patch('omega_kg.check_nodes.GraphDatabase.driver')
    @patch('builtins.print')
    def test_no_tasks_scenario(self, mock_print, mock_driver):
        """Test behavior when there are zero tasks in the database."""
        driver = Mock()
        session = Mock()
        mock_driver.return_value = driver
        driver.session.return_value = session
        
        # Mock zero task count
        count_result = Mock()
        count_result.single.return_value = {'count': 0}
        
        # Mock all nodes query
        all_nodes_result = Mock()
        all_nodes_result.__iter__ = Mock(return_value=iter([]))
        
        def run_side_effect(query, *args, **kwargs):
            if "MATCH (t:Task) RETURN count" in query:
                return count_result
            return all_nodes_result
        
        session.run.side_effect = run_side_effect
        
        import importlib, omega_kg.check_nodes as mod
        importlib.reload(mod)
        
        # Verify it printed total count but NOT sample tasks
        print_calls = [str(c) for c in mock_print.call_args_list]
        assert any("Total Task nodes: 0" in call for call in print_calls)
        # Should NOT query for sample tasks when count is 0
        issued_queries = [c.args[0] for c in session.run.call_args_list]
        sample_queries = [q for q in issued_queries if "MATCH (t:Task) RETURN t LIMIT 5" in q]
        assert len(sample_queries) == 0, "Should not fetch sample tasks when count is 0"

    @patch('omega_kg.check_nodes.GraphDatabase.driver')
    @patch('builtins.print')
    def test_sample_task_limit_is_five(self, mock_print, mock_driver):
        """Verify sample tasks query limits to exactly 5 tasks."""
        driver = Mock()
        session = Mock()
        mock_driver.return_value = driver
        driver.session.return_value = session
        
        # Mock task count > 0
        count_result = Mock()
        count_result.single.return_value = {'count': 10}
        
        # Mock sample tasks
        sample_result = Mock()
        sample_result.__iter__ = Mock(return_value=iter([
            {'t': {'uid': f'task-{i}', 'title': f'Task {i}'}} for i in range(5)
        ]))
        
        all_nodes_result = Mock()
        all_nodes_result.__iter__ = Mock(return_value=iter([]))
        
        def run_side_effect(query, *args, **kwargs):
            if "MATCH (t:Task) RETURN count" in query:
                return count_result
            if "MATCH (t:Task) RETURN t LIMIT 5" in query:
                return sample_result
            return all_nodes_result
        
        session.run.side_effect = run_side_effect
        
        import importlib, omega_kg.check_nodes as mod
        importlib.reload(mod)
        
        # Verify sample query with LIMIT 5 was executed
        issued_queries = [c.args[0] for c in session.run.call_args_list]
        sample_queries = [q for q in issued_queries if "MATCH (t:Task) RETURN t" in q]
        assert any("LIMIT 5" in q for q in sample_queries)


class TestCheckNodesEdgeCases:
    """Test edge cases and error conditions."""

    @patch('omega_kg.check_nodes.GraphDatabase.driver')
    @patch('builtins.print')
    def test_handles_empty_labels(self, mock_print, mock_driver):
        """Test handling of nodes with empty labels."""
        driver = Mock()
        session = Mock()
        mock_driver.return_value = driver
        driver.session.return_value = session
        
        count_result = Mock()
        count_result.single.return_value = None
        
        # Mock result with empty labels
        all_nodes_result = Mock()
        all_nodes_result.__iter__ = Mock(return_value=iter([
            {'count': 5, 'labels': []},
            {'count': 3, 'labels': ['Task']}
        ]))
        
        def run_side_effect(query, *args, **kwargs):
            if "MATCH (t:Task)" in query:
                return count_result
            return all_nodes_result
        
        session.run.side_effect = run_side_effect
        
        # Should not raise exception
        import importlib, omega_kg.check_nodes as mod
        importlib.reload(mod)
        
        # Verify it handled empty labels gracefully
        print_calls = [str(c) for c in mock_print.call_args_list]
        assert any("[]" in call for call in print_calls)

    @patch('omega_kg.check_nodes.GraphDatabase.driver')
    @patch('builtins.print')
    def test_handles_multiple_labels_per_node(self, mock_print, mock_driver):
        """Test handling of nodes with multiple labels."""
        driver = Mock()
        session = Mock()
        mock_driver.return_value = driver
        driver.session.return_value = session
        
        count_result = Mock()
        count_result.single.return_value = None
        
        # Mock result with multiple labels
        all_nodes_result = Mock()
        all_nodes_result.__iter__ = Mock(return_value=iter([
            {'count': 2, 'labels': ['Task', 'Active', 'Pinned']},
        ]))
        
        def run_side_effect(query, *args, **kwargs):
            if "MATCH (t:Task)" in query:
                return count_result
            return all_nodes_result
        
        session.run.side_effect = run_side_effect
        
        # Should handle multiple labels
        import importlib, omega_kg.check_nodes as mod
        importlib.reload(mod)
        
        print_calls = [str(c) for c in mock_print.call_args_list]
        assert any("['Task', 'Active', 'Pinned']" in call for call in print_calls)