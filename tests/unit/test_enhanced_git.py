"""
Tests for enhanced git context collection functionality.
"""

import subprocess
from pathlib import Path

import pytest

from hai_sh.context import (
    get_git_context_enhanced,
    format_git_context_enhanced,
)


# ============================================================================
# Enhanced Git Context Tests
# ============================================================================


@pytest.mark.unit
def test_get_git_context_enhanced_basic(sample_git_repo, monkeypatch):
    """Test enhanced git context in a git repository."""
    monkeypatch.chdir(sample_git_repo)

    context = get_git_context_enhanced()

    # Basic fields from original
    assert context["is_git_repo"] is True
    assert context["branch"] is not None
    assert context["error"] is None

    # Enhanced fields
    assert "dirty_files" in context
    assert "ahead_count" in context
    assert "behind_count" in context
    assert "stash_count" in context
    assert "recent_commits" in context
    assert "remote_branch" in context


@pytest.mark.unit
def test_get_git_context_enhanced_dirty_files(sample_git_repo, monkeypatch):
    """Test enhanced git context with dirty files listing."""
    monkeypatch.chdir(sample_git_repo)

    # Create different types of changes
    # Untracked file
    (sample_git_repo / "untracked.txt").write_text("new file")

    # Staged file
    staged = sample_git_repo / "staged.txt"
    staged.write_text("staged content")
    subprocess.run(["git", "add", "staged.txt"], cwd=sample_git_repo, check=True)

    # Modified but unstaged (README.md exists from fixture)
    readme = sample_git_repo / "README.md"
    readme.write_text("modified content")

    context = get_git_context_enhanced()

    dirty_files = context["dirty_files"]
    assert "staged" in dirty_files
    assert "unstaged" in dirty_files
    assert "untracked" in dirty_files

    # Check that file paths are included
    assert "staged.txt" in dirty_files["staged"]
    assert "README.md" in dirty_files["unstaged"]
    assert "untracked.txt" in dirty_files["untracked"]


@pytest.mark.unit
def test_get_git_context_enhanced_clean_repo(sample_git_repo, monkeypatch):
    """Test enhanced git context in clean repository."""
    monkeypatch.chdir(sample_git_repo)

    context = get_git_context_enhanced()

    assert context["is_clean"] is True
    dirty_files = context["dirty_files"]
    assert dirty_files["staged"] == []
    assert dirty_files["unstaged"] == []
    assert dirty_files["untracked"] == []


@pytest.mark.unit
def test_get_git_context_enhanced_recent_commits(sample_git_repo, monkeypatch):
    """Test enhanced git context includes recent commits."""
    monkeypatch.chdir(sample_git_repo)

    # Create a few more commits
    for i in range(3):
        (sample_git_repo / f"file{i}.txt").write_text(f"content {i}")
        subprocess.run(["git", "add", f"file{i}.txt"], cwd=sample_git_repo, check=True)
        subprocess.run(
            ["git", "commit", "-m", f"Commit {i}"],
            cwd=sample_git_repo,
            check=True,
        )

    context = get_git_context_enhanced()

    recent_commits = context["recent_commits"]
    assert len(recent_commits) >= 3
    # Each commit should have hash and message
    for commit in recent_commits:
        assert "hash" in commit
        assert "message" in commit


@pytest.mark.unit
def test_get_git_context_enhanced_stash_count(sample_git_repo, monkeypatch):
    """Test enhanced git context includes stash count."""
    monkeypatch.chdir(sample_git_repo)

    # Create some changes and stash them
    (sample_git_repo / "stash_test.txt").write_text("stash content")
    subprocess.run(["git", "add", "stash_test.txt"], cwd=sample_git_repo, check=True)
    subprocess.run(["git", "stash"], cwd=sample_git_repo, check=True)

    context = get_git_context_enhanced()

    assert context["stash_count"] >= 1


@pytest.mark.unit
def test_get_git_context_enhanced_stash_count_zero(sample_git_repo, monkeypatch):
    """Test enhanced git context with no stashes."""
    monkeypatch.chdir(sample_git_repo)

    # Clear any stashes
    subprocess.run(["git", "stash", "clear"], cwd=sample_git_repo, check=True)

    context = get_git_context_enhanced()

    assert context["stash_count"] == 0


