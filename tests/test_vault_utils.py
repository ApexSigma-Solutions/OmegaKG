# tests/test_vault_utils.py

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, mock_open

from omega_kg.vault_utils import VaultUtils, VaultUtilsError


class TestVaultUtils:
    """Test suite for VaultUtils class."""
    
    @pytest.fixture
    def temp_vault(self):
        """Create a temporary vault directory for testing."""
        temp_dir = tempfile.mkdtemp()
        vault_path = Path(temp_dir) / "test_vault"
        vault_path.mkdir()
        
        # Create some test files
        test_note = vault_path / "test_note.md"
        test_note.write_text("""---
title: Test Note
created: 2025-11-06
tags:
  - test
  - example
---

# Test Note

This is a test note with some content.
""", encoding='utf-8')
        
        # Create a subdirectory with a note
        subdir = vault_path / "subdir"
        subdir.mkdir()
        sub_note = subdir / "sub_note.md"
        sub_note.write_text("""---
title: Sub Note
status: active
---

Content in subdirectory.
""", encoding='utf-8')
        
        # Create a note without frontmatter
        no_frontmatter = vault_path / "no_frontmatter.md"
        no_frontmatter.write_text("Just plain content without frontmatter.", encoding='utf-8')
        
        yield vault_path
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    def test_init_valid_vault(self, temp_vault):
        """Test VaultUtils initialization with valid vault path."""
        vault_utils = VaultUtils(temp_vault)
        assert vault_utils.vault_path == temp_vault.resolve()
    
    def test_init_vault_path_as_string(self, temp_vault):
        """Test VaultUtils initialization with vault path as string."""
        vault_utils = VaultUtils(str(temp_vault))
        assert vault_utils.vault_path == temp_vault.resolve()
    
    def test_init_nonexistent_vault(self):
        """Test VaultUtils initialization with nonexistent vault path."""
        with pytest.raises(VaultUtilsError, match="Vault path does not exist"):
            VaultUtils("/nonexistent/path")
    
    def test_init_vault_is_file(self, temp_vault):
        """Test VaultUtils initialization when vault path is a file."""
        file_path = temp_vault / "test_file.txt"
        file_path.write_text("test")
        
        with pytest.raises(VaultUtilsError, match="Vault path is not a directory"):
            VaultUtils(file_path)
    
    def test_resolve_path_relative(self, temp_vault):
        """Test resolving relative paths."""
        vault_utils = VaultUtils(temp_vault)
        resolved = vault_utils.resolve_path("test_note.md")
        expected = temp_vault / "test_note.md"
        assert resolved == expected.resolve()
    
    def test_resolve_path_relative_subdirectory(self, temp_vault):
        """Test resolving relative paths in subdirectories."""
        vault_utils = VaultUtils(temp_vault)
        resolved = vault_utils.resolve_path("subdir/sub_note.md")
        expected = temp_vault / "subdir" / "sub_note.md"
        assert resolved == expected.resolve()
    
    def test_resolve_path_absolute_within_vault(self, temp_vault):
        """Test resolving absolute paths within vault."""
        vault_utils = VaultUtils(temp_vault)
        absolute_path = temp_vault / "test_note.md"
        resolved = vault_utils.resolve_path(absolute_path)
        assert resolved == absolute_path.resolve()
    
    def test_resolve_path_absolute_outside_vault(self, temp_vault):
        """Test resolving absolute paths outside vault raises error."""
        vault_utils = VaultUtils(temp_vault)
        outside_path = Path("/tmp/outside_note.md")
        
        with pytest.raises(VaultUtilsError, match="Note path is outside vault"):
            vault_utils.resolve_path(outside_path)
    
    def test_resolve_path_path_object(self, temp_vault):
        """Test resolving Path objects."""
        vault_utils = VaultUtils(temp_vault)
        path_obj = Path("test_note.md")
        resolved = vault_utils.resolve_path(path_obj)
        expected = temp_vault / "test_note.md"
        assert resolved == expected.resolve()
    
    def test_read_note_basic(self, temp_vault):
        """Test reading a basic note with frontmatter."""
        vault_utils = VaultUtils(temp_vault)
        metadata, content = vault_utils.read_note("test_note.md")
        
        assert metadata["title"] == "Test Note"
        # frontmatter automatically parses dates, so check the actual value
        assert str(metadata["created"]) == "2025-11-06"
        assert metadata["tags"] == ["test", "example"]
        assert "# Test Note" in content
        assert "This is a test note with some content." in content
    
    def test_read_note_subdirectory(self, temp_vault):
        """Test reading a note from subdirectory."""
        vault_utils = VaultUtils(temp_vault)
        metadata, content = vault_utils.read_note("subdir/sub_note.md")
        
        assert metadata["title"] == "Sub Note"
        assert metadata["status"] == "active"
        assert "Content in subdirectory." in content
    
    def test_read_note_no_frontmatter(self, temp_vault):
        """Test reading a note without frontmatter."""
        vault_utils = VaultUtils(temp_vault)
        metadata, content = vault_utils.read_note("no_frontmatter.md")
        
        assert metadata == {}
        assert content == "Just plain content without frontmatter."
    
    def test_read_note_path_object(self, temp_vault):
        """Test reading note with Path object."""
        vault_utils = VaultUtils(temp_vault)
        path_obj = Path("test_note.md")
        metadata, content = vault_utils.read_note(path_obj)
        
        assert metadata["title"] == "Test Note"
        assert "# Test Note" in content
    
    def test_read_note_absolute_path(self, temp_vault):
        """Test reading note with absolute path."""
        vault_utils = VaultUtils(temp_vault)
        absolute_path = temp_vault / "test_note.md"
        metadata, content = vault_utils.read_note(absolute_path)
        
        assert metadata["title"] == "Test Note"
        assert "# Test Note" in content
    
    def test_read_note_file_not_found(self, temp_vault):
        """Test reading nonexistent note raises FileNotFoundError."""
        vault_utils = VaultUtils(temp_vault)
        
        with pytest.raises(FileNotFoundError, match="Note file does not exist"):
            vault_utils.read_note("nonexistent.md")
    
    def test_read_note_path_is_directory(self, temp_vault):
        """Test reading directory path raises VaultUtilsError."""
        vault_utils = VaultUtils(temp_vault)
        
        with pytest.raises(VaultUtilsError, match="Path is not a file"):
            vault_utils.read_note("subdir")
    
    def test_read_note_outside_vault(self, temp_vault):
        """Test reading note outside vault raises VaultUtilsError."""
        vault_utils = VaultUtils(temp_vault)
        outside_path = Path("/tmp/outside_note.md")
        
        with pytest.raises(VaultUtilsError, match="Note path is outside vault"):
            vault_utils.read_note(outside_path)
    
    @patch("builtins.open", side_effect=OSError("Permission denied"))
    def test_read_note_permission_error(self, mock_open, temp_vault):
        """Test reading note with permission error."""
        vault_utils = VaultUtils(temp_vault)
        
        with pytest.raises(VaultUtilsError, match="Failed to read note file"):
            vault_utils.read_note("test_note.md")
    
    @patch("frontmatter.load", side_effect=Exception("Parsing error"))
    def test_read_note_parsing_error(self, mock_load, temp_vault):
        """Test reading note with parsing error."""
        vault_utils = VaultUtils(temp_vault)
        
        with pytest.raises(VaultUtilsError, match="Unexpected error reading note"):
            vault_utils.read_note("test_note.md")
    
    def test_read_note_empty_file(self, temp_vault):
        """Test reading empty file."""
        vault_utils = VaultUtils(temp_vault)
        empty_file = temp_vault / "empty.md"
        empty_file.write_text("", encoding='utf-8')
        
        metadata, content = vault_utils.read_note("empty.md")
        assert metadata == {}
        assert content == ""
    
    def test_read_note_only_frontmatter(self, temp_vault):
        """Test reading file with only frontmatter."""
        vault_utils = VaultUtils(temp_vault)
        frontmatter_only = temp_vault / "frontmatter_only.md"
        frontmatter_only.write_text("""---
title: Only Frontmatter
status: test
---""", encoding='utf-8')
        
        metadata, content = vault_utils.read_note("frontmatter_only.md")
        assert metadata["title"] == "Only Frontmatter"
        assert metadata["status"] == "test"
        assert content == ""
    
    def test_read_note_unicode_content(self, temp_vault):
        """Test reading file with unicode content."""
        vault_utils = VaultUtils(temp_vault)
        unicode_file = temp_vault / "unicode.md"
        unicode_file.write_text("""---
title: Unicode Test
emoji: 🚀
---

# Unicode Content

This has unicode: 🌟 ñáéíóú 中文 русский
""", encoding='utf-8')
        
        metadata, content = vault_utils.read_note("unicode.md")
        assert metadata["title"] == "Unicode Test"
        assert metadata["emoji"] == "🚀"
        assert "🌟 ñáéíóú 中文 русский" in content