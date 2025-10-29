"""
Tests for omega_kg.obsidian_sync.sync_task_note UID/status normalization and parameter mapping.
"""
from unittest.mock import MagicMock, patch
from omega_kg.obsidian_sync import ObsidianNeo4jSync


def test_sync_task_note_uid_fallback_and_status_strip(tmp_path):
    """
    Unit test for ObsidianNeo4jSync.sync_task_note that verifies UID fallback to filename, status normalization, and filepath parameter mapping.
    
    Creates a temporary vault with a Tasks/mytask.md containing YAML front matter where `uid` is a template placeholder and `status` is "[ready]". Patches settings and the Neo4j driver, calls sync_task_note, and asserts that the executed Cypher contains a MERGE for a Task and that the parameters include `uid` == "mytask", `status` == "ready", and `filepath` == "Tasks/mytask.md".
    
    Parameters:
    	tmp_path (pathlib.Path): pytest temporary directory fixture used to create the test vault and files.
    """
    vault = tmp_path / "vault"
    tasks = vault / "Tasks"
    tasks.mkdir(parents=True)
    md = tasks / "mytask.md"
    md.write_text(
        """---
uid: "<% tp.date.now() %>"
title: Demo
status: "[ready]"
---
Body
""",
        encoding="utf-8",
    )

    with patch("omega_kg.obsidian_sync.settings") as mock_settings, patch(
        "omega_kg.obsidian_sync.GraphDatabase"
    ) as mock_gdb:
        mock_settings.obsidian_vault_path = str(vault)
        mock_settings.neo4j_uri = "bolt://local"
        mock_settings.neo4j_user = "neo4j"
        mock_settings.neo4j_password = "pw"

        driver = MagicMock()
        session = MagicMock()
        driver.session.return_value.__enter__.return_value = session
        mock_gdb.driver.return_value = driver

        sync = ObsidianNeo4jSync(mock_mode=False)
        sync.sync_task_note(md)

        # Verify run() called with normalized params
        called_query = session.run.call_args[0][0]
        called_kwargs = session.run.call_args.kwargs
        assert "MERGE (t:Task" in called_query
        assert called_kwargs["uid"] == "mytask"
        assert called_kwargs["status"] == "ready"
        assert called_kwargs["filepath"] == "Tasks/mytask.md"