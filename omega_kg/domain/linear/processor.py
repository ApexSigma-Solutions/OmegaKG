"""
Linear Event Processor

Processes raw Linear webhook events from database to Obsidian markdown files.
Phase 7: TN-LINEAR-07 - Enriches issues with vector embeddings for semantic search.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import ValidationError
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from omega_kg.database.graph import graph_driver
from omega_kg.domain.common.embedding_service import generate_embedding
from omega_kg.domain.linear.graph_writer import GraphWriter
from omega_kg.domain.linear.mapper import LinearToObsidianMapper
from omega_kg.domain.linear.models import LinearIssue, LinearWebhookPayload

logger = logging.getLogger(__name__)


# Singleton instance for LinearProcessor
_linear_processor_instance: Optional["LinearProcessor"] = None


def get_linear_processor() -> "LinearProcessor":
    """
    Get singleton instance of LinearProcessor.
    
    Returns:
        LinearProcessor: Singleton instance
    """
    global _linear_processor_instance
    if _linear_processor_instance is None:
        _linear_processor_instance = LinearProcessor()
    return _linear_processor_instance


class LinearProcessor:
    """
    Domain processor for Linear webhook events.
    
    This processor is decoupled from database and HTTP layers,
    making it testable and reusable. It accepts parsed JSON payloads
    directly rather than querying the database.
    
    Attributes:
        graph_writer: GraphWriter instance for Neo4j operations
        mapper: LinearToObsidianMapper for markdown generation
    """
    
    def __init__(self, vault_path: Optional[Path] = None):
        """
        Initialize LinearProcessor.
        
        Args:
            vault_path: Path to Obsidian vault. If None, uses settings default.
        """
        from omega_kg.settings import settings
        from omega_kg.linear_sync import LinearSync
        
        self.vault_path = Path(vault_path) if vault_path else Path(settings.obsidian_vault_path)
        self.graph_writer = GraphWriter(graph_driver)
        self.mapper = LinearToObsidianMapper(self.vault_path)
        self.linear_sync = LinearSync(self.vault_path)
    
    async def process_single_event(self, payload: Dict[str, Any]) -> bool:
        """
        Process a single Linear webhook payload.
        
        This is the main entry point for the event processor. It validates
        the payload, maps to markdown, writes to vault, generates embeddings,
        and syncs to Neo4j.
        
        Args:
            payload: Parsed JSON dictionary from webhook
            
        Returns:
            bool: True if processed successfully, False otherwise
        """
        try:
            # Validate and parse payload
            webhook_payload = LinearWebhookPayload.model_validate(payload)
            
            # Skip if no data
            if not webhook_payload.data:
                logger.debug("Event has no data, skipping")
                return True
            
            # Extract issue
            issue = LinearIssue.model_validate(webhook_payload.data)
            
            # Step 1: Map to Obsidian markdown
            file_path, markdown_content = self.mapper.map_issue_to_markdown(issue)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(markdown_content, encoding="utf-8")
            
            logger.info(f"Wrote {file_path.name} for issue {issue.identifier}")
            
            # Step 2: Create Task Note Plan if needed
            self._create_tnp_if_needed(issue)
            
            # Step 3: Generate embedding (non-blocking)
            embedding = await self._generate_embedding(issue)
            
            # Step 4: Sync to Neo4j
            await self.graph_writer.upsert_issue(issue, embedding=embedding)
            
            if embedding:
                logger.info(
                    f"Synced {issue.identifier} to graph with 1024-dim embedding"
                )
            else:
                logger.info(
                    f"Synced {issue.identifier} to graph (no embedding)"
                )
            
            return True
            
        except ValidationError as e:
            logger.error(f"Payload validation failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Processing failed: {e}", exc_info=True)
            return False
    
    def _create_tnp_if_needed(self, issue: LinearIssue) -> None:
        """
        Create Task Note Plan (.tnp.md) if it doesn't exist.
        
        Non-blocking: Logs warning on failure but continues processing.
        
        Args:
            issue: The LinearIssue to create TNP for
        """
        try:
            # Template is in test_vault at project root
            template_path = (
                Path(__file__).parents[3]
                / "test_vault"
                / "template_task-note-plan.tnp.md"
            )
            tnp_path, tnp_content = self.mapper.map_issue_to_tnp(issue, template_path)
            
            if not tnp_path.exists():
                tnp_path.write_text(tnp_content, encoding="utf-8")
                logger.info(f"Created new TNP file: {tnp_path.name}")
            else:
                logger.debug(
                    f"TNP file already exists: {tnp_path.name}, skipping creation"
                )
        except Exception as e:
            logger.warning(f"Failed to create TNP file for {issue.identifier}: {e}")
            # Non-blocking, continue with graph sync
    
    async def _generate_embedding(self, issue: LinearIssue) -> Optional[List[float]]:
        """
        Generate semantic embedding for issue.
        
        Non-blocking: Returns None on failure rather than raising.
        
        Args:
            issue: The LinearIssue to generate an embedding for
            
        Returns:
            1024-dim float vector, or None if embedding generation fails
        """
        # Build embedding payload from title + description
        payload = f"{issue.title}"
        if issue.description:
            payload += f" {issue.description}"
        
        try:
            embedding = await generate_embedding(payload)
            logger.debug(f"Generated 1024-dim embedding for {issue.identifier}")
            return embedding
        except Exception as e:
            logger.warning(
                f"Embedding generation failed for {issue.identifier}: {e}. "
                "Issue will be stored without vector."
            )
            return None
    
    async def process_issue_update(self, payload: Dict[str, Any]) -> bool:
        """
        Process an IssueUpdated webhook event from Linear.
        
        This method handles status changes by updating the local markdown file's
        frontmatter. It uses LinearSync to find the file and update its status.
        
        Args:
            payload: Parsed JSON dictionary from webhook
            
        Returns:
            bool: True if processed successfully, False otherwise
        """
        try:
            # Validate payload
            webhook_payload = LinearWebhookPayload.model_validate(payload)
            
            if not webhook_payload.data:
                logger.debug("Issue update has no data, skipping")
                return True
            
            # Extract action type - only process update events with status changes
            action = webhook_payload.action
            
            if action != "update":
                logger.debug(f"Ignoring non-update event: {action}")
                return True
            
            # Check if this is a status update (state field changed)
            # Linear includes the updated state in the payload
            data = webhook_payload.data
            
            # Check if state is present in the update
            if "state" not in data:
                logger.debug("No state change in update, skipping local sync")
                return True
            
            # This is a status update - use LinearSync to update local file
            success = self.linear_sync.update_local_note(payload)
            
            if success:
                logger.info(f"Successfully processed issue update for {data.get('identifier', data.get('id'))}")
            
            return success
            
        except ValidationError as e:
            logger.error(f"Payload validation failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Issue update processing failed: {e}", exc_info=True)
            return False
    
    def close(self) -> None:
        """
        Close database connections and cleanup resources.
        """
        # GraphWriter manages its own connections
        # This method is provided for future cleanup needs
        pass


async def _generate_issue_embedding(issue: LinearIssue) -> Optional[List[float]]:
    """
    Generate a semantic embedding for a Linear issue.

    Combines title and description into a single payload for embedding.
    Non-blocking: returns None on failure rather than raising.

    Args:
        issue: The LinearIssue to generate an embedding for

    Returns:
        1024-dim float vector, or None if embedding generation fails
    """
    # Build embedding payload from title + description
    payload = f"{issue.title}"
    if issue.description:
        payload += f" {issue.description}"

    try:
        embedding = await generate_embedding(payload)
        logger.debug(f"Generated 1024-dim embedding for issue {issue.identifier}")
        return embedding
    except Exception as e:
        logger.warning(
            f"Embedding generation failed for {issue.identifier}: {e}. "
            "Issue will be stored without vector."
        )
        return None


async def process_pending_events(
    session: AsyncSession, vault_path: Path
) -> dict[str, Any]:
    """
    Process all unprocessed Linear events from database.

    Workflow:
    1. Query unprocessed events (processed=FALSE)
    2. Parse payload JSON as LinearWebhookPayload
    3. Extract LinearIssue from payload
    4. Map issue to Obsidian markdown
    5. Write markdown file to vault
    6. Mark event as processed
    7. Continue on errors (log to error_log column)

    Args:
        session: SQLAlchemy async session
        vault_path: Path to Obsidian vault root

    Returns:
        Processing statistics dict:
        {
            "processed": 5,
            "errors": 1,
            "skipped": 0
        }
    """
    from omega_kg.models import (
        RawLinearEvent,
        RawWebhookEvent,
    )  # Import here to avoid circular dependency

    # Initialize mapper and graph writer
    mapper = LinearToObsidianMapper(vault_path)
    graph_writer = GraphWriter(graph_driver)

    # Query unprocessed events from both models for backward compatibility
    # Old records in RawLinearEvent, new records in RawWebhookEvent
    query_old = (
        select(RawLinearEvent)
        .where(RawLinearEvent.processed == False)  # noqa: E712
        .order_by(RawLinearEvent.received_at)
    )
    
    query_new = (
        select(RawWebhookEvent)
        .where(RawWebhookEvent.source == 'linear')
        .where(RawWebhookEvent.processed_status == False)  # noqa: E712
        .order_by(RawWebhookEvent.received_at)
    )

    result_old = await session.execute(query_old)
    result_new = await session.execute(query_new)
    
    old_events = result_old.scalars().all()
    new_events = result_new.scalars().all()
    
    total_events = len(old_events) + len(new_events)
    logger.info(f"Found {total_events} unprocessed Linear events ({len(old_events)} old, {len(new_events)} new)")

    # Statistics
    stats = {
        "processed": 0,
        "errors": 0,
        "skipped": 0,
    }

    # Process old events (RawLinearEvent)
    for event in old_events:
        try:
            # Parse payload (already dict in old model)
            import json

            payload = LinearWebhookPayload.model_validate_json(json.dumps(event.body))

            # Skip non-issue events
            if not payload.data:
                logger.debug(f"Event {event.id} has no data, skipping")
                stats["skipped"] += 1
                continue

            # Validate issue as LinearIssue object BEFORE calling mapper
            issue = LinearIssue.model_validate(payload.data)

            # Map to Obsidian markdown
            file_path, markdown_content = mapper.map_issue_to_markdown(issue)

            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write markdown file
            file_path.write_text(markdown_content, encoding="utf-8")

            logger.info(f"Wrote {file_path.name} for old event {event.id}")

            # Create Task Note Plan (.tnp.md) if it doesn't exist
            try:
                # Template is in test_vault at project root
                template_path = (
                    Path(__file__).parents[3]
                    / "test_vault"
                    / "template_task-note-plan.tnp.md"
                )
                tnp_path, tnp_content = mapper.map_issue_to_tnp(issue, template_path)

                if not tnp_path.exists():
                    tnp_path.write_text(tnp_content, encoding="utf-8")
                    logger.info(f"Created new TNP file: {tnp_path.name}")
                else:
                    logger.debug(
                        f"TNP file already exists: {tnp_path.name}, skipping creation"
                    )
            except Exception as tnp_err:
                logger.warning(f"Failed to create TNP file for {issue.identifier}: {tnp_err}")
                # Non-blocking, continue with graph sync

            # Phase 6: Sync to Graph (Topology)
            # Phase 7: Enrich with embedding for semantic search
            try:
                # Phase 7: Generate embedding (non-blocking)
                embedding = await _generate_issue_embedding(issue)

                # Upsert issue with optional embedding
                await graph_writer.upsert_issue(issue, embedding=embedding)

                if embedding:
                    logger.info(
                        f"Synced {issue.identifier} to graph with 1024-dim embedding"
                    )
                else:
                    logger.info(
                        f"Synced {issue.identifier} to graph (no embedding)"
                    )
            except Exception as graph_err:
                logger.warning(
                    f"Graph sync failed for old event {event.id}: {graph_err}"
                )
                # Continue processing - graph sync is non-blocking

            # Mark as processed
            await session.execute(
                update(RawLinearEvent)
                .where(RawLinearEvent.id == event.id)
                .values(processed=True, error_log=None)
            )

            stats["processed"] += 1

        except ValidationError as e:
            # Log validation errors
            error_msg = f"Validation error: {e}"
            logger.error(f"Old event {event.id}: {error_msg}")

            # Update error log
            await session.execute(
                update(RawLinearEvent)
                .where(RawLinearEvent.id == event.id)
                .values(error_log=error_msg)
            )

            stats["errors"] += 1

        except Exception as e:
            # Log processing errors
            error_msg = f"Processing error: {str(e)}"
            logger.error(f"Old event {event.id}: {error_msg}", exc_info=True)

            # Update error log
            await session.execute(
                update(RawLinearEvent)
                .where(RawLinearEvent.id == event.id)
                .values(error_log=error_msg)
            )

            stats["errors"] += 1

    # Process new events (RawWebhookEvent)
    for event in new_events:
        try:
            # Parse payload (bytes in new model)
            import json

            # Decode bytes to string for parsing
            if isinstance(event.payload, bytes):
                payload_str = event.payload.decode('utf-8')
            else:
                payload_str = event.payload

            payload = LinearWebhookPayload.model_validate_json(payload_str)

            # Skip non-issue events
            if not payload.data:
                logger.debug(f"New event {event.id} has no data, skipping")
                stats["skipped"] += 1
                continue

            # Validate issue as LinearIssue object BEFORE calling mapper
            issue = LinearIssue.model_validate(payload.data)

            # Map to Obsidian markdown
            file_path, markdown_content = mapper.map_issue_to_markdown(issue)

            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write markdown file
            file_path.write_text(markdown_content, encoding="utf-8")

            logger.info(f"Wrote {file_path.name} for new event {event.id}")

            # Create Task Note Plan (.tnp.md) if it doesn't exist
            try:
                # Template is in test_vault at project root
                template_path = (
                    Path(__file__).parents[3]
                    / "test_vault"
                    / "template_task-note-plan.tnp.md"
                )
                tnp_path, tnp_content = mapper.map_issue_to_tnp(issue, template_path)

                if not tnp_path.exists():
                    tnp_path.write_text(tnp_content, encoding="utf-8")
                    logger.info(f"Created new TNP file: {tnp_path.name}")
                else:
                    logger.debug(
                        f"TNP file already exists: {tnp_path.name}, skipping creation"
                    )
            except Exception as tnp_err:
                logger.warning(f"Failed to create TNP file for {issue.identifier}: {tnp_err}")
                # Non-blocking, continue with graph sync

            # Phase 6: Sync to Graph (Topology)
            # Phase 7: Enrich with embedding for semantic search
            try:
                # Phase 7: Generate embedding (non-blocking)
                embedding = await _generate_issue_embedding(issue)

                # Upsert issue with optional embedding
                await graph_writer.upsert_issue(issue, embedding=embedding)

                if embedding:
                    logger.info(
                        f"Synced {issue.identifier} to graph with 1024-dim embedding"
                    )
                else:
                    logger.info(
                        f"Synced {issue.identifier} to graph (no embedding)"
                    )
            except Exception as graph_err:
                logger.warning(
                    f"Graph sync failed for new event {event.id}: {graph_err}"
                )
                # Continue processing - graph sync is non-blocking

            # Mark as processed
            await session.execute(
                update(RawWebhookEvent)
                .where(RawWebhookEvent.id == event.id)
                .values(processed_status=True, error_log=None)
            )

            stats["processed"] += 1

        except ValidationError as e:
            # Log validation errors
            error_msg = f"Validation error: {e}"
            logger.error(f"New event {event.id}: {error_msg}")

            # Update error log
            await session.execute(
                update(RawWebhookEvent)
                .where(RawWebhookEvent.id == event.id)
                .values(error_log=error_msg)
            )

            stats["errors"] += 1

        except Exception as e:
            # Log processing errors
            error_msg = f"Processing error: {str(e)}"
            logger.error(f"New event {event.id}: {error_msg}", exc_info=True)

            # Update error log
            await session.execute(
                update(RawWebhookEvent)
                .where(RawWebhookEvent.id == event.id)
                .values(error_log=error_msg)
            )

            stats["errors"] += 1

    # Commit transaction
    await session.commit()

    logger.info(
        f"Processing complete: {stats['processed']} processed, "
        f"{stats['errors']} errors, {stats['skipped']} skipped"
    )

    return stats


async def process_single_event(
    session: AsyncSession, event_id: int, vault_path: Path
) -> bool:
    """
    Process a single Linear event by ID.

    Useful for retry/recovery scenarios.

    Args:
        session: SQLAlchemy async session
        event_id: RawLinearEvent.id to process
        vault_path: Path to Obsidian vault root

    Returns:
        True if processed successfully, False otherwise
    """
    from omega_kg.models import RawLinearEvent

    # Initialize mapper
    mapper = LinearToObsidianMapper(vault_path)

    # Query event
    query = select(RawLinearEvent).where(RawLinearEvent.id == event_id)
    result = await session.execute(query)
    event = result.scalar_one_or_none()

    if not event:
        logger.error(f"Event {event_id} not found")
        return False

    try:
        # Parse payload
        import json

        payload = LinearWebhookPayload.model_validate_json(json.dumps(event.body))

        # Skip non-issue events
        if not payload.data:
            logger.debug(f"Event {event.id} has no data, skipping")
            return False

        # Map to Obsidian markdown
        file_path, markdown_content = mapper.map_issue_to_markdown(payload.data)  # type: ignore[arg-type]

        # Ensure directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write markdown file
        file_path.write_text(markdown_content, encoding="utf-8")

        logger.info(f"Wrote {file_path.name} for event {event.id}")

        # Mark as processed
        await session.execute(
            update(RawLinearEvent)
            .where(RawLinearEvent.id == event.id)
            .values(processed=True, error_log=None)
        )

        await session.commit()

        return True

    except Exception as e:
        # Log processing errors
        error_msg = f"Processing error: {str(e)}"
        logger.error(f"Event {event.id}: {error_msg}", exc_info=True)

        # Update error log
        await session.execute(
            update(RawLinearEvent)
            .where(RawLinearEvent.id == event.id)
            .values(error_log=error_msg)
        )

        await session.commit()

        return False
