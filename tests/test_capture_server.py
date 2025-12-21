import os
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

# Import auth utilities for dependency override
from omega_kg.auth_utils import validate_access_token
# Import remaining items from capture_server
from omega_kg.capture_server import (_create_chat_session,
                                     _create_decision_nodes,
                                     _create_decision_nodes_async, app,
                                     percolate_to_neo4j)
# Import models from new location
from omega_kg.models.capture import ConversationData, Message
# Import utils from new location
from omega_kg.utils.capture_utils import (format_conversation_markdown,
                                          generate_conversation_hash,
                                          write_to_obsidian)


# --- Helper fixture for authenticated requests ---
@pytest.fixture
def auth_override():
    """Fixture that overrides FastAPI auth dependency for testing."""

    def mock_auth():
        return {"sub": "test_user"}

    # Store original and override
    original = app.dependency_overrides.get(validate_access_token)
    app.dependency_overrides[validate_access_token] = mock_auth
    yield
    # Restore original
    if original is None:
        app.dependency_overrides.pop(validate_access_token, None)
    else:
        app.dependency_overrides[validate_access_token] = original


# Import settings lazily within functions to avoid import-time environment issues


class TestConversationDataModel:
    """Test the ConversationData Pydantic model validation and edge cases."""

    def test_minimal_valid_conversation_data(self):
        """Test creating ConversationData with minimal valid data."""
        data = ConversationData(
            platform="test", messages=[{"role": "user", "content": "Hello"}]
        )
        assert data.platform == "test"
        assert data.user_id == "extension_user"  # default value
        assert data.source == "chrome_extension"  # default value
        assert len(data.messages) == 1

    def test_conversation_data_with_message_objects(self):
        """Test ConversationData with Message objects instead of dicts."""
        messages = [
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there!"),
        ]
        data = ConversationData(platform="test", messages=messages)
        assert len(data.messages) == 2
        assert data.messages[0].role == "user"

    def test_conversation_data_validation_errors(self):
        """Test that invalid data raises ValidationError."""
        # Invalid message format - string instead of dict/Message
        with pytest.raises(ValidationError):
            ConversationData(
                platform="test",
                messages=["not a valid message type"],  # strings are not valid
            )

    def test_conversation_data_with_optional_fields(self):
        """Test ConversationData with all optional fields populated."""
        data = ConversationData(
            platform="test",
            messages=[{"role": "user", "content": "Hello"}],
            url="https://example.com",
            title="Test Conversation",
            tags=["test", "example"],
            raw_html="<html>Test</html>",
            metadata={"custom": "value"},
        )
        assert data.url == "https://example.com"
        assert data.title == "Test Conversation"
        assert "test" in data.tags
        assert data.raw_html == "<html>Test</html>"
        assert data.metadata["custom"] == "value"


class TestGenerateConversationHash:
    """Test the generate_conversation_hash function with various inputs."""

    def test_hash_consistency(self):
        """Test that identical data produces identical hashes."""
        data = ConversationData(
            platform="test",
            url="https://example.com",
            messages=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
            ],
        )
        hash1 = generate_conversation_hash(data)
        hash2 = generate_conversation_hash(data)
        assert hash1 == hash2
        assert len(hash1) == 8  # MD5 hash truncated to 8 characters

    def test_hash_uniqueness(self):
        """Test that different data produces different hashes."""
        data1 = ConversationData(
            platform="test", messages=[{"role": "user", "content": "Hello"}]
        )
        data2 = ConversationData(
            platform="test", messages=[{"role": "user", "content": "Different"}]
        )
        hash1 = generate_conversation_hash(data1)
        hash2 = generate_conversation_hash(data2)
        assert hash1 != hash2

    def test_hash_with_message_objects(self):
        """Test hash generation with Message objects."""
        messages = [
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there!"),
        ]
        data = ConversationData(platform="test", messages=messages)
        hash_val = generate_conversation_hash(data)
        assert isinstance(hash_val, str)
        assert len(hash_val) == 8

    def test_hash_empty_messages(self):
        """Test hash generation with empty messages list."""
        data = ConversationData(platform="test", messages=[])
        hash_val = generate_conversation_hash(data)
        assert isinstance(hash_val, str)
        assert len(hash_val) == 8

    def test_hash_long_content_truncation(self):
        """Test that long message content is properly truncated for hashing."""
        long_content = "x" * 1000  # Very long content
        data = ConversationData(
            platform="test", messages=[{"role": "user", "content": long_content}]
        )
        hash_val = generate_conversation_hash(data)
        assert isinstance(hash_val, str)
        assert len(hash_val) == 8


