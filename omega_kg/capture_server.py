#!/usr/bin/env python
"""
Omega_KG Capture Server

FastAPI server that receives AI conversations from chrome extension,
saves them to Obsidian vault, and percolates to Neo4j.
"""

import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from neo4j import GraphDatabase
from pydantic import BaseModel, Field

from omega_kg.settings import settings
from omega_kg.percolation import PercolationEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Omega_KG Capture Server",
    description="Receives AI conversations and integrates with Neo4j",
    version="1.0.0"
)

# Add CORS middleware for chrome extension
# SECURITY NOTE: Using wildcard origin for development/testing purposes.
# In production, restrict to specific Chrome extension ID: chrome-extension://<extension-id>
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for Chrome extension development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for request validation
class Message(BaseModel):
    """Individual message in a conversation."""
    role: str = Field(..., description="Message role (user/assistant)")
    content: str = Field(..., description="Message content")
    timestamp: Optional[str] = Field(None, description="Message timestamp")


class ConversationData(BaseModel):
    """Conversation data from chrome extension."""
    platform: str = Field(..., description="AI platform name")
    url: str = Field(..., description="Conversation URL")
    title: Optional[str] = Field(None, description="Conversation title")
    messages: List[Message] = Field(
        ..., description="List of conversation messages"
    )
    metadata: Optional[Dict] = Field(
        default_factory=dict, description="Additional metadata"
    )


class CaptureResponse(BaseModel):
    """Response after successful capture."""
    success: bool
    file_path: str
    nodes_created: int
    message: str


def generate_conversation_hash(data: ConversationData) -> str:
    """
    Create a short, deterministic identifier for a conversation.
    
    Parameters:
        data (ConversationData): Conversation payload whose platform, url, and messages list are used to derive the identifier.
    
    Returns:
        str: An 8-character hexadecimal string derived from the MD5 hash of the conversation's platform, URL, and message count.
    """
    content = f"{data.platform}-{data.url}-{len(data.messages)}"
    hash_obj = hashlib.md5(content.encode())
    return hash_obj.hexdigest()[:8]


def format_conversation_markdown(data: ConversationData) -> str:
    """
    Format a ConversationData into an Obsidian-compatible Markdown document with YAML frontmatter.
    
    The frontmatter contains platform, date, url, message_count, captured_at, conversation_hash, optional title, participants, and any provided metadata. The body contains a title, summary fields (date, platform, URL, message count) and the conversation messages as numbered sections with role, content, and optional message timestamps.
    
    Returns:
        str: Complete Markdown document including YAML frontmatter and human-readable conversation body.
    """
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    timestamp_str = now.isoformat()
    
    # Generate conversation hash
    conv_hash = generate_conversation_hash(data)
    
    # Build frontmatter
    frontmatter_lines = [
        "---",
        f"platform: {data.platform}",
        f"date: {date_str}",
        f"url: {data.url}",
        f"message_count: {len(data.messages)}",
        f"captured_at: {timestamp_str}",
        f"conversation_hash: {conv_hash}",
    ]
    
    if data.title:
        frontmatter_lines.append(f"title: {data.title}")
    
    # Add participants
    roles = list(set(msg.role for msg in data.messages))
    frontmatter_lines.append(f"participants: {roles}")
    
    # Add metadata if present
    if data.metadata:
        for key, value in data.metadata.items():
            frontmatter_lines.append(f"{key}: {value}")
    
    frontmatter_lines.append("---")
    frontmatter = "\n".join(frontmatter_lines)
    
    # Build conversation content
    title = data.title or f"{data.platform} Conversation"
    content_lines = [
        f"\n# {title}",
        f"\n**Date**: {date_str}",
        f"**Platform**: {data.platform}",
        f"**URL**: [{data.url}]({data.url})",
        f"**Messages**: {len(data.messages)}\n",
        "---\n"
    ]
    
    # Add messages
    for i, msg in enumerate(data.messages, 1):
        role_emoji = "👤" if msg.role.lower() == "user" else "🤖"
        role_title = msg.role.title()
        
        content_lines.append(f"\n## {role_emoji} Message {i} ({role_title})\n")
        content_lines.append(msg.content)
        content_lines.append("\n")
        
        if msg.timestamp:
            content_lines.append(f"*Sent: {msg.timestamp}*\n")
    
    # Combine frontmatter and content
    markdown = frontmatter + "\n" + "\n".join(content_lines)
    
    return markdown


