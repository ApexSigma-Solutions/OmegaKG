"""
Quipu Database Module
Handles PostgreSQL operations for heartbeat monitoring using synchronous psycopg2.
"""
import logging
from datetime import datetime
from typing import Any, Dict, Optional

import psycopg2
from psycopg2.extras import Json

from omega_kg.settings import settings

logger = logging.getLogger("QuipuDB")

# SQL Definitions
INIT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS system_heartbeats (
    id SERIAL PRIMARY KEY,
    service_name VARCHAR(50) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) NOT NULL,
    latency_ms INTEGER,
    model_loaded VARCHAR(100),
    meta JSONB
);
CREATE INDEX IF NOT EXISTS idx_heartbeat_timestamp ON system_heartbeats(timestamp DESC);
"""

INSERT_HEARTBEAT_SQL = """
INSERT INTO system_heartbeats (service_name, timestamp, status, latency_ms, model_loaded, meta)
VALUES (%s, %s, %s, %s, %s, %s);
"""


def get_db_connection() -> Optional[psycopg2.extensions.connection]:
    """Establishes connection to PostgreSQL using settings."""
    try:
        conn_string = settings.sync_database_url
        return psycopg2.connect(conn_string)
    except psycopg2.OperationalError as e:
        logger.error(f"Database connection failed: {e}")
        return None


def init_heartbeat_table() -> bool:
    """Initialize the system_heartbeats table if it doesn't exist."""
    conn = get_db_connection()
    if not conn:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute(INIT_TABLE_SQL)
            conn.commit()
            logger.info("Heartbeat table verified in database.")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize heartbeat table: {e}")
        return False
    finally:
        if conn:
            conn.close()


def insert_heartbeat(
    service_name: str,
    timestamp: datetime,
    status: str,
    latency_ms: int,
    model_loaded: Optional[str],
    meta: Dict[str, Any],
) -> bool:
    """Insert a heartbeat record into the database."""
    conn = get_db_connection()
    if not conn:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute(
                INSERT_HEARTBEAT_SQL,
                (service_name, timestamp, status, latency_ms, model_loaded, Json(meta)),
            )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to insert heartbeat: {e}")
        return False
    finally:
        if conn:
            conn.close()
