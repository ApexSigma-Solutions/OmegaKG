"""
Integration Tests - Graph Sync (TN-LINEAR-06)

Validates that LinearIssue models are correctly projected to Neo4j topology.
"""

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio

from omega_kg.database.graph import AsyncGraphDriver
from omega_kg.domain.linear.graph_writer import GraphWriter
from omega_kg.domain.linear.models import LinearIssue, LinearState, LinearUser


@pytest_asyncio.fixture
async def neo4j_driver():
    """Create a fresh Neo4j driver for each test to avoid event loop issues."""
    driver = AsyncGraphDriver()
    await driver.connect()
    yield driver
    await driver.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_graph_connectivity(neo4j_driver):
    """Verify we can talk to the Neo4j container."""
    assert await neo4j_driver.verify_connectivity() is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_upsert_issue_topology(neo4j_driver):
    """
    Test that an Issue + Assignee are correctly merged into the graph.

    Validates:
    - 1 LinearIssue node created
    - 1 LinearUser node created
    - 1 ASSIGNED_TO relationship (Issue -> User)
    """
    # 1. Setup Data - Casting UUIDs to strings explicitly
    user_id = str(uuid.uuid4())
    issue_id = str(uuid.uuid4())

    assignee = LinearUser(
        id=user_id,
        name="Test User",
        email="test@example.com",
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
        active=True,
    )

    state = LinearState(
        id=str(uuid.uuid4()), name="In Progress", color="#F00", type="started"
    )

    issue = LinearIssue(
        id=issue_id,
        identifier="LIN-999",
        title="Integration Test Issue",
        priority=1,
        state=state,
        assignee=assignee,
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
        url="http://linear.app/issue/LIN-999",
    )

    # 2. Execute Graph Writer
    writer = GraphWriter(neo4j_driver)
    await writer.upsert_issue(issue)

    # 3. Verify in Neo4j (Read back)
    # Query Direction: (Issue)-[:ASSIGNED_TO]->(User)
    query = """
    MATCH (i:LinearIssue {identifier: 'LIN-999'})
    MATCH (u:LinearUser {email: 'test@example.com'})
    MATCH (i)-[r:ASSIGNED_TO]->(u)
    RETURN i, u, r
    """

    async with neo4j_driver.session() as session:
        result = await session.run(query)
        record = await result.single()

        assert record is not None, "No matching Issue+User+Relationship found in graph"
        assert record["i"]["title"] == "Integration Test Issue"
        assert record["u"]["name"] == "Test User"
        assert record["r"] is not None

    # 4. Cleanup (ephemeral container usually handles this)
    async with neo4j_driver.session() as session:
        await session.run("MATCH (n) DETACH DELETE n")
