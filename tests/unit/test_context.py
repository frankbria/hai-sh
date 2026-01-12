"""
Tests for context collection functionality.
"""

import os
import stat
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from hai_sh.context import (
    _format_file_size,
    _filter_files_by_relevance,
    _reset_git_cache,
    format_cwd_context,
    format_env_context,
    format_file_listing_context,
    format_git_context,
    get_cwd_context,
    get_directory_info,
    get_env_context,
    get_file_listing_context,
    get_git_context,
    get_safe_env_vars,
    is_sensitive_env_var,
)


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


# ============================================================================
# Git Context Tests
# ============================================================================


@pytest.mark.unit
def test_get_git_context_in_repo(sample_git_repo, monkeypatch):
    """Test git context detection in a git repository."""
    monkeypatch.chdir(sample_git_repo)

    context = get_git_context()

    assert context["is_git_repo"] is True
    assert context["branch"] is not None
    assert context["error"] is None


@pytest.mark.unit
def test_get_git_context_not_in_repo(tmp_path, monkeypatch):
    """Test git context detection outside a git repository."""
    # Use a non-git directory
    test_dir = tmp_path / "not_a_repo"
    test_dir.mkdir()
    monkeypatch.chdir(test_dir)

    context = get_git_context()

    assert context["is_git_repo"] is False
    assert context["branch"] is None


@pytest.mark.unit
def test_get_git_context_clean_repo(sample_git_repo, monkeypatch):
    """Test git context in clean repository."""
    monkeypatch.chdir(sample_git_repo)

    context = get_git_context()

    assert context["is_git_repo"] is True
    assert context["is_clean"] is True
    assert context["has_staged"] is False
    assert context["has_unstaged"] is False
    assert context["has_untracked"] is False


@pytest.mark.unit
def test_get_git_context_dirty_repo(sample_git_repo, monkeypatch):
    """Test git context in dirty repository with uncommitted changes."""
    monkeypatch.chdir(sample_git_repo)

    # Create an untracked file
    (sample_git_repo / "untracked.txt").write_text("new file")

    context = get_git_context()

    assert context["is_git_repo"] is True
    assert context["is_clean"] is False
    assert context["has_untracked"] is True


@pytest.mark.unit
def test_get_git_context_staged_changes(sample_git_repo, monkeypatch):
    """Test git context with staged changes."""
    monkeypatch.chdir(sample_git_repo)

    # Create and stage a file
    new_file = sample_git_repo / "staged.txt"
    new_file.write_text("staged content")

    subprocess.run(["git", "add", "staged.txt"], cwd=sample_git_repo, check=True)

    context = get_git_context()

    assert context["is_git_repo"] is True
    assert context["is_clean"] is False
    assert context["has_staged"] is True


@pytest.mark.unit
def test_get_git_context_unstaged_changes(sample_git_repo, monkeypatch):
    """Test git context with unstaged changes."""
    monkeypatch.chdir(sample_git_repo)

    # Modify an existing file
    test_file = sample_git_repo / "test.txt"
    test_file.write_text("modified content")

    context = get_git_context()

    assert context["is_git_repo"] is True
    assert context["is_clean"] is False
    assert context["has_unstaged"] is True


@pytest.mark.unit
def test_get_git_context_branch_name(sample_git_repo, monkeypatch):
    """Test git context returns correct branch name."""
    monkeypatch.chdir(sample_git_repo)

    context = get_git_context()

    assert context["branch"] is not None
    # Default branch should be main or master
    assert context["branch"] in ["main", "master"]


@pytest.mark.unit
def test_get_git_context_commit_hash(sample_git_repo, monkeypatch):
    """Test git context returns commit hash."""
    monkeypatch.chdir(sample_git_repo)

    context = get_git_context()

    assert context["commit_hash"] is not None
    # Short hash should be 7 characters
    assert len(context["commit_hash"]) == 7


