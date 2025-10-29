"""
Unit tests for omega_kg.lifecycle module
"""

from unittest.mock import patch
from omega_kg.lifecycle import TaskStatus, LifecycleRule, TaskLifecycle


class TestTaskStatus:
    """Test the TaskStatus enum"""

    def test_task_status_values(self):
        """Test that TaskStatus enum has all required states"""
        assert TaskStatus.DRAFT.value == "draft"
        assert TaskStatus.READY.value == "ready"
        assert TaskStatus.ACTIVE.value == "active"
        assert TaskStatus.BLOCKED.value == "blocked"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.ARCHIVED.value == "archived"

    def test_task_status_enum_length(self):
        """Test that TaskStatus has exactly 6 states"""
        assert len(TaskStatus) == 6


class TestLifecycleRule:
    """Test the LifecycleRule dataclass"""

    def test_lifecycle_rule_creation(self, sample_lifecycle_rule_data):
        """Test creating a LifecycleRule"""
        rule = LifecycleRule(
            from_status=TaskStatus.DRAFT,
            to_status=TaskStatus.ARCHIVED,
            days_threshold=14,
            condition="NOT t.pinned = true",
            action="auto",
        )

        assert rule.from_status == TaskStatus.DRAFT
        assert rule.to_status == TaskStatus.ARCHIVED
        assert rule.days_threshold == 14
        assert rule.condition == "NOT t.pinned = true"
        assert rule.action == "auto"

    def test_lifecycle_rule_default_action(self):
        """Test that LifecycleRule has default action"""
        rule = LifecycleRule(
            from_status=TaskStatus.DRAFT,
            to_status=TaskStatus.ARCHIVED,
            days_threshold=14,
        )

        assert rule.action == "auto"


class TestTaskLifecycle:
    """Test the TaskLifecycle class"""

    def test_task_lifecycle_initialization(self, mock_neo4j_driver):
        """
        Verify TaskLifecycle initializes a Neo4j driver and exposes the configured vault path name.

        Patches the Neo4j driver and settings to instantiate TaskLifecycle, then asserts a driver is assigned and the vault path's name equals "vault".

        Parameters:
            mock_neo4j_driver: A mock object provided as the Neo4j driver replacement.
        """
        with patch(
            "omega_kg.lifecycle.GraphDatabase.driver", return_value=mock_neo4j_driver
        ):
            with patch("omega_kg.lifecycle.settings") as mock_settings:
                mock_settings.neo4j_uri = "bolt://localhost:7687"
                mock_settings.neo4j_user = "neo4j"
                mock_settings.neo4j_password = "password"
                mock_settings.obsidian_vault_path = "./vault"

                lifecycle = TaskLifecycle()

                assert lifecycle.driver is not None
                assert lifecycle.vault_path.name == "vault"

    def test_lifecycle_rules_defined(self):
        """Test that TaskLifecycle has rules defined"""
        assert len(TaskLifecycle.RULES) > 0
        assert all(isinstance(rule, LifecycleRule) for rule in TaskLifecycle.RULES)

    def test_first_rule_draft_archival(self):
        """Test the first rule (draft decay to archive)"""
        rule = TaskLifecycle.RULES[0]

        assert rule.from_status == TaskStatus.DRAFT
        assert rule.to_status == TaskStatus.ARCHIVED
        assert rule.days_threshold == 14
        assert rule.action == "auto"

    def test_second_rule_draft_warning(self):
        """Test the second rule (draft warning before archival)"""
        rule = TaskLifecycle.RULES[1]

        assert rule.from_status == TaskStatus.DRAFT
        assert rule.action == "warn"
        assert rule.days_threshold == 10

    def test_third_rule_active_stale(self):
        """Test the third rule (active tasks stale detection)"""
        rule = TaskLifecycle.RULES[2]

        assert rule.from_status == TaskStatus.ACTIVE
        assert rule.to_status == TaskStatus.BLOCKED
        assert rule.days_threshold == 30
        assert rule.action == "warn"

    def test_fourth_rule_completed_archival(self):
        """Test the fourth rule (completed archival)"""
        rule = TaskLifecycle.RULES[3]

        assert rule.from_status == TaskStatus.COMPLETED
        assert rule.to_status == TaskStatus.ARCHIVED
        assert rule.days_threshold == 90
        assert rule.action == "auto"


