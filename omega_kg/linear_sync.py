# omega_kg/linear_sync.py

import hmac
import hashlib
import json
import logging
from fastapi import Request, HTTPException
from starlette.concurrency import run_in_threadpool
from omega_kg.settings import settings
from pathlib import Path
from neo4j import GraphDatabase
from typing import Optional, Dict, Any
import neo4j
from omega_kg.vault_utils import VaultUtils

logger = logging.getLogger(__name__)


class LinearSync:
    """
    Contains all business logic for processing Linear webhooks.
    """

    def __init__(self):
        """
        Initializes the LinearSync engine.
        """
        self.driver = GraphDatabase.driver(
            settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
        )
        logger.info("LinearSync engine initialized.")

    @property
    def vault_utils(self) -> VaultUtils:
        if not hasattr(self, '_vault_utils'):
            self._vault_utils = VaultUtils()
        return self._vault_utils

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
        await run_in_threadpool(self.handle_linear_webhook, payload)

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
        """
        logger.info(f"Syncing issue update for: {issue.get('identifier')}")
        linear_id = issue.get(
            "id"
        )  # Use UUID for lookup as it's more stable, or identifier
        linear_identifier = issue.get("identifier")

        if not linear_id:
            logger.error("Linear issue payload missing 'id'.")
            return

        # 1. Try to find file via Neo4j first (faster if indexed)
        filepath = None
        try:
            with self.driver.session() as session:
                neo4j_result: Optional[neo4j.Record] = session.run(
                    """
                    MATCH (t:Task {linear_id: $linear_id})
                    RETURN t.filepath
                    """,
                    linear_id=linear_id,
                ).single()

                if neo4j_result:
                    filepath = neo4j_result.get("t.filepath")
        except Exception as e:
            logger.warning(f"Neo4j lookup failed: {e}")

        # 2. Fallback to Vault Scan if Neo4j didn't find it
        if not filepath:
            logger.info(
                f"Neo4j didn't return a path for {linear_identifier}. Scanning vault..."
            )
            path_obj = self.vault_utils.find_note_by_linear_id(linear_id)
            if path_obj:
                filepath = str(path_obj)
            else:
                # Try scanning by identifier as fallback
                # (Note: find_note_by_linear_id currently only checks linear_id)
                logger.warning(
                    f"⚠️  No Obsidian note found for Linear ID {linear_id} ({linear_identifier})"
                )
                return

        # 3. Update Obsidian file
        logger.info(f"Found note at: {filepath}")
        self._update_task_file(filepath, issue)

        # 4. Update Neo4j (to keep it in sync)
        try:
            with self.driver.session() as session:
                session.run(
                    """
                    MERGE (t:Task {linear_id: $linear_id})
                    SET t.linear_status = $status,
                        t.linear_priority = $priority,
                        t.linear_updated = datetime($updated),
                        t.filepath = $filepath
                    """,
                    linear_id=linear_id,
                    status=issue.get("state", {}).get("name", "Unknown"),
                    priority=issue.get("priority", 0),
                    updated=issue.get("updatedAt"),
                    filepath=filepath,
                )
        except Exception as e:
            logger.error(f"Failed to update Neo4j: {e}")

    def _update_task_file(self, path: str | Path, issue: Dict[str, Any]):
        """
        Update an Obsidian task file's frontmatter using VaultUtils.
        """
        updates = {}

        # Update metadata
        issue_state = issue.get("state", {}).get("name", "Unknown")
        updates["linear_status"] = issue_state
        updates["linear_priority"] = issue.get("priority", 0)
        updates["linear_updated"] = issue.get("updatedAt")

        # Map Linear status to Obsidian status
        # TODO: Move this map to settings or shared constant
        status_map = {
            "Backlog": "draft",
            "Todo": "ready",
            "In Progress": "active",
            "Done": "completed",
            "Canceled": "archived",
        }
        # Only update status if we have a mapping, otherwise keep existing
        if issue_state in status_map:
            updates["status"] = status_map[issue_state]

        if self.vault_utils.update_note_frontmatter(path, updates):
            logger.info(f"✓ Updated {Path(path).name} from Linear")
        else:
            logger.error(f"Failed to update task file {path}")

    def _handle_issue_deletion(self, issue: Dict[str, Any]):
        """
        Mark the Neo4j Task matching the Linear issue as archived.
        """
        linear_id = issue.get("id")
        if not linear_id:
            logger.error("Linear delete payload missing 'id'.")
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