@pytest.mark.unit
def test_get_git_context_with_directory_arg(sample_git_repo):
    """Test git context with explicit directory argument."""
    context = get_git_context(directory=str(sample_git_repo))

    assert context["is_git_repo"] is True
    assert context["branch"] is not None


@pytest.mark.unit
def test_get_git_context_git_not_installed(monkeypatch):
    """Test git context when git is not installed."""
    # Reset the git cache so our mock takes effect
    _reset_git_cache()

    # Mock subprocess.run to raise FileNotFoundError
    def mock_run(*args, **kwargs):
        raise FileNotFoundError("git not found")

    monkeypatch.setattr("subprocess.run", mock_run)

    context = get_git_context()

    assert context["is_git_repo"] is False
    assert "not installed" in context["error"] or "not in PATH" in context["error"]

    # Reset cache again for other tests
    _reset_git_cache()


@pytest.mark.unit
def test_get_git_context_git_timeout(monkeypatch):
    """Test git context when git command times out."""
    # Reset the git cache so our mock takes effect
    _reset_git_cache()

    # Mock subprocess.run to raise TimeoutExpired
    def mock_run(*args, **kwargs):
        import subprocess

        raise subprocess.TimeoutExpired("git", 5)

    monkeypatch.setattr("subprocess.run", mock_run)

    context = get_git_context()

    assert context["is_git_repo"] is False
    assert "timed out" in context["error"].lower()

    # Reset cache for other tests
    _reset_git_cache()


@pytest.mark.unit
def test_get_git_context_os_error(monkeypatch, sample_git_repo):
    """Test git context when OS error occurs."""
    monkeypatch.chdir(sample_git_repo)

    # Mock subprocess.run to raise OSError after version check
    call_count = {"count": 0}

    original_run = subprocess.run

    def mock_run(*args, **kwargs):
        call_count["count"] += 1
        # Let version check pass, but fail on subsequent calls
        if call_count["count"] == 1:
            return original_run(*args, **kwargs)
        raise OSError("Disk error")

    monkeypatch.setattr("subprocess.run", mock_run)

    context = get_git_context()

    assert "Error running git command" in context["error"]


@pytest.mark.unit
def test_format_git_context_in_repo():
    """Test formatting git context for repository."""
    context = {
        "is_git_repo": True,
        "branch": "main",
        "is_clean": True,
        "has_staged": False,
        "has_unstaged": False,
        "has_untracked": False,
        "commit_hash": "abc1234",
        "error": None,
    }

    formatted = format_git_context(context)

    assert "Git Repository: Yes" in formatted
    assert "Branch: main" in formatted
    assert "abc1234" in formatted
    assert "Status: clean" in formatted


@pytest.mark.unit
def test_format_git_context_not_in_repo():
    """Test formatting git context for non-repository."""
    context = {
        "is_git_repo": False,
        "branch": None,
        "is_clean": True,
        "has_staged": False,
        "has_unstaged": False,
        "has_untracked": False,
        "commit_hash": None,
        "error": None,
    }

    formatted = format_git_context(context)

    assert "Git Repository: No" in formatted


@pytest.mark.unit
def test_format_git_context_dirty_repo():
    """Test formatting git context for dirty repository."""
    context = {
        "is_git_repo": True,
        "branch": "feature-branch",
        "is_clean": False,
        "has_staged": True,
        "has_unstaged": True,
        "has_untracked": True,
        "commit_hash": "def5678",
        "error": None,
    }

    formatted = format_git_context(context)

    assert "Git Repository: Yes" in formatted
    assert "Branch: feature-branch" in formatted
    assert "staged changes" in formatted
    assert "unstaged changes" in formatted
    assert "untracked files" in formatted


@pytest.mark.unit
def test_format_git_context_with_error():
    """Test formatting git context with error."""
    context = {
        "is_git_repo": False,
        "branch": None,
        "is_clean": True,
        "has_staged": False,
        "has_unstaged": False,
        "has_untracked": False,
        "commit_hash": None,
        "error": "Git is not installed",
    }

    formatted = format_git_context(context)

    assert "Git Error:" in formatted
    assert "not installed" in formatted