def write_to_obsidian(
    platform: str,
    content: str,
    conversation_hash: str
) -> Path:
    """
    Write a conversation markdown file into the Obsidian vault under AI_Conversations/<platform>/.
    
    Parameters:
        platform (str): Platform name used to create the subfolder (spaces normalized to underscores).
        content (str): Markdown content to write to the file.
        conversation_hash (str): Short hash appended to the filename to ensure uniqueness.
    
    Returns:
        Path: Path to the created markdown file.
    
    Raises:
        ValueError: If the configured Obsidian vault path does not exist.
        IOError: If writing the file fails.
    """
    vault_path = Path(settings.obsidian_vault_path)
    
    if not vault_path.exists():
        raise ValueError(f"Obsidian vault not found: {vault_path}")
    
    # Normalize platform name for folder
    platform_folder = platform.replace(" ", "_")
    ai_conv_path = vault_path / "AI_Conversations" / platform_folder
    
    # Create folder if it doesn't exist
    ai_conv_path.mkdir(parents=True, exist_ok=True)
    
    # Generate filename: YYYY-MM-DD-{hash}.md
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"{date_str}-{conversation_hash}.md"
    file_path = ai_conv_path / filename
    
    # Write content
    try:
        file_path.write_text(content, encoding="utf-8")
        logger.info(f"Wrote conversation to: {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"Failed to write file: {e}")
        raise IOError(f"Failed to write markdown file: {e}")


def percolate_to_neo4j(file_path: Path, data: ConversationData) -> int:
    """
    Persist the conversation into Neo4j by creating or updating a ChatSession node and extracting Decision nodes from messages.
    
    Parameters:
        file_path (Path): Filesystem path to the conversation's markdown file.
        data (ConversationData): Conversation payload used to populate node properties and to extract decision content.
    
    Returns:
        int: Number of nodes created in Neo4j for this conversation.
    """
    try:
        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )
        
        nodes_created = 0
        
        with driver.session() as session:
            # Create ChatSession node
            conv_hash = generate_conversation_hash(data)
            
            result = session.run(
                """
                MERGE (s:ChatSession {conversation_hash: $hash})
                ON CREATE SET
                    s.date = date($date),
                    s.platform = $platform,
                    s.filepath = $filepath,
                    s.url = $url,
                    s.message_count = $msg_count,
                    s.created_at = datetime($created_at)
                ON MATCH SET
                    s.updated_at = datetime($created_at)
                RETURN s
                """,
                hash=conv_hash,
                date=datetime.now().strftime("%Y-%m-%d"),
                platform=data.platform,
                filepath=str(file_path),
                url=data.url,
                msg_count=len(data.messages),
                created_at=datetime.now().isoformat()
            )
            
            if result.single():
                nodes_created += 1
                logger.info(f"Created ChatSession node: {conv_hash}")
            
            # Extract potential decisions from conversation
            # (Simple keyword-based extraction for now)
            decision_keywords = [
                "decided to", "will use", "going to",
                "plan is", "approach is", "solution is"
            ]
            
            for i, msg in enumerate(data.messages):
                content_lower = msg.content.lower()
                
                # Check if message contains decision keywords
                for keyword in decision_keywords:
                    if keyword in content_lower:
                        # Extract sentence containing keyword
                        sentences = msg.content.split(".")
                        for sentence in sentences:
                            if keyword in sentence.lower():
                                decision_content = sentence.strip()
                                
                                # Create Decision node
                                result = session.run(
                                    """
                                    MATCH (s:ChatSession {
                                        conversation_hash: $hash
                                    })
                                    CREATE (d:Decision {
                                        content: $content,
                                        decision_id: $dec_id,
                                        extracted_at: datetime($extracted_at)
                                    })
                                    CREATE (s)-[:CONTAINS]->(d)
                                    RETURN d
                                    """,
                                    hash=conv_hash,
                                    content=decision_content,
                                    dec_id=f"{conv_hash}-dec-{i}",
                                    extracted_at=datetime.now().isoformat()
                                )
                                
                                if result.single():
                                    nodes_created += 1
                                    logger.info(
                                        f"Created Decision: {decision_content[:50]}"
                                    )
                                
                                break  # Only one decision per message
        
        driver.close()
        logger.info(f"Created {nodes_created} nodes in Neo4j")
        return nodes_created
        
    except Exception as e:
        logger.error(f"Neo4j percolation failed: {e}")
        raise


@app.get("/")
async def root():
    """
    Expose basic server metadata and available endpoints.
    
    Returns:
        dict: Mapping with keys:
            - service: service name
            - status: current service status
            - version: service version
            - endpoints: dict mapping endpoint names (e.g., "capture", "health") to their HTTP routes
    """
    return {
        "service": "Omega_KG Capture Server",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "capture": "POST /capture",
            "health": "GET /health"
        }
    }


