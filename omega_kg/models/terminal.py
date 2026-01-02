from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# --- Pydantic Models ---

class TerminalCommandData(BaseModel):
    """Payload received from the terminal hook."""
    command: str
    cwd: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    exit_code: Optional[int] = None
    output: Optional[str] = None
    user: Optional[str] = None
    host: Optional[str] = None
    session_id: Optional[str] = None

class TerminalCaptureResponse(BaseModel):
    status: str
    event_id: UUID
    processed: bool

# --- SQLAlchemy Models ---

class TerminalEvent(Base):
    """Raw terminal event stored in the Ingest Database."""
    __tablename__ = "terminal_events"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    command = Column(Text, nullable=False)
    cwd = Column(String, nullable=False)
    exit_code = Column(Integer, nullable=True)
    output = Column(Text, nullable=True)
    user = Column(String, nullable=True)
    host = Column(String, nullable=True)
    session_id = Column(String, nullable=True)
    
    # Processing Status
    processed = Column(Boolean, default=False)
    processed_at = Column(DateTime, nullable=True)
    error = Column(Text, nullable=True)

    def __repr__(self):
        return f"<TerminalEvent(id={self.id}, command='{self.command[:20]}...', timestamp={self.timestamp})>"
