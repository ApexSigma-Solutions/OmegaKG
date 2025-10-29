"""
Unit tests for omega_kg.linear_sync module
"""

from unittest.mock import MagicMock, patch
from pathlib import Path
from omega_kg.linear_sync import LinearSync


class TestLinearSyncInitialization:
    """Test LinearSync initialization"""

    @patch("omega_kg.linear_sync.GraphDatabase.driver")
    def test_linear_sync_init(self, mock_driver_class):
        """Test LinearSync initialization with mocked driver"""
        mock_driver = MagicMock()
        mock_driver_class.return_value = mock_driver

        with patch("omega_kg.linear_sync.settings") as mock_settings:
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_settings.neo4j_user = "neo4j"
            mock_settings.neo4j_password = "password"
            mock_settings.obsidian_vault_path = "./vault"

            sync = LinearSync()

            assert sync.driver is mock_driver
            assert sync.vault == Path("./vault")


class TestHandleLinearWebhook:
    """Test Linear webhook handling"""

    @patch("omega_kg.linear_sync.GraphDatabase.driver")
    def test_handle_update_webhook(self, mock_driver_class):
        """Test handling update webhook"""
        mock_driver = MagicMock()
        mock_driver_class.return_value = mock_driver

        with patch("omega_kg.linear_sync.settings") as mock_settings:
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_settings.neo4j_user = "neo4j"
            mock_settings.neo4j_password = "password"
            mock_settings.obsidian_vault_path = "./vault"

            sync = LinearSync()

            payload = {
                "action": "update",
                "data": {
                    "identifier": "LINEAR-123",
                    "state": {"name": "In Progress"},
                    "priority": 1,
                    "updatedAt": "2025-10-25T12:00:00Z",
                },
            }

            with patch.object(sync, "_sync_issue_update") as mock_update:
                sync.handle_linear_webhook(payload)
                mock_update.assert_called_once()

    @patch("omega_kg.linear_sync.GraphDatabase.driver")
    def test_handle_remove_webhook(self, mock_driver_class):
        """Test handling remove webhook"""
        mock_driver = MagicMock()
        mock_driver_class.return_value = mock_driver

        with patch("omega_kg.linear_sync.settings") as mock_settings:
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_settings.neo4j_user = "neo4j"
            mock_settings.neo4j_password = "password"
            mock_settings.obsidian_vault_path = "./vault"

            sync = LinearSync()

            payload = {
                "action": "remove",
                "data": {"identifier": "LINEAR-123"},
            }

            with patch.object(sync, "_handle_issue_deletion") as mock_delete:
                sync.handle_linear_webhook(payload)
                mock_delete.assert_called_once_with(payload["data"])


class TestSyncIssueUpdate:
    """Test issue update sync logic"""

    @patch("omega_kg.linear_sync.GraphDatabase.driver")
    def test_sync_issue_update_no_result(self, mock_driver_class):
        """Test sync when no task found in Neo4j"""
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_result = None

        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver.session.return_value.__exit__.return_value = None
        mock_session.run.return_value.single.return_value = mock_result
        mock_driver_class.return_value = mock_driver

        with patch("omega_kg.linear_sync.settings") as mock_settings:
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_settings.neo4j_user = "neo4j"
            mock_settings.neo4j_password = "password"
            mock_settings.obsidian_vault_path = "./vault"

            sync = LinearSync()
            issue = {
                "identifier": "LINEAR-999",
                "state": {"name": "In Progress"},
                "priority": 1,
                "updatedAt": "2025-10-25T12:00:00Z",
            }

            sync._sync_issue_update(issue)
            mock_session.run.assert_called_once()