@pytest.mark.unit
def test_get_git_context_integration(sample_git_repo, monkeypatch):
    """Integration test for get_git_context."""
    monkeypatch.chdir(sample_git_repo)

    # Start with clean repo
    context = get_git_context()
    assert context["is_git_repo"] is True
    assert context["is_clean"] is True

    # Add untracked file
    (sample_git_repo / "new.txt").write_text("new")
    context = get_git_context()
    assert context["is_clean"] is False
    assert context["has_untracked"] is True

    # Stage the file
    subprocess.run(["git", "add", "new.txt"], cwd=sample_git_repo, check=True)
    context = get_git_context()
    assert context["has_staged"] is True

    # Modify staged file
    (sample_git_repo / "new.txt").write_text("modified")
    context = get_git_context()
    assert context["has_staged"] is True
    assert context["has_unstaged"] is True

    # Test formatting
    formatted = format_git_context(context)
    assert "staged changes" in formatted
    assert "unstaged changes" in formatted


# ============================================================================
# Environment Variable Tests
# ============================================================================


@pytest.mark.unit
def test_get_env_context_basic(monkeypatch):
    """Test basic environment context collection."""
    monkeypatch.setenv("USER", "testuser")
    monkeypatch.setenv("HOME", "/home/testuser")
    monkeypatch.setenv("SHELL", "/bin/bash")
    monkeypatch.setenv("PATH", "/usr/bin:/bin")

    context = get_env_context()

    assert context["user"] == "testuser"
    assert context["home"] == "/home/testuser"
    assert context["shell"] == "/bin/bash"
    assert context["path"] == "/usr/bin:/bin"
    assert context["path_truncated"] is False
    assert len(context["missing"]) == 0


@pytest.mark.unit
def test_get_env_context_logname_fallback(monkeypatch):
    """Test USER fallback to LOGNAME."""
    monkeypatch.delenv("USER", raising=False)
    monkeypatch.setenv("LOGNAME", "logname_user")
    monkeypatch.setenv("HOME", "/home/testuser")
    monkeypatch.setenv("SHELL", "/bin/bash")

    context = get_env_context(include_path=False)

    assert context["user"] == "logname_user"


@pytest.mark.unit
def test_get_env_context_missing_vars(monkeypatch):
    """Test environment context with missing variables."""
    monkeypatch.delenv("USER", raising=False)
    monkeypatch.delenv("LOGNAME", raising=False)
    monkeypatch.delenv("HOME", raising=False)
    monkeypatch.delenv("SHELL", raising=False)
    monkeypatch.delenv("PATH", raising=False)

    context = get_env_context()

    assert context["user"] is None
    assert context["home"] is None
    assert context["shell"] is None
    assert context["path"] is None
    assert "USER" in context["missing"]
    assert "HOME" in context["missing"]
    assert "SHELL" in context["missing"]
    assert "PATH" in context["missing"]


@pytest.mark.unit
def test_get_env_context_path_truncation(monkeypatch):
    """Test PATH truncation when too long."""
    monkeypatch.setenv("USER", "testuser")
    monkeypatch.setenv("HOME", "/home/testuser")
    monkeypatch.setenv("SHELL", "/bin/bash")
    # Create a very long PATH
    long_path = ":".join([f"/usr/bin/path{i}" for i in range(100)])
    monkeypatch.setenv("PATH", long_path)

    context = get_env_context(max_path_length=100)

    assert context["path"] is not None
    assert len(context["path"]) <= 103  # 100 + "..."
    assert context["path"].endswith("...")
    assert context["path_truncated"] is True


@pytest.mark.unit
def test_get_env_context_without_path(monkeypatch):
    """Test environment context without PATH."""
    monkeypatch.setenv("USER", "testuser")
    monkeypatch.setenv("HOME", "/home/testuser")
    monkeypatch.setenv("SHELL", "/bin/bash")
    monkeypatch.setenv("PATH", "/usr/bin:/bin")

    context = get_env_context(include_path=False)

    assert context["path"] is None
    assert context["path_truncated"] is False
    assert "PATH" not in context["missing"]


