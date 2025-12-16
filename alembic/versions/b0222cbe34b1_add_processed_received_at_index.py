"""add_processed_received_at_index

Revision ID: b0222cbe34b1
Revises: b0221ebe33a0
Create Date: 2025-11-24 06:00:00.000000

This migration adds a composite index on (processed, received_at) for the
raw_linear_events table to optimize queries that fetch unprocessed events
ordered by receive timestamp.

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "b0222cbe34b1"
down_revision = "b0221ebe33a0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create composite index for efficient event processing queries."""
    # Composite index: (processed, received_at)
    # Used by: SELECT * FROM raw_linear_events WHERE processed = FALSE ORDER BY received_at
    op.create_index(
        "ix_raw_linear_events_processed_received_at",
        "raw_linear_events",
        ["processed", "received_at"],
        unique=False,
    )


def downgrade() -> None:
    """
    Remove the composite index on (processed, received_at) from the raw_linear_events table.
    
    This drops the index named `ix_raw_linear_events_processed_received_at`.
    """
    op.drop_index(
        "ix_raw_linear_events_processed_received_at", table_name="raw_linear_events"
    )