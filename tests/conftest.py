"""
Pytest configuration and shared fixtures for hai-sh tests.
"""

import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest
import requests
import yaml

# Default model used for Ollama integration tests.
# Override via HAI_TEST_OLLAMA_MODEL env var (e.g., HAI_TEST_OLLAMA_MODEL=mistral pytest -m ollama)
OLLAMA_TEST_MODEL = os.environ.get("HAI_TEST_OLLAMA_MODEL", "llama3.2")


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


# Provider-specific test configuration fixtures


@pytest.fixture
def test_config_openai(tmp_path: Path) -> Generator[Path, None, None]:
    """
    Create temporary config file for OpenAI provider testing.

    This fixture creates an isolated config that uses the OPENAI_API_KEY
    environment variable, ensuring tests don't interfere with user's
    ~/.hai/config.yaml.

    Args:
        tmp_path: Pytest's tmp_path fixture

    Yields:
        Path: Path to temporary config file

    Raises:
        pytest.skip: If OPENAI_API_KEY is not set
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY environment variable not set")

    config_dir = tmp_path / ".hai"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"

    config_content = {
        "provider": "openai",
        "providers": {
            "openai": {
                "api_key": api_key,
                "model": "gpt-4o-mini",
            }
        },
        "context": {
            "include_history": True,
            "history_length": 10,
            "include_env_vars": True,
            "include_git_state": True,
        },
        "output": {
            "show_conversation": True,
            "show_reasoning": True,
            "use_colors": False,  # Disable colors for cleaner test output
        },
    }

    config_file.write_text(yaml.dump(config_content))
    yield config_file


@pytest.fixture
def test_config_anthropic(tmp_path: Path) -> Generator[Path, None, None]:
    """
    Create temporary config file for Anthropic provider testing.

    This fixture creates an isolated config that uses the ANTHROPIC_API_KEY
    environment variable, ensuring tests don't interfere with user's
    ~/.hai/config.yaml.

    Args:
        tmp_path: Pytest's tmp_path fixture

    Yields:
        Path: Path to temporary config file

    Raises:
        pytest.skip: If ANTHROPIC_API_KEY is not set
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY environment variable not set")

    config_dir = tmp_path / ".hai"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"

    config_content = {
        "provider": "anthropic",
        "providers": {
            "anthropic": {
                "api_key": api_key,
                "model": "claude-sonnet-4-5",
            }
        },
        "context": {
            "include_history": True,
            "history_length": 10,
            "include_env_vars": True,
            "include_git_state": True,
        },
        "output": {
            "show_conversation": True,
            "show_reasoning": True,
            "use_colors": False,  # Disable colors for cleaner test output
        },
    }

    config_file.write_text(yaml.dump(config_content))
    yield config_file


@pytest.fixture
def test_config_ollama(tmp_path: Path) -> Generator[Path, None, None]:
    """
    Create temporary config file for Ollama provider testing.

    This fixture creates an isolated config for Ollama with default
    localhost configuration, ensuring tests don't interfere with user's
    ~/.hai/config.yaml.

    Args:
        tmp_path: Pytest's tmp_path fixture

    Yields:
        Path: Path to temporary config file

    Raises:
        pytest.skip: If Ollama server is not running or model is unavailable
    """
    if not is_ollama_available():
        pytest.skip("Ollama not running on localhost:11434")
    if not is_ollama_model_available(OLLAMA_TEST_MODEL):
        pytest.skip(f"Ollama model '{OLLAMA_TEST_MODEL}' not available")

    config_dir = tmp_path / ".hai"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"

    config_content = {
        "provider": "ollama",
        "providers": {
            "ollama": {
                "base_url": "http://localhost:11434",
                "model": OLLAMA_TEST_MODEL,
            }
        },
        "context": {
            "include_history": True,
            "history_length": 10,
            "include_env_vars": True,
            "include_git_state": True,
        },
        "output": {
            "show_conversation": True,
            "show_reasoning": True,
            "use_colors": False,  # Disable colors for cleaner test output
        },
    }

    config_file.write_text(yaml.dump(config_content))
    yield config_file


# Helper functions for provider availability checking


def is_openai_available() -> bool:
    """
    Check if OpenAI provider is available for testing.

    Returns:
        bool: True if OPENAI_API_KEY is set and TEST_OPENAI is enabled
    """
    return (
        os.environ.get("OPENAI_API_KEY") is not None and os.environ.get("TEST_OPENAI", "0") == "1"
    )


def is_anthropic_available() -> bool:
    """
    Check if Anthropic provider is available for testing.

    Returns:
        bool: True if ANTHROPIC_API_KEY is set and TEST_ANTHROPIC is enabled
    """
    return (
        os.environ.get("ANTHROPIC_API_KEY") is not None
        and os.environ.get("TEST_ANTHROPIC", "0") == "1"
    )


def is_ollama_available() -> bool:
    """
    Check if Ollama provider is available for testing.

    Returns:
        bool: True if Ollama is running on localhost:11434
    """
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        return response.status_code == 200
    except (requests.RequestException, OSError):
        return False


def is_ollama_model_available(model: str) -> bool:
    """
    Check if a specific Ollama model is available locally.

    Args:
        model: The model name to check (e.g., "llama3.2")

    Returns:
        bool: True if the model is available on the local Ollama server
    """
    try:
        response = requests.post(
            "http://localhost:11434/api/show",
            json={"name": model},
            timeout=5,
        )
        return response.status_code == 200
    except (requests.RequestException, OSError):
        return False


# Skip decorators for provider-specific tests

skip_if_no_openai = pytest.mark.skipif(
    not is_openai_available(),
    reason="OpenAI provider not available (set OPENAI_API_KEY and TEST_OPENAI=1)",
)

skip_if_no_anthropic = pytest.mark.skipif(
    not is_anthropic_available(),
    reason="Anthropic provider not available (set ANTHROPIC_API_KEY and TEST_ANTHROPIC=1)",
)

skip_if_no_ollama = pytest.mark.skipif(
    not is_ollama_available() or not is_ollama_model_available(OLLAMA_TEST_MODEL),
    reason=f"Ollama not running on localhost:11434 or model '{OLLAMA_TEST_MODEL}' not available",
)
