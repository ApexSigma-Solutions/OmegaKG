"""
Omega_KG Ephemeral Capture Server
Receives AI conversations from browser extension via localhost webhook

API Endpoints:
- POST /capture: Receives a conversation payload from the browser extension and writes it to the Obsidian vault.
    Payload (JSON):
        {
            "platform": str,
            "url": str,
            "messages": [
                {"role": "user"|"assistant", "content": str, "timestamp": str}
            ],
            "timestamp": str,
            "conversation_hash": str
        }
    Returns:
        {
            "success": True,
            "filepath": str,
            "message": str
        }
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime
from typing import List, Optional
import uvicorn

from omega_kg.settings import settings
from omega_kg.percolation import PercolationEngine
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

app = FastAPI(title="Omega_KG Capture")

async def batch_percolate():
    """
    Percolate new conversations periodically.

    Scans the 'AI Conversations' directory in the Obsidian vault for markdown notes
    created in the last 10 minutes and percolates them into the knowledge graph.
    """
    print("🔄 Running batch percolation... - capture_server.py:48")
    
    vault_path = Path(settings.obsidian_vault_path)
    conv_dir = vault_path / "AI Conversations"
    
    # Find notes created in last 10 minutes
    cutoff = datetime.now().timestamp() - 600  # 10 min
    
    new_notes = [
        f for f in conv_dir.rglob("*.md")
        if f.stat().st_mtime > cutoff
    ]
    
    if not new_notes:
        print("No new conversations to percolate - capture_server.py:62")
        return
    
    engine = PercolationEngine()
    try:
        for note in new_notes:
            engine.percolate(note)
        print(f"✓ Percolated {len(new_notes)} conversations - capture_server.py:69")
    finally:
        engine.close()

@app.on_event("startup")
async def startup():
    # Schedule percolation every 5 minutes
    scheduler.add_job(batch_percolate, 'interval', minutes=5)
    scheduler.start()
    print("✓ Batch percolation scheduled (every 5 min) - capture_server.py:78")

@app.on_event("shutdown")
async def shutdown():
    scheduler.shutdown()

# CORS for browser extension
# Use settings.cors_allowed_origins if defined, else default to ["*"] for development
if hasattr(settings, "cors_allowed_origins") and settings.cors_allowed_origins:
    allowed_origins = settings.cors_allowed_origins
else:
    allowed_origins = [
        "http://localhost",
        "http://127.0.0.1",
        "http://localhost:8765",
        "http://127.0.0.1:8765",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=[
        "*"
    ],
    allow_headers=[
        "*"
    ],
)


class Message(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: str


class ConversationCapture(BaseModel):
    platform: str
    url: str
    messages: List[Message]
    timestamp: str
    conversation_hash: str


@app.post("/capture")
async def capture_conversation(data: ConversationCapture):
    """
    Receive conversation from browser extension.

    Returns:
        dict: {
            "success": bool,
            "filepath": str,
            "message": str
        }
    """
    
    # Write to Obsidian immediately
    filepath = write_to_obsidian(data)
    
    # Percolate immediately (optional - can be async)
    # Commented out by default for performance
    # engine = PercolationEngine()
    # engine.percolate(filepath)
    # engine.close()
    
    return {
        "success": True,
        "filepath": str(filepath),
        "message": f"Captured {len(data.messages)} messages from {data.platform}"
    }
def write_to_obsidian(data: ConversationCapture) -> Path:
    """
    Write conversation to Obsidian vault.

    Uses a hash-based filename to prevent duplicates and ensure idempotency (skips writing if file already exists).
    """
    
    vault_path = Path(settings.obsidian_vault_path)
    conv_dir = vault_path / "AI Conversations" / data.platform
    conv_dir.mkdir(parents=True, exist_ok=True)
    
    # Use hash as filename (prevents duplicates)
    filename = f"{data.conversation_hash}.md"
    filepath = conv_dir / filename
    
    # Skip if already exists (idempotent)
    if filepath.exists():
        return filepath
    
    # Format as markdown
    markdown = format_conversation_markdown(data)
    filepath.write_text(markdown, encoding='utf-8')
    return filepath
def detect_query_type(query: str) -> str:
    """
    Detect query category from content.

    Categories:
        - 'code': Matches keywords like 'implement', 'code', 'function', 'debug', 'error', 'fix'.
        - 'research': Matches phrases such as 'what is', 'explain', 'how does', 'research', 'latest'.
        - 'planning': Matches 'plan', 'roadmap', 'architecture', 'design', 'strategy'.
        - 'debugging': Matches 'error', 'bug', 'not working', 'issue', 'problem'.
        - 'learning': Matches 'learn', 'tutorial', 'teach', 'understand', 'example'.
        - 'general': Used if no keywords match.

    Matching logic:
        The function checks if any keyword for each category is present in the lowercased query string.
        The first matching category is returned; otherwise, 'general' is returned.
    """
    query_lower = query.lower()
    
    patterns = {
        'code': ['implement', 'code', 'function', 'debug', 'fix'],
        'research': ['what is', 'explain', 'how does', 'research', 'latest'],
        'planning': ['plan', 'roadmap', 'architecture', 'design', 'strategy'],
        'debugging': ['error', 'bug', 'not working', 'issue', 'problem'],
        'learning': ['learn', 'tutorial', 'teach', 'understand', 'example']
    }
    
    for category, keywords in patterns.items():
        if any(kw in query_lower for kw in keywords):
            return category
    
    return 'general'


def format_conversation_markdown(data: ConversationCapture) -> str:
    """
    Format conversation as markdown with rich metadata.
    """
    import yaml

    # Map platform slugs to user-friendly display names
    platform_display_names = {
        "chatgpt": "ChatGPT",
        "claude": "Claude",
        "bard": "Google Bard",
        "gemini": "Gemini",
        "copilot": "GitHub Copilot",
        "bing": "Bing Chat",
        "openai": "OpenAI",
        "perplexity": "Perplexity",
        # Add more as needed
    }
    display_platform = platform_display_names.get(
        data.platform.lower(), data.platform.title()
    )

    # Extract query categories
    user_messages = [m for m in data.messages if m.role == 'user']
    first_query = (
        user_messages[0].content if user_messages else ""
    )

    # Detect query type
    query_type = detect_query_type(first_query)

    # Prepare frontmatter as a dict for YAML serialization,
    # including conversation_hash
    frontmatter = {
        "type": "ai-conversation",
        "platform": data.platform,
        "url": data.url,
        "captured": data.timestamp,
        "conversation_hash": data.conversation_hash,
        "query_type": query_type,
        "message_count": len(data.messages),
        "tags": ["ai", data.platform, "conversation", query_type],
    }
    yaml_frontmatter = yaml.safe_dump(frontmatter, sort_keys=False).strip()

    lines = [
        "---",
        yaml_frontmatter,
        "---",
    ]
    for msg in data.messages:
        role_emoji = "💭" if msg.role == 'user' else "🤖"
        role_label = "You" if msg.role == 'user' else display_platform
        lines.append(f"### {role_emoji} {role_label}")
        lines.append("")
        lines.append(msg.content)
        lines.append("")

    return "\n".join(lines)

def main():
    """
    Starts the Omega_KG Capture Server on port 8765.
    Health check endpoint available at /health.
    """
    print("🚀 Starting Omega_KG Capture Server - capture_server.py:271")
    print("Listening on: http://localhost:8765 - capture_server.py:272")
    print("Health check: http://localhost:8765/health - capture_server.py:273")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8765,
        log_level="info"
    )


if __name__ == "__main__":
    main()