class TestHandleIssueDeletion:
    """Test issue deletion handling"""

    @patch("omega_kg.linear_sync.GraphDatabase.driver")
    def test_handle_issue_deletion(self, mock_driver_class):
        """Test handling issue deletion"""
        mock_driver = MagicMock()
        mock_session = MagicMock()

        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver.session.return_value.__exit__.return_value = None
        mock_driver_class.return_value = mock_driver

        with patch("omega_kg.linear_sync.settings") as mock_settings:
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_settings.neo4j_user = "neo4j"
            mock_settings.neo4j_password = "password"
            mock_settings.obsidian_vault_path = "./vault"

            sync = LinearSync()
            issue = {"identifier": "LINEAR-123"}

            sync._handle_issue_deletion(issue)
            mock_session.run.assert_called_once()
    @patch("omega_kg.linear_sync.GraphDatabase.driver")
    def test_handle_issue_deletion_updates_db(self, mock_driver_class):
        """_handle_issue_deletion should archive the task in Neo4j."""
        driver = MagicMock()
        session = MagicMock()
        driver.session.return_value.__enter__.return_value = session
        mock_driver_class.return_value = driver

        with patch("omega_kg.linear_sync.settings") as mock_settings:
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_settings.neo4j_user = "neo4j"
            mock_settings.neo4j_password = "password"
            mock_settings.obsidian_vault_path = "./vault"

            sync = LinearSync()
            issue = {"identifier": "LIN-123"}
            sync._handle_issue_deletion(issue)

        # Validate Cypher and parameters
        cypher = session.run.call_args[0][0]
        params = session.run.call_args.kwargs
        assert "MATCH (t:Task {linear_id: $linear_id})" in cypher
        assert "SET t.status = 'archived'" in cypher
        assert "t.linear_status = 'Canceled'" in cypher
        assert params["linear_id"] == "LIN-123"

