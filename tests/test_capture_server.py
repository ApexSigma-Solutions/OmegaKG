"""
Comprehensive unit tests for omega_kg.capture_server module.

Tests cover:
- Pydantic models validation
- Pure functions (hash generation, markdown formatting)
- File I/O operations
- Neo4j integration
- FastAPI endpoints
- Error handling and edge cases
"""

import hashlib
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, AsyncMock
from fastapi.testclient import TestClient

from omega_kg.capture_server import (
    app,
    Message,
    ConversationData,
    CaptureResponse,
    generate_conversation_hash,
    format_conversation_markdown,
    write_to_obsidian,
    percolate_to_neo4j,
    batch_percolate_sessions,
)


# ============================================================================
# Pydantic Model Tests
# ============================================================================

class TestMessageModel:
    """Test Message pydantic model validation."""
    
    def test_message_with_all_fields(self):
        """Test creating message with all fields."""
        msg = Message(
            role="user",
            content="Hello, world!",
            timestamp="2024-01-01T12:00:00"
        )
        assert msg.role == "user"
        assert msg.content == "Hello, world!"
        assert msg.timestamp == "2024-01-01T12:00:00"
    
    def test_message_without_optional_timestamp(self):
        """Test creating message without optional timestamp."""
        msg = Message(role="assistant", content="Response")
        assert msg.role == "assistant"
        assert msg.content == "Response"
        assert msg.timestamp is None
    
    def test_message_requires_role_and_content(self):
        """Test that role and content are required fields."""
        with pytest.raises(Exception):  # Pydantic validation error
            Message(role="user")  # Missing content
        
        with pytest.raises(Exception):
            Message(content="Hello")  # Missing role


class TestConversationDataModel:
    """Test ConversationData pydantic model validation."""
    
    def test_conversation_data_minimal(self):
        """Test creating conversation with minimal required fields."""
        data = ConversationData(
            platform="ChatGPT",
            url="https://chat.openai.com/c/123",
            messages=[
                Message(role="user", content="Hello"),
                Message(role="assistant", content="Hi there!")
            ]
        )
        assert data.platform == "ChatGPT"
        assert data.url == "https://chat.openai.com/c/123"
        assert len(data.messages) == 2
        assert data.title is None
        assert data.metadata == {}
    
    def test_conversation_data_with_all_fields(self):
        """Test creating conversation with all optional fields."""
        data = ConversationData(
            platform="Claude.ai",
            url="https://claude.ai/chat/abc123",
            title="Test Conversation",
            messages=[Message(role="user", content="Test")],
            metadata={"session_id": "xyz", "duration": 300}
        )
        assert data.title == "Test Conversation"
        assert data.metadata["session_id"] == "xyz"
        assert data.metadata["duration"] == 300
    
    def test_conversation_data_empty_messages_list(self):
        """Test that empty messages list is allowed."""
        data = ConversationData(
            platform="Gemini",
            url="https://gemini.google.com/chat/1",
            messages=[]
        )
        assert len(data.messages) == 0


class TestCaptureResponseModel:
    """Test CaptureResponse pydantic model."""
    
    def test_capture_response_creation(self):
        """Test creating capture response."""
        response = CaptureResponse(
            success=True,
            file_path="/path/to/file.md",
            nodes_created=3,
            message="Success!"
        )
        assert response.success is True
        assert response.file_path == "/path/to/file.md"
        assert response.nodes_created == 3
        assert response.message == "Success!"


# ============================================================================
# Pure Function Tests
# ============================================================================

