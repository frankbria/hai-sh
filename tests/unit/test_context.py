"""
Tests for context collection functionality.
"""

import os
import stat
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from hai_sh.context import format_cwd_context, get_cwd_context, get_directory_info


@pytest.mark.unit
def test_get_cwd_context_basic():
    """Test basic CWD context collection."""
    context = get_cwd_context()

    assert "cwd" in context
    assert "exists" in context
    assert "readable" in context
    assert "writable" in context
    assert "size" in context
    assert "error" in context

    # CWD should exist and be readable
    assert context["cwd"] is not None
    assert context["exists"] is True
    assert context["readable"] is True


@pytest.mark.unit
def test_get_cwd_context_returns_absolute_path():
    """Test that CWD context returns absolute path."""
    context = get_cwd_context()

    assert context["cwd"] is not None
    assert Path(context["cwd"]).is_absolute()


@pytest.mark.unit
def test_get_cwd_context_directory_size():
    """Test that directory size is counted."""
    context = get_cwd_context()

    if context["readable"]:
        assert isinstance(context["size"], int)
        assert context["size"] >= 0


@pytest.mark.unit
def test_get_cwd_context_writable(tmp_path, monkeypatch):
    """Test CWD context in writable directory."""
    # Change to tmp directory which should be writable
    monkeypatch.chdir(tmp_path)

    context = get_cwd_context()

    assert context["cwd"] == str(tmp_path)
    assert context["exists"] is True
    assert context["readable"] is True
    assert context["writable"] is True
    assert context["error"] is None


@pytest.mark.unit
def test_get_cwd_context_permission_error(monkeypatch):
    """Test CWD context when directory is not readable."""
    # Mock os.listdir to raise PermissionError
    def mock_listdir(path):
        raise PermissionError("Permission denied")

    monkeypatch.setattr("os.listdir", mock_listdir)

    context = get_cwd_context()

    assert context["readable"] is False
    assert "Permission denied" in context["error"]


@pytest.mark.unit
def test_get_cwd_context_os_error(monkeypatch):
    """Test CWD context when OS error occurs reading directory."""
    # Mock os.listdir to raise OSError
    def mock_listdir(path):
        raise OSError("IO error")

    monkeypatch.setattr("os.listdir", mock_listdir)

    context = get_cwd_context()

    assert context["readable"] is False
    assert "IO error" in context["error"]


@pytest.mark.unit
def test_get_cwd_context_getcwd_error(monkeypatch):
    """Test CWD context when getcwd fails."""
    # Mock os.getcwd to raise OSError
    def mock_getcwd():
        raise OSError("Directory has been deleted")

    monkeypatch.setattr("os.getcwd", mock_getcwd)

    context = get_cwd_context()

    assert context["cwd"] is None
    assert "Error getting current directory" in context["error"]


@pytest.mark.unit
def test_get_directory_info_valid(tmp_path):
    """Test get_directory_info with valid directory."""
    # Create a test directory with some files
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()
    (test_dir / "file1.txt").write_text("test")
    (test_dir / "file2.txt").write_text("test")

    info = get_directory_info(str(test_dir))

    assert info["path"] == str(test_dir)
    assert info["exists"] is True
    assert info["is_dir"] is True
    assert info["readable"] is True
    assert info["writable"] is True
    assert info["executable"] is True
    assert info["size"] == 2  # Two files
    assert info["permissions"] is not None
    assert info["error"] is None


@pytest.mark.unit
def test_get_directory_info_nonexistent():
    """Test get_directory_info with non-existent directory."""
    info = get_directory_info("/nonexistent/directory/path")

    assert info["exists"] is False
    assert info["is_dir"] is False
    assert "does not exist" in info["error"]


@pytest.mark.unit
def test_get_directory_info_file_not_directory(tmp_path):
    """Test get_directory_info with file instead of directory."""
    # Create a file
    test_file = tmp_path / "test_file.txt"
    test_file.write_text("test")

    info = get_directory_info(str(test_file))

    assert info["exists"] is True
    assert info["is_dir"] is False
    assert "not a directory" in info["error"]


