# tests/test_refactored_functionality.py

import pytest
import tempfile
import asyncio
import time
import threading
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock, call
import frontmatter
from concurrent.futures import ThreadPoolExecutor, as_completed

from omega_kg.smart_parser import parse_and_create_task, TaskParsingError
from omega_kg.vault_utils import VaultUtils


class TestRefactoredFunctionality:
    """Comprehensive tests for refactored smart_parser functionality."""

    @pytest.fixture
    def temp_vault(self):
        """Create a temporary vault for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            vault_path = Path(temp_dir)
            yield vault_path

    @pytest.fixture
    def sample_task_note(self, temp_vault):
        """Create a sample task note for testing."""
        note_path = temp_vault / "test_task.md"
        content = """---
title: Test Task for Race Condition
uid: TEST-RACE-001
status: to-do
priority: high
tags: [test, race-condition]
---

This is a test task to verify race condition prevention.
The parser should not create duplicate Linear issues when run concurrently.
"""
        note_path.write_text(content)
        return note_path

    @pytest.fixture
    def multiple_task_notes(self, temp_vault):
        """Create multiple task notes for performance testing."""
        notes = []
        for i in range(10):
            note_path = temp_vault / f"task_{i:03d}.md"
            content = f"""---
title: Performance Test Task {i}
uid: PERF-TEST-{i:03d}
status: to-do
priority: medium
tags: [performance, test]
---

