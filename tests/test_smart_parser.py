# tests/test_smart_parser.py

import pytest
import tempfile
import frontmatter
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from omega_kg.smart_parser import (
    parse_and_create_task,
    _extract_task_data,
    validate_linear_config,
    TaskParsingError,
    LinearAPIError
)


class TestSmartParser:
    """Test suite for smart_parser module."""

    def test_extract_task_data_basic(self):
        """Test basic task data extraction from frontmatter."""
        content = """---
title: Test Task
priority: high
tags: [bug, urgent]
---

This is a test task description.
"""
        post = frontmatter.loads(content)
        task_data = _extract_task_data(post)
        
        assert task_data['title'] == 'Test Task'
        assert task_data['description'] == 'This is a test task description.'
        assert task_data['priority'] == 2  # high priority maps to 2
        assert task_data['labels'] == ['bug', 'urgent']

    def test_extract_task_data_minimal(self):
        """Test task data extraction with minimal frontmatter."""
        content = """---
uid: TASK-001
---

Minimal task content.
"""
        post = frontmatter.loads(content)
        task_data = _extract_task_data(post)
        
        assert task_data['title'] == 'TASK-001'
        assert task_data['description'] == 'Minimal task content.'
        assert task_data['priority'] == 0  # default priority
        assert task_data['labels'] == []

    def test_extract_task_data_no_title(self):
        """Test task data extraction when no title is provided."""
        content = """---
priority: low
---

Task without title.
"""
        post = frontmatter.loads(content)
        task_data = _extract_task_data(post)
        
        assert task_data['title'] == 'Untitled Task'
        assert task_data['priority'] == 4  # low priority maps to 4

    @patch('omega_kg.settings.get_settings')
    def test_validate_linear_config_valid(self, mock_get_settings):
        """Test Linear configuration validation with valid settings."""
        mock_settings = MagicMock()
        mock_settings.linear_api_key = "test-api-key"
        mock_settings.linear_team_id = "test-team-id"
        mock_get_settings.return_value = mock_settings
        
        assert validate_linear_config() is True

    @patch('omega_kg.settings.get_settings')
    def test_validate_linear_config_invalid(self, mock_get_settings):
        """Test Linear configuration validation with missing settings."""
        mock_settings = MagicMock()
        mock_settings.linear_api_key = None
        mock_settings.linear_team_id = "test-team-id"
        mock_get_settings.return_value = mock_settings
        
        assert validate_linear_config() is False

    @pytest.mark.asyncio
    async def test_parse_and_create_task_file_not_found(self):
        """Test parse_and_create_task with non-existent file."""
        non_existent_path = Path("/non/existent/file.md")
        
        with pytest.raises(TaskParsingError, match="Task file not found"):
            await parse_and_create_task(non_existent_path)

    @pytest.mark.asyncio
    async def test_parse_and_create_task_already_has_linear_id(self):
        """Test parse_and_create_task with task that already has Linear ID."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            content = """---
title: Test Task
linear_id: TEST-123
---

Task content.
"""
            f.write(content)
            f.flush()
            
            task_path = Path(f.name)
            
            try:
                result = await parse_and_create_task(task_path)
                
                assert result['success'] is True
                assert result['skipped'] is True
                assert result['linear_id'] == 'TEST-123'
                assert 'already has Linear issue' in result['message']
            finally:
                task_path.unlink()

    @pytest.mark.asyncio
    async def test_parse_and_create_task_pending_status(self):
        """Test parse_and_create_task with task that has pending status."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            content = """---
title: Test Task
linear_status: pending
---

Task content.
"""
            f.write(content)
            f.flush()
            
            task_path = Path(f.name)
            
            try:
                result = await parse_and_create_task(task_path)
                
                assert result['success'] is False
                assert result['skipped'] is True
                assert 'already being processed' in result['message']
            finally:
                task_path.unlink()

    @pytest.mark.asyncio
    @patch('omega_kg.smart_parser._create_linear_issue')
    async def test_parse_and_create_task_success(self, mock_create_issue):
        """Test successful task creation with Linear API."""
        
        # Mock Linear API response
        mock_linear_issue = {
            'identifier': 'TEST-456',
            'url': 'https://linear.app/test/issue/TEST-456',
            'state': {'name': 'Backlog'}
        }
        mock_create_issue.return_value = mock_linear_issue
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            content = """---
title: New Test Task
priority: medium
---

