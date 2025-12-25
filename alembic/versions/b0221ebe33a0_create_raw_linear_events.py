"""Create raw_linear_events table

Revision ID: b0221ebe33a0
Revises: 
Create Date: 2025-11-20 12:00:00.000000

TN-101: Integrity Layer - Raw Data Lake

Purpose:
Create the RawLinearEvent table to support the Integrity Layer.
Uses JSONB for payload storage to ensure zero data loss during ingestion.

Schema Design:
- id: Primary key with index
- signature: Webhook signature for verification
- received_at: Server timestamp when webhook received
- external_timestamp: Timestamp from Linear payload (optional)
- event_type: Indexed for efficient querying by type
- action: Event action from payload
- headers: JSONB storage for HTTP headers (zero data loss)
- body: JSONB storage for full webhook payload (zero data loss)
- processed: Boolean flag for processing status
- error_log: Error message if processing failed (nullable)

This table ensures we never lose webhook data, supporting replay and debugging.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = "b0221ebe33a0"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create the raw_linear_events table for the Integrity Layer.
    
    This table stores all incoming Linear webhook events with full payload preservation
    using JSONB to ensure zero data loss during ingestion.
    """
    op.create_table(
        "raw_linear_events",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column(
            "signature",
            sa.String(),
            nullable=False,
            comment="Webhook signature for verification",
        ),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment="Timestamp when webhook was received",
        ),
        sa.Column(
            "external_timestamp",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp from Linear payload (data.createdAt)",
        ),
        sa.Column(
            "event_type",
            sa.String(),
            nullable=True,
            comment="Type of event from webhook",
        ),
        sa.Column("action", sa.String(), nullable=True, comment="Action performed in the event"),
        sa.Column(
            "headers",
            JSONB(),
            nullable=False,
            comment="HTTP headers from webhook request",
        ),
        sa.Column("body", JSONB(), nullable=False, comment="Full webhook payload as JSON"),
        sa.Column(
            "processed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="Whether this event has been processed",
        ),
        sa.Column(
            "error_log",
            sa.String(),
            nullable=True,
            comment="Error message if processing failed",
        ),
        sa.PrimaryKeyConstraint("id"),
        comment="Raw Linear webhook event storage for Integrity Layer with JSONB payload preservation",
    )

    # Create indexes for efficient querying
    op.create_index("ix_raw_linear_events_id", "raw_linear_events", ["id"])
    op.create_index("ix_raw_linear_events_event_type", "raw_linear_events", ["event_type"])


def downgrade() -> None:
    """
    Drop the raw_linear_events table and its indexes.
    
    WARNING: This will permanently delete all Linear webhook event data.
    """
    op.drop_index("ix_raw_linear_events_event_type", table_name="raw_linear_events")
    op.drop_index("ix_raw_linear_events_id", table_name="raw_linear_events")
    op.drop_table("raw_linear_events")
