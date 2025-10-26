#!/usr/bin/env python3
"""Test Neo4j connection"""

from neo4j import GraphDatabase
from omega_kg.settings import settings


def test_connection():
    """
    Attempt to connect to a Neo4j instance and run a simple verification query.

    Attempts to create a Neo4j driver using configured settings, open a session, run a small Cypher query that returns a message, print the returned message on success, and close the driver.

    Returns:
        bool: `True` if the connection and query succeeded, `False` otherwise.
    """
    try:
        driver = GraphDatabase.driver(
            settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
        )

        with driver.session() as session:
            result = session.run("RETURN 'Neo4j is running!' as message")
            record = result.single()
            print("✅ Neo4j connection successful:", record["message"])

        driver.close()
        return True

    except Exception as e:
        print("❌ Neo4j connection failed:", str(e))
        return False


if __name__ == "__main__":
    test_connection()