class TestTaskLifecycleEnforcement:
    """Test TaskLifecycle enforcement methods"""

    @patch("omega_kg.lifecycle.GraphDatabase.driver")
    def test_enforce_lifecycle_dry_run(self, mock_driver_class, mock_neo4j_driver):
        """Test enforce_lifecycle with dry_run=True"""
        mock_driver_class.return_value = mock_neo4j_driver

        with patch("omega_kg.lifecycle.settings") as mock_settings:
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_settings.neo4j_user = "neo4j"
            mock_settings.neo4j_password = "password"
            mock_settings.obsidian_vault_path = "./vault"

            lifecycle = TaskLifecycle()
            results = lifecycle.enforce_lifecycle(dry_run=True)

            assert isinstance(results, dict)
            assert "archived" in results
            assert "warned" in results
            assert "blocked" in results
            assert "failed" in results

    @patch("omega_kg.lifecycle.GraphDatabase.driver")
    def test_enforce_lifecycle_returns_dict(self, mock_driver_class, mock_neo4j_driver):
        """Test that enforce_lifecycle returns expected dictionary structure"""
        mock_driver_class.return_value = mock_neo4j_driver

        with patch("omega_kg.lifecycle.settings") as mock_settings:
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_settings.neo4j_user = "neo4j"
            mock_settings.neo4j_password = "password"
            mock_settings.obsidian_vault_path = "./vault"

            lifecycle = TaskLifecycle()
            results = lifecycle.enforce_lifecycle(dry_run=True)

            assert isinstance(results, dict)
            assert all(isinstance(v, list) for v in results.values())


class TestTaskLifecycleMockMode:
    """Test TaskLifecycle with mock mode (no database connection)"""

    def test_task_lifecycle_mock_mode_init(self):
        """Test TaskLifecycle initialization in mock mode"""
        lifecycle = TaskLifecycle(mock_mode=True)

        assert lifecycle.mock_mode is True
        assert lifecycle.driver is None

    def test_task_lifecycle_mock_mode_enforce(self):
        """Test lifecycle enforcement in mock mode returns mock data"""
        lifecycle = TaskLifecycle(mock_mode=True)

        results = lifecycle.enforce_lifecycle(dry_run=True)

        # Should return mock results
        assert isinstance(results, dict)
        assert len(results["archived"]) > 0
        assert len(results["warned"]) > 0

    def test_task_lifecycle_connection_status_mock(self):
        """Test connection status in mock mode"""
        lifecycle = TaskLifecycle(mock_mode=True)

        status = lifecycle.get_connection_status()

        assert status["connected"] is False
        assert status["mock_mode"] is True
        assert status["uri"] == "mock://local"

    def test_task_lifecycle_connection_status_real(self, mock_neo4j_driver):
        """Test connection status with real driver"""
        with patch("omega_kg.lifecycle.GraphDatabase.driver") as mock_driver_class:
            mock_driver_class.return_value = mock_neo4j_driver
            # Configure mock session.run().single() to return a truthy result
            mock_neo4j_driver.session.return_value.run.return_value.single.return_value = {
                "count": 1
            }

            with patch("omega_kg.lifecycle.settings") as mock_settings:
                mock_settings.neo4j_uri = "bolt://localhost:7687"
                mock_settings.neo4j_user = "neo4j"
                mock_settings.neo4j_password = "password"
                mock_settings.obsidian_vault_path = "./vault"

                lifecycle = TaskLifecycle(mock_mode=False)
                status = lifecycle.get_connection_status()

                assert status["connected"] is True
                assert status["mock_mode"] is False
    def test_task_lifecycle_connection_status_mock(self):
        """get_connection_status should reflect mock mode correctly."""
        lc = TaskLifecycle(mock_mode=True)
        status = lc.get_connection_status()
        assert status["connected"] is False
        assert status["mock_mode"] is True
        assert status["uri"] == "mock://local"

    def test_task_lifecycle_connection_status_connected(self, mock_neo4j_driver):
        """get_connection_status should report connected when driver is set."""
        with patch("omega_kg.lifecycle.GraphDatabase.driver", return_value=mock_neo4j_driver):
            with patch("omega_kg.lifecycle.settings") as mock_settings:
                mock_settings.neo4j_uri = "bolt://localhost:7687"
                mock_settings.neo4j_user = "neo4j"
                mock_settings.neo4j_password = "password"
                mock_settings.obsidian_vault_path = "./vault"
                lc = TaskLifecycle(mock_mode=False)
                status = lc.get_connection_status()
                assert status["connected"] is True
                assert status["mock_mode"] is False
                assert status["uri"] == mock_settings.neo4j_uri

