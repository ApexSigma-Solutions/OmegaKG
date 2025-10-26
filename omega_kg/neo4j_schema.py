"""
Neo4j Schema Initialization
Creates constraints and indexes with connection recovery
"""

from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError
from omega_kg.settings import settings


class ConnectionError(Exception):
    """Raised when Neo4j connection cannot be established"""

    pass


class KnowledgeGraphSchema:
    """Initialize Neo4j schema with connection health checks"""

    def __init__(self, mock_mode: bool = False) -> None:
        """
        Initialize schema manager with connection health check.

        Args:
            mock_mode: If True, skip database operations (for testing)
        """
        self.driver = None
        self.mock_mode = mock_mode

        if not mock_mode:
            try:
                self.driver = GraphDatabase.driver(
                    settings.neo4j_uri,
                    auth=(settings.neo4j_user, settings.neo4j_password),
                )
                # Test the connection
                self._check_connection()
                print("✓ Neo4j connection established")
            except (ServiceUnavailable, AuthError, ConnectionError) as e:
                print(f"✗ Failed to connect to Neo4j: {e}")
                print("⚠ Schema initialization skipped (mock mode)")
                self.mock_mode = True
                self.driver = None

    def _check_connection(self) -> bool:
        """
        Verify Neo4j connection is working.

        Returns:
            True if connection is healthy

        Raises:
            ConnectionError: If connection fails
        """
        if not self.driver:
            raise ConnectionError("Driver not initialized")

        try:
            with self.driver.session() as session:
                result = session.run("RETURN 1 as status")
                _ = result.single()
                return True
        except Exception as e:
            raise ConnectionError(f"Connection health check failed: {e}")

    def get_connection_status(self) -> dict[str, bool | str]:
        """
        Get current connection status.

        Returns:
            Dictionary with connection info
        """
        return {
            "connected": self.driver is not None and not self.mock_mode,
            "mock_mode": self.mock_mode,
            "uri": (settings.neo4j_uri if not self.mock_mode else "mock://local"),
        }

    def initialize_schema(self) -> None:
        """Create constraints and indexes"""
        if self.mock_mode:
            print("⚠ Schema initialization skipped (mock mode)")
            return

        if not self.driver:
            print("✗ No database connection available")
            return

        try:
            with self.driver.session() as session:
                # Constraints
                session.run(
                    """
                    CREATE CONSTRAINT task_uid IF NOT EXISTS
                    FOR (t:Task) REQUIRE t.uid IS UNIQUE
                """
                )

                session.run(
                    """
                    CREATE CONSTRAINT plan_id IF NOT EXISTS
                    FOR (p:Plan) REQUIRE p.id IS UNIQUE
                """
                )

                # Indexes
                session.run(
                    """
                    CREATE INDEX task_status IF NOT EXISTS
                    FOR (t:Task) ON (t.status)
                """
                )

                session.run(
                    """
                    CREATE INDEX task_created IF NOT EXISTS
                    FOR (t:Task) ON (t.created)
                """
                )

                print("✓ Schema initialized successfully")

        except ServiceUnavailable as e:
            print(f"✗ Database connection lost: {e}")
            print(f"💡 Tip: Ensure Neo4j is running on {settings.neo4j_uri}")
        except Exception as e:
            print(f"✗ Schema initialization failed: {e}")

    def close(self) -> None:
        """Close database connection"""
        if self.driver:
            self.driver.close()


def main() -> None:
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Initialize Neo4j schema")
    parser.add_argument(
        "--skip-on-error",
        action="store_true",
        help="Skip if database unavailable",
    )
    parser.parse_args()

    schema = KnowledgeGraphSchema()

    # Print connection status
    status = schema.get_connection_status()
    if status["connected"]:
        print(f"✓ Connected to Neo4j: {status['uri']}")
    else:
        print("⚠ Running in mock mode (no Neo4j connection)")

    try:
        schema.initialize_schema()
    finally:
        schema.close()


if __name__ == "__main__":
    main()
