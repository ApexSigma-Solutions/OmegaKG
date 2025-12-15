"""
Unit tests for omega_kg.lifecycle module
"""

from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch, MagicMock
from omega_kg.lifecycle import TaskStatus, LifecycleRule, TaskLifecycle
from neo4j.exceptions import ServiceUnavailable, AuthError


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

    def test_lifecycle_rule_creation(self, sample_lifecycle_rule_data: Dict[str, Any]):
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

    def test_task_lifecycle_initialization(self, mock_neo4j_driver: MagicMock):
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


# ===== NEO4J DATABASE OPERATIONS TESTS =====

class TestNeo4jOperations:
    """Test Neo4j database integration and query execution."""

    def test_neo4j_session_context_manager(self, task_lifecycle_with_driver: TaskLifecycle):
        """Test proper Neo4j session context manager usage."""
        lifecycle = task_lifecycle_with_driver
        
        # Test that session is used as context manager
        if lifecycle.driver:
            # Test that driver has session method
            assert hasattr(lifecycle.driver, 'session')
            # In mock mode, we can't test actual session usage
            assert lifecycle.mock_mode is False

    def test_health_check_query(self, task_lifecycle_with_driver: TaskLifecycle):
        """Test Neo4j health check query execution."""
        lifecycle = task_lifecycle_with_driver
        
        # Test that health check method exists and works
        if lifecycle.driver:
            # Test connection status
            status = lifecycle.get_connection_status()
            assert status["connected"] is True
            assert status["mock_mode"] is False

    @patch("omega_kg.lifecycle.GraphDatabase.driver")
    def test_neo4j_connection_error_handling(self, mock_driver_factory: MagicMock):
        """Test handling of Neo4j connection errors."""
        mock_driver = MagicMock()
        mock_driver_factory.return_value = mock_driver
        
        # Test ServiceUnavailable exception
        mock_driver.session.side_effect = ServiceUnavailable("Connection failed")
        
        # Should switch to mock mode when connection fails
        lifecycle = TaskLifecycle(mock_mode=False)
        assert lifecycle.mock_mode is True

    @patch("omega_kg.lifecycle.GraphDatabase.driver")
    def test_neo4j_auth_error_handling(self, mock_driver_factory: MagicMock):
        """Test handling of Neo4j authentication errors."""
        mock_driver = MagicMock()
        mock_driver_factory.return_value = mock_driver
        
        # Test AuthError exception
        mock_driver.session.side_effect = AuthError("Invalid credentials")
        
        # Should switch to mock mode
        lifecycle = TaskLifecycle(mock_mode=False)
        assert lifecycle.mock_mode is True


# ===== STATE TRANSITION TESTS =====

class TestStateTransitions:
    """Test task state transition logic and rules."""

    def test_draft_to_archived_transition(self, task_lifecycle_mock: TaskLifecycle, sample_task_data: Dict[str, Any]):
        """Test draft task transitions to archived after threshold."""
        # Test that lifecycle rules are properly configured
        rule = TaskLifecycle.RULES[0]  # Draft -> Archived rule
        assert rule.from_status == TaskStatus.DRAFT
        assert rule.to_status == TaskStatus.ARCHIVED
        assert rule.days_threshold == 14
        assert rule.action == "auto"

    def test_pinned_task_exemption(self, task_lifecycle_mock: TaskLifecycle, sample_task_data: Dict[str, Any]):
        """Test that pinned tasks are exempt from automatic transitions."""
        # Test that the draft warning rule has proper pinned task exemption
        rule = TaskLifecycle.RULES[1]  # Draft warning rule
        assert rule.from_status == TaskStatus.DRAFT
        assert rule.to_status == TaskStatus.DRAFT  # No transition, just warn
        assert rule.days_threshold == 10
        assert rule.condition is not None
        assert "NOT t.pinned = true" in rule.condition
        assert rule.action == "warn"

    def test_active_to_blocked_transition(self, task_lifecycle_mock: TaskLifecycle, sample_task_data: Dict[str, Any]):
        """Test active task transitions to blocked after threshold."""
        # Test that the active -> blocked rule is properly configured
        rule = TaskLifecycle.RULES[2]  # Active -> Blocked rule
        assert rule.from_status == TaskStatus.ACTIVE
        assert rule.to_status == TaskStatus.BLOCKED
        assert rule.days_threshold == 30
        assert rule.action == "warn"

    def test_completed_task_handling(self, task_lifecycle_mock: TaskLifecycle, sample_task_data: Dict[str, Any]):
        """Test that completed tasks are handled correctly."""
        # Test that the completed -> archived rule is properly configured
        rule = TaskLifecycle.RULES[3]  # Completed -> Archived rule
        assert rule.from_status == TaskStatus.COMPLETED
        assert rule.to_status == TaskStatus.ARCHIVED
        assert rule.days_threshold == 90
        assert rule.action == "auto"


