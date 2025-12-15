"""
Enhanced test configuration with best practices and performance optimizations.

This file demonstrates advanced pytest configuration patterns including:
- Session-scoped fixtures for expensive setup
- Parameterized fixtures for multiple test scenarios
- Automatic test data cleanup
- Performance monitoring
- Parallel execution considerations
"""

import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Generator
from unittest.mock import MagicMock, patch

import pytest
from _pytest.config import Config
from _pytest.config.argparsing import Parser
from _pytest.fixtures import FixtureRequest
from _pytest.runner import CallInfo

# ===== Pytest Configuration Hooks =====


def pytest_addoption(parser: Parser):
    """
    Add custom command-line options for testing.

    Usage:
        pytest --neo4j-uri=bolt://localhost:7687
        pytest --skip-slow
        pytest --performance-threshold=1.0
    """
    parser.addoption(
        "--neo4j-uri",
        action="store",
        default="bolt://localhost:7687",
        help="Neo4j URI for integration tests",
    )
    parser.addoption(
        "--skip-slow",
        action="store_true",
        default=False,
        help="Skip slow running tests",
    )
    parser.addoption(
        "--performance-threshold",
        action="store",
        default=1.0,
        type=float,
        help="Performance threshold in seconds for slow tests",
    )
    parser.addoption(
        "--test-vault-path",
        action="store",
        default="./test_vault",
        help="Path to test Obsidian vault",
    )


def pytest_configure(config: Config):
    """
    Configure pytest with custom markers and settings.
    """
    # Add custom markers
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (may be skipped with --skip-slow)"
    )
    config.addinivalue_line(
        "markers", "performance: marks tests as performance benchmarks"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "smoke: marks tests as smoke tests")

    # Store command line options for use in fixtures
    config.option.test_start_time = time.time()


def pytest_collection_modifyitems(config, items):
    """
    Modify test collection based on command line options.
    """
    # Skip slow tests if --skip-slow is specified
    if config.getoption("--skip-slow"):
        skip_slow = pytest.mark.skip(reason="--skip-slow specified")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)

    # Add performance monitoring for performance tests
    performance_threshold = config.getoption("--performance-threshold")
    if performance_threshold:
        for item in items:
            if "performance" in item.keywords:
                # Add performance monitoring marker
                item.add_marker(
                    pytest.mark.performance_threshold(performance_threshold)
                )


# ===== Enhanced Fixtures =====


@pytest.fixture(scope="session")
def session_start_time():
    """Session start time for performance tracking."""
    return time.time()


@pytest.fixture(scope="session")
def test_environment():
    """
    Session-scoped fixture providing test environment configuration.

    This fixture is evaluated once per test session, making it ideal for
    expensive setup operations that don't need to be repeated.
    """
    return {
        "neo4j_uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        "neo4j_user": os.getenv("NEO4J_USER", "neo4j"),
        "neo4j_password": os.getenv("NEO4J_PASSWORD", "test-password"),
        "linear_webhook_secret": os.getenv("LINEAR_WEBHOOK_SECRET", "test-secret"),
        "test_data_dir": Path(__file__).parent / "test_data",
    }


@pytest.fixture(scope="session")
def mock_neo4j_driver_session(test_environment):
    """
    Session-scoped mock Neo4j driver for unit tests.

    This avoids the overhead of creating new mock drivers for each test.
    """
    driver = MagicMock()
    session = MagicMock()

    # Configure session context manager behavior
    driver.session.return_value.__enter__.return_value = session
    driver.session.return_value.__exit__.return_value = None

    # Configure common query responses
    session.run.return_value.single.return_value = MagicMock()
    session.run.return_value.single.return_value.__getitem__.side_effect = lambda key: {
        "test": "value"
    }[key]

    return driver