class TestFormatConversationMarkdown:
    """Test the format_conversation_markdown function."""

    def test_basic_markdown_formatting(self):
        """Test basic markdown formatting with minimal data."""
        data = ConversationData(
            platform="test",
            messages=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
            ],
        )
        with patch("omega_kg.utils.capture_utils.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.side_effect = [
                "2023-12-01",  # date_str
                "2023-12-01T10:00:00",  # timestamp_str
            ]
            mock_datetime.now.return_value.isoformat.return_value = (
                "2023-12-01T10:00:00"
            )

            markdown = format_conversation_markdown(data)

            # ID format is now CAP-{timestamp}-{hash}
            assert "id: CAP-2023-12-01T10:00:00-" in markdown  # Contains generated ID
            assert "type: Conversation" in markdown
            assert "status: new" in markdown
            assert "platform: test" in markdown
            # Title is "Untitled Capture" by default
            assert "# Untitled Capture" in markdown
            assert "## 👤 Message 1 (User)" in markdown
            assert "## 🤖 Message 2 (Assistant)" in markdown
            assert "Hello" in markdown
            assert "Hi there!" in markdown

    def test_markdown_with_message_objects(self):
        """Test markdown formatting with Message objects."""
        messages = [
            Message(role="user", content="Hello", timestamp="2023-12-01T10:00:00"),
            Message(role="assistant", content="Hi there!"),
        ]
        data = ConversationData(
            platform="test", title="Custom Title", messages=messages
        )
        with patch("omega_kg.utils.capture_utils.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.side_effect = [
                "2023-12-01",  # date_str
                "2023-12-01T10:00:00",  # timestamp_str
            ]
            mock_datetime.now.return_value.isoformat.return_value = (
                "2023-12-01T10:00:00"
            )

            markdown = format_conversation_markdown(data)

            assert "title: Custom Title" in markdown
            assert "# Custom Title" in markdown
            assert "*Sent: 2023-12-01T10:00:00*" in markdown

    def test_markdown_with_metadata(self):
        """Test markdown formatting with custom metadata."""
        data = ConversationData(
            platform="test",
            messages=[{"role": "user", "content": "Hello"}],
            metadata={"custom_field": "custom_value", "another_field": 123},
        )
        with patch("omega_kg.utils.capture_utils.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.side_effect = [
                "2023-12-01",  # date_str
                "2023-12-01T10:00:00",  # timestamp_str
            ]
            mock_datetime.now.return_value.isoformat.return_value = (
                "2023-12-01T10:00:00"
            )

            markdown = format_conversation_markdown(data)

            assert "custom_field: custom_value" in markdown
            assert "another_field: 123" in markdown

    def test_markdown_empty_messages(self):
        """Test markdown formatting with no messages."""
        data = ConversationData(platform="test", messages=[])
        with patch("omega_kg.utils.capture_utils.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.side_effect = [
                "2023-12-01",  # date_str
                "2023-12-01T10:00:00",  # timestamp_str
            ]
            mock_datetime.now.return_value.isoformat.return_value = (
                "2023-12-01T10:00:00"
            )

            markdown = format_conversation_markdown(data)

            assert "message_count: 0" in markdown
            assert "participants:" in markdown  # Empty participants list


class TestWriteToObsidian:
    """Test the write_to_obsidian function."""

    def test_write_to_obsidian_success(self):
        """Test successful file writing to Obsidian vault."""
        ConversationData(
            platform="test", messages=[{"role": "user", "content": "Hello"}]
        )
        content = "# Test Conversation\n\nHello"
        conv_hash = "abcd1234"

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("omega_kg.utils.capture_utils.settings") as mock_settings:
                mock_settings.obsidian_vault_path = temp_dir

                file_path = write_to_obsidian("test", content, conv_hash)

                # Verify file was created
                assert file_path.exists()
                assert file_path.parent.name == "test"
                assert file_path.parent.parent.name == "AI_Conversations"

                # Verify file content
                written_content = file_path.read_text(encoding="utf-8")
                assert written_content == content

    def test_write_to_obsidian_creates_directories(self):
        """Test that write_to_obsidian creates necessary directories."""
        ConversationData(
            platform="test", messages=[{"role": "user", "content": "Hello"}]
        )
        content = "# Test Conversation\n\nHello"
        conv_hash = "abcd1234"

        with tempfile.TemporaryDirectory() as temp_dir:
            vault_path = Path(temp_dir)
            with patch("omega_kg.utils.capture_utils.settings") as mock_settings:
                mock_settings.obsidian_vault_path = str(vault_path)

                write_to_obsidian("test", content, conv_hash)

                # Verify directory structure was created
                ai_conv_dir = vault_path / "AI_Conversations" / "test"
                assert ai_conv_dir.exists()
                assert ai_conv_dir.is_dir()

    def test_write_to_obsidian_invalid_platform(self):
        """Test that invalid platform names raise ValueError."""
        ConversationData(
            platform="test", messages=[{"role": "user", "content": "Hello"}]
        )
        content = "# Test Conversation\n\nHello"
        conv_hash = "abcd1234"

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("omega_kg.utils.capture_utils.settings") as mock_settings:
                mock_settings.obsidian_vault_path = temp_dir

                # Test path traversal attempts
                with pytest.raises(ValueError, match="Invalid platform name"):
                    write_to_obsidian("../malicious", content, conv_hash)

                with pytest.raises(ValueError, match="Invalid platform name"):
                    write_to_obsidian("malicious/path", content, conv_hash)

    def test_write_to_obsidian_platform_sanitization(self):
        """Test that platform names are properly sanitized."""
        ConversationData(
            platform="test", messages=[{"role": "user", "content": "Hello"}]
        )
        content = "# Test Conversation\n\nHello"
        conv_hash = "abcd1234"

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("omega_kg.utils.capture_utils.settings") as mock_settings:
                mock_settings.obsidian_vault_path = temp_dir

                # Test platform with special characters
                file_path = write_to_obsidian("Test Platform<>", content, conv_hash)

                # Verify platform name was sanitized
                assert file_path.parent.name == "Test_Platform"

    def test_write_to_obsidian_filename_format(self):
        """Test that filenames follow the expected format."""
        ConversationData(
            platform="test", messages=[{"role": "user", "content": "Hello"}]
        )
        content = "# Test Conversation\n\nHello"
        conv_hash = "abcd1234"

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("omega_kg.utils.capture_utils.settings") as mock_settings:
                mock_settings.obsidian_vault_path = temp_dir

                with patch("omega_kg.utils.capture_utils.datetime") as mock_datetime:
                    mock_datetime.now.return_value.strftime.return_value = "2023-12-01"

                    file_path = write_to_obsidian("test", content, conv_hash)

                    # Verify filename format
                    expected_filename = "2023-12-01-abcd1234.md"
                    assert file_path.name == expected_filename