class TestLinearSyncSimplification:
    """Test the simplified LinearSync implementation."""

    @patch("omega_kg.linear_sync.GraphDatabase.driver")
    @patch('builtins.print')
    def test_sync_issue_update_simplified_cypher(self, mock_print, mock_driver_class):
        """Verify _sync_issue_update uses simplified Cypher query."""
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver_class.return_value = mock_driver
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver.session.return_value.__exit__.return_value = None

        # Mock query result with filepath
        mock_result = MagicMock()
        mock_result.__getitem__ = lambda self, key: "tasks/task-001.md"
        mock_session.run.return_value.single.return_value = mock_result

        with patch("omega_kg.linear_sync.settings") as mock_settings:
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_settings.neo4j_user = "neo4j"
            mock_settings.neo4j_password = "password"
            mock_settings.obsidian_vault_path = "./vault"

            sync = LinearSync()
            
            issue = {
                "identifier": "LIN-123",
                "state": {"name": "In Progress"},
                "priority": 2,
                "updatedAt": "2025-01-15T10:00:00Z"
            }

            with patch.object(sync, '_update_task_file'):
                sync._sync_issue_update(issue)

            # Verify Cypher query structure
            cypher_call = mock_session.run.call_args
            query = cypher_call[0][0]
            
            # Should set linear_status, linear_priority, linear_updated
            assert "linear_status" in query
            assert "linear_priority" in query
            assert "linear_updated" in query
            
            # Should NOT set task status directly in this version
            assert "t.status =" not in query or "t.linear_status" in query

    @patch("omega_kg.linear_sync.GraphDatabase.driver")
    @patch('builtins.print')
    def test_sync_issue_update_no_task_found(self, mock_print, mock_driver_class):
        """Test _sync_issue_update when no matching task is found."""
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver_class.return_value = mock_driver
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver.session.return_value.__exit__.return_value = None

        # Return None to simulate no task found
        mock_session.run.return_value.single.return_value = None

        with patch("omega_kg.linear_sync.settings") as mock_settings:
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_settings.neo4j_user = "neo4j"
            mock_settings.neo4j_password = "password"
            mock_settings.obsidian_vault_path = "./vault"

            sync = LinearSync()
            
            issue = {
                "identifier": "LIN-999",
                "state": {"name": "Todo"},
                "updatedAt": "2025-01-15T10:00:00Z"
            }

            sync._sync_issue_update(issue)

            # Should print warning message
            print_calls = [str(call) for call in mock_print.call_args_list]
            assert any("⚠️  No Obsidian task found" in call for call in print_calls)
            assert any("LIN-999" in call for call in print_calls)

    @patch("omega_kg.linear_sync.GraphDatabase.driver")
    def test_update_task_file_uses_frontmatter_library(self, mock_driver_class):
        """Verify _update_task_file uses frontmatter library correctly."""
        from pathlib import Path
        import tempfile
        
        mock_driver = MagicMock()
        mock_driver_class.return_value = mock_driver

        with patch("omega_kg.linear_sync.settings") as mock_settings:
            with tempfile.TemporaryDirectory() as tmpdir:
                mock_settings.neo4j_uri = "bolt://localhost:7687"
                mock_settings.neo4j_user = "neo4j"
                mock_settings.neo4j_password = "password"
                mock_settings.obsidian_vault_path = tmpdir

                sync = LinearSync()
                
                # Create a test file
                test_file = Path(tmpdir) / "test_task.md"
                test_file.write_text("""---
title: Test Task
status: draft
---

# Test Task

Task content here.
""")

                issue = {
                    "identifier": "LIN-456",
                    "state": {"name": "In Progress"},
                    "priority": 1,
                    "updatedAt": "2025-01-15T12:00:00Z"
                }

                with patch('builtins.print'):
                    sync._update_task_file(test_file, issue)

                # Verify file was updated
                updated_content = test_file.read_text()
                assert "linear_status: In Progress" in updated_content
                assert "linear_priority: 1" in updated_content
                assert "linear_updated:" in updated_content
                assert "status: active" in updated_content  # Mapped from "In Progress"

    @patch("omega_kg.linear_sync.GraphDatabase.driver")
    def test_status_mapping_linear_to_obsidian(self, mock_driver_class):
        """Test Linear status to Obsidian status mapping."""
        from pathlib import Path
        import tempfile
        
        mock_driver = MagicMock()
        mock_driver_class.return_value = mock_driver

        status_mappings = [
            ("Backlog", "draft"),
            ("Todo", "ready"),
            ("In Progress", "active"),
            ("Done", "completed"),
            ("Canceled", "archived"),
        ]

        with patch("omega_kg.linear_sync.settings") as mock_settings:
            with tempfile.TemporaryDirectory() as tmpdir:
                mock_settings.neo4j_uri = "bolt://localhost:7687"
                mock_settings.neo4j_user = "neo4j"
                mock_settings.neo4j_password = "password"
                mock_settings.obsidian_vault_path = tmpdir

                sync = LinearSync()
                
                for linear_status, expected_obsidian_status in status_mappings:
                    test_file = Path(tmpdir) / f"task_{linear_status}.md"
                    test_file.write_text("---\ntitle: Test\n---\nContent")

                    issue = {
                        "identifier": "LIN-TEST",
                        "state": {"name": linear_status},
                        "priority": 0,
                        "updatedAt": "2025-01-15T10:00:00Z"
                    }

                    with patch('builtins.print'):
                        sync._update_task_file(test_file, issue)

                    updated_content = test_file.read_text()
                    assert f"status: {expected_obsidian_status}" in updated_content, \
                        f"Linear '{linear_status}' should map to '{expected_obsidian_status}'"

    @patch("omega_kg.linear_sync.GraphDatabase.driver")
    def test_update_task_file_handles_missing_priority(self, mock_driver_class):
        """Test _update_task_file handles missing priority field."""
        from pathlib import Path
        import tempfile
        
        mock_driver = MagicMock()
        mock_driver_class.return_value = mock_driver

        with patch("omega_kg.linear_sync.settings") as mock_settings:
            with tempfile.TemporaryDirectory() as tmpdir:
                mock_settings.neo4j_uri = "bolt://localhost:7687"
                mock_settings.neo4j_user = "neo4j"
                mock_settings.neo4j_password = "password"
                mock_settings.obsidian_vault_path = tmpdir

                sync = LinearSync()
                
                test_file = Path(tmpdir) / "task_no_priority.md"
                test_file.write_text("---\ntitle: Test\n---\nContent")

                issue = {
                    "identifier": "LIN-789",
                    "state": {"name": "Todo"},
                    # priority field omitted
                    "updatedAt": "2025-01-15T10:00:00Z"
                }

                with patch('builtins.print'):
                    sync._update_task_file(test_file, issue)

                updated_content = test_file.read_text()
                # Should default to 0
                assert "linear_priority: 0" in updated_content

    @patch("omega_kg.linear_sync.GraphDatabase.driver")
    @patch('builtins.print')
    def test_update_task_file_prints_success(self, mock_print, mock_driver_class):
        """Verify _update_task_file prints success message."""
        from pathlib import Path
        import tempfile
        
        mock_driver = MagicMock()
        mock_driver_class.return_value = mock_driver

        with patch("omega_kg.linear_sync.settings") as mock_settings:
            with tempfile.TemporaryDirectory() as tmpdir:
                mock_settings.neo4j_uri = "bolt://localhost:7687"
                mock_settings.neo4j_user = "neo4j"
                mock_settings.neo4j_password = "password"
                mock_settings.obsidian_vault_path = tmpdir

                sync = LinearSync()
                
                test_file = Path(tmpdir) / "my_task.md"
                test_file.write_text("---\ntitle: Test\n---\nContent")

                issue = {
                    "identifier": "LIN-SUCCESS",
                    "state": {"name": "Done"},
                    "priority": 3,
                    "updatedAt": "2025-01-15T10:00:00Z"
                }

                sync._update_task_file(test_file, issue)

                print_calls = [str(call) for call in mock_print.call_args_list]
                assert any("✓ Updated" in call and "my_task.md" in call for call in print_calls)
                assert any("Linear" in call for call in print_calls)