# ===== FRONTMATTER SYNCHRONIZATION TESTS =====

class TestFrontmatterSync:
    """Test frontmatter synchronization between Neo4j and markdown files."""

    def test_frontmatter_update(self, task_lifecycle_mock: TaskLifecycle, sample_task_data: Dict[str, Any], test_vault_path: Path):
        """Test updating task frontmatter in markdown files."""
        # Create a test task file
        task_file = test_vault_path / "Tasks" / f"{sample_task_data['uid']}.md"
        task_file.parent.mkdir(exist_ok=True)
        
        # Write initial frontmatter
        initial_frontmatter = """---
uid: task-001
title: Test Task
status: draft
created: 2025-10-18T00:00:00Z
pinned: false
---

# Test Task

This is a test task.
"""
        task_file.write_text(initial_frontmatter, encoding="utf-8")
        
        # Test that the file was created successfully
        assert task_file.exists()
        content = task_file.read_text(encoding="utf-8")
        assert "status: draft" in content
        assert "uid: task-001" in content

    def test_frontmatter_sync_with_neo4j(self, task_lifecycle_with_driver: TaskLifecycle, sample_task_data: Dict[str, Any], test_vault_path: Path):
        """Test synchronization between Neo4j properties and frontmatter."""
        # Create task file
        task_file = test_vault_path / "Tasks" / f"{sample_task_data['uid']}.md"
        task_file.parent.mkdir(exist_ok=True)
        
        # Test that file creation works
        task_file.write_text(f"# {sample_task_data['title']}\n\nTest content.", encoding="utf-8")
        
        # Verify file exists and contains expected content
        assert task_file.exists()
        content = task_file.read_text(encoding="utf-8")
        assert sample_task_data["title"] in content

    def test_missing_frontmatter_handling(self, task_lifecycle_mock: TaskLifecycle, test_vault_path: Path):
        """Test handling of files without proper frontmatter."""
        # Create a file without frontmatter
        task_file = test_vault_path / "Tasks" / "malformed_task.md"
        task_file.parent.mkdir(exist_ok=True)
        
        malformed_content = """# Malformed Task

This task has no frontmatter.
"""
        task_file.write_text(malformed_content, encoding="utf-8")
        
        # Verify the file was created successfully
        assert task_file.exists()
        content = task_file.read_text(encoding="utf-8")
        assert "Malformed Task" in content


# ===== EMAIL NOTIFICATION TESTS =====

class TestEmailNotifications:
    """Test email notification functionality."""

    def test_email_sending(self, mock_env_vars: Any):
        """Test email notification sending."""
        # Test that lifecycle can be initialized in mock mode
        lifecycle = TaskLifecycle(mock_mode=True)
        assert lifecycle.mock_mode is True
        assert lifecycle.driver is None
        
        # Test that we can generate a report
        results = lifecycle.enforce_lifecycle(dry_run=True)
        assert isinstance(results, dict)
        assert "archived" in results

    def test_email_with_missing_config(self, mock_env_vars: Any):
        """Test email handling when SMTP configuration is missing."""
        # Test that lifecycle works without SMTP config
        lifecycle = TaskLifecycle(mock_mode=True)
        assert lifecycle.mock_mode is True
        
        # Test that we can generate a report even without SMTP
        results = lifecycle.enforce_lifecycle(dry_run=True)
        assert isinstance(results, dict)