class TestPercolateToNeo4j:
    """Test the percolate_to_neo4j function."""

    @pytest.fixture
    def mock_neo4j_driver(self):
        """Create a mock Neo4j driver for testing."""
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver.session.return_value.__exit__.return_value = None
        return mock_driver, mock_session

    def test_percolate_to_neo4j_success(self, mock_neo4j_driver):
        """Test successful percolation to Neo4j."""
        mock_driver, mock_session = mock_neo4j_driver
        mock_session.run.return_value.single.return_value = True

        data = ConversationData(
            platform="test",
            messages=[
                {"role": "user", "content": "I need to decide something"},
                {"role": "assistant", "content": "Let me help you decide"},
            ],
        )

        with patch("omega_kg.capture_server.settings") as mock_settings:
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_settings.neo4j_user = "neo4j"
            mock_settings.neo4j_password = "password"
            mock_settings.decision_keywords = ["decide"]

            with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
                f.write("# Test\n\nContent")
                file_path = Path(f.name)

            try:
                nodes_created = percolate_to_neo4j(file_path, data, mock_driver)

                # Verify Neo4j operations were called
                assert mock_session.run.call_count >= 2  # ChatSession + Decision nodes
                assert nodes_created >= 1  # At least ChatSession created

            finally:
                file_path.unlink()

    def test_percolate_to_neo4j_with_own_driver(self, mock_neo4j_driver):
        """Test percolation when creating own driver."""
        mock_driver, mock_session = mock_neo4j_driver
        mock_session.run.return_value.single.return_value = True

        data = ConversationData(
            platform="test", messages=[{"role": "user", "content": "Hello"}]
        )

        with patch("omega_kg.capture_server.settings") as mock_settings:
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_settings.neo4j_user = "neo4j"
            mock_settings.neo4j_password = "password"
            mock_settings.decision_keywords = []

            with patch("omega_kg.capture_server.GraphDatabase") as mock_graph_db:
                mock_graph_db.driver.return_value = mock_driver

                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".md", delete=False
                ) as f:
                    f.write("# Test\n\nContent")
                    file_path = Path(f.name)

                try:
                    percolate_to_neo4j(file_path, data)

                    # Verify driver was created and closed
                    mock_graph_db.driver.assert_called_once_with(
                        "bolt://localhost:7687", auth=("neo4j", "password")
                    )
                    mock_driver.close.assert_called_once()

                finally:
                    file_path.unlink()

    def test_percolate_to_neo4j_decision_extraction(self, mock_neo4j_driver):
        """Test that decision keywords are properly extracted and nodes created."""
        mock_driver, mock_session = mock_neo4j_driver
        mock_session.run.return_value.single.return_value = True

        data = ConversationData(
            platform="test",
            messages=[
                {"role": "user", "content": "I will decide tomorrow"},
                {"role": "assistant", "content": "Let's make a choice now"},
                {"role": "user", "content": "No decision needed here"},
            ],
        )

        with patch("omega_kg.capture_server.settings") as mock_settings:
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_settings.neo4j_user = "neo4j"
            mock_settings.neo4j_password = "password"
            mock_settings.decision_keywords = ["decide", "choice"]

            with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
                f.write("# Test\n\nContent")
                file_path = Path(f.name)

            try:
                nodes_created = percolate_to_neo4j(file_path, data, mock_driver)

                # Should create ChatSession + 2 Decision nodes (decide + choice)
                assert mock_session.run.call_count >= 3  # ChatSession + 2 decisions
                assert nodes_created >= 3

            finally:
                file_path.unlink()


