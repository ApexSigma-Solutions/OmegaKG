"""
Shared test fixtures and configuration for Omega_KG tests
"""

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up mock environment variables for testing"""
    env_vars = {
        "APP_ENV": "test",
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "test-password",
        "OBSIDIAN_VAULT_PATH": "./test_vault",
        "SMTP_HOST": None,
        "SMTP_PORT": "587",
        "SMTP_USER": None,
        "SMTP_PASSWORD": None,
        "EMAIL_TO": None,
    }

    for key, value in env_vars.items():
        if value is not None:
            monkeypatch.setenv(key, value)
        else:
            monkeypatch.delenv(key, raising=False)

    return env_vars


@pytest.fixture
def test_vault_path(tmp_path):
    """Create a temporary vault directory for testing"""
    vault = tmp_path / "test_vault"
    vault.mkdir(exist_ok=True)
    return vault


@pytest.fixture
def mock_neo4j_driver():
    """Create a mock Neo4j driver for testing"""
    driver = MagicMock()
    session = MagicMock()
    driver.session.return_value.__enter__.return_value = session
    driver.session.return_value.__exit__.return_value = None
    return driver


@pytest.fixture
def mock_neo4j_session():
    """Create a mock Neo4j session"""
    session = MagicMock()
    return session


@pytest.fixture
def sample_task_data():
    """Sample task data for testing"""
    return {
        "uid": "task-001",
        "title": "Test Task",
        "filepath": "tasks/test_task.md",
        "status": "draft",
        "linear_id": "LINEAR-123",
        "linear_status": "Todo",
        "linear_priority": 1,
        "created": "2025-10-18T00:00:00Z",
        "pinned": False,
        "warned": False,
    }


@pytest.fixture
def sample_lifecycle_rule_data():
    """Sample lifecycle rule for testing"""
    return {
        "from_status": "draft",
        "to_status": "archived",
        "days_threshold": 14,
        "condition": "NOT t.pinned = true",
        "action": "auto",
    }


@pytest.fixture
def sample_linear_webhook_payload():
    """Sample Linear webhook payload for testing"""
    return {
        "action": "update",
        "data": {
            "identifier": "LINEAR-123",
            "state": {"name": "In Progress"},
            "priority": 1,
            "updatedAt": "2025-10-25T12:00:00Z",
        },
    }


@pytest.fixture
def sample_chat_session_data():
    """Sample chat session data for testing"""
    return {
        "date": "2025-10-25",
        "topic": "Initial Setup",
        "decisions": [
            "Use Neo4j as primary database",
            "Implement task lifecycle with time-based transitions",
        ],
    }


@pytest.fixture
def task_lifecycle_mock(mock_env_vars):
    """
    Create a TaskLifecycle instance in mock mode for testing.

    This fixture is useful for testing lifecycle logic without requiring
    a live Neo4j connection.
    """
    from omega_kg.lifecycle import TaskLifecycle

    lifecycle = TaskLifecycle(mock_mode=True)
    yield lifecycle
    lifecycle.close()


@pytest.fixture
def task_lifecycle_with_driver(mock_env_vars, mock_neo4j_driver):
    """
    Create a TaskLifecycle instance with mocked Neo4j driver.

    This fixture allows testing lifecycle logic that interacts with
    the database without requiring a live Neo4j connection.
    """
    from omega_kg.lifecycle import TaskLifecycle

    with patch("omega_kg.lifecycle.GraphDatabase.driver") as mock_driver_factory:
        mock_driver_factory.return_value = mock_neo4j_driver
        lifecycle = TaskLifecycle(mock_mode=False)
        # Override with mock to prevent actual connection
        lifecycle.driver = mock_neo4j_driver
        yield lifecycle
        lifecycle.close()
