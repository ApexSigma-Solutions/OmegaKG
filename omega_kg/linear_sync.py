# omega_kg/linear_sync.py

from neo4j import GraphDatabase
from pathlib import Path
import frontmatter
from omega_kg.settings import settings


class LinearSync:
    """Bidirectional sync between Linear and Obsidian via Neo4j"""

    def __init__(self):
        self.driver = GraphDatabase.driver(
            settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
        )
        self.vault = Path(settings.obsidian_vault_path)

    def handle_linear_webhook(self, payload: dict):
        """Process incoming Linear webhook"""
        action = payload.get("action")
        issue = payload.get("data")

        if action == "update":
            self._sync_issue_update(issue)
        elif action == "remove":
            self._handle_issue_deletion(issue)

    def _sync_issue_update(self, issue: dict):
        """Update Obsidian task from Linear issue change"""
        linear_id = issue["identifier"]

        # Update Neo4j
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (t:Task {linear_id: $linear_id})
                SET t.linear_status = $status,
                    t.linear_priority = $priority,
                    t.linear_updated = datetime($updated)
                RETURN t.filepath
            """,
                linear_id=linear_id,
                status=issue["state"]["name"],
                priority=issue.get("priority", 0),
                updated=issue["updatedAt"],
            ).single()

        if not result:
            print(f"⚠️  No Obsidian task found for {linear_id}")
            return

        # Update Obsidian file
        task_path = self.vault / result["t.filepath"]
        self._update_task_file(task_path, issue)

    def _update_task_file(self, path: Path, issue: dict):
        """Update task file frontmatter from Linear data"""
        with open(path, "r", encoding="utf-8") as f:
            post = frontmatter.load(f)

        # Update metadata
        post.metadata["linear_status"] = issue["state"]["name"]
        post.metadata["linear_priority"] = issue.get("priority", 0)
        post.metadata["linear_updated"] = issue["updatedAt"]

        # Map Linear status to Obsidian status
        status_map = {
            "Backlog": "draft",
            "Todo": "ready",
            "In Progress": "active",
            "Done": "completed",
            "Canceled": "archived",
        }
        post.metadata["status"] = status_map.get(issue["state"]["name"], "draft")

        # Write back
        with open(path, "w", encoding="utf-8") as f:
            f.write(frontmatter.dumps(post))

        print(f"✓ Updated {path.name} from Linear")

    def _handle_issue_deletion(self, issue: dict):
        """Handle Linear issue deletion/removal"""
        linear_id = issue["identifier"]

        # Update Neo4j to mark as archived
        with self.driver.session() as session:
            session.run(
                """
                MATCH (t:Task {linear_id: $linear_id})
                SET t.status = 'archived',
                    t.linear_status = 'Canceled',
                    t.transitioned_at = datetime()
            """,
                linear_id=linear_id,
            )

        print(f"✓ Archived task for Linear issue {linear_id}")