class TestGenerateConversationHash:
    """Test generate_conversation_hash function (pure function)."""
    
    def test_hash_generation_deterministic(self):
        """Test that same input produces same hash."""
        data = ConversationData(
            platform="ChatGPT",
            url="https://chat.openai.com/c/123",
            messages=[
                Message(role="user", content="Hello"),
                Message(role="assistant", content="Hi")
            ]
        )
        
        hash1 = generate_conversation_hash(data)
        hash2 = generate_conversation_hash(data)
        
        assert hash1 == hash2
        assert len(hash1) == 8
        assert all(c in '0123456789abcdef' for c in hash1)
    
    def test_hash_changes_with_platform(self):
        """Test that different platforms produce different hashes."""
        data1 = ConversationData(
            platform="ChatGPT",
            url="https://example.com/chat/1",
            messages=[Message(role="user", content="Test")]
        )
        data2 = ConversationData(
            platform="Claude.ai",
            url="https://example.com/chat/1",
            messages=[Message(role="user", content="Test")]
        )
        
        hash1 = generate_conversation_hash(data1)
        hash2 = generate_conversation_hash(data2)
        
        assert hash1 != hash2
    
    def test_hash_changes_with_url(self):
        """Test that different URLs produce different hashes."""
        data1 = ConversationData(
            platform="ChatGPT",
            url="https://example.com/chat/1",
            messages=[Message(role="user", content="Test")]
        )
        data2 = ConversationData(
            platform="ChatGPT",
            url="https://example.com/chat/2",
            messages=[Message(role="user", content="Test")]
        )
        
        hash1 = generate_conversation_hash(data1)
        hash2 = generate_conversation_hash(data2)
        
        assert hash1 != hash2
    
    def test_hash_changes_with_message_count(self):
        """Test that different message counts produce different hashes."""
        data1 = ConversationData(
            platform="ChatGPT",
            url="https://example.com/chat/1",
            messages=[Message(role="user", content="Test")]
        )
        data2 = ConversationData(
            platform="ChatGPT",
            url="https://example.com/chat/1",
            messages=[
                Message(role="user", content="Test"),
                Message(role="assistant", content="Response")
            ]
        )
        
        hash1 = generate_conversation_hash(data1)
        hash2 = generate_conversation_hash(data2)
        
        assert hash1 != hash2
    
    def test_hash_consistent_across_runs(self):
        """Test hash is consistent with known values."""
        data = ConversationData(
            platform="Test",
            url="https://test.com",
            messages=[Message(role="user", content="Hi")]
        )
        
        expected_content = "Test-https://test.com-1"
        expected_hash = hashlib.md5(expected_content.encode()).hexdigest()[:8]
        actual_hash = generate_conversation_hash(data)
        
        assert actual_hash == expected_hash


class TestFormatConversationMarkdown:
    """Test format_conversation_markdown function (pure function)."""
    
    def test_markdown_format_basic_structure(self):
        """Test basic markdown structure with frontmatter."""
        data = ConversationData(
            platform="ChatGPT",
            url="https://chat.openai.com/c/123",
            messages=[
                Message(role="user", content="Hello"),
                Message(role="assistant", content="Hi there!")
            ]
        )
        
        markdown = format_conversation_markdown(data)
        
        # Check frontmatter
        assert markdown.startswith("---")
        assert "platform: ChatGPT" in markdown
        assert "url: https://chat.openai.com/c/123" in markdown
        assert "message_count: 2" in markdown
        assert "conversation_hash:" in markdown
        
        # Check content structure
        assert "# ChatGPT Conversation" in markdown
        assert "👤" in markdown  # User emoji
        assert "🤖" in markdown  # Assistant emoji
        assert "Hello" in markdown
        assert "Hi there!" in markdown
    
    def test_markdown_format_with_title(self):
        """Test markdown includes custom title when provided."""
        data = ConversationData(
            platform="Claude.ai",
            url="https://claude.ai/chat/abc",
            title="My Custom Title",
            messages=[Message(role="user", content="Test")]
        )
        
        markdown = format_conversation_markdown(data)
        
        assert "title: My Custom Title" in markdown
        assert "# My Custom Title" in markdown
    
    def test_markdown_format_with_metadata(self):
        """Test markdown includes custom metadata."""
        data = ConversationData(
            platform="Gemini",
            url="https://gemini.google.com/chat/1",
            messages=[Message(role="user", content="Test")],
            metadata={"session_id": "xyz123", "model": "gemini-pro"}
        )
        
        markdown = format_conversation_markdown(data)
        
        assert "session_id: xyz123" in markdown
        assert "model: gemini-pro" in markdown
    
    def test_markdown_format_with_message_timestamps(self):
        """Test markdown includes message timestamps."""
        data = ConversationData(
            platform="ChatGPT",
            url="https://chat.openai.com/c/123",
            messages=[
                Message(
                    role="user",
                    content="Hello",
                    timestamp="2024-01-01T10:00:00"
                ),
                Message(
                    role="assistant",
                    content="Hi",
                    timestamp="2024-01-01T10:00:05"
                )
            ]
        )
        
        markdown = format_conversation_markdown(data)
        
        assert "*Sent: 2024-01-01T10:00:00*" in markdown
        assert "*Sent: 2024-01-01T10:00:05*" in markdown
    
    def test_markdown_format_participants_extraction(self):
        """Test that participants are extracted from messages."""
        data = ConversationData(
            platform="ChatGPT",
            url="https://chat.openai.com/c/123",
            messages=[
                Message(role="user", content="Hello"),
                Message(role="assistant", content="Hi"),
                Message(role="user", content="How are you?")
            ]
        )
        
        markdown = format_conversation_markdown(data)
        
        # Should extract unique roles
        assert "participants:" in markdown
        assert "user" in markdown
        assert "assistant" in markdown
    
    def test_markdown_format_empty_messages(self):
        """Test markdown handles empty message list."""
        data = ConversationData(
            platform="ChatGPT",
            url="https://chat.openai.com/c/123",
            messages=[]
        )
        
        markdown = format_conversation_markdown(data)
        
        assert "message_count: 0" in markdown
        assert "**Messages**: 0" in markdown
    
    def test_markdown_format_multiline_content(self):
        """Test markdown handles multi-line message content."""
        data = ConversationData(
            platform="ChatGPT",
            url="https://chat.openai.com/c/123",
            messages=[
                Message(
                    role="user",
                    content="Line 1\nLine 2\nLine 3"
                )
            ]
        )
        
        markdown = format_conversation_markdown(data)
        
        assert "Line 1\nLine 2\nLine 3" in markdown