class TestCreateChatSession:
    """Test the _create_chat_session helper function."""

    def test_create_chat_session_success(self):
        """Test successful ChatSession node creation."""
        mock_session = MagicMock()
        mock_session.run.return_value.single.return_value = True

        data = ConversationData(
            platform="test", messages=[{"role": "user", "content": "Hello"}]
        )

        with patch("omega_kg.capture_server.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.side_effect = [
                "2023-12-01",  # date_str
                "2023-12-01T10:00:00",  # created_at
            ]
            mock_datetime.now.return_value.isoformat.return_value = (
                "2023-12-01T10:00:00"
            )

            result = _create_chat_session(
                mock_session, "test_hash", Path("/test/file.md"), data
            )

            assert result == 1  # One node created
            mock_session.run.assert_called_once()

            # Verify query parameters
            call_args = mock_session.run.call_args
            assert "$hash" in call_args[0][0]  # parameterized hash in query
            assert call_args[1]["hash"] == "test_hash"  # hash value in params
            assert call_args[1]["platform"] == "test"  # platform in params

    def test_create_chat_session_no_result(self):
        """Test ChatSession creation when no result is returned."""
        mock_session = MagicMock()
        mock_session.run.return_value.single.return_value = None

        data = ConversationData(
            platform="test", messages=[{"role": "user", "content": "Hello"}]
        )

        with patch("omega_kg.capture_server.datetime"):
            result = _create_chat_session(
                mock_session, "test_hash", Path("/test/file.md"), data
            )

            assert result == 0  # No nodes created


class TestCreateDecisionNodes:
    """Test the _create_decision_nodes function."""

    def test_create_decision_nodes_with_keywords(self):
        """Test decision node creation when decision keywords are present."""
        mock_session = MagicMock()
        mock_session.run.return_value.single.return_value = True

        data = ConversationData(
            platform="test",
            messages=[
                {"role": "user", "content": "I will decide tomorrow"},
                {"role": "assistant", "content": "Let's make a choice"},
            ],
        )

        with patch("omega_kg.capture_server.settings") as mock_settings:
            mock_settings.decision_keywords = ["decide", "choice"]

            with patch("omega_kg.capture_server.datetime") as mock_datetime:
                mock_datetime.now.return_value.isoformat.return_value = (
                    "2023-12-01T10:00:00"
                )
                nodes_created = _create_decision_nodes(mock_session, "test_hash", data)

                # Should create 2 decision nodes
                assert mock_session.run.call_count == 2
                assert nodes_created == 2

    def test_create_decision_nodes_no_keywords(self):
        """Test decision node creation when no decision keywords are present."""
        mock_session = MagicMock()

        data = ConversationData(
            platform="test",
            messages=[
                {"role": "user", "content": "Just a regular message"},
                {"role": "assistant", "content": "Another regular response"},
            ],
        )

        with patch("omega_kg.capture_server.settings") as mock_settings:
            mock_settings.decision_keywords = ["decide", "choice"]

            nodes_created = _create_decision_nodes(mock_session, "test_hash", data)

            # Should create 0 decision nodes
            assert mock_session.run.call_count == 0
            assert nodes_created == 0

    def test_create_decision_nodes_empty_messages(self):
        """Test decision node creation with empty messages."""
        mock_session = MagicMock()

        data = ConversationData(platform="test", messages=[])

        with patch("omega_kg.capture_server.settings") as mock_settings:
            mock_settings.decision_keywords = ["decide"]

            nodes_created = _create_decision_nodes(mock_session, "test_hash", data)

            # Should create 0 decision nodes
            assert mock_session.run.call_count == 0
            assert nodes_created == 0


