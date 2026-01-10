import asyncio
import logging
import httpx
import json
from datetime import datetime
from sqlalchemy import select
from omega_kg.database.ingest_session import AsyncIngestSessionLocal
from omega_kg.models.raw_storage import RawConversation
from omega_kg.settings import settings
from omega_kg.database.graph import graph_driver
from omega_kg.vector_store import get_vector_store
from omega_kg.utils.capture_utils import write_to_obsidian

logger = logging.getLogger(__name__)


async def process_one_conversation(raw_id, raw_payload, platform):
    """
    Orchestrates the synthesis and storage of a raw conversation.
    """
    # 1. Call InGest-LLM for Synthesis
    # Note: InGest-LLM/digest endpoint expects IngestionRequest
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            logger.info(
                f"Requesting digest from InGest-LLM at {settings.ingest_llm_url}"
            )

            # Extract messages if present, otherwise use raw payload as string
            content_to_digest = ""
            if isinstance(raw_payload, dict) and "messages" in raw_payload:
                content_to_digest = json.dumps(raw_payload["messages"])
            else:
                content_to_digest = json.dumps(raw_payload)

            resp = await client.post(
                f"{settings.ingest_llm_url}/ingest/digest",
                json={
                    "content": content_to_digest,
                    "metadata": {
                        "source": "api",
                        "content_type": "json",
                        "title": raw_payload.get("title", "Conversation")
                        if isinstance(raw_payload, dict)
                        else "Conversation",
                        "source_url": raw_payload.get("url", "")
                        if isinstance(raw_payload, dict)
                        else "",
                    },
                },
            )
            resp.raise_for_status()
            digest = resp.json()
            logger.info(f"Digest received: {digest.get('title')}")
        except Exception as e:
            logger.error(f"Failed to get digest from InGest-LLM: {e}")
            raise

    # 2. Update Neo4j
    session_neo4j_id = None
    try:
        async with graph_driver.session() as session:
            logger.info("Connecting to Neo4j to store digest nodes...")
            # Create ChatSession
            res = await session.run(
                """
                MERGE (s:ChatSession {raw_id: $raw_id})
                SET s.title = $title,
                    s.summary = $summary,
                    s.platform = $platform,
                    s.url = $url,
                    s.processed_at = datetime($processed_at)
                RETURN elementId(s) as session_id
            """,
                raw_id=str(raw_id),
                title=digest.get("title", "Unknown"),
                summary=digest.get("summary", ""),
                platform=platform,
                url=raw_payload.get("url", "") if isinstance(raw_payload, dict) else "",
                processed_at=datetime.utcnow().isoformat(),
            )

            rec = await res.single()
            if rec:
                session_neo4j_id = rec["session_id"]
            else:
                session_neo4j_id = "unknown"

            # Create Entities & Concepts
            for ent in digest.get("entities", []):
                await session.run(
                    """
                    MATCH (s:ChatSession {raw_id: $raw_id})
                    MERGE (e:Entity {name: $name})
                    SET e.type = $type
                    MERGE (s)-[:MENTIONS]->(e)
                """,
                    raw_id=str(raw_id),
                    name=ent.get("name"),
                    type=ent.get("type", "Unknown"),
                )

            for concept in digest.get("concepts", []):
                await session.run(
                    """
                    MATCH (s:ChatSession {raw_id: $raw_id})
                    MERGE (c:Concept {name: $name})
                    MERGE (s)-[:DISCUSSES]->(c)
                """,
                    raw_id=str(raw_id),
                    name=concept,
                )

            # Create Decisions & Outcomes
            for i, dec in enumerate(digest.get("decisions", [])):
                await session.run(
                    """
                    MATCH (s:ChatSession {raw_id: $raw_id})
                    CREATE (d:Decision {content: $content, id: $dec_id, type: 'extracted'})
                    MERGE (s)-[:CONTAINS]->(d)
                """,
                    raw_id=str(raw_id),
                    content=dec,
                    dec_id=f"{raw_id}-dec-{i}",
                )

            for i, outcome in enumerate(digest.get("outcomes", [])):
                await session.run(
                    """
                    MATCH (s:ChatSession {raw_id: $raw_id})
                    CREATE (o:Outcome {content: $content, id: $out_id})
                    MERGE (s)-[:PRODUCES]->(o)
                """,
                    raw_id=str(raw_id),
                    content=outcome,
                    out_id=f"{raw_id}-out-{i}",
                )

            logger.info(f"Neo4j updates complete for {raw_id}")
    except Exception as e:
        logger.error(f"Neo4j processing failed: {e}")
        # Not raising here to allow vector storage and obsidian write if possible,
        # but in production we might want to fail the whole task.
        session_neo4j_id = "error_linking"

    # 3. Store in PGVector
    vector_id = None
    try:
        vector_store = await get_vector_store()
        logger.info("Storing digest summary in PGVector...")
        # We store the summary as the searchable content
        vector_id = await vector_store.store_memory(
            content=digest.get("summary", ""),
            metadata={
                "source": "conversation_digest",
                "raw_id": str(raw_id),
                "session_neo4j_id": session_neo4j_id,
                "title": digest.get("title"),
            },
            tags=digest.get("tags", []),
        )
        logger.info(f"PGVector store complete: {vector_id}")
    except Exception as e:
        logger.warning(f"Failed to store vector: {e}")

    # 4. Write to Obsidian
    try:
        logger.info("Writing summarized note to Obsidian vault...")
        tags_str = ", ".join(digest.get("tags", []))
        entities_str = ", ".join(
            [e.get("name") for e in digest.get("entities", []) if e.get("name")]
        )
        concepts_str = ", ".join(digest.get("concepts", []))
        decisions_list = "\n".join([f"  - {d}" for d in digest.get("decisions", [])])
        outcomes_list = "\n".join([f"  - {o}" for o in digest.get("outcomes", [])])

        enriched_content = f"""---
uid: {raw_id}
title: {digest.get("title", "Conversation")}
platform: {platform}
neo4j_id: {session_neo4j_id}
vector_id: {vector_id}
tags: [{tags_str}]
status: completed
created: {datetime.utcnow().isoformat()}
---

# {digest.get("title", "Conversation")}

## Summary
{digest.get("summary", "No summary generated.")}

## Structured Knowledge
- **Entities**: {entities_str}
- **Concepts**: {concepts_str}

### Decisions
{decisions_list if decisions_list else "  - None identified"}

### Outcomes
{outcomes_list if outcomes_list else "  - None identified"}

---
**🤖 Metadata**
- **Raw Record ID**: `{raw_id}`
- **Graph Node ID**: `{session_neo4j_id}`
- **Vector Index**: `{vector_id}`
- **Platform**: {platform}
- **Processed At**: {datetime.utcnow().isoformat()}

[View Raw Context in memOS](memos://search?query={raw_id})
"""
        # Using the platform and generating a filename based on title or ID
        safe_platform = platform if platform else "unknown"
        write_to_obsidian(safe_platform, enriched_content, str(raw_id)[:8])
        logger.info("Obsidian note written successfully.")
    except Exception as e:
        logger.error(f"Failed to write to Obsidian: {e}")

    return True