# ============================================================================
# File I/O Tests
# ============================================================================

class TestWriteToObsidian:
    """Test write_to_obsidian function."""
    
    def test_write_creates_file_successfully(self, tmp_path, monkeypatch):
        """Test successful file creation in vault."""
        vault_path = tmp_path / "test_vault"
        vault_path.mkdir()
        
        monkeypatch.setattr("omega_kg.capture_server.settings.obsidian_vault_path", str(vault_path))
        
        result_path = write_to_obsidian(
            platform="ChatGPT",
            content="# Test Conversation\n\nContent here",
            conversation_hash="abc12345"
        )
        
        assert result_path.exists()
        assert result_path.parent.name == "ChatGPT"
        assert result_path.name.endswith("-abc12345.md")
        assert "Test Conversation" in result_path.read_text()
    
    def test_write_creates_platform_folder(self, tmp_path, monkeypatch):
        """Test that platform folder is created if it doesn't exist."""
        vault_path = tmp_path / "test_vault"
        vault_path.mkdir()
        
        monkeypatch.setattr("omega_kg.capture_server.settings.obsidian_vault_path", str(vault_path))
        
        result_path = write_to_obsidian(
            platform="Claude.ai",
            content="Test content",
            conversation_hash="xyz789"
        )
        
        expected_folder = vault_path / "AI_Conversations" / "Claude.ai"
        assert expected_folder.exists()
        assert result_path.parent == expected_folder
    
    def test_write_normalizes_platform_name(self, tmp_path, monkeypatch):
        """Test that platform names with spaces are normalized."""
        vault_path = tmp_path / "test_vault"
        vault_path.mkdir()
        
        monkeypatch.setattr("omega_kg.capture_server.settings.obsidian_vault_path", str(vault_path))
        
        result_path = write_to_obsidian(
            platform="GitHub Copilot",
            content="Test content",
            conversation_hash="def456"
        )
        
        expected_folder = vault_path / "AI_Conversations" / "GitHub_Copilot"
        assert expected_folder.exists()
    
    def test_write_raises_value_error_if_vault_missing(self, tmp_path, monkeypatch):
        """Test that ValueError is raised if vault doesn't exist."""
        nonexistent_vault = tmp_path / "nonexistent_vault"
        monkeypatch.setattr("omega_kg.capture_server.settings.obsidian_vault_path", str(nonexistent_vault))
        
        with pytest.raises(ValueError, match="Obsidian vault not found"):
            write_to_obsidian(
                platform="ChatGPT",
                content="Test",
                conversation_hash="abc123"
            )
    
    def test_write_filename_includes_date(self, tmp_path, monkeypatch):
        """Test that filename includes current date."""
        vault_path = tmp_path / "test_vault"
        vault_path.mkdir()
        
        monkeypatch.setattr("omega_kg.capture_server.settings.obsidian_vault_path", str(vault_path))
        
        result_path = write_to_obsidian(
            platform="ChatGPT",
            content="Test",
            conversation_hash="abc123"
        )
        
        today = datetime.now().strftime("%Y-%m-%d")
        assert result_path.name.startswith(today)
    
    def test_write_handles_special_characters_in_content(self, tmp_path, monkeypatch):
        """Test writing content with special characters."""
        vault_path = tmp_path / "test_vault"
        vault_path.mkdir()
        
        monkeypatch.setattr("omega_kg.capture_server.settings.obsidian_vault_path", str(vault_path))
        
        special_content = "# Test\n\n```python\ndef test():\n    pass\n```\n\n🎉 Emoji!"
        
        result_path = write_to_obsidian(
            platform="ChatGPT",
            content=special_content,
            conversation_hash="xyz789"
        )
        
        written_content = result_path.read_text(encoding="utf-8")
        assert special_content in written_content


