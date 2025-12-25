"""
Database models for the Integrity Layer.

This module contains SQLAlchemy models for raw webhook event storage,
ensuring zero data loss during ingestion using JSONB payload storage.
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from omega_kg.database.base import Base


class RawWebhookEvent(Base):
    """
    Raw webhook event storage table for the Integrity Layer.
    
    Stores all incoming webhook events with full payload preservation
    using JSONB to ensure zero data loss during ingestion.
    """
    __tablename__ = "raw_webhook_events"

    id = Column(Integer, primary_key=True, index=True)

    # Audit Trail
    signature = Column(String, nullable=False, comment="Webhook signature for verification")
    received_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="Timestamp when webhook was received"
    )
    external_timestamp = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp from webhook payload (e.g., data.createdAt)"
    )

    # Metadata
    event_type = Column(String, index=True, comment="Type of event from webhook")
    action = Column(String, comment="Action performed in the event")
    source = Column(
        String,
        nullable=False,
        default="linear",
        server_default=text("'linear'"),
        comment="Source system of the webhook (e.g., linear, github)"
    )

    # Payload - JSONB for zero data loss
    headers = Column(JSONB, nullable=False, comment="HTTP headers from webhook request")
    body = Column(JSONB, nullable=False, comment="Full webhook payload as JSON")

    # Processing Status
    processed = Column(
        Boolean,
        default=False,
        server_default=text("false"),
        comment="Whether this event has been processed"
    )
    processed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when event was processed"
    )
    error_log = Column(String, nullable=True, comment="Error message if processing failed")