async def conversation_worker_loop():
    """
    Main loop for polling and processing raw conversations.
    """
    logger.info("Conversation Synthesis Worker started.")

    # Give other services a moment to start
    await asyncio.sleep(5)

    while True:
        try:
            async with AsyncIngestSessionLocal() as db:
                # Fetch unprocessed records
                stmt = (
                    select(RawConversation)
                    .where(RawConversation.processed == False)
                    .limit(5)
                )
                res = await db.execute(stmt)
                records = res.scalars().all()

                if records:
                    logger.info(f"Found {len(records)} conversations to synthesize.")
                    for rec in records:
                        try:
                            logger.info(f"Processing Record {rec.id} ({rec.platform})")
                            success = await process_one_conversation(
                                rec.id, rec.raw_payload, rec.platform
                            )
                            if success:
                                rec.processed = True
                                rec.processed_at = datetime.utcnow()
                                await db.commit()
                                logger.info(f"Record {rec.id} marked as PROCESSED.")
                        except Exception as e:
                            logger.error(
                                f"Error processing record {rec.id}: {e}", exc_info=True
                            )
                            rec.error = str(e)
                            await db.commit()

        except Exception as e:
            logger.error(f"Conversation worker loop error: {e}", exc_info=True)

        await asyncio.sleep(15)  # Wait between polls


def start_conversation_worker():
    """Starts the conversation worker in the background."""
    return asyncio.create_task(conversation_worker_loop())