@app.get("/health")
async def health_check():
    """
    Provide a health snapshot of Obsidian vault accessibility and Neo4j connectivity.
    
    Returns:
        dict: Health information containing:
            - status (str): Overall status, typically "healthy".
            - timestamp (str): ISO 8601 timestamp of the check.
            - vault_accessible (bool): `True` if the configured vault path exists, `False` otherwise.
            - vault_path (str, optional): The configured vault path if available.
            - neo4j_connected (bool): `True` if a simple query to Neo4j succeeded, `False` otherwise.
            - neo4j_error (str, optional): Error message when Neo4j connectivity failed.
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "vault_accessible": False,
        "neo4j_connected": False
    }
    
    # Check vault accessibility
    try:
        vault_path = Path(settings.obsidian_vault_path)
        health_status["vault_accessible"] = vault_path.exists()
        health_status["vault_path"] = str(vault_path)
    except Exception as e:
        logger.warning(f"Vault check failed: {e}")
    
    # Check Neo4j connectivity
    try:
        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )
        with driver.session() as session:
            session.run("RETURN 1")
        driver.close()
        health_status["neo4j_connected"] = True
    except Exception as e:
        logger.warning(f"Neo4j check failed: {e}")
        health_status["neo4j_error"] = str(e)
    
    return health_status


@app.post("/capture", response_model=CaptureResponse)
async def capture_conversation(data: ConversationData):
    """
    Process a captured ConversationData by formatting it to Obsidian-compatible Markdown, saving it to the configured vault, and percolating the conversation into Neo4j.
    
    Parameters:
        data (ConversationData): Conversation payload from the Chrome extension containing platform, url, messages, and optional metadata.
    
    Returns:
        CaptureResponse: Contains success status, the created file path, the number of Neo4j nodes created, and a descriptive message.
    
    Raises:
        HTTPException: On failure to validate input (400), write the file (500), or percolate data to Neo4j (500).
    """
    logger.info(
        f"Received capture request: {data.platform} "
        f"({len(data.messages)} messages)"
    )
    
    try:
        # 1. Format as markdown
        markdown_content = format_conversation_markdown(data)
        logger.info("Formatted conversation as markdown")
        
        # 2. Generate hash for filename
        conv_hash = generate_conversation_hash(data)
        
        # 3. Write to Obsidian vault
        file_path = write_to_obsidian(
            platform=data.platform,
            content=markdown_content,
            conversation_hash=conv_hash
        )
        logger.info(f"Wrote to Obsidian: {file_path}")
        
        # 4. Percolate to Neo4j
        nodes_created = percolate_to_neo4j(file_path, data)
        logger.info(f"Created {nodes_created} Neo4j nodes")
        
        # 5. Return success response
        return CaptureResponse(
            success=True,
            file_path=str(file_path),
            nodes_created=nodes_created,
            message=(
                f"Successfully captured {len(data.messages)} messages "
                f"from {data.platform}"
            )
        )
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except IOError as e:
        logger.error(f"File write error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Capture failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to capture conversation: {str(e)}"
        )


async def batch_percolate_sessions():
    """
    Percolates PowerShell session logs from the configured Sessions folder into Neo4j.
    
    If the Sessions folder is missing, the function returns without error. When session files are present, it uses the PercolationEngine to percolate them into Neo4j and logs aggregated statistics; errors are logged.
    """
    try:
        sessions_path = Path(settings.obsidian_vault_path) / "Sessions"
        
        if not sessions_path.exists():
            logger.warning(f"Sessions path does not exist: {sessions_path}")
            return
        
        # Initialize Neo4j driver and percolation engine
        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )
        engine = PercolationEngine(driver)
        
        # Percolate all session files
        stats = engine.percolate_from_vault(sessions_path)
        logger.info(
            f"Percolated session logs: {stats['tasks']} tasks, "
            f"{stats['commits']} commits, {stats['links']} decision links"
        )
        
        driver.close()
        
    except Exception as e:
        logger.error(f"Batch session percolation failed: {e}")


@app.on_event("startup")
async def startup_event():
    """Schedule batch percolation on server startup."""
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        batch_percolate_sessions,
        'interval',
        minutes=5,
        id='session_percolation'
    )
    scheduler.start()
    logger.info("✓ Session percolation scheduled (every 5 minutes)")


def main():
    """
    Start the Omega_KG FastAPI capture server using Uvicorn on 127.0.0.1:8765.
    
    Logs configured startup information (Obsidian vault path and Neo4j URI) and blocks the calling process while the server runs.
    """
    import uvicorn
    
    logger.info("Starting Omega_KG Capture Server...")
    logger.info(f"Vault path: {settings.obsidian_vault_path}")
    logger.info(f"Neo4j URI: {settings.neo4j_uri}")
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8765,
        log_level="info"
    )


if __name__ == "__main__":
    main()