@pytest.fixture
def temp_test_vault(tmp_path: Path) -> Generator[Path, None, None]:
    """
    Create a temporary test vault directory structure.

    This fixture creates a realistic Obsidian vault structure for testing.
    """
    vault_dir = tmp_path / "test_vault"
    vault_dir.mkdir()

    # Create standard Obsidian directories
    (vault_dir / "Attachments").mkdir()
    (vault_dir / "Templates").mkdir()
    (vault_dir / "Daily Notes").mkdir()

    # Create test markdown files
    test_files = {
        "README.md": "# Test Vault\n\nThis is a test vault for pytest.",
        "Tasks/Task 1.md": """---
status: draft
priority: high
created: 2025-11-12
---

# Task 1

This is a test task.
""",
        "Templates/Task Template.md": """---
template: task
---

# {{title}}

## Description

{{description}}

## Steps

1. Step 1
2. Step 2
3. Step 3
""",
    }

    for file_path, content in test_files.items():
        full_path = vault_dir / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")

    yield vault_dir


@pytest.fixture(params=["claude", "chatgpt", "gemini"])
def platform_data(request):
    """
    Parameterized fixture providing different platform test data.

    This fixture will run the test with each parameter value, effectively
    creating multiple test cases from one test function.
    """
    platform = request.param

    platform_configs = {
        "claude": {
            "name": "Claude",
            "url_pattern": r"https://claude\.ai/chat/.*",
            "api_endpoint": "https://api.anthropic.com",
            "test_messages": [
                {"role": "user", "content": "Hello Claude"},
                {"role": "assistant", "content": "Hello User"},
            ],
        },
        "chatgpt": {
            "name": "ChatGPT",
            "url_pattern": r"https://chat\.openai\.com/c/.*",
            "api_endpoint": "https://api.openai.com/v1/chat/completions",
            "test_messages": [
                {"role": "user", "content": "Hello ChatGPT"},
                {"role": "assistant", "content": "Hello User"},
            ],
        },
        "gemini": {
            "name": "Gemini",
            "url_pattern": r"https://gemini\.google\.com/app/.*",
            "api_endpoint": "https://generativelanguage.googleapis.com/v1beta/models",
            "test_messages": [
                {"role": "user", "content": "Hello Gemini"},
                {"role": "assistant", "content": "Hello User"},
            ],
        },
    }

    return platform_configs[platform]


@pytest.fixture
def sample_task_factory():
    """
    Factory fixture for creating sample task data.

    This provides a clean way to generate test data with customizable parameters.
    """

    def create_task(
        uid: str = "task-001",
        title: str = "Test Task",
        status: str = "draft",
        priority: str = "medium",
        **kwargs,
    ):
        task_data = {
            "uid": uid,
            "title": title,
            "status": status,
            "priority": priority,
            "created": "2025-11-12T10:00:00Z",
            "updated": "2025-11-12T10:00:00Z",
            "pinned": False,
            "warned": False,
            "filepath": f"Tasks/{title.replace(' ', '_')}.md",
            "content": f"# {title}\n\nTask content here.",
        }
        task_data.update(kwargs)
        return task_data

    return create_task


@pytest.fixture
def mock_settings(test_environment):
    """
    Mock settings for testing without environment dependencies.
    """
    with patch("omega_kg.settings.Settings") as mock_settings_class:
        mock_settings_instance = MagicMock()
        mock_settings_instance.neo4j_uri = test_environment["neo4j_uri"]
        mock_settings_instance.neo4j_user = test_environment["neo4j_user"]
        mock_settings_instance.neo4j_password = test_environment["neo4j_password"]
        mock_settings_instance.linear_webhook_secret = test_environment[
            "linear_webhook_secret"
        ]
        mock_settings_instance.app_env = "test"

        mock_settings_class.return_value = mock_settings_instance
        yield mock_settings_instance


# ===== Performance and Monitoring Fixtures =====


@pytest.fixture(autouse=True)
def performance_monitor(request: FixtureRequest):
    """
    Automatic performance monitoring for all tests.

    This fixture automatically tracks test execution time and reports
    slow tests based on the performance threshold.
    """
    start_time = time.time()

    yield

    # Calculate execution time
    execution_time = time.time() - start_time

    # Check if test is marked as performance test
    performance_marker = request.node.get_closest_marker("performance")
    if performance_marker:
        threshold = request.config.getoption("--performance-threshold")
        if execution_time > threshold:
            pytest.fail(
                f"Performance test exceeded threshold of {threshold}s. "
                f"Execution time: {execution_time:.2f}s"
            )

    # Log slow tests (but don't fail)
    if execution_time > 1.0:  # 1 second threshold for slow tests
        print(
            f"\n⚠️  Slow test detected: {request.node.name} "
            f"took {execution_time:.2f}s"
        )