class TestLifecycleLoggingToConsole:
    """Test that lifecycle uses print statements instead of logging."""

    @patch('omega_kg.lifecycle.GraphDatabase.driver')
    @patch('builtins.print')
    def test_initialization_prints_connection_status(self, mock_print, mock_driver_class):
        """Verify initialization prints connection status instead of logging."""
        mock_driver = Mock()
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        
        mock_result = Mock()
        mock_result.single.return_value = {'status': 1}
        mock_session.run.return_value = mock_result
        
        mock_driver.session.return_value = mock_session
        mock_driver_class.return_value = mock_driver
        
        with patch('omega_kg.lifecycle.settings') as mock_settings:
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_settings.neo4j_user = "neo4j"
            mock_settings.neo4j_password = "password"
            mock_settings.obsidian_vault_path = "./vault"
            
            lifecycle = TaskLifecycle(mock_mode=False)
            
            # Should print success message
            print_calls = [str(call) for call in mock_print.call_args_list]
            assert any("✓ Neo4j connection established" in call for call in print_calls)
            
            lifecycle.close()

    @patch('omega_kg.lifecycle.GraphDatabase.driver')
    @patch('builtins.print')
    def test_connection_failure_prints_error(self, mock_print, mock_driver_class):
        """Verify connection failures print error messages."""
        from neo4j.exceptions import ServiceUnavailable
        
        mock_driver_class.side_effect = ServiceUnavailable("Connection failed")
        
        with patch('omega_kg.lifecycle.settings') as mock_settings:
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_settings.neo4j_user = "neo4j"
            mock_settings.neo4j_password = "password"
            mock_settings.obsidian_vault_path = "./vault"
            
            lifecycle = TaskLifecycle(mock_mode=False)
            
            # Should print error and fallback messages
            print_calls = [str(call) for call in mock_print.call_args_list]
            assert any("✗ Failed to connect to Neo4j" in call for call in print_calls)
            assert any("⚠ Falling back to mock mode" in call for call in print_calls)
            assert lifecycle.mock_mode is True
            
            lifecycle.close()

    @patch('builtins.print')
    def test_enforce_lifecycle_dry_run_prints_actions(self, mock_print):
        """Verify dry-run mode prints intended actions."""
        lifecycle = TaskLifecycle(mock_mode=True)
        
        # Run in dry-run mode
        results = lifecycle.enforce_lifecycle(dry_run=True)
        
        # Should print dry-run warnings
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("⚠ Running in mock mode" in call for call in print_calls)
        
        lifecycle.close()

    @patch('omega_kg.lifecycle.GraphDatabase.driver')
    @patch('builtins.print')
    def test_transition_task_prints_success(self, mock_print, mock_driver_class):
        """Verify successful task transitions are printed."""
        mock_driver = Mock()
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        mock_driver.session.return_value = mock_session
        mock_driver_class.return_value = mock_driver
        
        # Mock the run method to return minimal result
        mock_result = Mock()
        mock_result.single.return_value = {'status': 1}
        mock_session.run.return_value = mock_result
        
        with patch('omega_kg.lifecycle.settings') as mock_settings:
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_settings.neo4j_user = "neo4j"
            mock_settings.neo4j_password = "password"
            mock_settings.obsidian_vault_path = "./vault"
            
            lifecycle = TaskLifecycle(mock_mode=False)
            lifecycle.driver = mock_driver
            
            rule = LifecycleRule(
                from_status=TaskStatus.DRAFT,
                to_status=TaskStatus.ARCHIVED,
                days_threshold=14
            )
            
            # Mock file operations
            with patch.object(lifecycle, '_update_task_file'):
                lifecycle._transition_task(mock_session, 'TASK-001', rule)
            
            # Should print transition success
            print_calls = [str(call) for call in mock_print.call_args_list]
            assert any("✓ Transitioned TASK-001" in call for call in print_calls)
            assert any("draft → archived" in call for call in print_calls)
            
            lifecycle.close()


