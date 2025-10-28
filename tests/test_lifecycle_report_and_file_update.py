"""
Additional tests for omega_kg.lifecycle focusing on report formatting and note updates.
"""
from pathlib import Path
from unittest.mock import patch
import frontmatter
from omega_kg.lifecycle import TaskLifecycle, LifecycleRule, TaskStatus


def test_generate_report_formats_counts(monkeypatch):
    lifecycle = TaskLifecycle(mock_mode=True)
    with patch.object(lifecycle, "_get_stale_active_tasks") as mock_stale:
        mock_stale.return_value = [
            {"t.linear_id": "LIN-1", "t.uid": "TASK-001", "t.title": "Stale 1"},
            {"t.linear_id": None, "t.uid": "TASK-002", "t.title": "Stale 2"},
        ]
        results = {
            "archived": [{"t.uid": "TASK-A", "t.title": "Old Draft", "days_old": 15}],
            "warned": [{"t.uid": "TASK-W", "t.title": "Almost", "days_old": 12}],
            "failed": [],
        }
        report = lifecycle.generate_report(results)
        assert "SUMMARY" in report
        assert "Archived: 1" in report
        assert "Warned: 1" in report
        assert "Stale Active: 2" in report
        assert "AUTO-ARCHIVED" in report
        assert "WARNINGS" in report


def test_update_task_file_writes_frontmatter_and_appends(tmp_path, monkeypatch):
    vault = tmp_path / "vault"
    (vault / "Tasks/sub").mkdir(parents=True)
    uid = "UID-123"
    md_path = vault / f"Tasks/sub/{uid}.md"
    md_path.write_text("---\nstatus: draft\ntitle: Sample\n---\nBody\n", encoding="utf-8")

    with patch("omega_kg.lifecycle.settings") as mock_settings:
        mock_settings.obsidian_vault_path = str(vault)
        lifecycle = TaskLifecycle(mock_mode=True)
        rule = LifecycleRule(
            from_status=TaskStatus.DRAFT, to_status=TaskStatus.ARCHIVED, days_threshold=14
        )
        lifecycle._update_task_file(uid, "archived", rule)

    post = frontmatter.load(md_path)
    assert post.metadata["status"] == "archived"
    lt = post.metadata.get("lifecycle_transition", {})
    assert lt.get("from") == "draft" and lt.get("to") == "archived"
    assert "Lifecycle Transition" in post.content