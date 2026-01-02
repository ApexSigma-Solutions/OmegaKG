# Dual-Write Saga Weaver
import asyncio
import logging
import re
import json
from typing import List, Dict, Any
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import JSONB

# Internal Imports
from omega_kg.database import get_ingest_session, get_vector_session
from omega_kg.models.terminal import TerminalEvent
from omega_kg.services.neo4j_adapter import Neo4jAdapter
from omega_kg.services.openai_service import generate_embedding

# Setup Logger
logger = logging.getLogger("omega.worker.embedding")
# Ensuring level is set if not configured elsewhere
logger.setLevel(logging.INFO)

# --- CONFIGURATION ---
BATCH_SIZE = 10
POLL_INTERVAL = 5  # Seconds
AGENT_ID = "ghost-monitor" # The persona for these automated memories

# --- REGEX FOR ENTITY EXTRACTION ---
# Matches LIN-123 or #123
ISSUE_PATTERN = re.compile(r'\b([A-Z]{2,5}-\d+)\b|\b#(\d+)\b')

class SagaWeaver:
    """
    The Loom that stitches raw events into the Knowledge Graph (Neo4j) 
    AND the Semantic Memory (PGVector).
    """
    def __init__(self):
        self.neo4j = Neo4jAdapter()
        self.running = True

    async def start(self):
        logger.info("🕸️  Saga Weaver (Dual-Write) Started.")
        while self.running:
            try:
                await self.process_terminal_queue()
                await asyncio.sleep(POLL_INTERVAL)
            except Exception as e:
                logger.error(f"Worker Loop Error: {e}", exc_info=True)
                await asyncio.sleep(POLL_INTERVAL)

    async def process_terminal_queue(self):
        """
        Fetches unprocessed terminal events and weaves them into the Graph and Vector Store.
        """
        # We use the Ingest DB to read events
        # Utilizing async context manager for session
        async with get_ingest_session() as read_session:
            # 1. Fetch unprocessed events
            statement = select(TerminalEvent).where(TerminalEvent.processed == False).limit(BATCH_SIZE)
            result = await read_session.execute(statement)
            events = result.scalars().all()

            if not events:
                return

            logger.info(f"Processing {len(events)} terminal events...")

            # We use the Vector DB (Memos) to write memories
            # Using a separate async session context for the write operation
            async with get_vector_session() as write_session:
                for event in events:
                    try:
                        # 2. Extract Entities (The "Saga" Link)
                        linked_entities = self._extract_references(event.command)
                        
                        # 3. Compile Context String (The "Memory")
                        context_text = self._compile_context(event)
                        
                        # 4. Generate Vector (1536d or 1024d)
                        embedding = await generate_embedding(context_text)

                        # 5. WRITE A: Neo4j (Structure)
                        self._push_to_neo4j(event, context_text, embedding, linked_entities)

                        # 6. WRITE B: PGVector (Recall)
                        await self._push_to_pgvector(write_session, event, context_text, embedding, linked_entities)

                        # 7. Mark as Processed
                        event.processed = True
                        # Commit is handled by the context manager or manual commit? 
                        # In SQLAlchemy async, we usually commit on the session.
                        # Committing both sessions.
                        await read_session.commit() # Commit the 'processed' flag
                        await write_session.commit() # Commit the new memory
                        
                        logger.info(f"Weaved Event {event.id} -> Neo4j & PGVector")

                    except Exception as e:
                        logger.error(f"Failed to process event {event.id}: {e}", exc_info=True)
                        await read_session.rollback()
                        await write_session.rollback()

    def _extract_references(self, text: str) -> List[str]:
        if not text:
            return []
        matches = ISSUE_PATTERN.findall(text)
        refs = []
        for m in matches:
            refs.extend([item for item in m if item])
        return list(set(refs))

    def _compile_context(self, event: TerminalEvent) -> str:
        status = "Success" if event.exit_code == 0 else "Failed"
        # Handle cases where timestamps might be None (though schema implies not nullable)
        ts = event.timestamp.isoformat() if event.timestamp else "UNKNOWN_TIME"
        return (
            f"TERMINAL EXECUTION [{ts}]\n"
            f"Command: {event.command}\n"
            f"Directory: {event.cwd}\n"
            f"Result: {status} (Exit Code: {event.exit_code})\n"
            f"Host: {event.host}"
        )

    def _push_to_neo4j(self, event, text: str, vector: List[float], references: List[str]):
        """
        Cypher logic to create nodes and link them to Issues/Projects.
        This runs synchronously via the Neo4j driver adapter which abstracts the session.
        """
        cypher = """
        MERGE (t:TerminalExecution {id: $id})
        SET t.command = $command,
            t.cwd = $cwd,
            t.timestamp = $timestamp,
            t.exit_code = $exit_code,
            t.embedding = $vector,
            t.full_text = $text
        
        MERGE (s:DevSession {id: $session_id})
        MERGE (s)-[:CONTAINS]->(t)
        
        WITH t
        UNWIND $refs as ref
        MATCH (i:LinearIssue {identifier: ref})
        MERGE (t)-[:RESOLVES_OR_RELATES]->(i)
        """
        
        ts = event.timestamp.isoformat() if event.timestamp else None
        
        params = {
            "id": str(event.id),
            "command": event.command,
            "cwd": event.cwd,
            "timestamp": ts,
            "exit_code": event.exit_code,
            "vector": vector,
            "text": text,
            "session_id": event.session_id or "unknown_session",
            "refs": references
        }
        self.neo4j.run(cypher, params)

    async def _push_to_pgvector(self, session, event, text: str, vector: List[float], references: List[str]):
        """
        Raw SQL insertion into the memos.memories table.
        We use raw SQL here to avoid tightly coupling the worker to the memos ORM models.
        """
        
        # Metadata payload for filtering
        metadata = {
            "source": "ghost-terminal",
            "cwd": event.cwd,
            "session_id": event.session_id,
            "exit_code": event.exit_code,
            "references": references
        }

        # Tags for quick filtering in Memos
        tags = ["#terminal", "#ghost", "#auto-capture"]
        if event.exit_code != 0:
            tags.append("#error")
        if references:
            tags.append("#saga")

        sql = text("""
            INSERT INTO memos.memories (
                conversation_hash, 
                agent_id, 
                content, 
                embedding, 
                metadata, 
                tags, 
                created_at
            ) VALUES (
                :hash, 
                :agent, 
                :content, 
                :vector, 
                :metadata, 
                :tags, 
                :created_at
            )
        """)

        await session.execute(sql, {
            "hash": str(event.id), # Use Event UUID as the hash
            "agent": AGENT_ID,
            "content": text,
            "vector": str(vector), # pgvector expects string representation often, or list depending on driver. asyncpg tends to handle lists if registered, but using str is safer for generic SQL execution unless type binding is confirmed.
            "metadata": json.dumps(metadata),
            "tags": tags, # SQLAlchemy handles list->array conversion typically using Postgres dialects
            "created_at": event.timestamp
        })

if __name__ == "__main__":
    # Configure root logger to see output
    logging.basicConfig(level=logging.INFO)
    weaver = SagaWeaver()
    try:
        asyncio.run(weaver.start())
    except KeyboardInterrupt:
        logger.info("Worker stopped.")
