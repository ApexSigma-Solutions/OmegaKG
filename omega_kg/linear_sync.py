# omega_kg/linear_sync.py

import hmac
import hashlib
import json
import logging
from fastapi import Request, HTTPException
from omega_kg.settings import settings
from pathlib import Path
from neo4j import GraphDatabase
import frontmatter
from typing import Optional, Dict, Any
import neo4j

logger = logging.getLogger(__name__)


class LinearSync:
    """
    Contains all business logic for processing Linear webhooks.
    """

    def __init__(self):
        """
        Initializes the LinearSync engine.
        """
        self.vault = Path(settings.obsidian_vault_path)
        self.driver = GraphDatabase.driver(
            settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
        )
        logger.info("LinearSync engine initialized.")

    async def verify_linear_signature(self, request: Request) -> bytes:
        """
        Verifies the X-Linear-Signature header.
        Raises HTTPException if invalid.
        """
        signature = request.headers.get("X-Linear-Signature")
        if not signature:
            logger.error("Missing X-Linear-Signature header.")
            raise HTTPException(status_code=400, detail="Missing X-Linear-Signature")

        raw_body = await request.body()

        if not raw_body:
            logger.warning("Received Linear webhook with empty body.")
            raise HTTPException(status_code=400, detail="Empty request body")

        # settings.py now GUARANTEES linear_webhook_secret is a string
        secret = settings.linear_webhook_secret.encode("utf-8")

        hashed_body = hmac.new(secret, raw_body, hashlib.sha256).hexdigest()

        if not hmac.compare_digest(hashed_body, signature):
            logger.error(
                f"Invalid signature. Expected: {hashed_body}, Got: {signature}"
            )
            raise HTTPException(status_code=403, detail="Invalid signature")

        return raw_body

    async def handle_linear_webhook_request(self, request: Request):
        """
        Validates and routes a Linear webhook payload.
        This is called BY the FastAPI endpoint.
        """
        # 1. Verify signature and get raw body
        raw_body = await self.verify_linear_signature(request)

        # 2. Parse incoming JSON
        payload: Dict[str, Any] = json.loads(raw_body)

        # 3. Continue with existing logic
        action = payload.get("action")
        issue = payload.get("data")

        if not issue or not action:
            logger.warning(
                f"Invalid Linear payload structure. Action: {action}, Issue: {issue}"
            )
            raise HTTPException(status_code=400, detail="Invalid payload structure")

        logger.info(
            f"Processing Linear webhook. Action: {action}, Issue ID: {issue.get('id')}"
        )

        # Delegate to the synchronous payload handler for the actual logic
        self.handle_linear_webhook(payload)

        # handle_linear_webhook returns the status dict
        # This return is for safety and consistency with FastAPI expectations.
        return {"status": f"action '{action}' processed"}

    def handle_linear_webhook(self, payload: Dict[str, Any]):
        """
        Synchronously handle a parsed Linear webhook payload (used by unit tests).
        """
        action = payload.get("action")
        issue = payload.get("data")

        if not issue or not action:
            logger.warning(
                f"Invalid Linear payload structure. Action: {action}, Issue: {issue}"
            )
            raise ValueError("Invalid payload structure")

        logger.info(
            f"Processing Linear webhook. Action: {action}, Issue ID: {issue.get('id')}"
        )

        if action == "update":
            self._sync_issue_update(issue)
        elif action == "remove":
            self._handle_issue_deletion(issue)
        else:
            logger.info(f"Received unhandled Linear action: {action}")

        return {"status": f"action '{action}' processed"}

    def _sync_issue_update(self, issue: Dict[str, Any]):
        """
        Synchronize a Linear issue update with Neo4j and Obsidian.
        (This is your logic from linear_sync_old.py)
        """
        logger.info(f"Syncing issue update for: {issue.get('identifier')}")
        linear_id = issue.get("identifier")
        if not linear_id:
            logger.error("Linear issue payload missing 'identifier'.")
            return

        # Update Neo4j
        with self.driver.session() as session:
            # THIS IS THE FIX: Use neo4j_result everywhere
            neo4j_result: Optional[neo4j.Record] = session.run(
                """
                MATCH (t:Task {linear_id: $linear_id})
                SET t.linear_status = $status,
                    t.linear_priority = $priority,
                    t.linear_updated = datetime($updated)
                RETURN t.filepath
            """,
                linear_id=linear_id,
                status=issue.get("state", {}).get("name", "Unknown"),
                priority=issue.get("priority", 0),
                updated=issue.get("updatedAt"),
            ).single()

        if not neo4j_result:
            logger.warning(f"⚠️  No Obsidian task found for {linear_id}")
            return

        # Update Obsidian file
        filepath = neo4j_result.get("t.filepath")
        if not filepath:
            logger.error(f"Neo4j task {linear_id} has no filepath attribute.")
            return

        task_path = self.vault / filepath
        self._update_task_file(task_path, issue)

    def _update_task_file(self, path: Path, issue: Dict[str, Any]):
        """
        Update an Obsidian task file's frontmatter.
        (This is your logic from linear_sync_old.py)
        """
        if not path.is_file():
            logger.error(f"Cannot update task file: File not found at {path}")
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                post = frontmatter.load(f)

            # Update metadata
            issue_state = issue.get("state", {}).get("name", "Unknown")
            post.metadata["linear_status"] = issue_state
            post.metadata["linear_priority"] = issue.get("priority", 0)
            post.metadata["linear_updated"] = issue.get("updatedAt")

            # Map Linear status to Obsidian status
            status_map = {
                "Backlog": "draft",
                "Todo": "ready",
                "In Progress": "active",
                "Done": "completed",
                "Canceled": "archived",
            }
            post.metadata["status"] = status_map.get(issue_state, "draft")

            # Write back
            with open(path, "w", encoding="utf-8") as f:
                frontmatter.dump(post, f)

            logger.info(f"✓ Updated {path.name} from Linear")
        except Exception as e:
            logger.error(f"Failed to update task file {path}: {e}")

    def _handle_issue_deletion(self, issue: Dict[str, Any]):
        """
        Mark the Neo4j Task matching the Linear issue as archived.
        (This is your logic from linear_sync_old.py)
        """
        linear_id = issue.get("identifier")
        if not linear_id:
            logger.error("Linear delete payload missing 'identifier'.")
            return

        logger.info(f"Archiving task for Linear issue {linear_id}")

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

        logger.info(f"✓ Archived task for Linear issue {linear_id}")