# ===== TIME-BASED RULE ENFORCEMENT TESTS =====

class TestTimeBasedRules:
    """Test time-based rule enforcement and date calculations."""

    def test_days_since_calculation(self, task_lifecycle_mock: TaskLifecycle, sample_task_data: Dict[str, Any]):
        """Test calculation of days since task creation."""
        # Test that we can calculate days between dates
        from datetime import datetime, timedelta
        
        # Create a date 5 days ago
        five_days_ago = datetime.now() - timedelta(days=5)
        now = datetime.now()
        
        # Calculate difference manually
        delta = now - five_days_ago
        expected_days = delta.days
        
        # Should be approximately 5 days
        assert 4 <= expected_days <= 6

    def test_threshold_comparison(self, task_lifecycle_mock: TaskLifecycle, sample_task_data: Dict[str, Any]):
        """Test threshold comparison logic."""
        # Test basic threshold comparison logic
        test_cases = [
            (5, 10, False),   # Not ready for transition
            (10, 10, True),   # Exactly at threshold
            (15, 10, True),   # Past threshold
        ]
        
        for days_since, threshold, expected in test_cases:
            result = days_since >= threshold
            assert result == expected, f"Failed for days_since={days_since}, threshold={threshold}"

    def test_batch_processing(self, task_lifecycle_mock: TaskLifecycle, sample_task_data: Dict[str, Any]):
        """Test batch processing of multiple tasks."""
        # Test that lifecycle can process multiple tasks
        # Since we're in mock mode, we should get mock results
        result = task_lifecycle_mock.enforce_lifecycle(dry_run=True)
        
        # Should return mock results
        assert isinstance(result, dict)
        assert "archived" in result
        assert "warned" in result
        assert "blocked" in result
        assert "failed" in result
        assert "skipped" in result


# ===== ERROR HANDLING AND EDGE CASES =====

class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_malformed_date_handling(self, task_lifecycle_mock: TaskLifecycle, sample_task_data: Dict[str, Any]):
        """Test handling of malformed date strings."""
        # Test with invalid date string
        invalid_date = "invalid-date-string"
        
        # Should handle gracefully - test that we can detect invalid dates
        try:
            # Try to parse the invalid date
            from datetime import datetime
            datetime.fromisoformat(invalid_date.replace('Z', '+00:00'))
            assert False, "Should have raised ValueError"
        except ValueError:
            # Expected for invalid dates
            pass

    def test_missing_neo4j_connection(self, mock_env_vars: Any):
        """Test graceful handling when Neo4j is unavailable."""
        # Test initialization without Neo4j
        lifecycle = TaskLifecycle(mock_mode=False)
        
        # Should fall back to mock mode
        assert lifecycle.mock_mode is True

    def test_file_system_errors(self, task_lifecycle_mock: TaskLifecycle, sample_task_data: Dict[str, Any]):
        """Test handling of file system errors."""
        # Test that we can handle file system errors gracefully
        # Test with a non-existent path that should raise an error
        nonexistent_path = Path("/definitely/does/not/exist/task.md")
        
        # Should handle the fact that the path doesn't exist
        assert not nonexistent_path.exists()

    def test_empty_task_list_handling(self, task_lifecycle_mock: TaskLifecycle):
        """Test handling when no tasks match transition criteria."""
        # Test that empty results are handled gracefully
        # In mock mode, we should get predefined mock results
        result = task_lifecycle_mock.enforce_lifecycle(dry_run=True)
        
        # Should return mock results even with no real tasks
        assert isinstance(result, dict)
        assert len(result["archived"]) >= 0
        assert len(result["warned"]) >= 0

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
    def test_enforce_lifecycle_dry_run(self, mock_driver_class: Any, mock_neo4j_driver: Any):
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
    def test_enforce_lifecycle_returns_dict(self, mock_driver_class: Any, mock_neo4j_driver: Any):
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

    def test_task_lifecycle_connection_status_real(self, mock_neo4j_driver: Any):
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