This is a new task to be created in Linear.
"""
            f.write(content)
            f.flush()
            
            task_path = Path(f.name)
            
            try:
                result = await parse_and_create_task(task_path)
                
                assert result['success'] is True
                assert result['linear_id'] == 'TEST-456'
                assert result['linear_url'] == 'https://linear.app/test/issue/TEST-456'
                
                # Verify the file was updated
                with open(task_path, 'r') as updated_file:
                    updated_post = frontmatter.load(updated_file)
                    assert updated_post.metadata['linear_id'] == 'TEST-456'
                    assert updated_post.metadata['linear_url'] == 'https://linear.app/test/issue/TEST-456'
                    assert updated_post.metadata['linear_status'] == 'Backlog'
                    
            finally:
                task_path.unlink()

    @pytest.mark.asyncio
    @patch('omega_kg.smart_parser._create_linear_issue')
    async def test_parse_and_create_task_api_failure_cleanup(self, mock_create_issue):
        """Test that pending status is cleaned up when Linear API fails."""
        
        # Mock Linear API failure
        mock_create_issue.side_effect = LinearAPIError("API failed")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            content = """---
title: Test Task
---

Task content.
"""
            f.write(content)
            f.flush()
            
            task_path = Path(f.name)
            
            try:
                with pytest.raises(LinearAPIError):
                    await parse_and_create_task(task_path)
                
                # Verify pending status was cleaned up
                with open(task_path, 'r') as updated_file:
                    updated_post = frontmatter.load(updated_file)
                    assert updated_post.metadata.get('linear_status') != 'pending'
                    
            finally:
                task_path.unlink()

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    @patch('omega_kg.settings.get_settings')
    async def test_create_linear_issue_success(self, mock_get_settings, mock_client):
        """Test successful Linear issue creation via API."""
        # Mock settings
        mock_settings = MagicMock()
        mock_settings.linear_api_key = "test-api-key"
        mock_settings.linear_team_id = "test-team-id"
        mock_settings.linear_project_id = None
        mock_get_settings.return_value = mock_settings
        
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "issueCreate": {
                    "success": True,
                    "issue": {
                        "id": "issue-id",
                        "identifier": "TEST-789",
                        "title": "Test Issue",
                        "description": "Test description",
                        "url": "https://linear.app/test/issue/TEST-789",
                        "state": {"id": "state-id", "name": "Backlog"},
                        "priority": 2,
                        "createdAt": "2023-01-01T00:00:00Z",
                        "updatedAt": "2023-01-01T00:00:00Z"
                    }
                }
            }
        }
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        from omega_kg.smart_parser import _create_linear_issue
        
        task_data = {
            'title': 'Test Issue',
            'description': 'Test description',
            'priority': 2,
            'labels': []
        }
        
        result = await _create_linear_issue(task_data)
        
        assert result['identifier'] == 'TEST-789'
        assert result['title'] == 'Test Issue'
        assert result['url'] == 'https://linear.app/test/issue/TEST-789'

    @pytest.mark.asyncio
    @patch('omega_kg.settings.get_settings')
    async def test_create_linear_issue_no_api_key(self, mock_get_settings):
        """Test Linear issue creation without API key."""
        mock_settings = MagicMock()
        mock_settings.linear_api_key = None
        mock_get_settings.return_value = mock_settings
        
        from omega_kg.smart_parser import _create_linear_issue
        
        task_data = {'title': 'Test', 'description': 'Test', 'priority': 0, 'labels': []}
        
        with pytest.raises(LinearAPIError, match="Linear API key not configured"):
            await _create_linear_issue(task_data)

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    @patch('omega_kg.settings.get_settings')
    async def test_create_linear_issue_api_error(self, mock_get_settings, mock_client):
        """Test Linear issue creation with API error response."""
        # Mock settings
        mock_settings = MagicMock()
        mock_settings.linear_api_key = "test-api-key"
        mock_settings.linear_team_id = "test-team-id"
        mock_get_settings.return_value = mock_settings
        
        # Mock HTTP error response
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        from omega_kg.smart_parser import _create_linear_issue
        
        task_data = {'title': 'Test', 'description': 'Test', 'priority': 0, 'labels': []}
        
        with pytest.raises(LinearAPIError, match="Linear API returned status 400"):
            await _create_linear_issue(task_data)