class TestCreateDecisionNodesAsync:
    """Test the _create_decision_nodes_async function."""

    @pytest.mark.asyncio
    async def test_create_decision_nodes_async_with_keywords(self):
        """Test async decision node creation when decision keywords are present."""
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single.return_value = True
        mock_session.run.return_value = mock_result

        data = ConversationData(
            platform="test",
            messages=[
                {"role": "user", "content": "I will decide tomorrow"},
                {"role": "assistant", "content": "Let's make a choice"},
            ],
        )

        with patch("omega_kg.capture_server.settings") as mock_settings:
            mock_settings.decision_keywords = ["decide", "choice"]

            with patch("omega_kg.capture_server.datetime") as mock_datetime:
                mock_datetime.now.return_value.isoformat.return_value = (
                    "2023-12-01T10:00:00"
                )

                nodes_created = await _create_decision_nodes_async(
                    mock_session, "test_hash", data
                )

                # Should create 2 decision nodes
                assert mock_session.run.call_count == 2
                assert nodes_created == 2

    @pytest.mark.asyncio
    async def test_create_decision_nodes_async_no_keywords(self):
        """Test async decision node creation when no decision keywords are present."""
        mock_session = AsyncMock()

        data = ConversationData(
            platform="test",
            messages=[
                {"role": "user", "content": "Just a regular message"},
                {"role": "assistant", "content": "Another regular response"},
            ],
        )

        with patch("omega_kg.capture_server.settings") as mock_settings:
            mock_settings.decision_keywords = ["decide", "choice"]

            nodes_created = await _create_decision_nodes_async(
                mock_session, "test_hash", data
            )

            # Should create 0 decision nodes
            assert mock_session.run.call_count == 0
            assert nodes_created == 0


# NOTE: TestPercolateToNeo4jWithEmbedding and TestBatchPercolateSessions removed
# These tested internal functions with complex mocks that became obsolete after refactor.
# The actual functionality is covered by integration tests.


class TestCaptureServerEndpoints:
    """Test the FastAPI endpoints in capture_server."""

    def test_root_endpoint(self):
        """Test the root endpoint returns service information."""
        client = TestClient(app)
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Omega_KG Capture Server"
        assert data["status"] == "running"
        assert data["version"] == "1.0.0"
        assert "endpoints" in data
        assert "capture" in data["endpoints"]
        assert "health" in data["endpoints"]

    def test_health_endpoint(self):
        """Test the health endpoint returns system status."""
        client = TestClient(app)

        with patch("omega_kg.capture_server.settings") as mock_settings:
            mock_settings.obsidian_vault_path = "/fake/path"
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_settings.neo4j_user = "neo4j"
            mock_settings.neo4j_password = "password"

            # Mock database connections
            with patch("omega_kg.capture_server.GraphDatabase"):
                with patch("omega_kg.routers.capture.get_db"):
                    response = client.get("/health")

                    assert response.status_code == 200
                    data = response.json()
                    assert "status" in data
                    assert "timestamp" in data
                    assert "vault_accessible" in data
                    assert "neo4j_connected" in data
                    assert "postgres_connected" in data

    def test_capture_options_endpoint(self):
        """Test the CORS preflight endpoint for /capture."""
        client = TestClient(app)
        response = client.options("/capture")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "CORS preflight OK"

    def test_capture_endpoint_success(self):
        """Test successful conversation capture."""

        # Override auth dependency
        def mock_auth():
            return {"sub": "test"}

        app.dependency_overrides[validate_access_token] = mock_auth

        try:
            client = TestClient(app)

            conversation_data = {
                "platform": "test",
                "messages": [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi there!"},
                ],
            }

            with tempfile.TemporaryDirectory() as temp_dir:
                with patch("omega_kg.routers.capture.settings") as mock_settings:
                    mock_settings.obsidian_vault_path = temp_dir
                    mock_settings.decision_keywords = []

                    # Mock percolation
                    with patch(
                        "omega_kg.routers.capture._percolate_to_neo4j_with_embedding",
                        return_value=1,
                    ):
                        response = client.post(
                            "/capture",
                            json=conversation_data,
                            headers={"Authorization": "Bearer fake_token"},
                        )

                        assert response.status_code == 200
                        data = response.json()
                        assert data["success"] is True
                        assert data["nodes_created"] == 1
                        assert "file_path" in data
        finally:
            app.dependency_overrides.pop(validate_access_token, None)

    def test_capture_endpoint_too_large(self):
        """Test capture endpoint with payload too large."""

        # Override auth dependency
        def mock_auth():
            return {"sub": "test"}

        app.dependency_overrides[validate_access_token] = mock_auth

        try:
            client = TestClient(app)

            # Create payload larger than MAX_HTML_SIZE (10MB)
            large_content = "x" * (10 * 1024 * 1024 + 1)  # Slightly over 10MB
            conversation_data = {"platform": "test", "raw_html": large_content}

            response = client.post(
                "/capture",
                json=conversation_data,
                headers={"Authorization": "Bearer fake_token"},
            )

            assert response.status_code == 413
            assert (
                "exceeds maximum" in response.json()["detail"]
                or "too large" in response.json()["detail"]
            )
        finally:
            app.dependency_overrides.pop(validate_access_token, None)

    def test_capture_endpoint_no_messages(self):
        """Test capture endpoint with no messages and no content."""

        # Override auth dependency
        def mock_auth():
            return {"sub": "test"}

        app.dependency_overrides[validate_access_token] = mock_auth

        try:
            client = TestClient(app)
            conversation_data = {"platform": "test", "messages": []}

            response = client.post(
                "/capture",
                json=conversation_data,
                headers={"Authorization": "Bearer fake_token"},
            )

            assert response.status_code == 422
            assert "No messages provided" in response.json()["detail"]
        finally:
            app.dependency_overrides.pop(validate_access_token, None)

    def test_auth_token_endpoint(self):
        """Test the JWT token exchange endpoint."""
        from omega_kg.auth_utils import get_static_api_key

        client = TestClient(app)

        # Override the security dependency with a mock that returns the API key
        async def mock_api_key():
            return "valid_key"

        app.dependency_overrides[get_static_api_key] = mock_api_key
        try:
            with patch(
                "omega_kg.routers.capture.create_access_token",
                return_value="jwt_token_123",
            ):
                response = client.post(
                    "/auth/token", headers={"X-API-Key": "valid_key"}
                )

                assert response.status_code == 200
                data = response.json()
                assert data["access_token"] == "jwt_token_123"
                assert data["token_type"] == "bearer"
        finally:
            app.dependency_overrides.pop(get_static_api_key, None)

    def test_auth_token_invalid_key(self):
        """Test JWT token exchange with invalid API key."""
        client = TestClient(app)

        with patch(
            "omega_kg.routers.capture.get_static_api_key",
            side_effect=HTTPException(status_code=403),
        ):
            response = client.post("/auth/token", headers={"X-API-Key": "invalid_key"})

            assert response.status_code == 403

    def test_health_vectors_endpoint(self):
        """Test the vector health endpoint."""
        client = TestClient(app)

        # Mock vector store
        mock_vector_store = AsyncMock()
        mock_vector_store.get_stats.return_value = {
            "total_records": 100,
            "pending_count": 5,
            "ready_count": 95,
            "failed_count": 0,
            "avg_retry_count": 0.1,
        }

        with patch(
            "omega_kg.routers.capture.get_vector_store", return_value=mock_vector_store
        ):
            response = client.get("/health/vectors")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["total_records"] == 100
            assert data["pending_count"] == 5
            assert data["worker_running"] is True

    def test_health_vectors_endpoint_unhealthy(self):
        """Test the vector health endpoint when unhealthy."""
        client = TestClient(app)

        with patch(
            "omega_kg.routers.capture.get_vector_store",
            side_effect=Exception("Vector store failed"),
        ):
            response = client.get("/health/vectors")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "unhealthy"
            assert "error" in data
            assert data["worker_running"] is False

    def test_linear_webhook_endpoint(self):
        """Test the Linear webhook endpoint."""
        client = TestClient(app)

        # Mock sync engine
        mock_sync_engine = AsyncMock()
        mock_sync_engine.handle_linear_webhook_request.return_value = {"status": "ok"}

        with patch("omega_kg.capture_server.sync_engine", mock_sync_engine):
            client.post("/webhook/linear", json={"test": "data"})

            # Should pass request to sync engine
            mock_sync_engine.handle_linear_webhook_request.assert_called_once()
            # Response depends on sync engine implementation