@pytest.fixture
def benchmark_fixture():
    """
    Simple benchmark fixture for measuring code performance.

    Usage:
        def test_something(benchmark_fixture):
            result = benchmark_fixture(lambda: expensive_function())
            assert result < 1.0  # Should complete in under 1 second
    """

    def benchmark(func, *args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = time.time() - start_time
        return execution_time, result

    return benchmark


# ===== Database and Service Fixtures =====


@pytest.fixture
def mock_database_connection():
    """
    Mock database connection for unit tests.

    This provides a consistent database interface without requiring
    actual database setup.
    """
    connection = MagicMock()
    connection.execute.return_value = MagicMock()
    connection.commit.return_value = None
    connection.rollback.return_value = None
    connection.close.return_value = None
    return connection


@pytest.fixture
def isolated_database(mock_neo4j_driver_session):
    """
    Provide isolated database state for integration tests.

    This fixture ensures each test starts with a clean database state
    by clearing data before and after the test.
    """
    # Setup: Clear database state
    session = mock_neo4j_driver_session.session.return_value.__enter__.return_value
    session.run("MATCH (n) DETACH DELETE n")

    yield mock_neo4j_driver_session

    # Teardown: Clear database state
    session.run("MATCH (n) DETACH DELETE n")


# ===== Test Data Fixtures =====


@pytest.fixture
def sample_conversation_data():
    """
    Sample conversation data for testing capture functionality.
    """
    return {
        "platform": "claude",
        "url": "https://claude.ai/chat/test-conversation",
        "messages": [
            {
                "role": "user",
                "content": "How do I implement JWT authentication?",
                "timestamp": "2025-11-12T10:00:00Z",
                "metadata": {"user_id": "user123"},
            },
            {
                "role": "assistant",
                "content": "JWT authentication involves several steps...",
                "timestamp": "2025-11-12T10:00:05Z",
                "metadata": {"model": "claude-3-sonnet"},
            },
        ],
        "title": "JWT Authentication Implementation",
        "capture_date": "2025-11-12T10:00:10Z",
        "metadata": {
            "conversation_id": "conv-123",
            "user_agent": "Mozilla/5.0...",
        },
    }


@pytest.fixture
def linear_webhook_payload():
    """
    Sample Linear webhook payload for testing.
    """
    return {
        "action": "update",
        "data": {
            "identifier": "LINEAR-123",
            "title": "Test Issue",
            "state": {"name": "In Progress"},
            "priority": 1,
            "updatedAt": "2025-11-12T10:00:00Z",
            "assignee": {"name": "John Doe"},
            "description": "Test issue description",
        },
        "team": {"name": "Engineering"},
    }


# ===== Cleanup and Teardown =====


def pytest_sessionfinish(session, exitstatus):
    """
    Clean up after test session completion.
    """
    print(
        f"\n\nTest session completed in {time.time() - session.config.option.test_start_time:.2f}s"
    )

    # Print summary statistics
    if hasattr(session.config, "_performance_stats"):
        stats = session.config._performance_stats
        print(f"Performance tests: {len(stats)}")
        for test_name, duration in stats.items():
            print(f"  {test_name}: {duration:.2f}s")


# ===== Custom Markers and Utilities =====


def pytest_make_collect_report(collector):
    """
    Custom collection report for better test discovery feedback.
    """
    pass


# ===== Error Handling and Debugging =====


@pytest.fixture(autouse=True)
def debug_mode(request: FixtureRequest):
    """
    Automatic debug mode for failed tests.
    """
    yield

    # This would be called after each test
    # Can be extended to capture debug information on test failure
    if hasattr(request.node, "rep_call") and request.node.rep_call.failed:
        print(f"\n🔍 Debug info for failed test: {request.node.name}")
        # Could add additional debug output here