@pytest.mark.unit
def test_is_sensitive_env_var_sensitive():
    """Test detecting sensitive environment variables."""
    assert is_sensitive_env_var("API_KEY") is True
    assert is_sensitive_env_var("SECRET_TOKEN") is True
    assert is_sensitive_env_var("PASSWORD") is True
    assert is_sensitive_env_var("OPENAI_API_KEY") is True
    assert is_sensitive_env_var("AUTH_TOKEN") is True
    assert is_sensitive_env_var("PRIVATE_KEY") is True
    assert is_sensitive_env_var("ACCESS_TOKEN") is True
    assert is_sensitive_env_var("SESSION_SECRET") is True
    assert is_sensitive_env_var("DB_PASSWORD") is True
    assert is_sensitive_env_var("CREDENTIALS") is True


@pytest.mark.unit
def test_is_sensitive_env_var_safe():
    """Test that safe variables are not marked as sensitive."""
    assert is_sensitive_env_var("HOME") is False
    assert is_sensitive_env_var("USER") is False
    assert is_sensitive_env_var("SHELL") is False
    assert is_sensitive_env_var("PATH") is False
    assert is_sensitive_env_var("LANG") is False
    assert is_sensitive_env_var("EDITOR") is False
    assert is_sensitive_env_var("TERM") is False


@pytest.mark.unit
def test_is_sensitive_env_var_case_insensitive():
    """Test that sensitivity check is case-insensitive."""
    assert is_sensitive_env_var("api_key") is True
    assert is_sensitive_env_var("Api_Key") is True
    assert is_sensitive_env_var("secret") is True
    assert is_sensitive_env_var("SECRET") is True


@pytest.mark.unit
def test_get_safe_env_vars(monkeypatch):
    """Test getting safe environment variables."""
    # Set up test environment
    monkeypatch.setenv("HOME", "/home/testuser")
    monkeypatch.setenv("USER", "testuser")
    monkeypatch.setenv("SHELL", "/bin/bash")
    monkeypatch.setenv("API_KEY", "test_key")
    monkeypatch.setenv("PASSWORD", "test_pw")

    safe_vars = get_safe_env_vars()

    # Safe variables should be included
    assert "HOME" in safe_vars
    assert "USER" in safe_vars
    assert "SHELL" in safe_vars

    # Sensitive variables should be excluded
    assert "API_KEY" not in safe_vars
    assert "PASSWORD" not in safe_vars


@pytest.mark.unit
def test_get_safe_env_vars_with_exclude_patterns(monkeypatch):
    """Test getting safe variables with additional exclude patterns."""
    monkeypatch.setenv("HOME", "/home/testuser")
    monkeypatch.setenv("USER", "testuser")
    monkeypatch.setenv("CUSTOM_VAR", "value")

    safe_vars = get_safe_env_vars(exclude_patterns=["CUSTOM"])

    assert "HOME" in safe_vars
    assert "USER" in safe_vars
    assert "CUSTOM_VAR" not in safe_vars


@pytest.mark.unit
def test_get_safe_env_vars_case_insensitive_exclude(monkeypatch):
    """Test that exclude patterns are case-insensitive."""
    monkeypatch.setenv("MY_CUSTOM_VAR", "value")

    safe_vars = get_safe_env_vars(exclude_patterns=["custom"])

    assert "MY_CUSTOM_VAR" not in safe_vars


@pytest.mark.unit
def test_format_env_context_complete(monkeypatch):
    """Test formatting complete environment context."""
    monkeypatch.setenv("USER", "testuser")
    monkeypatch.setenv("HOME", "/home/testuser")
    monkeypatch.setenv("SHELL", "/bin/bash")
    monkeypatch.setenv("PATH", "/usr/bin:/bin")

    context = get_env_context()
    formatted = format_env_context(context)

    assert "User: testuser" in formatted
    assert "Home: /home/testuser" in formatted
    assert "Shell: /bin/bash" in formatted
    assert "PATH: /usr/bin:/bin" in formatted
    assert "(truncated)" not in formatted


