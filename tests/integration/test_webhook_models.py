"""
Integration tests for RawWebhookEvent database models and migrations.

Tests the SQLAlchemy models against a real PostgreSQL database.
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy import inspect, text


@pytest.mark.integration
@pytest.mark.requires_postgres
def test_raw_webhook_events_table_structure(db_engine):
    """Test that the raw_webhook_events table has the correct structure."""
    from omega_kg.database.models import RawWebhookEvent
    from omega_kg.database.base import Base
    
    # Create tables
    Base.metadata.create_all(db_engine)
    
    # Inspect the table
    inspector = inspect(db_engine)
    
    # Verify table exists
    assert "raw_webhook_events" in inspector.get_table_names()
    
    # Get columns
    columns = {col["name"]: col for col in inspector.get_columns("raw_webhook_events")}
    
    # Verify required columns exist
    assert "id" in columns
    assert "signature" in columns
    assert "received_at" in columns
    assert "external_timestamp" in columns
    assert "event_type" in columns
    assert "action" in columns
    assert "source" in columns
    assert "headers" in columns
    assert "body" in columns
    assert "processed" in columns
    assert "processed_at" in columns
    assert "error_log" in columns
    
    # Verify primary key
    pk_constraint = inspector.get_pk_constraint("raw_webhook_events")
    assert pk_constraint["constrained_columns"] == ["id"]
    
    # Verify indexes
    indexes = inspector.get_indexes("raw_webhook_events")
    index_names = [idx["name"] for idx in indexes]
    
    # Should have index on id and event_type
    assert any("id" in idx["name"] or idx["column_names"] == ["id"] for idx in indexes)
    assert any("event_type" in idx["name"] or "event_type" in idx["column_names"] for idx in indexes)


@pytest.mark.integration
@pytest.mark.requires_postgres
def test_raw_webhook_event_insert_and_query(db_engine):
    """Test inserting and querying RawWebhookEvent records."""
    from omega_kg.database.models import RawWebhookEvent
    from omega_kg.database.base import Base
    from sqlalchemy.orm import Session
    
    # Create tables
    Base.metadata.create_all(db_engine)
    
    # Create a session
    with Session(db_engine) as session:
        # Create an event
        event = RawWebhookEvent(
            signature="test_signature_123",
            event_type="Issue",
            action="create",
            source="linear",
            headers={"Content-Type": "application/json"},
            body={"type": "Issue", "action": "create", "data": {"id": "test-123"}},
            external_timestamp=datetime.now(timezone.utc),
            processed=False,
        )
        
        session.add(event)
        session.commit()
        
        # Query it back
        queried_event = session.query(RawWebhookEvent).filter_by(
            signature="test_signature_123"
        ).first()
        
        assert queried_event is not None
        assert queried_event.signature == "test_signature_123"
        assert queried_event.event_type == "Issue"
        assert queried_event.action == "create"
        assert queried_event.source == "linear"
        assert queried_event.headers == {"Content-Type": "application/json"}
        assert queried_event.body["data"]["id"] == "test-123"
        assert queried_event.processed is False
        assert queried_event.received_at is not None


@pytest.mark.integration
@pytest.mark.requires_postgres
def test_raw_webhook_event_jsonb_storage(db_engine):
    """Test that JSONB columns properly store and retrieve complex JSON data."""
    from omega_kg.database.models import RawWebhookEvent
    from omega_kg.database.base import Base
    from sqlalchemy.orm import Session
    
    # Create tables
    Base.metadata.create_all(db_engine)
    
    # Complex nested JSON structure
    complex_headers = {
        "Content-Type": "application/json",
        "X-Custom-Header": "value",
        "nested": {"key": "value", "array": [1, 2, 3]},
    }
    
    complex_body = {
        "type": "Issue",
        "action": "update",
        "data": {
            "id": "test-456",
            "title": "Test Issue",
            "description": "This is a test",
            "labels": ["bug", "urgent"],
            "metadata": {"priority": 1, "tags": ["backend", "api"]},
        },
    }
    
    with Session(db_engine) as session:
        event = RawWebhookEvent(
            signature="test_complex_json",
            headers=complex_headers,
            body=complex_body,
        )
        
        session.add(event)
        session.commit()
        
        # Query it back
        queried_event = session.query(RawWebhookEvent).filter_by(
            signature="test_complex_json"
        ).first()
        
        assert queried_event is not None
        assert queried_event.headers == complex_headers
        assert queried_event.body == complex_body
        assert queried_event.body["data"]["labels"] == ["bug", "urgent"]
        assert queried_event.body["data"]["metadata"]["tags"] == ["backend", "api"]


@pytest.mark.integration
@pytest.mark.requires_postgres
def test_raw_webhook_event_processing_workflow(db_engine):
    """Test the processing workflow with processed flag and timestamps."""
    from omega_kg.database.models import RawWebhookEvent
    from omega_kg.database.base import Base
    from sqlalchemy.orm import Session
    
    # Create tables
    Base.metadata.create_all(db_engine)
    
    with Session(db_engine) as session:
        # Create an unprocessed event
        event = RawWebhookEvent(
            signature="test_workflow",
            headers={"test": "header"},
            body={"test": "body"},
            processed=False,
        )
        
        session.add(event)
        session.commit()
        
        event_id = event.id
        
        # Simulate processing
        event_to_process = session.get(RawWebhookEvent, event_id)
        assert event_to_process.processed is False
        assert event_to_process.processed_at is None
        
        # Mark as processed
        event_to_process.processed = True
        event_to_process.processed_at = datetime.now(timezone.utc)
        session.commit()
        
        # Verify update
        processed_event = session.get(RawWebhookEvent, event_id)
        assert processed_event.processed is True
        assert processed_event.processed_at is not None


@pytest.mark.integration
@pytest.mark.requires_postgres
def test_raw_linear_events_table_exists(db_engine):
    """Test backward compatibility - RawLinearEvent table can be created."""
    from omega_kg.models.linear import RawLinearEvent
    from omega_kg.database.base import Base
    
    # Create tables
    Base.metadata.create_all(db_engine)
    
    # Inspect the table
    inspector = inspect(db_engine)
    
    # Verify table exists
    assert "raw_linear_events" in inspector.get_table_names()