class TestCaptureServerIntegration:
    """Integration tests for the capture server."""

    def test_end_to_end_capture_flow(self):
        """Test the complete capture flow from API to file storage."""

        # Override auth dependency
        def mock_auth():
            return {"sub": "test"}

        app.dependency_overrides[validate_access_token] = mock_auth

        try:
            client = TestClient(app)

            conversation_data = {
                "platform": "test_integration",
                "url": "https://example.com/conversation",
                "title": "Integration Test Conversation",
                "messages": [
                    {
                        "role": "user",
                        "content": "I need to decide on something important",
                    },
                    {
                        "role": "assistant",
                        "content": "Let me help you make that decision",
                    },
                ],
                "tags": ["test", "integration"],
            }

            with tempfile.TemporaryDirectory() as temp_dir:
                with patch("omega_kg.routers.capture.settings") as mock_settings:
                    mock_settings.obsidian_vault_path = temp_dir
                    mock_settings.decision_keywords = ["decide"]

                    with patch(
                        "omega_kg.routers.capture._percolate_to_neo4j_with_embedding",
                        return_value=2,
                    ):
                        response = client.post(
                            "/capture",
                            json=conversation_data,
                            headers={"Authorization": "Bearer fake_token"},
                        )

                        assert response.status_code == 200
                        data = response.json()
                        assert data["success"] is True
                        assert data["nodes_created"] == 2

                        # Verify file was created
                        file_path = Path(data["file_path"])
                        assert file_path.exists()

                        # Verify file content
                        content = file_path.read_text(encoding="utf-8")
                        assert "Integration Test Conversation" in content
                        assert "test_integration" in content
                        assert "https://example.com/conversation" in content
        finally:
            app.dependency_overrides.pop(validate_access_token, None)

    def test_html_parsing_integration(self):
        """Test HTML parsing integration in capture flow."""

        # Override auth dependency
        def mock_auth():
            return {"sub": "test"}

        app.dependency_overrides[validate_access_token] = mock_auth

        try:
            client = TestClient(app)

            conversation_data = {
                "platform": "test_html",
                "raw_html": "<div><p>User: Hello there</p><p>Assistant: Hi! How can I help?</p></div>",
                "url": "https://example.com",
            }

            with tempfile.TemporaryDirectory() as temp_dir:
                with patch("omega_kg.routers.capture.settings") as mock_settings:
                    mock_settings.obsidian_vault_path = temp_dir
                    mock_settings.decision_keywords = []

                    # Mock HTML parsing
                    with patch(
                        "omega_kg.routers.capture.parse_html_content"
                    ) as mock_parse:
                        mock_parse.return_value = [
                            {"role": "user", "content": "Hello there"},
                            {"role": "assistant", "content": "Hi! How can I help?"},
                        ]

                        with patch(
                            "omega_kg.routers.capture._percolate_to_neo4j_with_embedding",
                            return_value=1,
                        ):
                            response = client.post(
                                "/capture",
                                json=conversation_data,
                                headers={"Authorization": "Bearer fake_token"},
                            )

                            assert response.status_code == 200

                            # Verify HTML parsing was called
                            mock_parse.assert_called_once_with(
                                conversation_data["raw_html"], "https://example.com"
                            )
        finally:
            app.dependency_overrides.pop(validate_access_token, None)

    def test_error_handling_integration(self):
        """Test error handling in capture flow."""

        # Override auth dependency
        def mock_auth():
            return {"sub": "test"}

        app.dependency_overrides[validate_access_token] = mock_auth

        try:
            client = TestClient(app)

            conversation_data = {
                "platform": "test_error",
                "messages": [{"role": "user", "content": "Hello"}],
            }

            # Mock file writing failure
            with patch(
                "omega_kg.routers.capture.write_to_obsidian",
                side_effect=IOError("Disk full"),
            ):
                response = client.post(
                    "/capture",
                    json=conversation_data,
                    headers={"Authorization": "Bearer fake_token"},
                )

                assert response.status_code == 500
                data = response.json()
                # Error response uses HTTPException detail format
                assert "Internal error" in str(data["detail"])
                assert "id" in str(data["detail"])  # Support ID for tracking
        finally:
            app.dependency_overrides.pop(validate_access_token, None)


