"""
Shared test fixtures and configuration for Omega_KG tests

This module ensures critical environment variables are set before any test imports
to prevent import-time configuration issues.
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

# NOTE: Do not mutate os.environ at import time.
# Test isolation is controlled via .env/.env.test and per-test monkeypatch fixtures.

# Add project root to Python path to ensure imports work correctly
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Create test vault directory at import time
test_vault_dir = Path("./test_vault")
test_vault_dir.mkdir(parents=True, exist_ok=True)


def pytest_configure(config):
    try:
        from dotenv import load_dotenv
    except ImportError as e:
        raise RuntimeError(
            "python-dotenv is required for tests to load .env/.env.test. "
            "Install dev dependencies (poetry install --with dev)."
        ) from e

    load_dotenv(".env", override=False)
    load_dotenv(".env.test", override=True)


@pytest.fixture
def mock_env_vars(monkeypatch):
    """
    Apply a predefined set of environment variables for tests using the provided monkeypatch fixture.

    Returns:
        env_vars (dict): Mapping of environment variable names to their applied values. A value of `None` indicates the variable was removed from the environment.
    """
    env_vars = {
        "APP_ENV": "test",  # Use test to bypass zero-trust validation
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "test-password",
        "JWT_EXPIRATION_MINUTES": "60",
        "JWT_SECRET_KEY": "test-jwt-secret-key",
        "LINEAR_WEBHOOK_SECRET": "test-secret",
        "EXTENSION_API_KEY": "test_api_key_1234567890",
        "OBSIDIAN_VAULT_PATH": "./test_vault",
        "POSTGRES_USER": "omega_user",
        "POSTGRES_SERVER": "127.0.0.1",
        "POSTGRES_PORT": "5433",
        "POSTGRES_DB": "omega_kg",
        "POSTGRES_PASSWORD": "test-postgres-password",
        "OLLAMA_ENABLED": "False",
        "NANO_GPT_ENABLED": "False",
        "GEMINI_ENABLED": "False",
        "SMTP_HOST": None,
        "SMTP_PORT": "587",
        "SMTP_USER": None,
        "SMTP_PASSWORD": None,
        "EMAIL_TO": None,
        "EMBEDDING_PROVIDER": "ollama",
        "OLLAMA_BASE_URL": "http://localhost:11434",
        "PERCOLATION_SIMILARITY_THRESHOLD": "0.8",
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


# ===== ENHANCED PERCOLATION FIXTURES =====

@pytest.fixture
def mock_percolation_engine(mock_neo4j_driver):
    """
    Create a mock PercolationEngine for comprehensive testing.
    
    Returns:
        MagicMock: Mock percolation engine with all required methods and attributes.
    """
    from unittest.mock import MagicMock
    
    engine = MagicMock()
    engine.driver = mock_neo4j_driver
    engine.similarity_threshold = 0.8
    engine.similarity_cache = {}
    
    # Mock vector similarity calculation
    engine.calculate_vector_similarity.return_value = 0.85
    engine.should_create_relationship.return_value = [True, True, False]
    
    # Mock file operations
    engine.percolate_from_vault.return_value = {"tasks": 5, "commits": 3, "links": 2}
    
    # Mock graph operations
    engine._create_task_node.return_value = True
    engine._create_commit_node.return_value = True
    engine._create_relationship.return_value = True
    engine._validate_relationship.return_value = True
    
    return engine


@pytest.fixture
def mock_embedding_service():
    """
    Create a mock embedding service for vector operations.
    
    Returns:
        MagicMock: Mock embedding service with configurable responses.
    """
    from unittest.mock import MagicMock
    
    service = MagicMock()
    
    # Mock embedding generation
    service.generate_embedding.return_value = [0.1, 0.2, 0.3, 0.4, 0.5] * 200  # 1024-dim vector
    service.generate_embeddings_batch.return_value = [
        [0.1, 0.2, 0.3, 0.4, 0.5] * 200 for _ in range(5)
    ]
    
    # Mock similarity calculations
    service.calculate_similarity.return_value = 0.85
    service.find_similar_vectors.return_value = [
        {"vector": [0.1, 0.2, 0.3], "similarity": 0.92, "id": "vec-001"},
        {"vector": [0.4, 0.5, 0.6], "similarity": 0.88, "id": "vec-002"},
    ]
    
    return service


@pytest.fixture
def mock_file_system(tmp_path):
    """
    Create a comprehensive mock file system for testing file operations.
    
    Args:
        tmp_path: Pytest fixture providing temporary directory.
        
    Returns:
        dict: Dictionary containing mock file paths and helper methods.
    """
    from pathlib import Path
    from unittest.mock import MagicMock
    
    # Create test directory structure
    test_dir = tmp_path / "test_files"
    test_dir.mkdir()
    
    tasks_dir = test_dir / "Tasks"
    tasks_dir.mkdir()
    
    sessions_dir = test_dir / "Sessions"
    sessions_dir.mkdir()
    
    # Create sample markdown files
    sample_files = {
        "valid_task.md": """---
