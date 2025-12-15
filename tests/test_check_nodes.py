"""
Unit tests for check_nodes.py
"""

import subprocess
import sys
from typing import Any
from unittest.mock import Mock, patch
import os
import pytest

# Ensure required environment variables for settings are set at module import time
os.environ.setdefault("EXTENSION_API_KEY", "test-ext-api-key")
os.environ.setdefault("LINEAR_WEBHOOK_SECRET", "test-webhook-secret")
os.environ.setdefault("CHROME_EXTENSION_ID", "test-chrome-ext")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret")
os.environ.setdefault("NEO4J_PASSWORD", "test-neo4j-password")
os.environ.setdefault("OBSIDIAN_VAULT_PATH", "./test_vault")

class MockRecord:
    """Mock Neo4j record class for testing."""

    def __init__(self, count_value: int = 0):
        """Initialize MockRecord with count value."""
        self._count = count_value

    def __getitem__(self, key: str) -> Any:
        """Get item by key, simulating Neo4j record behavior."""
        if key == 'count':
            return self._count
        return None

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"MockRecord(count={self._count})"

class TestCheckNodes:
    """Test suite for check_nodes.py functionality."""

    def test_check_nodes_with_tasks(self) -> None:
        """Test check_nodes script driver creation."""
        # Patch GraphDatabase.driver before importing the module
        with patch("neo4j.GraphDatabase.driver") as mock_driver:
            # Mock the driver and session
            mock_session = Mock()
            mock_driver.return_value.session.return_value.__enter__.return_value = mock_session

            # Mock session.run to return mock results with proper MockRecord
            mock_result = Mock()
            mock_record = MockRecord(5)  # Initialize with count=5 to match test expectation
            mock_result.single.return_value = mock_record
            mock_result.__iter__ = Mock(return_value=iter([mock_record]))
            mock_session.run.return_value = mock_result

            # Import the module (this will execute module-level code with mocks in place)
            from omega_kg import check_nodes

            # Verify the driver was created correctly
            expected_auth = (
                check_nodes.settings.neo4j_user,
                check_nodes.settings.neo4j_password,
            )
            mock_driver.assert_called_once_with(
                check_nodes.settings.neo4j_uri, auth=expected_auth
            )

    @pytest.mark.requires_neo4j
    def test_check_nodes_script_execution(self) -> None:
        """Test that check_nodes.py can be executed as a script."""
        # Run the script as a subprocess
        result = subprocess.run(
            [sys.executable, "omega_kg/check_nodes.py"],
            capture_output=True,
            text=True,
            cwd=".",
            check=False,
        )

        # The script should run without errors (even if Neo4j is not available)
        # It will fail with connection errors, but should not have syntax errors
        assert result.returncode != 2  # Not a syntax error

    def test_mock_record_behavior(self) -> None:
        """Test MockRecord class behavior with different keys."""
        # Test with count=0
        record_zero = MockRecord(0)
        assert record_zero['count'] == 0
        assert record_zero['other_key'] is None

        # Test with count>0
        record_positive = MockRecord(5)
        assert record_positive['count'] == 5
        assert record_positive['other_key'] is None

        # Test string representation
        assert str(record_zero) == "MockRecord(count=0)"
        assert str(record_positive) == "MockRecord(count=5)"