class TestLinearSyncHandleIssueDeletion:
    """Test _handle_issue_deletion behavior."""

    @patch("omega_kg.linear_sync.GraphDatabase.driver")
    @patch('builtins.print')
    def test_handle_issue_deletion_archives_task(self, mock_print, mock_driver_class):
        """Verify _handle_issue_deletion marks task as archived."""
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver_class.return_value = mock_driver
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver.session.return_value.__exit__.return_value = None

        with patch("omega_kg.linear_sync.settings") as mock_settings:
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_settings.neo4j_user = "neo4j"
            mock_settings.neo4j_password = "password"
            mock_settings.obsidian_vault_path = "./vault"

            sync = LinearSync()
            
            issue = {"identifier": "LIN-DELETE"}

            sync._handle_issue_deletion(issue)

            # Verify Cypher query
            cypher_call = mock_session.run.call_args
            query = cypher_call[0][0]
            params = cypher_call[1]
            
            # Should set status to archived
            assert "status = 'archived'" in query
            assert "linear_status = 'Canceled'" in query
            assert "transitioned_at = datetime()" in query
            assert params['linear_id'] == "LIN-DELETE"

            # Should print success message
            print_calls = [str(call) for call in mock_print.call_args_list]
            assert any("✓ Archived task" in call for call in print_calls)
            assert any("LIN-DELETE" in call for call in print_calls)