# ============================================================================
# Neo4j Integration Tests
# ============================================================================

class TestPercolateToNeo4j:
    """Test percolate_to_neo4j function."""
    
    @patch("omega_kg.capture_server.GraphDatabase.driver")
    def test_percolate_creates_chat_session_node(self, mock_driver_class):
        """Test that ChatSession node is created."""
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.single.return_value = {"s": "node"}
        
        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver_class.return_value = mock_driver
        
        data = ConversationData(
            platform="ChatGPT",
            url="https://chat.openai.com/c/123",
            messages=[Message(role="user", content="Hello")]
        )
        file_path = Path("/tmp/test.md")
        
        nodes_created = percolate_to_neo4j(file_path, data)
        
        assert nodes_created >= 1
        mock_driver_class.assert_called_once()
        mock_session.run.assert_called()
    
    @patch("omega_kg.capture_server.GraphDatabase.driver")
    def test_percolate_extracts_decisions(self, mock_driver_class):
        """Test that decision nodes are created from keywords."""
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.single.return_value = {"d": "decision_node"}
        
        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver_class.return_value = mock_driver
        
        data = ConversationData(
            platform="ChatGPT",
            url="https://chat.openai.com/c/123",
            messages=[
                Message(
                    role="user",
                    content="We decided to use FastAPI for the API."
                )
            ]
        )
        file_path = Path("/tmp/test.md")
        
        nodes_created = percolate_to_neo4j(file_path, data)
        
        # Should create at least ChatSession + Decision node
        assert nodes_created >= 2
    
    @patch("omega_kg.capture_server.GraphDatabase.driver")
    def test_percolate_handles_neo4j_error(self, mock_driver_class):
        """Test that Neo4j connection errors are raised."""
        mock_driver_class.side_effect = Exception("Connection failed")
        
        data = ConversationData(
            platform="ChatGPT",
            url="https://chat.openai.com/c/123",
            messages=[Message(role="user", content="Test")]
        )
        file_path = Path("/tmp/test.md")
        
        with pytest.raises(Exception, match="Connection failed"):
            percolate_to_neo4j(file_path, data)
    
    @patch("omega_kg.capture_server.GraphDatabase.driver")
    def test_percolate_decision_keywords(self, mock_driver_class):
        """Test various decision keywords are detected."""
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.single.return_value = {"node": "data"}
        
        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver_class.return_value = mock_driver
        
        decision_phrases = [
            "We decided to implement this feature",
            "The plan is to refactor the code",
            "The approach is to use microservices",
            "The solution is to add caching",
            "We will use Redis for storage",
            "We are going to deploy tomorrow"
        ]
        
        for phrase in decision_phrases:
            data = ConversationData(
                platform="ChatGPT",
                url="https://chat.openai.com/c/test",
                messages=[Message(role="user", content=phrase)]
            )
            
            nodes_created = percolate_to_neo4j(Path("/tmp/test.md"), data)
            
            # Should create ChatSession + at least one Decision
            assert nodes_created >= 2, f"Failed for phrase: {phrase}"


# ============================================================================
# FastAPI Endpoint Tests
# ============================================================================