This is performance test task number {i}.
Used to measure file I/O improvements.
"""
            note_path.write_text(content)
            notes.append(note_path)
        return notes

    @pytest.mark.asyncio
    async def test_race_condition_prevention(self, sample_task_note, temp_vault):
        """Test that multiple concurrent runs don't create duplicate Linear issues."""
        
        # Mock the Linear API to track calls
        created_issues = []
        
        async def mock_create_issue(*args, **kwargs):
            # Simulate API delay
            await asyncio.sleep(0.1)
            issue_id = f"TEST-{len(created_issues) + 1}"
            created_issues.append(issue_id)
            return {
                "id": issue_id, 
                "identifier": f"TST-{len(created_issues)}",
                "url": f"https://linear.app/test/issue/TST-{len(created_issues)}",
                "state": {"name": "Todo"}
            }
        
        with patch('omega_kg.smart_parser._create_linear_issue', side_effect=mock_create_issue):
            with patch('omega_kg.smart_parser.validate_linear_config', return_value=True):
                
                # Run parser concurrently multiple times on the same note
                tasks = []
                for i in range(5):
                    task = asyncio.create_task(
                        parse_and_create_task(sample_task_note)
                    )
                    tasks.append(task)
                
                # Wait for all tasks to complete
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Verify only one Linear issue was created
                assert len(created_issues) == 1, f"Expected 1 issue, got {len(created_issues)}: {created_issues}"
                
                # Verify that subsequent calls returned early (already has linear_id)
                successful_results = [r for r in results if not isinstance(r, Exception)]
                assert len(successful_results) >= 1, "At least one call should succeed"

    def test_performance_file_io_reduction(self, multiple_task_notes, temp_vault):
        """Test that file reading is reduced with VaultUtils integration."""
        
        # Track file read operations only for our test files
        read_operations = []
        original_read_text = Path.read_text
        
        def track_read_text(self, *args, **kwargs):
            # Only track reads of our test files
            if str(self).startswith(str(temp_vault)):
                read_operations.append(str(self))
            return original_read_text(self, *args, **kwargs)
        
        with patch.object(Path, 'read_text', track_read_text):
            # Process multiple notes
            for note_path in multiple_task_notes[:3]:  # Test with 3 notes
                try:
                    # Mock Linear API to avoid actual API calls
                    with patch('omega_kg.smart_parser.validate_linear_config', return_value=False):
                        asyncio.run(parse_and_create_task(note_path))
                except Exception:
                    # Expected since we're not actually creating Linear issues
                    pass
        
        # With VaultUtils integration, each note should be read efficiently
        # Each note might be read once for parsing and once for cleanup
        unique_reads = set(read_operations)
        
        # Verify efficient file reading - should be reasonable number of reads
        assert len(read_operations) <= len(multiple_task_notes[:3]) * 3, \
            f"Too many file reads: {len(read_operations)} operations for {len(multiple_task_notes[:3])} notes"
        
        print(f"File read operations: {len(read_operations)}")
        print(f"Unique files read: {len(unique_reads)}")
        print(f"Read operations: {read_operations}")

    @pytest.mark.asyncio
    async def test_functionality_preservation(self, sample_task_note, temp_vault):
        """Test that all existing features work correctly after refactoring."""
        
        mock_issue = {
            "id": "test-issue-id",
            "identifier": "test-issue-id",
            "title": "Test Task for Race Condition",
            "url": "https://linear.app/test/issue/test-issue-id",
            "state": {"name": "Todo"}
        }
        
        with patch('omega_kg.smart_parser._create_linear_issue', return_value=mock_issue):
            with patch('omega_kg.smart_parser.validate_linear_config', return_value=True):
                
                # Test successful task creation
                result = await parse_and_create_task(sample_task_note)
                
                assert result is not None
                assert result["success"] is True
                assert "linear_id" in result
                
                # Verify frontmatter was updated
                updated_content = sample_task_note.read_text()
                post = frontmatter.loads(updated_content)
                
                assert post.metadata.get("linear_id") == "test-issue-id"
                assert post.metadata.get("linear_url") == "https://linear.app/test/issue/test-issue-id"
                assert post.metadata.get("linear_status") == "Todo"

    @pytest.mark.asyncio
    async def test_error_handling_and_cleanup(self, sample_task_note, temp_vault):
        """Test proper cleanup on failures and error paths."""
        
        # Test API failure scenario
        with patch('omega_kg.smart_parser._create_linear_issue', side_effect=Exception("API Error")):
            with patch('omega_kg.smart_parser.validate_linear_config', return_value=True):
                
                # Store original content
                original_content = sample_task_note.read_text()
                
                # Attempt to create task (should fail)
                with pytest.raises(TaskParsingError) as exc_info:
                    await parse_and_create_task(sample_task_note)
                
                # Verify the error message contains the original error
                assert "API Error" in str(exc_info.value)
                
                # Verify file wasn't corrupted (cleanup occurred)
                current_content = sample_task_note.read_text()
                
                # File should either be unchanged or properly cleaned up
                post = frontmatter.loads(current_content)
                
                # Should not have partial Linear data
                assert post.metadata.get("linear_id") is None or post.metadata.get("linear_id") == ""
                assert post.metadata.get("status") != "pending" or post.metadata.get("status") == "to-do"

    @pytest.mark.asyncio
    async def test_integration_end_to_end(self, temp_vault):
        """Test complete workflow from note parsing to Linear issue creation."""
        
        # Create a comprehensive test note
        note_path = temp_vault / "integration_test.md"
        content = """---
title: Integration Test Task
uid: INT-TEST-001
status: to-do
priority: high
tags: [integration, test, e2e]
assignee: test-user
due_date: 2025-12-01
---

# Integration Test Task

This is a comprehensive integration test to verify the complete workflow:

1. Note parsing and validation
2. Task data extraction
3. Linear issue creation
4. Frontmatter updates
5. Error handling

## Acceptance Criteria

- [ ] All components work together
- [ ] Data flows correctly through the pipeline
- [ ] Proper error handling at each stage
"""
        note_path.write_text(content)
        
        # Mock Linear API response
        mock_issue = {
            "id": "integration-test-id",
            "identifier": "integration-test-id",
            "title": "Integration Test Task",
            "url": "https://linear.app/test/issue/integration-test-id",
            "state": {"name": "Todo"}
        }
        
        with patch('omega_kg.smart_parser._create_linear_issue', return_value=mock_issue):
            with patch('omega_kg.smart_parser.validate_linear_config', return_value=True):
                
                # Execute complete workflow
                result = await parse_and_create_task(note_path)
                
                # Verify successful completion
                assert result["success"] is True
                assert result["linear_id"] == "integration-test-id"
                
                # Verify frontmatter updates
                updated_content = note_path.read_text()
                post = frontmatter.loads(updated_content)
                
                expected_updates = {
                    "linear_id": "integration-test-id",
                    "linear_url": "https://linear.app/test/issue/integration-test-id",
                    "linear_status": "Todo"
                }
                
                for key, expected_value in expected_updates.items():
                    assert post.metadata.get(key) == expected_value, \
                        f"Expected {key}={expected_value}, got {post.metadata.get(key)}"
                
                # Verify content preservation
                assert "Integration Test Task" in post.content
                assert "Acceptance Criteria" in post.content

    def test_vault_utils_integration(self, temp_vault):
        """Test VaultUtils integration and proper usage."""
        
        # Create test note
        note_path = temp_vault / "vault_utils_test.md"
        content = """---
title: VaultUtils Test
uid: VU-TEST-001
---

Testing VaultUtils integration.
"""
        note_path.write_text(content)
        
        # Test VaultUtils functionality
        vault_utils = VaultUtils(temp_vault)
        
        # Test read_note method
        frontmatter_data, content_data = vault_utils.read_note("vault_utils_test.md")
        
        assert frontmatter_data["title"] == "VaultUtils Test"
        assert frontmatter_data["uid"] == "VU-TEST-001"
        assert "Testing VaultUtils integration" in content_data
        
        # Test resolve_path method
        resolved_path = vault_utils.resolve_path("vault_utils_test.md")
        assert resolved_path == temp_vault / "vault_utils_test.md"
        assert resolved_path.exists()

    @pytest.mark.asyncio
    async def test_concurrent_different_notes(self, multiple_task_notes, temp_vault):
        """Test concurrent processing of different notes (should work fine)."""
        
        created_issues = []
        
        async def mock_create_issue(*args, **kwargs):
            await asyncio.sleep(0.05)  # Simulate API delay
            issue_id = f"CONCURRENT-{len(created_issues) + 1}"
            created_issues.append(issue_id)
            return {
                "id": issue_id, 
                "identifier": f"CON-{len(created_issues)}",
                "url": f"https://linear.app/test/issue/CON-{len(created_issues)}",
                "state": {"name": "Todo"}
            }
        
        with patch('omega_kg.smart_parser._create_linear_issue', side_effect=mock_create_issue):
            with patch('omega_kg.smart_parser.validate_linear_config', return_value=True):
                
                # Process different notes concurrently
                tasks = []
                for note_path in multiple_task_notes[:3]:  # Test with 3 notes
                    task = asyncio.create_task(
                        parse_and_create_task(note_path)
                    )
                    tasks.append(task)
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # All should succeed since they're different notes
                successful_results = [r for r in results if not isinstance(r, Exception) and r.get("success")]
                assert len(successful_results) == 3, f"Expected 3 successes, got {len(successful_results)}"
                
                # Should have created 3 different issues
                assert len(created_issues) == 3, f"Expected 3 issues, got {len(created_issues)}"