@pytest.mark.unit
def test_format_env_context_truncated_path(monkeypatch):
    """Test formatting environment context with truncated PATH."""
    monkeypatch.setenv("USER", "testuser")
    monkeypatch.setenv("HOME", "/home/testuser")
    monkeypatch.setenv("SHELL", "/bin/bash")
    long_path = ":".join([f"/usr/bin/path{i}" for i in range(100)])
    monkeypatch.setenv("PATH", long_path)

    context = get_env_context(max_path_length=50)
    formatted = format_env_context(context)

    assert "PATH:" in formatted
    assert "(truncated)" in formatted


@pytest.mark.unit
def test_format_env_context_missing_vars(monkeypatch):
    """Test formatting environment context with missing variables."""
    monkeypatch.delenv("USER", raising=False)
    monkeypatch.delenv("LOGNAME", raising=False)
    monkeypatch.delenv("HOME", raising=False)
    monkeypatch.setenv("SHELL", "/bin/bash")

    context = get_env_context(include_path=False)
    formatted = format_env_context(context)

    assert "Shell: /bin/bash" in formatted
    assert "Missing: USER, HOME" in formatted


@pytest.mark.unit
def test_format_env_context_empty():
    """Test formatting empty environment context."""
    context = {
        "user": None,
        "home": None,
        "shell": None,
        "path": None,
        "path_truncated": False,
        "missing": [],
    }

    formatted = format_env_context(context)

    # Should return empty string or minimal output
    assert formatted == "" or len(formatted) == 0


@pytest.mark.unit
def test_get_env_context_integration():
    """Integration test for environment context collection."""
    # Get actual environment
    context = get_env_context()

    # Check structure
    assert "user" in context
    assert "home" in context
    assert "shell" in context
    assert "path" in context
    assert "path_truncated" in context
    assert "missing" in context

    # At least one of these should be set in most environments
    has_values = any(
        [context["user"], context["home"], context["shell"], context["path"]]
    )
    assert has_values

    # Test formatting
    formatted = format_env_context(context)
    assert isinstance(formatted, str)


# ==================== File Listing Context Tests ====================


@pytest.mark.unit
def test_format_file_size_bytes():
    """Test file size formatting for bytes."""
    assert _format_file_size(0) == "0 B"
    assert _format_file_size(512) == "512 B"
    assert _format_file_size(1023) == "1023 B"


@pytest.mark.unit
def test_format_file_size_kilobytes():
    """Test file size formatting for kilobytes."""
    assert _format_file_size(1024) == "1.0 KB"
    assert _format_file_size(1536) == "1.5 KB"
    assert _format_file_size(2048) == "2.0 KB"


@pytest.mark.unit
def test_format_file_size_megabytes():
    """Test file size formatting for megabytes."""
    assert _format_file_size(1048576) == "1.0 MB"
    assert _format_file_size(1572864) == "1.5 MB"
    assert _format_file_size(10485760) == "10.0 MB"


@pytest.mark.unit
def test_format_file_size_gigabytes():
    """Test file size formatting for gigabytes."""
    assert _format_file_size(1073741824) == "1.0 GB"
    assert _format_file_size(2147483648) == "2.0 GB"


@pytest.mark.unit
def test_filter_files_by_relevance_no_query():
    """Test file filtering without query returns first max_files."""
    files = [
        {'name': 'file1.txt', 'type': 'file'},
        {'name': 'file2.txt', 'type': 'file'},
        {'name': 'file3.txt', 'type': 'file'},
    ]
    result = _filter_files_by_relevance(files, "", 2)
    assert len(result) == 2
    assert result == files[:2]


@pytest.mark.unit
def test_filter_files_by_relevance_exact_match():
    """Test file filtering with exact match gets highest priority."""
    files = [
        {'name': 'test.py', 'type': 'file'},
        {'name': 'test_something.py', 'type': 'file'},
        {'name': 'other.py', 'type': 'file'},
    ]
    result = _filter_files_by_relevance(files, 'test.py', 10)
    assert result[0]['name'] == 'test.py'


