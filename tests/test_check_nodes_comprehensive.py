"""
Comprehensive unit tests for omega_kg.check_nodes module covering all execution paths.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestCheckNodesErrorHandling:
    """Test error handling in check_nodes module."""
    
    @patch('omega_kg.check_nodes.GraphDatabase.driver')
    def test_check_nodes_handles_connection_failure(self, mock_driver_class):
        """Test that check_nodes handles Neo4j connection failures gracefully."""
        from neo4j.exceptions import ServiceUnavailable
        mock_driver_class.side_effect = ServiceUnavailable("Connection refused")
        
        # Should raise the exception (no error handling in the module)
        with pytest.raises(ServiceUnavailable):
            import importlib
            import omega_kg.check_nodes as mod
            importlib.reload(mod)
    
    @patch('omega_kg.check_nodes.GraphDatabase.driver')
    def test_check_nodes_handles_authentication_error(self, mock_driver_class):
        """Test that check_nodes handles authentication errors."""
        from neo4j.exceptions import AuthError
        mock_driver_class.side_effect = AuthError("Invalid credentials")
        
        with pytest.raises(AuthError):
            import importlib
            import omega_kg.check_nodes as mod
            importlib.reload(mod)
    
    @patch('omega_kg.check_nodes.GraphDatabase.driver')
    @patch('builtins.print')
    def test_check_nodes_with_zero_tasks(self, mock_print, mock_driver_class):
        """Test check_nodes behavior when no tasks exist."""
        driver = Mock()
        session = Mock()
        mock_driver_class.return_value = driver
        driver.session.return_value = session
        
        # Return zero tasks
        count_result = Mock()
        count_result.single.return_value = {'count': 0}
        session.run.return_value = count_result
        
        import importlib
        import omega_kg.check_nodes as mod
        importlib.reload(mod)
        
        # Should print "Total Task nodes: 0"
        printed_args = [str(call.args[0]) for call in mock_print.call_args_list]
        assert any("Total Task nodes: 0" in arg for arg in printed_args)
    
    @patch('omega_kg.check_nodes.GraphDatabase.driver')
    @patch('builtins.print')
    def test_check_nodes_query_returns_multiple_label_groups(self, mock_print, mock_driver_class):
        """Test check_nodes with multiple node label groups."""
        driver = Mock()
        session = Mock()
        mock_driver_class.return_value = driver
        driver.session.return_value = session
        
        # Mock task count query
        count_result = Mock()
        count_result.single.return_value = {'count': 0}
        
        # Mock "all nodes" query with multiple label types
        label_results = [
            {'labels': ['Task'], 'count': 10},
            {'labels': ['Decision'], 'count': 5},
            {'labels': ['Commit'], 'count': 3}
        ]
        label_result = Mock()
        label_result.__iter__ = Mock(return_value=iter(label_results))
        
        def run_side_effect(query, *args, **kwargs):
            if "MATCH (t:Task)" in query:
                return count_result
            return label_result
        
        session.run.side_effect = run_side_effect
        
        import importlib
        import omega_kg.check_nodes as mod
        importlib.reload(mod)
        
        # Verify output includes multiple label types
        printed = [str(call.args[0]) for call in mock_print.call_args_list]
        assert any("Task" in p for p in printed)


class TestCheckNodesOutputFormatting:
    """Test output formatting and display."""
    
    @patch('omega_kg.check_nodes.GraphDatabase.driver')
    @patch('builtins.print')
    def test_check_nodes_prints_task_details(self, mock_print, mock_driver_class):
        """Test that task details are printed in expected format."""
        driver = Mock()
        session = Mock()
        mock_driver_class.return_value = driver
        driver.session.return_value = session
        
        # Mock having tasks
        count_result = Mock()
        count_result.single.return_value = {'count': 2}
        
        # Mock task sample
        task_data = [
            {'t': {'uid': 'TASK-001', 'title': 'Test Task 1'}},
            {'t': {'uid': 'TASK-002', 'title': 'Test Task 2'}}
        ]
        sample_result = Mock()
        sample_result.__iter__ = Mock(return_value=iter(task_data))
        
        # Mock empty "all nodes" query
        empty_result = Mock()
        empty_result.__iter__ = Mock(return_value=iter([]))
        
        call_count = [0]
        def run_side_effect(query, *args, **kwargs):
            call_count[0] += 1
            if "MATCH (t:Task) RETURN count" in query:
                return count_result
            elif "MATCH (t:Task) RETURN t LIMIT 5" in query:
                return sample_result
            return empty_result
        
        session.run.side_effect = run_side_effect
        
        import importlib
        import omega_kg.check_nodes as mod
        importlib.reload(mod)
        
        # Verify task details were printed
        printed = [str(call.args[0]) for call in mock_print.call_args_list]
        assert any("TASK-001" in p for p in printed)
        assert any("TASK-002" in p for p in printed)


class TestCheckNodesDriverManagement:
    """Test Neo4j driver lifecycle management."""
    
    @patch('omega_kg.check_nodes.GraphDatabase.driver')
    def test_check_nodes_closes_driver(self, mock_driver_class):
        """Test that driver.close() is called."""
        driver = Mock()
        session = Mock()
        mock_driver_class.return_value = driver
        driver.session.return_value = session
        
        # Mock query results
        result = Mock()
        result.single.return_value = {'count': 0}
        result.__iter__ = Mock(return_value=iter([]))
        session.run.return_value = result
        
        import importlib
        import omega_kg.check_nodes as mod
        importlib.reload(mod)
        
        # Verify driver was closed
        driver.close.assert_called_once()