class TestLinearSyncDocstrings:
    """Test that LinearSync docstrings were updated."""

    def test_class_docstring_simplified(self):
        """Verify LinearSync class docstring is concise."""
        assert LinearSync.__doc__ is not None
        doc = LinearSync.__doc__
        
        assert "Bidirectional sync" in doc or "sync" in doc
        assert "Linear" in doc
        assert "Obsidian" in doc
        assert "Neo4j" in doc

    def test_init_docstring_detailed(self):
        """Verify __init__ docstring describes initialization."""
        assert LinearSync.__init__.__doc__ is not None
        doc = LinearSync.__init__.__doc__
        
        assert "Initialize" in doc or "Create" in doc
        assert "driver" in doc
        assert "vault" in doc

    def test_handle_webhook_docstring_updated(self):
        """Verify handle_linear_webhook docstring describes routing."""
        assert LinearSync.handle_linear_webhook.__doc__ is not None
        doc = LinearSync.handle_linear_webhook.__doc__
        
        assert "Route" in doc or "handle" in doc
        assert "update" in doc
        assert "remove" in doc
        assert "action" in doc

    def test_sync_issue_update_docstring_updated(self):
        """Verify _sync_issue_update docstring is descriptive."""
        assert LinearSync._sync_issue_update.__doc__ is not None
        doc = LinearSync._sync_issue_update.__doc__
        
        assert "Synchronize" in doc or "Update" in doc
        assert "Neo4j" in doc
        assert "Obsidian" in doc
        assert "identifier" in doc

    def test_update_task_file_docstring_detailed(self):
        """Verify _update_task_file docstring explains frontmatter update."""
        assert LinearSync._update_task_file.__doc__ is not None
        doc = LinearSync._update_task_file.__doc__
        
        assert "frontmatter" in doc
        assert "linear_status" in doc
        assert "linear_priority" in doc
        assert "linear_updated" in doc

    def test_handle_deletion_docstring_updated(self):
        """Verify _handle_issue_deletion docstring describes behavior."""
        assert LinearSync._handle_issue_deletion.__doc__ is not None
        doc = LinearSync._handle_issue_deletion.__doc__
        
        assert "archived" in doc or "archive" in doc
        assert "deleted" in doc or "deletion" in doc
        assert "identifier" in doc


class TestLinearSyncEdgeCases:
    """Test edge cases and error handling."""

    @patch("omega_kg.linear_sync.GraphDatabase.driver")
    def test_webhook_unknown_action_ignored(self, mock_driver_class):
        """Test that unknown webhook actions are gracefully ignored."""
        mock_driver = MagicMock()
        mock_driver_class.return_value = mock_driver

        with patch("omega_kg.linear_sync.settings") as mock_settings:
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_settings.neo4j_user = "neo4j"
            mock_settings.neo4j_password = "password"
            mock_settings.obsidian_vault_path = "./vault"

            sync = LinearSync()
            
            payload = {
                "action": "unknown_action",
                "data": {"identifier": "LIN-UNKNOWN"}
            }

            # Should not raise exception
            sync.handle_linear_webhook(payload)

    @patch("omega_kg.linear_sync.GraphDatabase.driver")
    def test_status_mapping_handles_unknown_status(self, mock_driver_class):
        """Test that unknown Linear statuses default to 'draft'."""
        from pathlib import Path
        import tempfile
        
        mock_driver = MagicMock()
        mock_driver_class.return_value = mock_driver

        with patch("omega_kg.linear_sync.settings") as mock_settings:
            with tempfile.TemporaryDirectory() as tmpdir:
                mock_settings.neo4j_uri = "bolt://localhost:7687"
                mock_settings.neo4j_user = "neo4j"
                mock_settings.neo4j_password = "password"
                mock_settings.obsidian_vault_path = tmpdir

                sync = LinearSync()
                
                test_file = Path(tmpdir) / "task_unknown_status.md"
                test_file.write_text("---\ntitle: Test\n---\nContent")

                issue = {
                    "identifier": "LIN-UNKNOWN",
                    "state": {"name": "UnknownStatus"},
                    "priority": 0,
                    "updatedAt": "2025-01-15T10:00:00Z"
                }

                with patch('builtins.print'):
                    sync._update_task_file(test_file, issue)

                updated_content = test_file.read_text()
                # Should default to "draft"
                assert "status: draft" in updated_content

    @patch("omega_kg.linear_sync.GraphDatabase.driver")
    def test_handle_webhook_with_missing_data(self, mock_driver_class):
        """Test webhook handling with missing data field."""
        mock_driver = MagicMock()
        mock_driver_class.return_value = mock_driver

        with patch("omega_kg.linear_sync.settings") as mock_settings:
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_settings.neo4j_user = "neo4j"
            mock_settings.neo4j_password = "password"
            mock_settings.obsidian_vault_path = "./vault"

            sync = LinearSync()
            
            payload = {
                "action": "update"
                # data field missing
            }

            # Should handle None data gracefully
            with patch.object(sync, '_sync_issue_update') as mock_sync:
                sync.handle_linear_webhook(payload)
                mock_sync.assert_called_once_with(None)