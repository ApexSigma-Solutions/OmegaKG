from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from pgvector.sqlalchemy import Vector
from omega_kg.database.base import Base


class RawConversation(Base):
    """
    Stores raw conversation data received from the Chrome extension.
    This serves as the 'raw lake' for AI conversations before processing.
    """

    __tablename__ = "raw_conversations"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    source_id = Column(String(255), unique=True, nullable=False)  # Conversation Hash
    platform = Column(String(50), nullable=True)
    raw_payload = Column(JSONB, nullable=False)  # Full JSON payload
    captured_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Processing Status (for InGest-LLM)
    processed = Column(Boolean, default=False)
    processed_at = Column(DateTime, nullable=True)
    processing_attempts = Column(Integer, default=0, nullable=False)
    last_error = Column(Text, nullable=True)

    # Text Embedding (Vector)
    embedding = Column(Vector(1024), nullable=True)

    def __repr__(self):
        return f"<RawConversation(id={self.id}, platform='{self.platform}', source_id='{self.source_id}')>"