class TestFastAPIEndpoints:
    """Test FastAPI application endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client for FastAPI app."""
        return TestClient(app)
    
    def test_root_endpoint(self, client):
        """Test GET / returns service info."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Omega_KG Capture Server"
        assert data["status"] == "running"
        assert data["version"] == "1.0.0"
        assert "capture" in data["endpoints"]
        assert "health" in data["endpoints"]
    
    @patch("omega_kg.capture_server.Path")
    @patch("omega_kg.capture_server.GraphDatabase.driver")
    def test_health_endpoint_all_healthy(self, mock_driver_class, mock_path_class, client):
        """Test GET /health when all systems are operational."""
        # Mock vault existence
        mock_vault_path = MagicMock()
        mock_vault_path.exists.return_value = True
        mock_path_class.return_value = mock_vault_path
        
        # Mock Neo4j connection
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver_class.return_value = mock_driver
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["vault_accessible"] is True
        assert data["neo4j_connected"] is True
        assert "timestamp" in data
    
    @patch("omega_kg.capture_server.Path")
    def test_health_endpoint_vault_missing(self, mock_path_class, client):
        """Test GET /health when vault is not accessible."""
        mock_vault_path = MagicMock()
        mock_vault_path.exists.return_value = False
        mock_path_class.return_value = mock_vault_path
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["vault_accessible"] is False
    
    @patch("omega_kg.capture_server.write_to_obsidian")
    @patch("omega_kg.capture_server.percolate_to_neo4j")
    def test_capture_endpoint_success(self, mock_percolate, mock_write, client):
        """Test POST /capture with valid data."""
        mock_write.return_value = Path("/vault/AI_Conversations/ChatGPT/2024-01-01-abc123.md")
        mock_percolate.return_value = 2
        
        payload = {
            "platform": "ChatGPT",
            "url": "https://chat.openai.com/c/123",
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"}
            ]
        }
        
        response = client.post("/capture", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "ChatGPT" in data["file_path"]
        assert data["nodes_created"] == 2
        assert "2 messages" in data["message"]
    
    def test_capture_endpoint_invalid_data(self, client):
        """Test POST /capture with invalid data."""
        payload = {
            "platform": "ChatGPT",
            # Missing required 'url' and 'messages'
        }
        
        response = client.post("/capture", json=payload)
        
        assert response.status_code == 422  # Validation error
    
    @patch("omega_kg.capture_server.write_to_obsidian")
    def test_capture_endpoint_file_write_error(self, mock_write, client):
        """Test POST /capture handles file write errors."""
        mock_write.side_effect = IOError("Disk full")
        
        payload = {
            "platform": "ChatGPT",
            "url": "https://chat.openai.com/c/123",
            "messages": [{"role": "user", "content": "Test"}]
        }
        
        response = client.post("/capture", json=payload)
        
        assert response.status_code == 500
        assert "Disk full" in response.json()["detail"]
    
    @patch("omega_kg.capture_server.write_to_obsidian")
    @patch("omega_kg.capture_server.percolate_to_neo4j")
    def test_capture_endpoint_neo4j_error(self, mock_percolate, mock_write, client):
        """Test POST /capture handles Neo4j errors."""
        mock_write.return_value = Path("/vault/test.md")
        mock_percolate.side_effect = Exception("Neo4j connection failed")
        
        payload = {
            "platform": "ChatGPT",
            "url": "https://chat.openai.com/c/123",
            "messages": [{"role": "user", "content": "Test"}]
        }
        
        response = client.post("/capture", json=payload)
        
        assert response.status_code == 500
        assert "Neo4j connection failed" in response.json()["detail"]
    
    @patch("omega_kg.capture_server.write_to_obsidian")
    @patch("omega_kg.capture_server.percolate_to_neo4j")
    def test_capture_endpoint_with_optional_fields(self, mock_percolate, mock_write, client):
        """Test POST /capture with optional title and metadata."""
        mock_write.return_value = Path("/vault/test.md")
        mock_percolate.return_value = 1
        
        payload = {
            "platform": "Claude.ai",
            "url": "https://claude.ai/chat/abc",
            "title": "My Custom Title",
            "messages": [{"role": "user", "content": "Test"}],
            "metadata": {"session_id": "xyz", "model": "claude-3"}
        }
        
        response = client.post("/capture", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


# ============================================================================
# Async Function Tests
# ============================================================================

class TestBatchPercolateSessions:
    """Test batch_percolate_sessions async function."""
    
    @pytest.mark.asyncio
    @patch("omega_kg.capture_server.Path")
    async def test_batch_percolate_sessions_missing(self, mock_path_class):
        """Test batch percolation when Sessions folder doesn't exist."""
        mock_sessions_path = MagicMock()
        mock_sessions_path.exists.return_value = False
        
        mock_vault_path = MagicMock()
        mock_vault_path.__truediv__.return_value = mock_sessions_path
        mock_path_class.return_value = mock_vault_path
        
        # Should not raise error
        await batch_percolate_sessions()
    
    @pytest.mark.asyncio
    @patch("omega_kg.capture_server.PercolationEngine")
    @patch("omega_kg.capture_server.GraphDatabase.driver")
    @patch("omega_kg.capture_server.Path")
    async def test_batch_percolate_sessions_success(
        self, mock_path_class, mock_driver_class, mock_engine_class
    ):
        """Test successful batch percolation."""
        # Mock sessions path
        mock_sessions_path = MagicMock()
        mock_sessions_path.exists.return_value = True
        
        mock_vault_path = MagicMock()
        mock_vault_path.__truediv__.return_value = mock_sessions_path
        mock_path_class.return_value = mock_vault_path
        
        # Mock Neo4j driver
        mock_driver = MagicMock()
        mock_driver_class.return_value = mock_driver
        
        # Mock PercolationEngine
        mock_engine = MagicMock()
        mock_engine.percolate_from_vault.return_value = {
            "tasks": 5,
            "commits": 10,
            "links": 3
        }
        mock_engine_class.return_value = mock_engine
        
        await batch_percolate_sessions()
        
        mock_engine.percolate_from_vault.assert_called_once_with(mock_sessions_path)
        mock_driver.close.assert_called_once()


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_hash_with_unicode_characters(self):
        """Test hash generation with Unicode characters."""
        data = ConversationData(
            platform="ChatGPT",
            url="https://chat.openai.com/c/测试",
            messages=[Message(role="user", content="こんにちは")]
        )
        
        hash_result = generate_conversation_hash(data)
        
        assert len(hash_result) == 8
        assert all(c in '0123456789abcdef' for c in hash_result)
    
    def test_markdown_with_very_long_content(self):
        """Test markdown formatting with very long message content."""
        long_content = "A" * 10000
        data = ConversationData(
            platform="ChatGPT",
            url="https://chat.openai.com/c/123",
            messages=[Message(role="user", content=long_content)]
        )
        
        markdown = format_conversation_markdown(data)
        
        assert long_content in markdown
        assert markdown.startswith("---")
    
    def test_markdown_with_special_yaml_characters(self):
        """Test markdown handles YAML special characters in metadata."""
        data = ConversationData(
            platform="ChatGPT",
            url="https://chat.openai.com/c/123",
            messages=[Message(role="user", content="Test")],
            metadata={"key_with_colon": "value:with:colons"}
        )
        
        markdown = format_conversation_markdown(data)
        
        # Should not break YAML parsing
        assert "key_with_colon: value:with:colons" in markdown
    
    @patch("omega_kg.capture_server.settings.obsidian_vault_path", "/read-only-path")
    def test_write_to_obsidian_permission_error(self, tmp_path):
        """Test write handles permission errors gracefully."""
        # This test would require actual permission manipulation
        # which is difficult in a unit test, so we mock the write failure
        with patch("pathlib.Path.write_text") as mock_write:
            mock_write.side_effect = PermissionError("Access denied")
            
            with patch("pathlib.Path.exists", return_value=True):
                with pytest.raises(IOError, match="Failed to write markdown file"):
                    write_to_obsidian(
                        platform="ChatGPT",
                        content="Test",
                        conversation_hash="abc123"
                    )


