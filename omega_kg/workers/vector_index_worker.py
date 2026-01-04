
import asyncio
import logging
from typing import Optional, Any
from omega_kg.vector_store import get_vector_store
from omega_kg.services.openai_service import generate_embedding
from neo4j import GraphDatabase
from omega_kg.settings import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("omega.worker.vector")
logger.setLevel(logging.INFO)

POLL_INTERVAL = 10  # Seconds
BATCH_SIZE = 50

class VectorIndexWorker:
    def __init__(self):
        self.running = True
        self.driver = GraphDatabase.driver(
            settings.neo4j_uri, 
            auth=(settings.neo4j_user, settings.neo4j_password)
        )
        logger.info("Vector Index Worker Initialized")

    async def start(self):
        logger.info("Vector Index Worker Started. Polling for pending embeddings...")
        while self.running:
            try:
                await self.process_batch()
            except Exception as e:
                logger.error(f"Worker Loop Error: {e}", exc_info=True)
            
            await asyncio.sleep(POLL_INTERVAL)

    async def process_batch(self):
        # 1. Fetch pending items
        vs = await get_vector_store()
        try:
            items = await vs.fetch_pending_batch(BATCH_SIZE)
        except Exception as e:
             logger.error(f"Database Fetch Error: {e}")
             return

        if not items:
            return

        logger.info(f"Processing batch of {len(items)} items...")

        for item in items:
            await self.process_item(vs, item)

    async def process_item(self, vs, item):
        vector_id = item['vector_id']
        uid = item['message_id']
        label = item['node_label']
        
        try:
            text_to_embed = self._fetch_content_neo4j(uid, label)
            
            if not text_to_embed:
                logger.warning(f"No content found for {label} {uid}. Marking as failed.")
                await vs.mark_failed(vector_id)
                return

            embedding = await generate_embedding(text_to_embed)
            
            if not embedding:
                logger.error(f"Failed to generate embedding for {uid}.")
                await vs.mark_failed(vector_id)
                return

            # Update PGVector
            await vs.update_embedding(vector_id, embedding)
            
            # Update Neo4j
            self._update_neo4j_embedding(uid, label, embedding)
            
            logger.info(f"Indexed {label} {uid} successfully.")

        except Exception as e:
            logger.error(f"Error processing {uid}: {e}")
            await vs.mark_failed(vector_id)

    def _fetch_content_neo4j(self, uid: str, label: str) -> Optional[str]:
        with self.driver.session() as session:
            if label == 'Task':
                query = "MATCH (t:Task {uid: $uid}) RETURN t.title, t.content"
                res = session.run(query, uid=uid)
                record = res.single()
                if record:
                    title = record['t.title'] or ""
                    content = record['t.content'] or ""
                    return f"Task: {title}\n{content}"
            # Add other node types here if needed
            elif label == 'TerminalExecution':
                 # Fallback if we start indexing terminal via this queue too
                 query = "MATCH (n:TerminalExecution {id: $uid}) RETURN n.full_text"
                 res = session.run(query, uid=uid)
                 record = res.single()
                 if record:
                     return record['n.full_text']
            
            logger.warning(f"Unsupported or missing node: {label} {uid}")
            return None

    def _update_neo4j_embedding(self, uid: str, label: str, embedding: Any):
        with self.driver.session() as session:
            query = f"MATCH (n:{label} {{uid: $uid}}) SET n.embedding = $emb"
            session.run(query, uid=uid, emb=embedding)

    async def close(self):
        self.running = False
        self.driver.close()

# Integration helpers
_worker_instance: Optional[VectorIndexWorker] = None
_worker_task: Optional[asyncio.Task] = None

async def start_worker():
    global _worker_instance, _worker_task
    if _worker_instance: 
        return
    _worker_instance = VectorIndexWorker()
    _worker_task = asyncio.create_task(_worker_instance.start())

async def stop_worker():
    global _worker_instance, _worker_task
    if _worker_instance:
        await _worker_instance.close()
    if _worker_task:
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass
    _worker_instance = None
    _worker_task = None

if __name__ == "__main__":
    worker = VectorIndexWorker()
    try:
        asyncio.run(worker.start())
    except KeyboardInterrupt:
        asyncio.run(worker.close())
