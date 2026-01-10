from fastapi import APIRouter, Depends, HTTPException, Body
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from omega_kg.database.session import get_db
from omega_kg.database.graph import graph_driver
from omega_kg.vector_store import get_vector_store
from omega_kg.utils.capture_utils import write_to_obsidian
from omega_kg.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/guardian", tags=["guardian"])


class Entity(BaseModel):
    name: str
    type: str


class KnowledgeDigest(BaseModel):
    title: str
    summary: str
    entities: List[Entity] = []
    concepts: List[str] = []
    decisions: List[str] = []
    outcomes: List[str] = []
    tags: List[str] = []


class CommitRequest(BaseModel):
    raw_id: str
    type: str  # 'conversation' or 'terminal'
    digest: KnowledgeDigest
    metadata: Dict[str, Any] = {}


class CommitResponse(BaseModel):
    success: bool
    message: str
    storage_results: Dict[str, Any]


@router.post("/commit", response_model=CommitResponse)
async def commit_knowledge(
    request: CommitRequest,
) -> CommitResponse:
    """
    Guardian endpoint to commit prepped knowledge to the ecosystem.
    Evaluates relevance and handles distribution to Graph, Vault, and Vector tiers.
    """
    logger.info(f"Guardian received commit request for {request.type}:{request.raw_id}")

    # 1. Noise Filter / Policy Engine
    # (In the future, we can use an LLM here to evaluate request.digest.summary against
    #  retrieved constraints to decide if it's noise or signal)
    is_relevant = _evaluate_relevance(request)
    if not is_relevant:
        return CommitResponse(
            success=True,
            message="Item marked as noise and skipped for persistence.",
            storage_results={"status": "filtered_out"},
        )

    results = {}

    # 2. Neo4j - Graph Topology
    try:
        results["graph"] = await _store_graph(request)
    except Exception as e:
        logger.error(f"Graph storage failed: {e}")
        results["graph"] = {"success": False, "error": str(e)}

    # 3. Obsidian - Documentation Tier
    try:
        results["vault"] = await _store_vault(request)
    except Exception as e:
        logger.error(f"Vault storage failed: {e}")
        results["vault"] = {"success": False, "error": str(e)}

    # 4. PGVector - Semantic Memory
    try:
        results["vector"] = await _store_vector(request)
    except Exception as e:
        logger.error(f"Vector storage failed: {e}")
        results["vector"] = {"success": False, "error": str(e)}

    return CommitResponse(
        success=True,
        message=f"Knowledge committed for {request.raw_id}",
        storage_results=results,
    )


def _evaluate_relevance(request: CommitRequest) -> bool:
    """
    Guardian logic to determine if data is worth storing.
    Currently a simple heuristic, but intended for LLM evaluation.
    """
    # Filter out empty or extremely short summaries
    if len(request.digest.summary) < 20:
        return False

    # Filter out known 'noise' patterns in terminal
    if request.type == "terminal":
        command = request.metadata.get("command", "")
        if any(p in command for p in ["ls", "cd", "clear", "cls", "dir"]):
            return False

    return True


async def _store_graph(request: CommitRequest) -> Dict:
    async with graph_driver.session() as session:
        if request.type == "conversation":
            # Store Conversation & Relationships
            res = await session.run(
                """
                MERGE (s:ChatSession {raw_id: $raw_id})
                SET s.title = $title,
                    s.summary = $summary,
                    s.platform = $platform,
                    s.processed_at = datetime()
                RETURN elementId(s) as id
            """,
                raw_id=request.raw_id,
                title=request.digest.title,
                summary=request.digest.summary,
                platform=request.metadata.get("platform", "unknown"),
            )

            # Entities
            for ent in request.digest.entities:
                await session.run(
                    """
                    MATCH (s:ChatSession {raw_id: $raw_id})
                    MERGE (e:Entity {name: $name})
                    SET e.type = $type
                    MERGE (s)-[:MENTIONS]->(e)
                """,
                    raw_id=request.raw_id,
                    name=ent.name,
                    type=ent.type,
                )

            return {"success": True, "type": "ChatSession"}

        elif request.type == "terminal":
            await session.run(
                """
                MERGE (t:TerminalExecution {raw_id: $raw_id})
                SET t.command = $command,
                    t.summary = $summary,
                    t.exit_code = $exit_code,
                    t.processed_at = datetime()
            """,
                raw_id=request.raw_id,
                command=request.metadata.get("command", ""),
                summary=request.digest.summary,
                exit_code=request.metadata.get("exit_code", 0),
            )
            return {"success": True, "type": "TerminalExecution"}

    return {"success": False, "message": "Unknown type"}


async def _store_vault(request: CommitRequest) -> Dict:
    if request.type == "conversation":
        tags_str = ", ".join(request.digest.tags)
        safe_platform = request.metadata.get("platform", "unknown").lower()

        content = f"""---
uid: {request.raw_id}
title: {request.digest.title}
tags: [{tags_str}]
created: {datetime.utcnow().isoformat()}
---

# {request.digest.title}

## Summary
{request.digest.summary}

## Key Entities
{chr(10).join([f"- {e.name} ({e.type})" for e in request.digest.entities])}

## Decisions
{chr(10).join([f"- {d}" for d in request.digest.decisions])}
"""
        write_to_obsidian(safe_platform, content, request.raw_id[:8])
        return {"success": True, "path": f"{safe_platform}/{request.raw_id[:8]}.md"}

    return {"success": True, "message": "Not for vault"}


async def _store_vector(request: CommitRequest) -> Dict:
    vector_store = await get_vector_store()

    # Prefix summary with type for better context
    memory_content = f"[{request.type.upper()}] {request.digest.summary}"

    vector_id = await vector_store.store_memory(
        content=memory_content,
        metadata={
            "raw_id": request.raw_id,
            "type": request.type,
            "title": request.digest.title,
        },
        tags=request.digest.tags,
    )
    return {"success": True, "vector_id": vector_id}
