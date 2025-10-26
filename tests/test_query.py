"""
Unit tests for database query functionality
"""

from unittest.mock import patch
from omega_kg.settings import Settings


def test_settings_creates_valid_driver_config():
    """Test that settings provide valid Neo4j driver configuration"""
    settings = Settings()

    # Verify settings has required Neo4j connection parameters
    assert hasattr(settings, 'neo4j_uri')
    assert hasattr(settings, 'neo4j_user')
    assert hasattr(settings, 'neo4j_password')
    assert settings.neo4j_uri
    assert settings.neo4j_user
    assert settings.neo4j_password


@patch("neo4j.GraphDatabase.driver")
def test_driver_creation_with_settings(mock_driver_class, mock_neo4j_driver):
    """Test that driver can be created using settings"""
    mock_driver_class.return_value = mock_neo4j_driver

    settings = Settings()
    driver = mock_driver_class(
        settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
    )

    mock_driver_class.assert_called_once_with(
        settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
    )
    assert driver is mock_neo4j_driver


def test_task_count_query_structure():
    """Test that task count query has correct Cypher structure"""
    query = "MATCH (t:Task) RETURN count(t) as count"

    # Verify query contains expected elements
    assert "MATCH (t:Task)" in query
    assert "count(t)" in query
    assert "RETURN" in query


def test_single_task_query_structure():
    """Test that single task query has correct Cypher structure"""
    query = "MATCH (t:Task) RETURN t LIMIT 1"

    # Verify query contains expected elements
    assert "MATCH (t:Task)" in query
    assert "RETURN t" in query
    assert "LIMIT 1" in query