@pytest.mark.unit
def test_filter_files_by_relevance_starts_with():
    """Test file filtering with name starting with query."""
    files = [
        {'name': 'test_file.py', 'type': 'file'},
        {'name': 'other_test.py', 'type': 'file'},
        {'name': 'main.py', 'type': 'file'},
    ]
    result = _filter_files_by_relevance(files, 'test', 10)
    assert len(result) == 2
    assert result[0]['name'] == 'test_file.py'


@pytest.mark.unit
def test_filter_files_by_relevance_substring():
    """Test file filtering with substring match."""
    files = [
        {'name': 'config_test.py', 'type': 'file'},
        {'name': 'test_utils.py', 'type': 'file'},
        {'name': 'main.py', 'type': 'file'},
    ]
    result = _filter_files_by_relevance(files, 'test', 10)
    assert len(result) == 2


@pytest.mark.unit
def test_filter_files_by_relevance_case_insensitive():
    """Test file filtering is case-insensitive."""
    files = [
        {'name': 'TEST.py', 'type': 'file'},
        {'name': 'test.py', 'type': 'file'},
        {'name': 'Test.py', 'type': 'file'},
    ]
    result = _filter_files_by_relevance(files, 'test', 10)
    assert len(result) == 3


@pytest.mark.unit
def test_filter_files_by_relevance_multiple_words():
    """Test file filtering with multiple query words."""
    files = [
        {'name': 'test_config.py', 'type': 'file'},
        {'name': 'config.py', 'type': 'file'},
        {'name': 'test.py', 'type': 'file'},
        {'name': 'main.py', 'type': 'file'},
    ]
    result = _filter_files_by_relevance(files, 'test config', 10)
    assert len(result) >= 1
    assert result[0]['name'] == 'test_config.py'


@pytest.mark.unit
def test_get_file_listing_context_basic(tmp_path, monkeypatch):
    """Test basic file listing in temporary directory."""
    monkeypatch.chdir(tmp_path)

    # Create test files
    (tmp_path / "file1.txt").write_text("content")
    (tmp_path / "file2.py").write_text("code")
    (tmp_path / "dir1").mkdir()

    context = get_file_listing_context()

    assert "directory" in context
    assert "files" in context
    assert "total_count" in context
    assert "truncated" in context
    assert "depth" in context
    assert "error" in context

    assert context["directory"] == str(tmp_path)
    assert context["total_count"] == 3
    assert context["truncated"] is False
    assert context["error"] is None
    assert len(context["files"]) == 3


@pytest.mark.unit
def test_get_file_listing_context_empty_directory(tmp_path, monkeypatch):
    """Test file listing in empty directory."""
    monkeypatch.chdir(tmp_path)

    context = get_file_listing_context()

    assert context["directory"] == str(tmp_path)
    assert context["total_count"] == 0
    assert context["files"] == []
    assert context["error"] is None


@pytest.mark.unit
def test_get_file_listing_context_max_files(tmp_path, monkeypatch):
    """Test max_files limit."""
    monkeypatch.chdir(tmp_path)

    # Create more files than max_files
    for i in range(25):
        (tmp_path / f"file{i}.txt").write_text("content")

    context = get_file_listing_context(max_files=10)

    assert context["total_count"] == 25
    assert len(context["files"]) == 10
    assert context["truncated"] is True


@pytest.mark.unit
def test_get_file_listing_context_hidden_files(tmp_path, monkeypatch):
    """Test hidden files filtering."""
    monkeypatch.chdir(tmp_path)

    # Create visible and hidden files
    (tmp_path / "visible.txt").write_text("content")
    (tmp_path / ".hidden").write_text("secret")

    # Without show_hidden
    context = get_file_listing_context(show_hidden=False)
    assert context["total_count"] == 1
    assert context["files"][0]["name"] == "visible.txt"

    # With show_hidden
    context = get_file_listing_context(show_hidden=True)
    assert context["total_count"] == 2


