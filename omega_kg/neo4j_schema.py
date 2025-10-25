from neo4j import GraphDatabase
from omega_kg.settings import settings


class KnowledgeGraphSchema:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
        )

    def initialize_schema(self):
        """Create constraints and indexes"""
        with self.driver.session() as session:
            # Constraints
            session.run("""
                CREATE CONSTRAINT task_uid IF NOT EXISTS
                FOR (t:Task) REQUIRE t.uid IS UNIQUE
            """)

            session.run("""
                CREATE CONSTRAINT plan_id IF NOT EXISTS
                FOR (p:Plan) REQUIRE p.id IS UNIQUE
            """)

            # Indexes
            session.run("""
                CREATE INDEX task_status IF NOT EXISTS
                FOR (t:Task) ON (t.status)
            """)

            session.run("""
                CREATE INDEX task_created IF NOT EXISTS
                FOR (t:Task) ON (t.created)
            """)

            print("✓ Schema initialized")

    def close(self):
        self.driver.close()


if __name__ == "__main__":
    schema = KnowledgeGraphSchema()
    schema.initialize_schema()
    schema.close()
