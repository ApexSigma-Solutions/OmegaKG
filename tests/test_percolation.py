"""
Unit tests for percolation.py
"""

from unittest.mock import Mock, patch
from pathlib import Path
from omega_kg.percolation import PercolationEngine, create_percolation_engine


class TestPercolationEngine:
    """Test suite for PercolationEngine functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_driver = Mock()
        # Make session a context manager
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        self.mock_driver.session.return_value = mock_session
        self.engine = PercolationEngine(self.mock_driver)

    def test_initialization(self):
        """Test PercolationEngine initialization."""
        assert self.engine.driver == self.mock_driver

    @patch("omega_kg.percolation.Path")
    def test_percolate_from_vault(self, mock_path_class):
        """Test percolating from a vault with multiple files."""
        # Mock Path and file operations
        mock_vault_path = Mock(spec=Path)
        mock_file1 = Mock(spec=Path)
        mock_file1.read_text.return_value = """
---
date: 2023-01-01
---

# Task
[[PROJ-001]]

#### Git Commit [repo1]: `abc123`
**Linear:** [[PROJ-001]]
**Message:**
```
commit message
```

## Decision
This is a decision
"""
        mock_file2 = Mock(spec=Path)
        mock_file2.read_text.return_value = """
---
date: 2023-01-02
---

# Another Task
[[PROJ-002]]
"""
        mock_vault_path.rglob.return_value = [mock_file1, mock_file2]

        # Mock session
        mock_session = Mock()
        self.mock_driver.session.return_value = mock_session

        # Mock the percolation methods
        with (
            patch.object(self.engine, "_extract_frontmatter") as mock_extract,
            patch.object(self.engine, "_percolate_task") as mock_task,
            patch.object(self.engine, "_percolate_commits") as mock_commits,
            patch.object(self.engine, "_percolate_session") as mock_session_percolate,
        ):

            mock_extract.side_effect = [
                {"date": "2023-01-01", "decision_id": "DEC-001"},
                {"date": "2023-01-02"},
            ]
            mock_task.side_effect = [1, 1]  # One task each
            mock_commits.side_effect = [1, 0]  # One commit from first file
            mock_session_percolate.side_effect = [1, 0]  # One session link

            result = self.engine.percolate_from_vault(mock_vault_path)

            expected = {"tasks": 2, "commits": 1, "links": 1}
            assert result == expected

    def test_extract_frontmatter_valid(self):
        """Test extracting valid frontmatter."""
        content = """---
date: 2023-01-01
title: Test Note
---

# Content
Some content here.
"""

        result = self.engine._extract_frontmatter(content)
        expected = {"date": "2023-01-01", "title": "Test Note"}
        assert result == expected

    def test_extract_frontmatter_no_frontmatter(self):
        """Test extracting from content without frontmatter."""
        content = "# Just content\nNo frontmatter here."

        result = self.engine._extract_frontmatter(content)
        assert result is None

    def test_extract_frontmatter_malformed(self):
        """Test extracting from malformed frontmatter."""
        content = "---\ninvalid: yaml: content:\n---\nContent"

        result = self.engine._extract_frontmatter(content)
        # The method parses what it can, so it returns the parsed dict
        assert result == {"invalid": "yaml: content:"}

    @patch("omega_kg.percolation.datetime")
    def test_percolate_task(self, mock_datetime):
        """Test percolating tasks from content."""
        mock_datetime.now.return_value.isoformat.return_value = "2023-01-01T00:00:00"

        mock_file = Mock(spec=Path)
        metadata = {"date": "2023-01-01"}
        content = "Some content [[PROJ-001]] and [[PROJ-002]]"

        result = self.engine._percolate_task(mock_file, metadata, content)

        assert result == 2  # Two tasks found
        # Verify session.run was called for each task
        session_calls = self.mock_driver.session.return_value.run.call_count
        assert session_calls == 2

    @patch("omega_kg.percolation.datetime")
    def test_percolate_commits(self, mock_datetime):
        """Test percolating commits from content."""
        mock_datetime.now.return_value.isoformat.return_value = "2023-01-01T00:00:00"

        mock_file = Mock(spec=Path)
        metadata = {}
        content = """#### Git Commit [myrepo]: `abc123`
**Linear:** [[PROJ-001]]
**Message:**
```
Initial commit
```
"""

        result = self.engine._percolate_commits(mock_file, metadata, content)

        assert result == 1  # One commit found
        # Verify session.run was called for commit and relationship
        session_calls = self.mock_driver.session.return_value.run.call_count
        assert session_calls == 2

    def test_percolate_session(self):
        """Test percolating session data."""
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        self.mock_driver.session.return_value = mock_session

        mock_file = Mock(spec=Path)
        metadata = {"date": "2023-01-01", "topic": "Test Session"}
        content = """
## Decision

This is a test decision about the project.
"""

        with patch.object(self.engine, "_generate_decision_id") as mock_gen_id:
            mock_gen_id.return_value = "DEC-001"

            result = self.engine._percolate_session(mock_file, metadata, content)

            assert result == 1  # One decision link created
            assert (
                mock_session.run.call_count == 3
            )  # MERGE session + MERGE decision + MERGE relationship

    def test_generate_decision_id(self):
        """Test generating decision IDs."""
        content = "This is a test decision content for hashing"
        result = self.engine._generate_decision_id(content)

        # Should return a string in format DEC-XXXX
        assert result.startswith("DEC-")
        assert len(result) == 8  # DEC- + 4 digits

        # Same content should generate same ID
        result2 = self.engine._generate_decision_id(content)
        assert result == result2

    def test_detect_stale_tasks(self):
        """Test detecting stale tasks."""
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        self.mock_driver.session.return_value = mock_session

        # Mock query results
        mock_records = [
            Mock(
                __getitem__=lambda self, key: {
                    "t.uid": "TASK-001",
                    "t.title": "Stale Task",
                    "t.status": "active",
                    "t.created": "2023-01-01",
                }.get(key)
            )
        ]
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter(mock_records))
        mock_session.run.return_value = mock_result

        result = self.engine.detect_stale_tasks(days_threshold=30)

        assert len(result) == 1
        assert result[0]["uid"] == "TASK-001"
        assert result[0]["title"] == "Stale Task"
        assert result[0]["status"] == "active"

    @patch("omega_kg.percolation.GraphDatabase")
    def test_create_percolation_engine(self, mock_graph_db):
        """Test the factory function."""
        mock_driver = Mock()
        mock_graph_db.driver.return_value = mock_driver

        result = create_percolation_engine("uri", "user", "pass")

        assert isinstance(result, PercolationEngine)
        assert result.driver == mock_driver
        mock_graph_db.driver.assert_called_once_with("uri", auth=("user", "pass"))
