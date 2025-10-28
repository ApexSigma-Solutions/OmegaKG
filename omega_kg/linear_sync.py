"""
Linear synchronization module for Omega_KG.

Handles bidirectional sync between Linear issues and Neo4j knowledge graph,
with updates reflected back to Obsidian vault files.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from neo4j import GraphDatabase
from pydantic import BaseModel

from omega_kg.settings import settings

logger = logging.getLogger(__name__)


class LinearIssue(BaseModel):
    """Linear issue data model."""
    identifier: str
    state: Optional[Dict[str, Any]] = None
    priority: Optional[int] = None
    updatedAt: Optional[str] = None


class LinearSync:
    """Handles synchronization between Linear and Neo4j/Obsidian."""

    def __init__(self):
        """Initialize the LinearSync instance."""
        self.driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )
        self.vault = Path(settings.obsidian_vault_path)

    def handle_linear_webhook(self, payload: Dict[str, Any]) -> None:
        """
        Handle Linear webhook payload.

        Routes to appropriate handler based on action type.

        Args:
            payload: Webhook payload from Linear
        """
        action = payload.get("action")
        data = payload.get("data", {})

        if action == "update":
            self._sync_issue_update(data)
        elif action == "remove":
            self._handle_issue_deletion(data)
        else:
            logger.warning(f"Unknown webhook action: {action}")

    def _sync_issue_update(self, issue: Dict[str, Any]) -> None:
        """
        Sync issue update to Neo4j and Obsidian.

        Args:
            issue: Issue data from Linear webhook
        """
        identifier = issue.get("identifier")
        if not identifier:
            logger.error("Issue update missing identifier")
            return

        # Map Linear state to Omega_KG status
        linear_state = issue.get("state", {}).get("name", "")
        status_mapping = {
            "Backlog": "draft",
            "Todo": "ready",
            "In Progress": "active",
            "Done": "completed",
            "Canceled": "archived"
        }
        omega_status = status_mapping.get(linear_state, "draft")

        with self.driver.session() as session:
            # Update Neo4j task node
            result = session.run(
                """
                MATCH (t:Task {linear_id: $linear_id})
                SET t.status = $status,
                    t.linear_status = $linear_status,
                    t.linear_priority = $priority,
                    t.transitioned_at = datetime($updated_at)
                RETURN t.uid, t.filepath
                """,
                linear_id=identifier,
                status=omega_status,
                linear_status=linear_state,
                priority=issue.get("priority"),
                updated_at=issue.get("updatedAt")
            )

            task_record = result.single()
            if task_record:
                task_uid = task_record["t.uid"]
                task_filepath = task_record["t.filepath"]
                logger.info(
                    f"Updated task {task_uid} to status {omega_status}"
                )

                # Update Obsidian file
                self._update_task_file(task_filepath, issue)
            else:
                logger.warning(f"No task found for Linear ID: {identifier}")

    def _update_task_file(self, filepath: str, issue: Dict[str, Any]) -> None:
        """
        Update the Obsidian task file with Linear data.

        Args:
            filepath: Relative path to task file
            issue: Issue data from Linear
        """
        full_path = self.vault / filepath
        if not full_path.exists():
            logger.warning(f"Task file not found: {full_path}")
            return

        try:
            content = full_path.read_text(encoding="utf-8")

            # Update frontmatter with Linear data
            # This is a simplified implementation - in practice you'd want
            # more sophisticated frontmatter parsing/updating
            linear_status = issue.get("state", {}).get("name", "")

            # Simple frontmatter update (this could be improved)
            updated_content = content
            if "linear_status:" in content:
                # Replace existing status
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if line.startswith("linear_status:"):
                        lines[i] = f"linear_status: {linear_status}"
                        break
                updated_content = '\n'.join(lines)
            else:
                # Add status if not present
                if "---" in content:
                    parts = content.split("---", 2)
                    if len(parts) >= 2:
                        frontmatter = parts[1]
                        frontmatter += f"\nlinear_status: {linear_status}"
                        updated_content = (
                            "---" + frontmatter + "---" + parts[2]
                        )

            full_path.write_text(updated_content, encoding="utf-8")
            logger.info(f"Updated task file: {full_path}")

        except Exception as e:
            logger.error(f"Failed to update task file {full_path}: {e}")

    def _handle_issue_deletion(self, issue: Dict[str, Any]) -> None:
        """
        Handle Linear issue deletion.

        Args:
            issue: Issue data from Linear webhook
        """
        identifier = issue.get("identifier")
        if not identifier:
            logger.error("Issue deletion missing identifier")
            return

        with self.driver.session() as session:
            # Mark task as archived or remove Linear references
            result = session.run(
                """
                MATCH (t:Task {linear_id: $linear_id})
                SET t.status = "archived",
                    t.linear_id = null,
                    t.linear_status = null,
                    t.transitioned_at = datetime()
                RETURN t.uid
                """,
                linear_id=identifier
            )

            task_record = result.single()
            if task_record:
                task_uid = task_record["t.uid"]
                logger.info(
                    f"Archived task {task_uid} due to Linear issue deletion"
                )
            else:
                logger.warning(
                    f"No task found for deleted Linear ID: {identifier}"
                )
