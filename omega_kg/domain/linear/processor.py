"""
Linear Event Processor

Processes raw Linear webhook events from database to Obsidian markdown files.
"""

import logging
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from omega_kg.domain.linear.models import LinearWebhookPayload
from omega_kg.domain.linear.mapper import LinearToObsidianMapper

logger = logging.getLogger(__name__)


async def process_pending_events(
    session: AsyncSession,
    vault_path: Path
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
    from omega_kg.models import RawLinearEvent  # Import here to avoid circular dependency
    
    # Initialize mapper
    mapper = LinearToObsidianMapper(vault_path)
    
    # Query unprocessed events
    query = select(RawLinearEvent).where(
        RawLinearEvent.processed == False  # noqa: E712
    ).order_by(RawLinearEvent.received_at)
    
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
            
            # Map to Obsidian markdown
            file_path, markdown_content = mapper.map_issue_to_markdown(payload.data)
            
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write markdown file
            file_path.write_text(markdown_content, encoding='utf-8')
            
            logger.info(f"Wrote {file_path.name} for event {event.id}")
            
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
    session: AsyncSession,
    event_id: int,
    vault_path: Path
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
        file_path, markdown_content = mapper.map_issue_to_markdown(payload.data)
        
        # Ensure directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write markdown file
        file_path.write_text(markdown_content, encoding='utf-8')
        
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
