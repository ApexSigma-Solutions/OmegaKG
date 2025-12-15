"""Minimal test file to validate pytest execution in VSCode."""
import pytest

def test_basic_assertion():
    """Test to verify pytest execution works."""
    assert True

def test_vscode_test_adapter_fix():
    """Test to validate the fix for unsaved file execution."""
    # This test should pass when run from a saved file
    assert 1 + 1 == 2

if __name__ == "__main__":
    pytest.main([__file__, "-v"])