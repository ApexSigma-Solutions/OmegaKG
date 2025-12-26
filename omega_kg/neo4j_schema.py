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
        Create a KnowledgeGraphSchema and, unless mock_mode is True, attempt to establish and verify a Neo4j driver connection.

        Parameters:
            mock_mode (bool): If True, skip creating a Neo4j driver and leave the instance in mock mode.

        Details:
            When mock_mode is False, the initializer attempts to create a Neo4j driver using configured settings and runs a health check. On successful connection the driver is stored on the instance. If connection or authentication fails, the instance switches to mock mode and the driver is set to None.
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
        Verify that the configured Neo4j driver can run a simple test query.

        Returns:
            `true` if the driver executed the test query successfully.

        Raises:
            ConnectionError: If no driver is initialized or the test query fails; includes underlying error details.
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
        Report the current Neo4j connection state and related metadata.

        Returns:
            dict: Mapping with connection details:
                - "connected": `True` if a live driver exists and mock mode is not active, `False` otherwise.
                - "mock_mode": `True` if the instance is operating in mock mode, `False` otherwise.
                - "uri": The Neo4j URI when not in mock mode, or the string "mock://local" when in mock mode.
        """
        return {
            "connected": self.driver is not None and not self.mock_mode,
            "mock_mode": self.mock_mode,
            "uri": (settings.neo4j_uri if not self.mock_mode else "mock://local"),
        }

    def initialize_schema(self) -> None:
        """
        Create the required Neo4j schema for the knowledge graph.

        When a live Neo4j driver is available, this creates database constraints and indexes:
        - Constraint: Task.uid is unique
        - Constraint: Plan.id is unique
        - Index: Task.status
        - Index: Task.created

        If running in mock mode or no driver is available, the method makes no changes.
        """
        if self.mock_mode:
            print("⚠ Schema initialization skipped (mock mode)")
            return

        if not self.driver:
            print("✗ No database connection available")
            return

        try:
            with self.driver.session() as session:
                # Drop old constraints that reference uid-based schema
                session.run("DROP CONSTRAINT task_uid IF EXISTS")
                session.run("DROP CONSTRAINT plan_id IF EXISTS")

                # Create new UNIQUE constraints on the new Golden Schema 'id' property
                labels = ["Task", "TaskPlan", "ADR", "BacklogPlan", "Plan"]
                for label in labels:
                    name = f"{label.lower()}_id"
                    session.run(
                        f"""
                        CREATE CONSTRAINT {name} IF NOT EXISTS
                        FOR (n:{label}) REQUIRE n.id IS UNIQUE
                    """
                    )
                
                # Intelligence Layer constraints
                session.run(
                    """
                    CREATE CONSTRAINT constraint_id IF NOT EXISTS
                    FOR (n:Constraint) REQUIRE n.id IS UNIQUE
                """
                )
                
                session.run(
                    """
                    CREATE CONSTRAINT context_name IF NOT EXISTS
                    FOR (n:Context) REQUIRE n.name IS UNIQUE
                """
                )
                
                session.run(
                    """
                    CREATE CONSTRAINT incident_id IF NOT EXISTS
                    FOR (n:Incident) REQUIRE n.id IS UNIQUE
                """
                )

                # Indexes - keep commonly used indexes for Task
                session.run(
                    """
                    CREATE INDEX task_status IF NOT EXISTS
                    FOR (t:Task) ON (t.status)
                """
                )

                # Support both older 'created' and new 'created_at' fields during migration
                session.run(
                    """
                    CREATE INDEX task_created IF NOT EXISTS
                    FOR (t:Task) ON (t.created)
                """
                )

                session.run(
                    """
                    CREATE INDEX task_created_at IF NOT EXISTS
                    FOR (t:Task) ON (t.created_at)
                """
                )

                print("✓ Schema initialized successfully")

        except ServiceUnavailable as e:
            print(f"✗ Database connection lost: {e}")
            print(f"💡 Tip: Ensure Neo4j is running on {settings.neo4j_uri}")
        except Exception as e:
            print(f"✗ Schema initialization failed: {e}")

    def create_sample_relationships(self) -> None:
        """
        Create a small set of example nodes & relationships for demo / onboarding.

        This is intentionally lightweight: if running in mock mode the method is
        a no-op; if a live driver is available we create a minimal sample graph.
        """
        if self.mock_mode or not self.driver:
            print("⚠ create_sample_relationships skipped (mock mode or no driver)")
            return

        try:
            with self.driver.session() as session:
                # Create example Task and ADR nodes with a relationship for demos
                session.run(
                    """
                    MERGE (t:Task {id: 'SAMPLE-TASK-1'})
                    SET t.title = 'Sample Task', t.status = 'active'
                    MERGE (a:ADR {id: 'SAMPLE-ADR-1'})
                    SET a.title = 'Sample ADR'
                    MERGE (t)-[:RELATED_TO]->(a)
                """
                )
            print("✓ Sample relationships created (demo data)")
        except Exception as e:
            print(f"✗ Failed to create sample relationships: {e}")

    def close(self) -> None:
        """
        Close the Neo4j driver if one is open.

        Does nothing when running in mock mode or if the driver is already None/closed.
        """
        if self.driver:
            self.driver.close()


def main() -> None:
    """
    CLI entry point to initialize the Neo4j schema and report connection status.

    Creates a KnowledgeGraphSchema, performs schema initialization according to command-line options, prints whether a real Neo4j connection or mock mode is in use, and ensures the driver is closed on exit.
    """
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
