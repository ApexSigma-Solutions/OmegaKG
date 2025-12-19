"""
Linear Event Processor

Processes raw Linear webhook events from database to Obsidian markdown files.
Phase 7: TN-LINEAR-07 - Enriches issues with vector embeddings for semantic search.
"""

import logging
from pathlib import Path
from typing import Any, List, Optional

from pydantic import ValidationError
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from omega_kg.database.graph import graph_driver
from omega_kg.domain.common.embedding_service import generate_embedding
from omega_kg.domain.linear.graph_writer import GraphWriter
from omega_kg.domain.linear.mapper import LinearToObsidianMapper
from omega_kg.domain.linear.models import LinearIssue, LinearWebhookPayload

logger = logging.getLogger(__name__)


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
    )  # Import here to avoid circular dependency

    # Initialize mapper and graph writer
    mapper = LinearToObsidianMapper(vault_path)
    graph_writer = GraphWriter(graph_driver)

    # Query unprocessed events
    query = (
        select(RawLinearEvent)
        .where(RawLinearEvent.processed == False)  # noqa: E712
        .order_by(RawLinearEvent.received_at)
    )

    result = await session.execute(query)
    events = result.scalars().all()

    logger.info(f"Found {len(events)} unprocessed Linear events")

    # Statistics
    stats = {
        "processed": 0,
        "errors": 0,
        "skipped": 0,
    }

    # Process each event
    for event in events:
        try:
            # Parse payload
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

            logger.info(f"Wrote {file_path.name} for event {event.id}")

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
                    f"Graph sync failed for event {event.id}: {graph_err}"
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
            logger.error(f"Event {event.id}: {error_msg}")

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
            logger.error(f"Event {event.id}: {error_msg}", exc_info=True)

            # Update error log
            await session.execute(
                update(RawLinearEvent)
                .where(RawLinearEvent.id == event.id)
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
