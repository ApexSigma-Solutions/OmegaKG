"""
Integration-like unit tests for the schema migration code paths in `neo4j_schema.py`.

These tests mock a Neo4j driver and assert that the expected Cypher statements
are issued when `initialize_schema` is called, including dropping old constraints
and creating new id-based constraints for Golden Schema entity labels.
"""

from unittest.mock import MagicMock, patch

from omega_kg.neo4j_schema import KnowledgeGraphSchema


def _get_run_calls(mock_session):
    """Return the list of run() call argument strings for assertions."""
    return [args[0] for args, _ in mock_session.run.call_args_list]


@patch("omega_kg.neo4j_schema.GraphDatabase.driver")
def test_initialize_schema_runs_expected_queries(mock_driver_class, mock_neo4j_driver):
    """Verify that migrate logic drops old uid constraints and creates id-based constraints and indexes."""

    mock_driver_class.return_value = mock_neo4j_driver

    with patch("omega_kg.neo4j_schema.settings") as mock_settings:
        mock_settings.neo4j_uri = "bolt://localhost:7687"
        mock_settings.neo4j_user = "neo4j"
        mock_settings.neo4j_password = "password"

        # Mocked session to satisfy the health check and capture run calls
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.single.return_value = {"status": 1}
        mock_session.run.return_value = mock_result
        mock_neo4j_driver.session.return_value.__enter__.return_value = mock_session

        schema = KnowledgeGraphSchema(mock_mode=False)

        # Run the migration
        schema.initialize_schema()

        calls = _get_run_calls(mock_session)

        # Old constraints should be dropped
        assert any("DROP CONSTRAINT task_uid IF EXISTS" in q for q in calls)
        assert any("DROP CONSTRAINT plan_id IF EXISTS" in q for q in calls)

        # New id constraints should be created
        assert any("CREATE CONSTRAINT task_id IF NOT EXISTS" in q for q in calls)
        assert any("CREATE CONSTRAINT taskplan_id IF NOT EXISTS" in q for q in calls)
        assert any("CREATE CONSTRAINT adr_id IF NOT EXISTS" in q for q in calls)
        assert any("CREATE CONSTRAINT backlogplan_id IF NOT EXISTS" in q for q in calls)
        assert any("CREATE CONSTRAINT plan_id IF NOT EXISTS" in q for q in calls)

        # Indexes for task status and created fields are applied
        assert any("CREATE INDEX task_status IF NOT EXISTS" in q for q in calls)
        assert any("CREATE INDEX task_created IF NOT EXISTS" in q for q in calls)
        assert any("CREATE INDEX task_created_at IF NOT EXISTS" in q for q in calls)