@pytest.mark.unit
def test_get_file_listing_context_sorting(tmp_path, monkeypatch):
    """Test files are sorted directories first, then alphabetically."""
    monkeypatch.chdir(tmp_path)

    # Create files and directories in non-alphabetical order
    (tmp_path / "zebra.txt").write_text("content")
    (tmp_path / "dir_b").mkdir()
    (tmp_path / "apple.txt").write_text("content")
    (tmp_path / "dir_a").mkdir()

    context = get_file_listing_context()

    files = context["files"]
    # First two should be directories
    assert files[0]["type"] == "dir"
    assert files[1]["type"] == "dir"
    # Directories should be alphabetically sorted
    assert files[0]["name"] == "dir_a"
    assert files[1]["name"] == "dir_b"
    # Then files, alphabetically sorted
    assert files[2]["name"] == "apple.txt"
    assert files[3]["name"] == "zebra.txt"


@pytest.mark.unit
def test_get_file_listing_context_with_query(tmp_path, monkeypatch):
    """Test file listing with query filtering."""
    monkeypatch.chdir(tmp_path)

    # Create test files
    (tmp_path / "test_file.py").write_text("code")
    (tmp_path / "test_data.txt").write_text("data")
    (tmp_path / "main.py").write_text("code")
    (tmp_path / "readme.md").write_text("docs")

    context = get_file_listing_context(query="test")

    # Should only return files matching "test"
    assert len(context["files"]) == 2
    names = [f["name"] for f in context["files"]]
    assert "test_file.py" in names
    assert "test_data.txt" in names


@pytest.mark.unit
def test_get_file_listing_context_depth_zero(tmp_path, monkeypatch):
    """Test max_depth=0 only scans current directory."""
    monkeypatch.chdir(tmp_path)

    # Create nested structure
    (tmp_path / "file.txt").write_text("content")
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    (subdir / "nested.txt").write_text("nested")

    context = get_file_listing_context(max_depth=0)

    # Should only see file.txt and subdir, not nested.txt
    assert context["total_count"] == 2
    names = [f["name"] for f in context["files"]]
    assert "file.txt" in names
    assert "subdir" in names
    assert "subdir/nested.txt" not in names


@pytest.mark.unit
def test_get_file_listing_context_depth_one(tmp_path, monkeypatch):
    """Test max_depth=1 scans one level deep."""
    monkeypatch.chdir(tmp_path)

    # Create nested structure
    (tmp_path / "file.txt").write_text("content")
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    (subdir / "nested.txt").write_text("nested")
    subsubdir = subdir / "subsubdir"
    subsubdir.mkdir()
    (subsubdir / "deep.txt").write_text("deep")

    context = get_file_listing_context(max_depth=1)

    # Should see file.txt, subdir, and subdir/nested.txt, but not deeper
    names = [f["name"] for f in context["files"]]
    assert "file.txt" in names
    assert "subdir" in names
    assert "subdir/nested.txt" in names
    # Should not see subsubdir contents at depth 2
    assert not any("subsubdir" in name for name in names if name != "subdir/subsubdir")


@pytest.mark.unit
def test_get_file_listing_context_nonexistent_directory():
    """Test file listing with nonexistent directory."""
    context = get_file_listing_context(directory="/nonexistent/path")

    assert context["error"] is not None
    assert "does not exist" in context["error"].lower()
    assert context["files"] == []


@pytest.mark.unit
def test_get_file_listing_context_file_not_directory(tmp_path):
    """Test file listing when path is a file, not directory."""
    file_path = tmp_path / "file.txt"
    file_path.write_text("content")

    context = get_file_listing_context(directory=str(file_path))

    assert context["error"] is not None
    assert "not a directory" in context["error"].lower()


