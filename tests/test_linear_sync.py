import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from omega_kg.linear_client import LinearClient
from omega_kg.smart_parser import SmartParser

# --- FIXTURES ---

@pytest.fixture
def mock_settings():
    with patch("omega_kg.linear_client.settings") as mock:
        mock.linear_api_key = "test_api_key"
        yield mock

@pytest.fixture
def mock_parser_settings():
    with patch("omega_kg.smart_parser.settings") as mock:
        mock.linear_team_id = "team_123"
        mock.linear_user_map_json = '{"test_user": "user_123"}'
        mock.linear_label_map_json = '{"TestLabel": "label_123"}'
        mock.linear_status_map_json = '{"in-progress": "state_123"}'
        yield mock

@pytest.fixture
def mock_httpx():
    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def mock_vault():
    with patch("omega_kg.smart_parser.VaultUtils") as mock:
        yield mock.return_value

# --- LINEAR CLIENT TESTS ---

@pytest.mark.asyncio
async def test_create_issue(mock_settings, mock_httpx):
    client = LinearClient()
    
    # Mock response - need to mock the response object properly
    mock_response = AsyncMock()
    mock_response.json = AsyncMock(return_value={
        "data": {
            "issueCreate": {
                "success": True,
                "issue": {
                    "id": "issue_123",
                    "identifier": "APX-1",
                    "title": "Test Issue",
                    "url": "https://linear.app/issue/APX-1"
                }
            }
        }
    })
    mock_response.raise_for_status = MagicMock()
    mock_httpx.post = AsyncMock(return_value=mock_response)
    
    result = await client.create_issue(
        title="Test Issue",
        description="Desc",
        team_id="team_123",
        priority=1
    )
    
    assert result["id"] == "issue_123"
    assert result["identifier"] == "APX-1"
    
    # Verify payload
    call_args = mock_httpx.post.call_args
    assert call_args is not None
    payload = call_args.kwargs["json"]
    assert payload["variables"]["input"]["title"] == "Test Issue"
    assert payload["variables"]["input"]["teamId"] == "team_123"

@pytest.mark.asyncio
async def test_update_issue(mock_settings, mock_httpx):
    client = LinearClient()
    
    mock_response = AsyncMock()
    mock_response.json = AsyncMock(return_value={
        "data": {
            "issueUpdate": {
                "success": True,
                "issue": {
                    "id": "issue_123",
                    "identifier": "APX-1",
                    "title": "Updated Title"
                }
            }
        }
    })
    mock_response.raise_for_status = MagicMock()
    mock_httpx.post = AsyncMock(return_value=mock_response)
    
    result = await client.update_issue("issue_123", {"title": "Updated Title"})
    
    assert result["title"] == "Updated Title"
    
    payload = mock_httpx.post.call_args.kwargs["json"]
    assert payload["variables"]["id"] == "issue_123"
    assert payload["variables"]["input"]["title"] == "Updated Title"


# --- SMART PARSER TESTS ---

@pytest.mark.asyncio
async def test_sync_note_create(mock_parser_settings, mock_vault):
    # Mock LinearClient within SmartParser
    with patch("omega_kg.smart_parser.linear_client") as mock_client:
        mock_client.create_issue = AsyncMock(return_value={
            "id": "issue_123",
            "identifier": "APX-1",
            "url": "http://url"
        })
        
        parser = SmartParser()
        
        # Mock Vault interactions
        mock_vault.read_note_frontmatter.return_value = {"status": "In Progress"}
        mock_vault._resolve_path.return_value.is_file.return_value = True
        
        # Mock file content
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = """---
status: In Progress
---
# New Task
Description here.
@assignee/test_user
@label/TestLabel
@priority/1
"""
        # We need to mock frontmatter.load to return content
        with patch("omega_kg.smart_parser.frontmatter.load") as mock_fm:
            mock_fm.return_value.content = """# New Task
Description here.
@assignee/test_user
@label/TestLabel
@priority/1
"""
            mock_fm.return_value.metadata = {"status": "In Progress"}
            
            mock_vault._resolve_path.return_value.open.return_value = mock_file
            
            # Run Sync
            result = await parser.sync_note_to_linear("Tasks/NewTask.md")
            
            assert result["identifier"] == "APX-1"
            
            # Verify Create Call
            mock_client.create_issue.assert_called_once()
            args = mock_client.create_issue.call_args.kwargs
            assert args["title"] == "New Task"
            assert args["assignee_id"] == "user_123"
            assert "label_123" in args["label_ids"]
            assert args["priority"] == 1
            assert args["state_id"] == "state_123"
            
            # Verify Write Back
            mock_vault.update_note_frontmatter.assert_called_once()
            updates = mock_vault.update_note_frontmatter.call_args[0][1]
            assert updates["linear_id"] == "issue_123"

@pytest.mark.asyncio
async def test_sync_note_update(mock_parser_settings, mock_vault):
    with patch("omega_kg.smart_parser.linear_client") as mock_client:
        mock_client.update_issue = AsyncMock(return_value={
            "id": "issue_123",
            "identifier": "APX-1"
        })
        
        parser = SmartParser()
        
        # Existing ID in frontmatter
        mock_vault.read_note_frontmatter.return_value = {
            "linear_id": "issue_123",
            "status": "In Progress"
        }
        mock_vault._resolve_path.return_value.is_file.return_value = True
        
        mock_file = MagicMock()
        with patch("omega_kg.smart_parser.frontmatter.load") as mock_fm:
            mock_fm.return_value.content = "# Updated Task"
            mock_fm.return_value.metadata = {"linear_id": "issue_123"}
            mock_vault._resolve_path.return_value.open.return_value = mock_file
            
            # Run Sync
            result = await parser.sync_note_to_linear("Tasks/ExistingTask.md")
            
            assert result["identifier"] == "APX-1"
            
            # Verify Update Call
            mock_client.update_issue.assert_called_once()
            call_args = mock_client.update_issue.call_args
            assert call_args[0][0] == "issue_123"
            assert call_args[0][1]["title"] == "Updated Task"