# ============================================================================
# Integration-style Tests
# ============================================================================

class TestEndToEndCapture:
    """Test end-to-end capture workflow."""
    
    @patch("omega_kg.capture_server.percolate_to_neo4j")
    def test_full_capture_workflow(self, mock_percolate, tmp_path, monkeypatch):
        """Test complete capture workflow from request to file creation."""
        vault_path = tmp_path / "test_vault"
        vault_path.mkdir()
        
        monkeypatch.setattr("omega_kg.capture_server.settings.obsidian_vault_path", str(vault_path))
        mock_percolate.return_value = 2
        
        client = TestClient(app)
        
        payload = {
            "platform": "ChatGPT",
            "url": "https://chat.openai.com/c/integration-test",
            "title": "Integration Test Conversation",
            "messages": [
                {"role": "user", "content": "What is FastAPI?"},
                {"role": "assistant", "content": "FastAPI is a modern web framework."},
                {"role": "user", "content": "Thanks!"}
            ],
            "metadata": {"test": "integration"}
        }
        
        response = client.post("/capture", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # Verify file was created
        created_file = Path(data["file_path"])
        assert created_file.exists()
        
        # Verify file content
        content = created_file.read_text()
        assert "platform: ChatGPT" in content
        assert "What is FastAPI?" in content
        assert "FastAPI is a modern web framework" in content
        assert "title: Integration Test Conversation" in content
        assert "test: integration" in content