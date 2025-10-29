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
        """
        Validate that _handle_issue_deletion triggers a database update for the given issue identifier.
        
        Sets up a mocked Neo4j driver and session plus patched settings, instantiates LinearSync, calls _handle_issue_deletion with an issue containing an `identifier`, and asserts that a Cypher query was executed exactly once via the session.
        """
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