class TestLifecycleDocstringUpdates:
    """Test that lifecycle docstrings were updated."""

    def test_init_docstring_updated(self):
        """Verify __init__ docstring has new format."""
        assert TaskLifecycle.__init__.__doc__ is not None
        doc = TaskLifecycle.__init__.__doc__
        
        # Should mention creation/initialization
        assert "Create" in doc or "Initialize" in doc
        # Should describe mock_mode parameter
        assert "mock_mode" in doc
        assert "If True" in doc or "If False" in doc

    def test_check_connection_docstring_updated(self):
        """Verify _check_connection docstring is concise."""
        assert TaskLifecycle._check_connection.__doc__ is not None
        doc = TaskLifecycle._check_connection.__doc__
        
        assert "Check" in doc or "Verify" in doc
        assert "Neo4j driver" in doc

    def test_get_connection_status_docstring_updated(self):
        """Verify get_connection_status docstring describes return value."""
        assert TaskLifecycle.get_connection_status.__doc__ is not None
        doc = TaskLifecycle.get_connection_status.__doc__
        
        # Should describe return dict structure
        assert "connected" in doc
        assert "mock_mode" in doc
        assert "uri" in doc

    def test_transition_task_docstring_updated(self):
        """Verify _transition_task docstring is more descriptive."""
        assert TaskLifecycle._transition_task.__doc__ is not None
        doc = TaskLifecycle._transition_task.__doc__
        
        # Should mention both database and file updates
        assert "Neo4j" in doc
        assert "Obsidian" in doc or "vault" in doc


class TestLifecycleErrorHandling:
    """Test improved error handling in lifecycle module."""

    @patch('omega_kg.lifecycle.GraphDatabase.driver')
    @patch('builtins.print')
    def test_enforce_lifecycle_handles_service_unavailable(self, mock_print, mock_driver_class):
        """Test handling of ServiceUnavailable during enforcement."""
        from neo4j.exceptions import ServiceUnavailable
        
        mock_driver = Mock()
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        mock_driver.session.return_value = mock_session
        
        # Mock connection check success
        mock_result = Mock()
        mock_result.single.return_value = {'status': 1}
        mock_session.run.return_value = mock_result
        mock_driver_class.return_value = mock_driver
        
        with patch('omega_kg.lifecycle.settings') as mock_settings:
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_settings.neo4j_user = "neo4j"
            mock_settings.neo4j_password = "password"
            mock_settings.obsidian_vault_path = "./vault"
            
            lifecycle = TaskLifecycle(mock_mode=False)
            
            # Make session.run raise ServiceUnavailable during enforcement
            mock_session.run.side_effect = ServiceUnavailable("Connection lost")
            
            results = lifecycle.enforce_lifecycle(dry_run=False)
            
            # Should handle gracefully and add to skipped
            assert "skipped" in results
            assert len(results["skipped"]) > 0
            
            # Should print helpful error messages
            print_calls = [str(call) for call in mock_print.call_args_list]
            assert any("✗ Database connection lost" in call for call in print_calls)
            
            lifecycle.close()

    @patch('omega_kg.lifecycle.GraphDatabase.driver')
    @patch('builtins.print')
    def test_enforce_lifecycle_handles_unexpected_errors(self, mock_print, mock_driver_class):
        """Test handling of unexpected errors during enforcement."""
        mock_driver = Mock()
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        mock_driver.session.return_value = mock_session
        
        # Mock connection check success
        mock_result = Mock()
        mock_result.single.return_value = {'status': 1}
        mock_session.run.return_value = mock_result
        mock_driver_class.return_value = mock_driver
        
        with patch('omega_kg.lifecycle.settings') as mock_settings:
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_settings.neo4j_user = "neo4j"
            mock_settings.neo4j_password = "password"
            mock_settings.obsidian_vault_path = "./vault"
            
            lifecycle = TaskLifecycle(mock_mode=False)
            
            # Make session.run raise unexpected error
            mock_session.run.side_effect = RuntimeError("Unexpected error")
            
            results = lifecycle.enforce_lifecycle(dry_run=False)
            
            # Should handle gracefully
            assert "failed" in results
            assert len(results["failed"]) > 0
            
            # Should print error message
            print_calls = [str(call) for call in mock_print.call_args_list]
            assert any("✗ Unexpected error" in call for call in print_calls)
            
            lifecycle.close()