@pytest.mark.unit
def test_get_git_context_enhanced_ahead_behind_local(sample_git_repo, monkeypatch):
    """Test ahead/behind counts for local-only repo (no remote)."""
    monkeypatch.chdir(sample_git_repo)

    context = get_git_context_enhanced()

    # Local repo without remote tracking
    assert context["ahead_count"] == 0
    assert context["behind_count"] == 0
    assert context["remote_branch"] is None


@pytest.mark.unit
def test_get_git_context_enhanced_not_in_repo(tmp_path, monkeypatch):
    """Test enhanced git context outside a repository."""
    monkeypatch.chdir(tmp_path)

    context = get_git_context_enhanced()

    assert context["is_git_repo"] is False
    assert context["dirty_files"] == {"staged": [], "unstaged": [], "untracked": []}
    assert context["ahead_count"] == 0
    assert context["behind_count"] == 0
    assert context["stash_count"] == 0
    assert context["recent_commits"] == []


@pytest.mark.unit
def test_get_git_context_enhanced_with_directory(sample_git_repo):
    """Test enhanced git context with explicit directory argument."""
    context = get_git_context_enhanced(directory=str(sample_git_repo))

    assert context["is_git_repo"] is True
    assert context["branch"] is not None


@pytest.mark.unit
def test_get_git_context_enhanced_commit_limit(sample_git_repo, monkeypatch):
    """Test that recent commits are limited."""
    monkeypatch.chdir(sample_git_repo)

    # Create many commits
    for i in range(10):
        (sample_git_repo / f"file{i}.txt").write_text(f"content {i}")
        subprocess.run(["git", "add", f"file{i}.txt"], cwd=sample_git_repo, check=True)
        subprocess.run(
            ["git", "commit", "-m", f"Commit {i}"],
            cwd=sample_git_repo,
            check=True,
        )

    context = get_git_context_enhanced(max_commits=5)

    assert len(context["recent_commits"]) <= 5


# ============================================================================
# Format Enhanced Git Context Tests
# ============================================================================


@pytest.mark.unit
def test_format_git_context_enhanced_clean():
    """Test formatting enhanced git context for clean repo."""
    context = {
        "is_git_repo": True,
        "branch": "main",
        "commit_hash": "abc1234",
        "is_clean": True,
        "has_staged": False,
        "has_unstaged": False,
        "has_untracked": False,
        "dirty_files": {"staged": [], "unstaged": [], "untracked": []},
        "ahead_count": 0,
        "behind_count": 0,
        "stash_count": 0,
        "recent_commits": [
            {"hash": "abc1234", "message": "Initial commit"},
        ],
        "remote_branch": None,
        "error": None,
    }

    formatted = format_git_context_enhanced(context)

    assert "Branch: main" in formatted
    assert "clean" in formatted.lower()


@pytest.mark.unit
def test_format_git_context_enhanced_dirty():
    """Test formatting enhanced git context for dirty repo."""
    context = {
        "is_git_repo": True,
        "branch": "feature-branch",
        "commit_hash": "def5678",
        "is_clean": False,
        "has_staged": True,
        "has_unstaged": True,
        "has_untracked": True,
        "dirty_files": {
            "staged": ["src/main.py"],
            "unstaged": ["src/utils.py"],
            "untracked": ["new_file.txt"],
        },
        "ahead_count": 2,
        "behind_count": 1,
        "stash_count": 3,
        "recent_commits": [
            {"hash": "def5678", "message": "Latest commit"},
            {"hash": "abc1234", "message": "Previous commit"},
        ],
        "remote_branch": "origin/feature-branch",
        "error": None,
    }

    formatted = format_git_context_enhanced(context)

    assert "feature-branch" in formatted
    assert "staged" in formatted.lower()
    assert "unstaged" in formatted.lower()
    assert "untracked" in formatted.lower()


@pytest.mark.unit
def test_format_git_context_enhanced_ahead_behind():
    """Test formatting shows ahead/behind counts."""
    context = {
        "is_git_repo": True,
        "branch": "main",
        "commit_hash": "abc1234",
        "is_clean": True,
        "has_staged": False,
        "has_unstaged": False,
        "has_untracked": False,
        "dirty_files": {"staged": [], "unstaged": [], "untracked": []},
        "ahead_count": 3,
        "behind_count": 2,
        "stash_count": 0,
        "recent_commits": [],
        "remote_branch": "origin/main",
        "error": None,
    }

    formatted = format_git_context_enhanced(context)

    assert "ahead" in formatted.lower() or "3" in formatted
    assert "behind" in formatted.lower() or "2" in formatted


