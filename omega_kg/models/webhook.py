"""
Pydantic models for webhook events.

These models mirror the database schema for RawWebhookEvent
and provide validation for webhook event data.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class RawWebhookEventBase(BaseModel):
    """Base model for raw webhook events."""
    
    signature: str = Field(..., description="Webhook signature for verification")
    event_type: Optional[str] = Field(None, description="Type of event from webhook")
    action: Optional[str] = Field(None, description="Action performed in the event")
    source: str = Field(default="linear", description="Source system of the webhook")
    headers: Dict[str, Any] = Field(..., description="HTTP headers from webhook request")
    body: Dict[str, Any] = Field(..., description="Full webhook payload as JSON")
    external_timestamp: Optional[datetime] = Field(
        None,
        description="Timestamp from webhook payload"
    )


class RawWebhookEventCreate(RawWebhookEventBase):
    """Model for creating a new raw webhook event."""
    pass


class RawWebhookEventUpdate(BaseModel):
    """Model for updating an existing raw webhook event."""
    
    processed: Optional[bool] = Field(None, description="Whether event has been processed")
    processed_at: Optional[datetime] = Field(None, description="When event was processed")
    error_log: Optional[str] = Field(None, description="Error message if processing failed")


class RawWebhookEvent(RawWebhookEventBase):
    """Complete model for raw webhook event including DB fields."""
    
    id: int
    received_at: datetime = Field(..., description="Timestamp when webhook was received")
    processed: bool = Field(default=False, description="Whether event has been processed")
    processed_at: Optional[datetime] = Field(None, description="When event was processed")
    error_log: Optional[str] = Field(None, description="Error message if processing failed")

    model_config = {"from_attributes": True}