class TestLifecycleMockResults:
    """Test mock results generation."""

    def test_get_mock_results_structure(self):
        """Verify _get_mock_results returns expected structure."""
        lifecycle = TaskLifecycle(mock_mode=True)
        
        results = lifecycle._get_mock_results()
        
        # Should have all expected keys
        assert "archived" in results
        assert "warned" in results
        assert "blocked" in results
        assert "failed" in results
        assert "skipped" in results
        
        # Should have realistic mock data
        assert isinstance(results["archived"], list)
        assert len(results["archived"]) > 0
        
        # Mock tasks should have expected structure
        if len(results["archived"]) > 0:
            task = results["archived"][0]
            assert "t.uid" in task
            assert "t.title" in task
            assert "days_old" in task
        
        lifecycle.close()

    def test_mock_mode_returns_mock_results(self):
        """Verify mock mode returns mock results."""
        lifecycle = TaskLifecycle(mock_mode=True)
        
        results = lifecycle.enforce_lifecycle(dry_run=False)
        
        # Should return mock data
        assert len(results["archived"]) > 0
        assert all("MOCK" in task.get("t.uid", "") for task in results["archived"])
        
        lifecycle.close()


class TestLifecycleConnectionRecovery:
    """Test connection recovery and fallback behavior."""

    @patch('omega_kg.lifecycle.GraphDatabase.driver')
    def test_auth_error_triggers_mock_mode(self, mock_driver_class):
        """Verify AuthError triggers fallback to mock mode."""
        from neo4j.exceptions import AuthError
        
        mock_driver_class.side_effect = AuthError("Invalid credentials")
        
        with patch('omega_kg.lifecycle.settings') as mock_settings:
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_settings.neo4j_user = "neo4j"
            mock_settings.neo4j_password = "wrong"
            mock_settings.obsidian_vault_path = "./vault"
            
            with patch('builtins.print'):
                lifecycle = TaskLifecycle(mock_mode=False)
                
                assert lifecycle.mock_mode is True
                assert lifecycle.driver is None
                
                lifecycle.close()

    @patch('omega_kg.lifecycle.GraphDatabase.driver')
    @patch('builtins.print')
    def test_no_database_connection_available_message(self, mock_print, mock_driver_class):
        """Test message when no database connection is available."""
        mock_driver_class.side_effect = Exception("Cannot connect")
        
        with patch('omega_kg.lifecycle.settings') as mock_settings:
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_settings.neo4j_user = "neo4j"
            mock_settings.neo4j_password = "password"
            mock_settings.obsidian_vault_path = "./vault"
            
            lifecycle = TaskLifecycle(mock_mode=False)
            
            # Now try to enforce without a driver
            lifecycle.driver = None
            lifecycle.mock_mode = False  # Force non-mock mode
            
            results = lifecycle.enforce_lifecycle(dry_run=False)
            
            # Should print error message
            print_calls = [str(call) for call in mock_print.call_args_list]
            assert any("✗ No database connection available" in call for call in print_calls)
            
            lifecycle.close()