date: 2023-01-01
title: Test Task
uid: task-001
status: active
---

# Test Task

This is a valid task with proper frontmatter.
""",
        "complex_task.md": """---
date: 2023-01-01
title: Complex Task
uid: task-002
status: draft
tags:
  - python
  - testing
metadata:
  author: Test Author
  priority: high
---

# Complex Task

This task has complex frontmatter with nested structures.
""",
        "invalid_task.md": """# Invalid Task

This file has no frontmatter and should be handled gracefully.
""",
        "unicode_task.md": """---
date: 2023-01-01
title: 测试文档 🚀
uid: task-unicode-001
---

# Unicode Task

This file contains Unicode characters: 你好世界 émojis 🎉
""",
        "session_001.md": """---
date: 2023-01-01
title: Test Session
uid: session-001
---

# Test Session

This is a test session file.
""",
    }
    
    # Write files to disk
    file_paths = {}
    for filename, content in sample_files.items():
        if filename.startswith("session_"):
            file_path = sessions_dir / filename
        else:
            file_path = tasks_dir / filename
        
        file_path.write_text(content, encoding="utf-8")
        file_paths[filename] = file_path
    
    # Mock file operations
    mock_fs = {
        "test_dir": test_dir,
        "tasks_dir": tasks_dir,
        "sessions_dir": sessions_dir,
        "file_paths": file_paths,
        "read_text": lambda path: Path(path).read_text(encoding="utf-8"),
        "write_text": lambda path, content: Path(path).write_text(content, encoding="utf-8"),
        "exists": lambda path: Path(path).exists(),
        "rglob": lambda pattern: list(test_dir.rglob(pattern)),
    }
    
    return mock_fs


@pytest.fixture
def mock_neo4j_enhanced(mock_neo4j_driver):
    """
    Create an enhanced Neo4j mock with realistic query behavior.
    
    Args:
        mock_neo4j_driver: Base Neo4j driver mock.
        
    Returns:
        MagicMock: Enhanced Neo4j driver mock with realistic session behavior.
    """
    from unittest.mock import MagicMock
    
    # Enhanced session mock
    session = MagicMock()
    result = MagicMock()
    
    # Mock different query responses based on query content
    def mock_run(query, **params):
        if "CREATE" in query and "Task" in query:
            result.single.return_value = {"id": "task-001"}
        elif "MATCH" in query and "RETURN" in query:
            result.data.return_value = [
                {"uid": "task-001", "title": "Test Task"},
                {"uid": "task-002", "title": "Another Task"},
            ]
        elif "count" in query.lower():
            result.single.return_value = {"count": 1}
        else:
            result.data.return_value = []
        
        return result
    
    session.run = mock_run
    session.write_transaction = MagicMock()
    session.read_transaction = MagicMock()
    
    # Configure driver to return enhanced session
    mock_neo4j_driver.session.return_value.__enter__.return_value = session
    
    return mock_neo4j_driver


@pytest.fixture
def sample_vector_data():
    """
    Provide sample vector data for similarity testing.
    
    Returns:
        dict: Dictionary containing various vector test cases.
    """
    return {
        "similar_vectors": {
            "vector_a": [0.1, 0.2, 0.3, 0.4, 0.5] * 200,  # 1024-dim
            "vector_b": [0.11, 0.21, 0.31, 0.41, 0.51] * 200,  # Very similar
            "vector_c": [0.15, 0.25, 0.35, 0.45, 0.55] * 200,  # Similar
        },
        "dissimilar_vectors": {
            "vector_d": [0.9, 0.8, 0.7, 0.6, 0.5] * 200,  # Very different
            "vector_e": [0.01, 0.02, 0.03, 0.04, 0.05] * 200,  # Very different
        },
        "expected_similarities": {
            "similar": 0.92,  # High similarity for similar vectors
            "dissimilar": 0.15,  # Low similarity for dissimilar vectors
        },
        "batch_vectors": [
            [0.1, 0.2, 0.3] * 341,  # 1023-dim (close to 1024)
            [0.4, 0.5, 0.6] * 341,
            [0.7, 0.8, 0.9] * 341,
        ] * 100,  # Large batch for performance testing
    }


@pytest.fixture
def sample_frontmatter_data():
    """
    Provide sample frontmatter data for parsing tests.
    
    Returns:
        dict: Dictionary containing various frontmatter test cases.
    """
    return {
        "simple_frontmatter": {
            "content": """---
