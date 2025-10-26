"""
Shared test fixtures and configuration for Omega_KG tests
"""

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_env_vars(monkeypatch):
    """
    Prepare a predefined set of environment variables for tests and apply them using the provided monkeypatch fixture.
    
    Returns:
    	env_vars (dict): Mapping of environment variable names to values. Keys with value `None` indicate the variable was removed from the environment; other values were set.
    """
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
    """
    Creates a temporary "test_vault" directory under the provided tmp_path for use in tests.
    
    Returns:
        pathlib.Path: Path to the created temporary vault directory (tmp_path / "test_vault").
    """
    vault = tmp_path / "test_vault"
    vault.mkdir(exist_ok=True)
    return vault


@pytest.fixture
def mock_neo4j_driver():
    """
    Create a mock Neo4j driver that yields a mock session when used as a context manager.
    
    Returns:
        MagicMock: A mock driver whose session() returns a context manager that yields a mock session.
    """
    driver = MagicMock()
    session = MagicMock()
    driver.session.return_value.__enter__.return_value = session
    driver.session.return_value.__exit__.return_value = None
    return driver


@pytest.fixture
def mock_neo4j_session():
    """
    Provide a MagicMock that simulates a Neo4j session for tests.
    
    Returns:
        MagicMock: A mock object representing a Neo4j session, suitable for use wherever a session is expected in tests.
    """
    session = MagicMock()
    return session


@pytest.fixture
def sample_task_data():
    """
    Provide sample task data for tests.
    
    Returns:
        dict: A mapping representing a task with the following keys:
            uid (str): Unique task identifier.
            title (str): Task title.
            filepath (str): Relative path to the task file.
            status (str): Local workflow status.
            linear_id (str): External Linear issue identifier.
            linear_status (str): Status name from Linear.
            linear_priority (int): Priority value from Linear.
            created (str): ISO 8601 UTC creation timestamp.
            pinned (bool): Whether the task is pinned.
            warned (bool): Whether the task has been warned.
    """
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
    """
    Provide a sample lifecycle rule dictionary used in tests.
    
    Returns:
        dict: A lifecycle rule with the following keys:
            - from_status (str): Source task status (e.g., "draft").
            - to_status (str): Target task status (e.g., "archived").
            - days_threshold (int): Number of days before the transition should occur.
            - condition (str): Condition expression applied to tasks (e.g., "NOT t.pinned = true").
            - action (str): Action to perform when the rule matches (e.g., "auto").
    """
    return {
        "from_status": "draft",
        "to_status": "archived",
        "days_threshold": 14,
        "condition": "NOT t.pinned = true",
        "action": "auto",
    }


@pytest.fixture
def sample_linear_webhook_payload():
    """
    Provide a representative Linear webhook payload for tests.
    
    Returns:
        payload (dict): A dictionary simulating a Linear webhook update event with keys:
            - "action": event action string ("update").
            - "data": dict containing:
                - "identifier": issue identifier string.
                - "state": dict with "name" (status string).
                - "priority": integer priority.
                - "updatedAt": ISO 8601 timestamp string.
    """
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
    """
    Provide a sample chat session payload for tests.
    
    Returns:
        dict: A chat session dictionary containing:
            - date (str): ISO date string of the session (e.g., "2025-10-25").
            - topic (str): Topic discussed in the session.
            - decisions (list[str]): List of decisions or action items agreed during the session.
    """
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
    Provide a TaskLifecycle configured in mock mode for tests.
    
    Yields a TaskLifecycle instance created with mock_mode=True and ensures lifecycle.close() is called after use.
    
    Returns:
        TaskLifecycle: A lifecycle instance suitable for unit tests (mock mode).
    """
    from omega_kg.lifecycle import TaskLifecycle

    lifecycle = TaskLifecycle(mock_mode=True)
    yield lifecycle
    lifecycle.close()


@pytest.fixture
def task_lifecycle_with_driver(mock_env_vars, mock_neo4j_driver):
    """
    Provide a TaskLifecycle instance configured to use a mocked Neo4j driver.
    
    Yields a TaskLifecycle created with mock_mode=False whose .driver is replaced by the provided mock_neo4j_driver, allowing tests to exercise lifecycle logic without a real Neo4j connection. Ensures lifecycle.close() is called after the fixture is torn down.
    
    Returns:
        TaskLifecycle: A lifecycle instance with its driver overridden by the mock.
    """
    from omega_kg.lifecycle import TaskLifecycle

    with patch("omega_kg.lifecycle.GraphDatabase.driver") as mock_driver_factory:
        mock_driver_factory.return_value = mock_neo4j_driver
        lifecycle = TaskLifecycle(mock_mode=False)
        # Override with mock to prevent actual connection
        lifecycle.driver = mock_neo4j_driver
        yield lifecycle
        lifecycle.close()