@pytest.mark.unit
def test_get_directory_info_permission_error(tmp_path, monkeypatch):
    """Test get_directory_info with permission error."""
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()

    # Mock os.listdir to raise PermissionError
    original_listdir = os.listdir

    def mock_listdir(path):
        if str(path) == str(test_dir):
            raise PermissionError("Permission denied")
        return original_listdir(path)

    monkeypatch.setattr("os.listdir", mock_listdir)

    info = get_directory_info(str(test_dir))

    assert info["exists"] is True
    assert info["is_dir"] is True
    assert info["readable"] is False
    assert "Permission denied" in info["error"]


@pytest.mark.unit
def test_get_directory_info_relative_path(tmp_path, monkeypatch):
    """Test get_directory_info resolves relative paths."""
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()

    # Change to tmp_path
    monkeypatch.chdir(tmp_path)

    # Use relative path
    info = get_directory_info("test_dir")

    # Should resolve to absolute path
    assert info["path"] == str(test_dir)
    assert info["exists"] is True
    assert info["is_dir"] is True


@pytest.mark.unit
def test_get_directory_info_permissions_format(tmp_path):
    """Test that permissions are formatted correctly."""
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir(mode=0o755)

    info = get_directory_info(str(test_dir))

    assert info["permissions"] is not None
    # Should be a 3-digit string
    assert len(info["permissions"]) == 3
    assert info["permissions"].isdigit()


@pytest.mark.unit
def test_get_directory_info_empty_directory(tmp_path):
    """Test get_directory_info with empty directory."""
    test_dir = tmp_path / "empty_dir"
    test_dir.mkdir()

    info = get_directory_info(str(test_dir))

    assert info["size"] == 0
    assert info["readable"] is True


@pytest.mark.unit
def test_format_cwd_context_normal():
    """Test formatting normal CWD context."""
    context = {
        "cwd": "/home/user/project",
        "exists": True,
        "readable": True,
        "writable": True,
        "size": 15,
        "error": None,
    }

    formatted = format_cwd_context(context)

    assert "/home/user/project" in formatted
    assert "readable" in formatted
    assert "writable" in formatted
    assert "15" in formatted


@pytest.mark.unit
def test_format_cwd_context_readonly():
    """Test formatting read-only CWD context."""
    context = {
        "cwd": "/readonly/path",
        "exists": True,
        "readable": True,
        "writable": False,
        "size": 5,
        "error": None,
    }

    formatted = format_cwd_context(context)

    assert "/readonly/path" in formatted
    assert "readable" in formatted
    assert "read-only" in formatted


@pytest.mark.unit
def test_format_cwd_context_not_readable():
    """Test formatting non-readable CWD context."""
    context = {
        "cwd": "/restricted/path",
        "exists": True,
        "readable": False,
        "writable": False,
        "size": 0,
        "error": None,
    }

    formatted = format_cwd_context(context)

    assert "/restricted/path" in formatted
    assert "not readable" in formatted
    assert "read-only" in formatted
    # Size should not be shown if not readable
    assert "Items:" not in formatted


@pytest.mark.unit
def test_format_cwd_context_with_error():
    """Test formatting CWD context with error."""
    context = {
        "cwd": "/error/path",
        "exists": False,
        "readable": False,
        "writable": False,
        "size": 0,
        "error": "Permission denied",
    }

    formatted = format_cwd_context(context)

    assert "Error: Permission denied" in formatted
    assert "/error/path" in formatted


@pytest.mark.unit
def test_format_cwd_context_error_no_cwd():
    """Test formatting context with error and no CWD."""
    context = {
        "cwd": None,
        "exists": False,
        "readable": False,
        "writable": False,
        "size": 0,
        "error": "Could not determine current directory",
    }

    formatted = format_cwd_context(context)

    assert "Error:" in formatted
    assert "Could not determine current directory" in formatted


@pytest.mark.unit
def test_get_cwd_context_integration(tmp_path, monkeypatch):
    """Integration test for get_cwd_context in real directory."""
    # Create a test directory with known structure
    test_dir = tmp_path / "integration_test"
    test_dir.mkdir()

    # Create some files
    for i in range(5):
        (test_dir / f"file{i}.txt").write_text("test")

    # Change to test directory
    monkeypatch.chdir(test_dir)

    context = get_cwd_context()

    assert context["cwd"] == str(test_dir)
    assert context["exists"] is True
    assert context["readable"] is True
    assert context["writable"] is True
    assert context["size"] == 5
    assert context["error"] is None

    # Test formatting
    formatted = format_cwd_context(context)
    assert str(test_dir) in formatted
    assert "5" in formatted
