"""
Pytest configuration and shared fixtures for hai-sh tests.
"""

import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture
def tmp_config_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """
    Create a temporary directory for config files (~/.hai/).

    This fixture simulates the ~/.hai/ directory structure for testing
    configuration loading and management.

    Yields:
        Path: Path to temporary config directory
    """
    config_dir = tmp_path / ".hai"
    config_dir.mkdir()
    yield config_dir


@pytest.fixture
def mock_shell_context(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """
    Mock shell environment variables for testing.

    Sets up a controlled environment with standard shell variables
    for testing context collection.

    Args:
        monkeypatch: Pytest's monkeypatch fixture

    Returns:
        dict: Dictionary of environment variables that were set
    """
    env_vars = {
        "USER": "testuser",
        "HOME": "/home/testuser",
        "SHELL": "/bin/bash",
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "PWD": "/home/testuser/projects/test",
    }

    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    return env_vars


@pytest.fixture
def sample_git_repo(tmp_path: Path) -> Generator[Path, None, None]:
    """
    Create a temporary git repository for testing git-related features.

    This fixture creates a minimal git repository with an initial commit
    for testing git state detection and related functionality.

    Args:
        tmp_path: Pytest's tmp_path fixture

    Yields:
        Path: Path to the git repository root
    """
    repo_dir = tmp_path / "git_repo"
    repo_dir.mkdir()

    # Initialize git repo
    import subprocess

    subprocess.run(
        ["git", "init"],
        cwd=repo_dir,
        capture_output=True,
        check=True,
    )

    # Configure git for the test repo
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_dir,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_dir,
        capture_output=True,
        check=True,
    )

    # Create initial commit
    readme = repo_dir / "README.md"
    readme.write_text("# Test Repository\n")

    subprocess.run(
        ["git", "add", "README.md"],
        cwd=repo_dir,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo_dir,
        capture_output=True,
        check=True,
    )

    yield repo_dir


@pytest.fixture
def mock_llm_response() -> dict[str, str]:
    """
    Provide mock LLM API response data for testing.

    Returns sample responses that would come from LLM providers
    for testing command generation without making actual API calls.

    Returns:
        dict: Sample LLM response with explanation and command
    """
    return {
        "explanation": "I'll search for large files in your home directory.",
        "command": "find ~ -type f -size +100M",
        "confidence": 85,
    }


@pytest.fixture
def capture_output():
    """
    Helper fixture for capturing stdout/stderr in tests.

    Provides a context manager for capturing command output during tests.
    """
    from io import StringIO
    import sys

    class OutputCapture:
        def __enter__(self):
            self.stdout = StringIO()
            self.stderr = StringIO()
            self._old_stdout = sys.stdout
            self._old_stderr = sys.stderr
            sys.stdout = self.stdout
            sys.stderr = self.stderr
            return self

        def __exit__(self, *args):
            sys.stdout = self._old_stdout
            sys.stderr = self._old_stderr

        def get_stdout(self) -> str:
            return self.stdout.getvalue()

        def get_stderr(self) -> str:
            return self.stderr.getvalue()

    return OutputCapture