@pytest.mark.unit
def test_format_git_context_enhanced_stash():
    """Test formatting shows stash count."""
    context = {
        "is_git_repo": True,
        "branch": "main",
        "commit_hash": "abc1234",
        "is_clean": True,
        "has_staged": False,
        "has_unstaged": False,
        "has_untracked": False,
        "dirty_files": {"staged": [], "unstaged": [], "untracked": []},
        "ahead_count": 0,
        "behind_count": 0,
        "stash_count": 5,
        "recent_commits": [],
        "remote_branch": None,
        "error": None,
    }

    formatted = format_git_context_enhanced(context)

    assert "stash" in formatted.lower() or "5" in formatted


@pytest.mark.unit
def test_format_git_context_enhanced_recent_commits():
    """Test formatting includes recent commits."""
    context = {
        "is_git_repo": True,
        "branch": "main",
        "commit_hash": "abc1234",
        "is_clean": True,
        "has_staged": False,
        "has_unstaged": False,
        "has_untracked": False,
        "dirty_files": {"staged": [], "unstaged": [], "untracked": []},
        "ahead_count": 0,
        "behind_count": 0,
        "stash_count": 0,
        "recent_commits": [
            {"hash": "abc1234", "message": "Add feature X"},
            {"hash": "def5678", "message": "Fix bug Y"},
        ],
        "remote_branch": None,
        "error": None,
    }

    formatted = format_git_context_enhanced(context)

    assert "commit" in formatted.lower() or "abc1234" in formatted


@pytest.mark.unit
def test_format_git_context_enhanced_not_in_repo():
    """Test formatting when not in a git repo."""
    context = {
        "is_git_repo": False,
        "branch": None,
        "commit_hash": None,
        "is_clean": True,
        "has_staged": False,
        "has_unstaged": False,
        "has_untracked": False,
        "dirty_files": {"staged": [], "unstaged": [], "untracked": []},
        "ahead_count": 0,
        "behind_count": 0,
        "stash_count": 0,
        "recent_commits": [],
        "remote_branch": None,
        "error": None,
    }

    formatted = format_git_context_enhanced(context)

    assert "No" in formatted or "not" in formatted.lower()


@pytest.mark.unit
def test_format_git_context_enhanced_with_error():
    """Test formatting when error occurred."""
    context = {
        "is_git_repo": False,
        "branch": None,
        "commit_hash": None,
        "is_clean": True,
        "has_staged": False,
        "has_unstaged": False,
        "has_untracked": False,
        "dirty_files": {"staged": [], "unstaged": [], "untracked": []},
        "ahead_count": 0,
        "behind_count": 0,
        "stash_count": 0,
        "recent_commits": [],
        "remote_branch": None,
        "error": "Git is not installed",
    }

    formatted = format_git_context_enhanced(context)

    assert "error" in formatted.lower() or "not installed" in formatted.lower()


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.unit
def test_get_git_context_enhanced_integration(sample_git_repo, monkeypatch):
    """Integration test for enhanced git context."""
    monkeypatch.chdir(sample_git_repo)

    # Create realistic git state
    # 1. Staged file
    staged = sample_git_repo / "staged.py"
    staged.write_text("print('staged')")
    subprocess.run(["git", "add", "staged.py"], cwd=sample_git_repo, check=True)

    # 2. Unstaged modification (README.md exists from fixture)
    readme = sample_git_repo / "README.md"
    readme.write_text("modified content")

    # 3. Untracked file
    (sample_git_repo / "untracked.log").write_text("log")

    # Get context
    context = get_git_context_enhanced()

    assert context["is_git_repo"] is True
    assert context["is_clean"] is False
    assert len(context["dirty_files"]["staged"]) >= 1
    assert len(context["dirty_files"]["unstaged"]) >= 1
    assert len(context["dirty_files"]["untracked"]) >= 1

    # Format and verify
    formatted = format_git_context_enhanced(context)
    assert isinstance(formatted, str)
    assert len(formatted) > 0
