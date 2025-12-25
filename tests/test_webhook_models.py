"""
Unit tests for RawWebhookEvent models.

Tests both SQLAlchemy and Pydantic models for the Integrity Layer.
"""

import pytest
from datetime import datetime, timezone


@pytest.mark.unit
def test_raw_webhook_event_sqlalchemy_model():
    """Test that RawWebhookEvent SQLAlchemy model is properly defined."""
    from omega_kg.database.models import RawWebhookEvent
    
    # Verify table name
    assert RawWebhookEvent.__tablename__ == "raw_webhook_events"
    
    # Verify columns exist
    columns = RawWebhookEvent.__table__.columns.keys()
    expected_columns = [
        "id",
        "signature",
        "received_at",
        "external_timestamp",
        "event_type",
        "action",
        "source",
        "headers",
        "body",
        "processed",
        "processed_at",
        "error_log",
    ]
    
    for col in expected_columns:
        assert col in columns, f"Column {col} not found in model"


@pytest.mark.unit
def test_pydantic_raw_webhook_event_create():
    """Test Pydantic RawWebhookEventCreate model."""
    from omega_kg.models.webhook import RawWebhookEventCreate
    
    # Create a valid event
    event_data = {
        "signature": "test_signature_123",
        "event_type": "Issue",
        "action": "create",
        "source": "linear",
        "headers": {"Content-Type": "application/json"},
        "body": {"type": "Issue", "action": "create", "data": {}},
    }
    
    event = RawWebhookEventCreate(**event_data)
    
    assert event.signature == "test_signature_123"
    assert event.event_type == "Issue"
    assert event.action == "create"
    assert event.source == "linear"
    assert event.headers == {"Content-Type": "application/json"}
    assert event.body == {"type": "Issue", "action": "create", "data": {}}


@pytest.mark.unit
def test_pydantic_raw_webhook_event_full():
    """Test Pydantic RawWebhookEvent model with all fields."""
    from omega_kg.models.webhook import RawWebhookEvent
    
    now = datetime.now(timezone.utc)
    
    event_data = {
        "id": 1,
        "signature": "test_signature_123",
        "received_at": now,
        "external_timestamp": now,
        "event_type": "Issue",
        "action": "create",
        "source": "linear",
        "headers": {"Content-Type": "application/json"},
        "body": {"type": "Issue", "action": "create", "data": {}},
        "processed": True,
        "processed_at": now,
        "error_log": None,
    }
    
    event = RawWebhookEvent(**event_data)
    
    assert event.id == 1
    assert event.signature == "test_signature_123"
    assert event.processed is True
    assert event.error_log is None


@pytest.mark.unit
def test_pydantic_raw_webhook_event_update():
    """Test Pydantic RawWebhookEventUpdate model."""
    from omega_kg.models.webhook import RawWebhookEventUpdate
    
    now = datetime.now(timezone.utc)
    
    update_data = {
        "processed": True,
        "processed_at": now,
        "error_log": "Test error message",
    }
    
    update = RawWebhookEventUpdate(**update_data)
    
    assert update.processed is True
    assert update.processed_at == now
    assert update.error_log == "Test error message"


@pytest.mark.unit
def test_pydantic_raw_webhook_event_default_source():
    """Test that source defaults to 'linear'."""
    from omega_kg.models.webhook import RawWebhookEventCreate
    
    event_data = {
        "signature": "test_signature_123",
        "headers": {"Content-Type": "application/json"},
        "body": {"type": "Issue", "action": "create", "data": {}},
    }
    
    event = RawWebhookEventCreate(**event_data)
    
    assert event.source == "linear"


@pytest.mark.unit
def test_raw_linear_event_compatibility():
    """Test that RawLinearEvent model is still available for backward compatibility."""
    from omega_kg.models.linear import RawLinearEvent
    
    # Verify table name
    assert RawLinearEvent.__tablename__ == "raw_linear_events"
    
    # Verify it has the expected columns
    columns = RawLinearEvent.__table__.columns.keys()
    expected_columns = ["id", "signature", "received_at", "event_type", "action", "headers", "body", "processed"]
    
    for col in expected_columns:
        assert col in columns, f"Column {col} not found in RawLinearEvent"
