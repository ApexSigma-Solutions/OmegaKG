"""
Additional tests for omega_kg.linear_sync update flow and frontmatter writes.
"""
from unittest.mock import MagicMock, patch
from pathlib import Path
import frontmatter
from omega_kg.linear_sync import LinearSync


def test_sync_issue_update_updates_frontmatter(tmp_path):
    """
    Verify that syncing a Linear issue update updates the linked task's frontmatter.
    
    Asserts that after invoking LinearSync._sync_issue_update with an issue linked to a task file, the task's frontmatter contains `linear_status`, `linear_priority`, and `linear_updated`, and that `status` is mapped to `"active"`.
    
    Parameters:
        tmp_path (pathlib.Path): Pytest temporary directory fixture used to create the mock vault and task file.
    """
    vault = tmp_path / "vault"
    tasks_dir = vault / "Tasks"
    tasks_dir.mkdir(parents=True)
    task_file = tasks_dir / "TASK-001.md"
    task_file.write_text("---\nstatus: draft\ntitle: T\n---\nBody\n", encoding="utf-8")

    with patch("omega_kg.linear_sync.settings") as mock_settings, patch(
        "omega_kg.linear_sync.GraphDatabase"
    ) as mock_gdb:
        mock_settings.obsidian_vault_path = str(vault)
        mock_settings.neo4j_uri = "bolt://localhost:7687"
        mock_settings.neo4j_user = "neo4j"
        mock_settings.neo4j_password = "pw"

        driver = MagicMock()
        session = MagicMock()
        driver.session.return_value.__enter__.return_value = session
        mock_gdb.driver.return_value = driver
        session.run.return_value.single.return_value = {"t.filepath": "Tasks/TASK-001.md"}

        sync = LinearSync()
        issue = {
            "identifier": "LIN-123",
            "state": {"name": "In Progress"},
            "priority": 2,
            "updatedAt": "2025-10-25T12:00:00Z",
        }
        sync._sync_issue_update(issue)

    post = frontmatter.load(task_file)
    assert post.metadata["linear_status"] == "In Progress"
    assert post.metadata["linear_priority"] == 2
    assert post.metadata["linear_updated"] == "2025-10-25T12:00:00Z"
    # Status should be mapped by _update_task_file
    assert post.metadata["status"] == "active"