"""
Shared test fixtures and configuration for Omega_KG tests
"""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path


@pytest.fixture
def mock_env_vars(monkeypatch):
    """
    Apply a predefined set of environment variables for tests using the provided monkeypatch fixture.

    Returns:
        env_vars (dict): Mapping of environment variable names to their applied values. A value of `None` indicates the variable was removed from the environment.
    """
    env_vars = {
        "APP_ENV": "test",
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "test-password",
        "LINEAR_WEBHOOK_SECRET": "test-secret",
        "OBSIDIAN_VAULT_PATH": "./test_vault",
        "SMTP_HOST": None,
        "SMTP_PORT": "587",
        "SMTP_USER": None,
        "SMTP_PASSWORD": None,
        "EMAIL_TO": None,
    }

    # Ensure the test vault directory exists when tests reference it via env var
    test_vault_dir = Path("./test_vault")
    test_vault_dir.mkdir(parents=True, exist_ok=True)

    for key, value in env_vars.items():
        if value is not None:
            monkeypatch.setenv(key, value)
        else:
            monkeypatch.delenv(key, raising=False)

    return env_vars


@pytest.fixture
def test_vault_path(tmp_path):
    """
    Create a temporary "test_vault" directory under the provided tmp_path for use in tests.

    Returns:
        pathlib.Path: Path to the created directory (tmp_path / "test_vault").
    """
    vault = tmp_path / "test_vault"
    vault.mkdir(exist_ok=True)
    return vault


@pytest.fixture
def mock_neo4j_driver():
    """
    Create a MagicMock that emulates a Neo4j driver whose session() context manager yields a mock session.

    Returns:
        MagicMock: Mock Neo4j driver whose session() context manager yields a MagicMock representing the session.
    """
    driver = MagicMock()
    session = MagicMock()
    driver.session.return_value.__enter__.return_value = session
    driver.session.return_value.__exit__.return_value = None
    return driver


@pytest.fixture
def mock_neo4j_session():
    """
    Create a MagicMock that simulates a Neo4j session for tests.

    Returns:
        MagicMock: A mock object configured to act as a Neo4j session for use in tests.
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
    Return a representative Linear webhook payload used in tests.

    Returns:
        payload (dict): Dictionary representing a Linear webhook update event with keys:
            - "action": string, event action (e.g., "update").
            - "data": dict containing:
                - "identifier": string, issue identifier.
                - "state": dict with "name": string status.
                - "priority": int priority value.
                - "updatedAt": string, ISO 8601 timestamp.
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
    Sample chat session payload for tests.

    Returns:
        dict: A dictionary with:
            - date (str): ISO 8601 date string of the session.
            - topic (str): Topic discussed in the session.
            - decisions (list[str]): Decisions or action items agreed during the session.
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
    Create a TaskLifecycle instance configured for mock mode for use in tests.

    The fixture yields a TaskLifecycle instantiated with mock_mode=True and ensures lifecycle.close() is called after the fixture is torn down.

    Returns:
        TaskLifecycle: Instance configured with mock_mode=True.
    """
    from omega_kg.lifecycle import TaskLifecycle

    lifecycle = TaskLifecycle(mock_mode=True)
    yield lifecycle
    lifecycle.close()


@pytest.fixture
def task_lifecycle_with_driver(mock_env_vars, mock_neo4j_driver):
    """
    Provide a TaskLifecycle instance configured to use a mocked Neo4j driver.

    Yields a TaskLifecycle created with mock_mode=False whose `driver` attribute is replaced by the provided mock; ensures `lifecycle.close()` is called after the fixture is torn down.

    Parameters:
        mock_neo4j_driver (unittest.mock.MagicMock): Mock Neo4j driver to assign to the lifecycle to prevent real DB connections.

    Returns:
        TaskLifecycle: Lifecycle instance with its driver overridden by the mock.
    """
    from omega_kg.lifecycle import TaskLifecycle

    with patch("omega_kg.lifecycle.GraphDatabase.driver") as mock_driver_factory:
        mock_driver_factory.return_value = mock_neo4j_driver
        lifecycle = TaskLifecycle(mock_mode=False)
        # Override with mock to prevent actual connection
        lifecycle.driver = mock_neo4j_driver
        yield lifecycle
        lifecycle.close()