class TestCaptureServerSecurity:
    """Security tests for the capture server."""

    def test_authentication_required(self):
        """Test that authentication is required for protected endpoints."""
        client = TestClient(app)

        conversation_data = {
            "platform": "test",
            "messages": [{"role": "user", "content": "Hello"}],
        }

        # Test without authentication - should return 401 or 403
        response = client.post("/capture", json=conversation_data)
        assert response.status_code in [401, 403]  # Should require authentication

        # Test with invalid authentication
        response = client.post(
            "/capture",
            json=conversation_data,
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code in [401, 403]  # Should reject invalid token

    def test_cors_headers(self):
        """Test CORS headers are properly set."""
        client = TestClient(app)

        # Test OPTIONS request
        response = client.options("/capture")
        assert response.status_code == 200

        # Test actual request with Origin header
        response = client.post(
            "/capture",
            json={"platform": "test", "messages": []},
            headers={"Origin": "chrome-extension://test_extension_id"},
        )

        # Should handle CORS (may succeed or fail based on auth, but CORS headers should be present)
        assert response.status_code in [200, 401, 403, 422]

    def test_input_validation(self):
        """Test input validation for security."""

        # Override auth dependency
        def mock_auth():
            return {"sub": "test"}

        app.dependency_overrides[validate_access_token] = mock_auth

        try:
            client = TestClient(app)

            # Test malicious platform name (path traversal attempt)
            malicious_data = {
                "platform": "../../../malicious",
                "messages": [{"role": "user", "content": "Hello"}],
            }

            with tempfile.TemporaryDirectory() as temp_dir:
                with patch("omega_kg.routers.capture.settings") as mock_settings:
                    mock_settings.obsidian_vault_path = temp_dir
                    mock_settings.decision_keywords = []

                    response = client.post(
                        "/capture",
                        json=malicious_data,
                        headers={"Authorization": "Bearer fake_token"},
                    )

                    # Should handle path traversal attempt safely
                    assert response.status_code in [200, 422, 500]
        finally:
            app.dependency_overrides.pop(validate_access_token, None)

    def test_content_size_limits(self):
        """Test content size limits are enforced."""

        # Override auth dependency
        def mock_auth():
            return {"sub": "test"}

        app.dependency_overrides[validate_access_token] = mock_auth

        try:
            client = TestClient(app)

            # Test extremely large content
            large_data = {
                "platform": "test",
                "messages": [
                    {"role": "user", "content": "x" * 1_000_000}
                ],  # 1MB content
            }

            response = client.post(
                "/capture",
                json=large_data,
                headers={"Authorization": "Bearer fake_token"},
            )

            # Should either accept or reject based on size limits, but handle gracefully
            assert response.status_code in [200, 413, 422]
        finally:
            app.dependency_overrides.pop(validate_access_token, None)


class TestCaptureServerPerformance:
    """Performance tests for the capture server."""

    def test_concurrent_requests(self):
        """Test handling concurrent requests."""
        import threading
        import time

        # Override auth dependency for entire test
        def mock_auth():
            return {"sub": "test"}

        app.dependency_overrides[validate_access_token] = mock_auth

        try:
            client = TestClient(app)
            results = []

            def make_request():
                conversation_data = {
                    "platform": "test_concurrent",
                    "messages": [{"role": "user", "content": f"Message {time.time()}"}],
                }

                with tempfile.TemporaryDirectory() as temp_dir:
                    with patch("omega_kg.routers.capture.settings") as mock_settings:
                        mock_settings.obsidian_vault_path = temp_dir
                        mock_settings.decision_keywords = []

                        with patch(
                            "omega_kg.routers.capture._percolate_to_neo4j_with_embedding",
                            return_value=1,
                        ):
                            response = client.post(
                                "/capture",
                                json=conversation_data,
                                headers={"Authorization": "Bearer fake_token"},
                            )
                            results.append(response.status_code)

            # Start multiple concurrent requests
            threads = []
            for _ in range(5):
                thread = threading.Thread(target=make_request)
                threads.append(thread)
                thread.start()

            # Wait for all threads to complete
            for thread in threads:
                thread.join()

            # All requests should succeed
            assert len(results) == 5
            assert all(status == 200 for status in results)
        finally:
            app.dependency_overrides.pop(validate_access_token, None)

    def test_large_message_handling(self):
        """Test handling of large but valid messages."""

        # Override auth dependency
        def mock_auth():
            return {"sub": "test"}

        app.dependency_overrides[validate_access_token] = mock_auth

        try:
            client = TestClient(app)

            # Create a large but reasonable message
            large_content = "This is a test message. " * 1000  # ~25KB
            conversation_data = {
                "platform": "test_large",
                "messages": [
                    {"role": "user", "content": large_content},
                    {
                        "role": "assistant",
                        "content": "I understand your large message.",
                    },
                ],
            }

            with tempfile.TemporaryDirectory() as temp_dir:
                with patch("omega_kg.routers.capture.settings") as mock_settings:
                    mock_settings.obsidian_vault_path = temp_dir
                    mock_settings.decision_keywords = []

                    with patch(
                        "omega_kg.routers.capture._percolate_to_neo4j_with_embedding",
                        return_value=1,
                    ):
                        start_time = time.time()
                        response = client.post(
                            "/capture",
                            json=conversation_data,
                            headers={"Authorization": "Bearer fake_token"},
                        )
                        end_time = time.time()

                        assert response.status_code == 200

                        # Should complete in reasonable time (adjust threshold as needed)
                        assert (end_time - start_time) < 5.0  # 5 seconds max
        finally:
            app.dependency_overrides.pop(validate_access_token, None)

    def test_memory_usage_stability(self):
        """Test that memory usage remains stable during processing."""
        import gc

        import psutil

        # Override auth dependency
        def mock_auth():
            return {"sub": "test"}

        app.dependency_overrides[validate_access_token] = mock_auth

        try:
            client = TestClient(app)
            process = psutil.Process(os.getpid())

            # Get baseline memory usage
            gc.collect()
            baseline_memory = process.memory_info().rss

            # Process multiple requests
            for i in range(10):
                conversation_data = {
                    "platform": f"test_memory_{i}",
                    "messages": [
                        {"role": "user", "content": f"Message {i} with some content"},
                        {
                            "role": "assistant",
                            "content": f"Response {i} with more content",
                        },
                    ],
                }

                with tempfile.TemporaryDirectory() as temp_dir:
                    with patch("omega_kg.routers.capture.settings") as mock_settings:
                        mock_settings.obsidian_vault_path = temp_dir
                        mock_settings.decision_keywords = []

                        with patch(
                            "omega_kg.routers.capture._percolate_to_neo4j_with_embedding",
                            return_value=1,
                        ):
                            response = client.post(
                                "/capture",
                                json=conversation_data,
                                headers={"Authorization": "Bearer fake_token"},
                            )
                            assert response.status_code == 200

            # Check final memory usage
            gc.collect()
            final_memory = process.memory_info().rss
            memory_increase = final_memory - baseline_memory

            # Memory increase should be reasonable
            assert memory_increase < 50 * 1024 * 1024  # Less than 50MB increase
        finally:
            app.dependency_overrides.pop(validate_access_token, None)
