# omega_kg/linear_sync.py

import logging
from neo4j import GraphDatabase
from pathlib import Path
import frontmatter
from omega_kg.settings import settings

logger = logging.getLogger(__name__)


class LinearSync:
    """Bidirectional sync between Linear and Obsidian via Neo4j"""

    def __init__(self):
        """
        Initialize the LinearSync instance and prepare the Neo4j driver and Obsidian vault path.
        
        Creates a Neo4j driver using credentials from settings and stores the Obsidian vault path as a Path object.

        Attributes:
            driver: Neo4j driver connected using settings.neo4j_uri and credentials from settings.neo4j_user/settings.neo4j_password.
            vault: Path to the Obsidian vault directory from settings.obsidian_vault_path.
        """
        self.driver = GraphDatabase.driver(
            settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
        )
        self.vault = Path(settings.obsidian_vault_path)

    def handle_linear_webhook(self, payload: dict):
        """
        Route and handle a Linear webhook payload by dispatching supported actions.

        Processes the incoming `payload` dictionary, reading the `action` key to determine the operation and the `data` key for the issue payload. Supported actions:
        - "update": synchronize the provided issue into Neo4j and the Obsidian vault.
        - "remove": mark the corresponding issue as archived in Neo4j.

        Parameters:
            payload (dict): Webhook payload expected to contain:
                - "action" (str): the webhook event type ("update" or "remove").
                - "data" (dict): the Linear issue object for the event.

        """
        action = payload.get("action")
        issue = payload.get("data")

        # Type guard: ensure issue is a dict before proceeding
        if not isinstance(issue, dict):
            logger.warning("Invalid issue data in Linear webhook payload")
            return

        if action == "update":
            self._sync_issue_update(issue)
        elif action == "remove":
            self._handle_issue_deletion(issue)

    def _sync_issue_update(self, issue: dict):
        """
        Synchronize a Linear issue update into Neo4j and the corresponding Obsidian task file.

        Updates the matching Task node's Linear metadata in the Neo4j graph and then updates the Obsidian file's frontmatter for that task. If no matching Task node is found, no file updates are performed.

        Parameters:
            issue (dict): Linear issue payload; must include 'identifier', 'state' (with 'name'), and 'updatedAt'. May include 'priority'.
        """
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
        """
        Update an Obsidian task file's frontmatter with fields from a Linear issue.

        Reads the file at `path`, sets frontmatter keys `linear_status`, `linear_priority`, and
        `linear_updated` from the provided `issue`, maps the Linear state to an Obsidian
        `status` value, and writes the updated frontmatter back to disk.

        Parameters:
            path (Path): Filesystem path to the Obsidian note to update.
            issue (dict): Linear issue payload containing at least `state["name"]` and
                `updatedAt`. May include `priority`; if absent, `linear_priority` will be 0.
        """
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
        """
        Mark the Neo4j Task matching the Linear issue as archived.
        
        Sets the Task's `status` to "archived", `linear_status` to "Canceled", and `transitioned_at` to the current datetime.
        
        Parameters:
            issue (dict): Linear issue payload containing the "identifier" key with the Linear issue ID.
        """
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