date: 2023-01-01
title: Simple Task
uid: simple-001
---

# Simple Task
""",
            "expected": {"date": "2023-01-01", "title": "Simple Task", "uid": "simple-001"},
        },
        "complex_frontmatter": {
            "content": """---
date: 2023-01-01
title: Complex Task
uid: complex-001
status: active
tags:
  - python
  - testing
metadata:
  author: Test Author
  priority: high
  version: 1.0
pinned: false
---

# Complex Task
""",
            "expected": {
                "date": "2023-01-01",
                "title": "Complex Task",
                "uid": "complex-001",
                "status": "active",
                "tags": ["python", "testing"],
                "metadata": {"author": "Test Author", "priority": "high", "version": "1.0"},
                "pinned": False,
            },
        },
        "unicode_frontmatter": {
            "content": """---
date: 2023-01-01
title: 测试文档 🚀
uid: unicode-001
description: Document with émojis and spëcial çhars
---

# Unicode Task
""",
            "expected": {
                "date": "2023-01-01",
                "title": "测试文档 🚀",
                "uid": "unicode-001",
                "description": "Document with émojis and spëcial çhars",
            },
        },
        "invalid_frontmatter": {
            "content": """---
date: invalid-date
title: Invalid YAML
  malformed: indentation
---

# Invalid Task
""",
            "expected": None,  # Should return None for invalid YAML
        },
        "no_frontmatter": {
            "content": "# Just content\nNo frontmatter here.",
            "expected": None,  # Should return None for content without frontmatter
        },
    }


@pytest.fixture
def sample_graph_data():
    """
    Provide sample graph data for Neo4j relationship testing.
    
    Returns:
        dict: Dictionary containing sample nodes and relationships.
    """
    return {
        "nodes": {
            "tasks": [
                {"uid": "task-001", "title": "Test Task 1", "status": "active", "created": "2023-01-01"},
                {"uid": "task-002", "title": "Test Task 2", "status": "draft", "created": "2023-01-02"},
                {"uid": "task-003", "title": "Test Task 3", "status": "completed", "created": "2023-01-03"},
            ],
            "sessions": [
                {"uid": "session-001", "title": "Test Session 1", "date": "2023-01-01"},
                {"uid": "session-002", "title": "Test Session 2", "date": "2023-01-02"},
            ],
            "commits": [
                {"hash": "abc123", "message": "Initial commit", "date": "2023-01-01", "repo": "test-repo"},
                {"hash": "def456", "message": "Add feature", "date": "2023-01-02", "repo": "test-repo"},
            ],
        },
        "relationships": [
            {"from": "task-001", "to": "session-001", "type": "CONTAINS_SESSION"},
            {"from": "task-002", "to": "commit-abc123", "type": "CONTAINS_COMMIT"},
            {"from": "session-001", "to": "task-001", "type": "CONTAINS_TASK"},
            {"from": "task-001", "to": "task-002", "type": "RELATES_TO"},
        ],
        "orphan_nodes": [
            {"uid": "orphan-001", "title": "Orphan Task", "status": "draft"},
            {"uid": "orphan-002", "title": "Another Orphan", "status": "draft"},
        ],
    }


@pytest.fixture
def mock_error_conditions():
    """
    Create mock error conditions for testing error handling.
    
    Returns:
        dict: Dictionary containing various error scenarios.
    """
    from unittest.mock import MagicMock
    
    return {
        "neo4j_errors": {
            "service_unavailable": MagicMock(side_effect=Exception("Service unavailable")),
            "auth_error": MagicMock(side_effect=Exception("Authentication failed")),
            "connection_error": MagicMock(side_effect=Exception("Connection failed")),
        },
        "file_errors": {
            "permission_error": PermissionError("Permission denied"),
            "io_error": IOError("I/O error"),
            "file_not_found": FileNotFoundError("File not found"),
        },
        "parsing_errors": {
            "yaml_error": Exception("Invalid YAML syntax"),
            "encoding_error": UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte"),
        },
        "embedding_errors": {
            "service_timeout": TimeoutError("Embedding service timeout"),
            "service_unavailable": Exception("Embedding service unavailable"),
            "invalid_input": Exception("Invalid input for embedding"),
        },
    }


@pytest.fixture
def performance_monitor():
    """
    Create a performance monitoring utility for timing test operations.
    
    Returns:
        dict: Dictionary containing timing and performance measurement tools.
    """
    import time
    from contextlib import contextmanager
    
    @contextmanager
    def measure_time():
        start_time = time.time()
        try:
            yield
        finally:
            end_time = time.time()
            duration = end_time - start_time
            print(f"Operation took {duration:.4f} seconds")
    
    def measure_function(func, *args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        duration = end_time - start_time
        return result, duration
    
    return {
        "measure_time": measure_time,
        "measure_function": measure_function,
        "check_performance": lambda duration, threshold: duration < threshold,
    }


# ===== INTEGRATION TEST FIXTURES =====

@pytest.fixture
def capture_server_test_client():
    """
    Create a test client for the FastAPI capture server.
    
    Returns:
        TestClient: FastAPI test client configured for testing.
    """
    from fastapi.testclient import TestClient
    from omega_kg.capture_server import app
    
    client = TestClient(app)
    return client


@pytest.fixture
def mock_linear_webhook():
    """
    Create a mock Linear webhook handler for testing.
    
    Returns:
        MagicMock: Mock Linear webhook handler.
    """
    from unittest.mock import MagicMock
    
    webhook = MagicMock()
    webhook.process_webhook.return_value = {"success": True, "processed": 1}
    webhook.validate_signature.return_value = True
    webhook.handle_issue_update.return_value = {"updated": 1}
    
    return webhook


@pytest.fixture
def mock_bitwarden_client():
    """
    Create a mock Bitwarden client for testing secret retrieval.
    
    Returns:
        MagicMock: Mock Bitwarden client.
    """
    from unittest.mock import MagicMock
    
    client = MagicMock()
    client.get_secret.return_value = "test-secret-value"
    client.get_secrets.return_value = {
        "LINEAR_WEBHOOK_SECRET_PRD_ID": "test-linear-secret",
        "JWT_SECRET_PRD_ID": "test-jwt-secret",
    }
    client.is_available.return_value = True
    
    return client


@pytest.fixture
def comprehensive_test_environment(mock_env_vars, mock_neo4j_enhanced, mock_percolation_engine, 
                                  mock_file_system, sample_vector_data, sample_frontmatter_data):
    """
    Create a comprehensive test environment with all necessary mocks and data.
    
    This fixture combines multiple other fixtures to provide a complete testing environment
    that can be used for integration tests and complex test scenarios.
    
    Returns:
        dict: Comprehensive test environment with all necessary components.
    """
    return {
        "env_vars": mock_env_vars,
        "neo4j_driver": mock_neo4j_enhanced,
        "percolation_engine": mock_percolation_engine,
        "file_system": mock_file_system,
        "vector_data": sample_vector_data,
        "frontmatter_data": sample_frontmatter_data,
        "capture_server_client": None,  # Will be initialized if needed
        "linear_webhook": None,  # Will be initialized if needed
        "bitwarden_client": None,  # Will be initialized if needed
    }