@pytest.mark.unit
def test_format_file_listing_context_normal(tmp_path, monkeypatch):
    """Test formatting normal file listing."""
    monkeypatch.chdir(tmp_path)

    # Create test files
    (tmp_path / "dir1").mkdir()
    (tmp_path / "file1.txt").write_text("x" * 1024)  # 1 KB

    context = get_file_listing_context()
    formatted = format_file_listing_context(context)

    assert isinstance(formatted, str)
    assert str(tmp_path) in formatted
    assert "dir1/" in formatted
    assert "file1.txt" in formatted
    assert "KB" in formatted


@pytest.mark.unit
def test_format_file_listing_context_truncated(tmp_path, monkeypatch):
    """Test formatting when file list is truncated."""
    monkeypatch.chdir(tmp_path)

    # Create many files
    for i in range(25):
        (tmp_path / f"file{i}.txt").write_text("content")

    context = get_file_listing_context(max_files=10)
    formatted = format_file_listing_context(context)

    assert "truncated" in formatted.lower()
    assert "showing 10 of 25" in formatted


@pytest.mark.unit
def test_format_file_listing_context_empty(tmp_path, monkeypatch):
    """Test formatting empty directory."""
    monkeypatch.chdir(tmp_path)

    context = get_file_listing_context()
    formatted = format_file_listing_context(context)

    assert "(empty)" in formatted


@pytest.mark.unit
def test_format_file_listing_context_with_error():
    """Test formatting when error occurred."""
    context = {
        "directory": "/some/path",
        "files": [],
        "total_count": 0,
        "truncated": False,
        "depth": 1,
        "error": "Permission denied"
    }

    formatted = format_file_listing_context(context)

    assert "error" in formatted.lower()
    assert "Permission denied" in formatted
    assert "/some/path" in formatted


@pytest.mark.unit
def test_get_file_listing_context_file_metadata(tmp_path, monkeypatch):
    """Test that file metadata includes all required fields."""
    monkeypatch.chdir(tmp_path)

    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")

    context = get_file_listing_context()

    assert len(context["files"]) == 1
    file_info = context["files"][0]

    assert "name" in file_info
    assert "type" in file_info
    assert "size" in file_info
    assert "modified" in file_info

    assert file_info["name"] == "test.txt"
    assert file_info["type"] == "file"
    assert isinstance(file_info["size"], int)
    assert isinstance(file_info["modified"], float)


@pytest.mark.unit
def test_get_file_listing_context_directory_metadata(tmp_path, monkeypatch):
    """Test that directory metadata is correct."""
    monkeypatch.chdir(tmp_path)

    # Create a test directory
    (tmp_path / "testdir").mkdir()

    context = get_file_listing_context()

    assert len(context["files"]) == 1
    dir_info = context["files"][0]

    assert dir_info["name"] == "testdir"
    assert dir_info["type"] == "dir"


@pytest.mark.unit
def test_get_file_listing_context_default_directory():
    """Test that default directory is current working directory."""
    context = get_file_listing_context()

    assert context["directory"] == os.getcwd()


@pytest.mark.unit
def test_get_file_listing_context_explicit_directory(tmp_path):
    """Test file listing with explicitly provided directory."""
    # Create test file
    (tmp_path / "test.txt").write_text("content")

    context = get_file_listing_context(directory=str(tmp_path))

    assert context["directory"] == str(tmp_path)
    assert len(context["files"]) == 1


@pytest.mark.unit
def test_get_file_listing_context_handles_permission_errors(tmp_path, monkeypatch):
    """Test graceful handling of permission errors."""
    monkeypatch.chdir(tmp_path)

    # Create a directory we'll make unreadable
    subdir = tmp_path / "restricted"
    subdir.mkdir()

    # Mock scandir to raise PermissionError
    original_scandir = os.scandir
    def mock_scandir(path):
        if str(path).endswith("restricted"):
            raise PermissionError("Access denied")
        return original_scandir(path)

    monkeypatch.setattr("os.scandir", mock_scandir)

    # This should not crash, but handle the error gracefully
    context = get_file_listing_context(max_depth=1)

    # The function should continue with other files
    # (behavior depends on where the permission error occurs)
