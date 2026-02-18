"""
Test utilities and helper functions for hai-sh tests.
"""

from pathlib import Path
from typing import Any

from tests.conftest import OLLAMA_TEST_MODEL


def create_sample_config(config_dir: Path, provider: str = "ollama") -> Path:
    """
    Create a sample config file for testing.

    Args:
        config_dir: Directory to create config in
        provider: LLM provider to configure (default: "ollama")

    Returns:
        Path: Path to created config file
    """
    import yaml

    config_data = {
        "provider": provider,
        "model": OLLAMA_TEST_MODEL if provider == "ollama" else "gpt-4o-mini",
        "providers": {
            "openai": {
                "api_key": "sk-test-key",
                "model": "gpt-4o-mini",
            },
            "ollama": {
                "base_url": "http://localhost:11434",
                "model": OLLAMA_TEST_MODEL,
            },
        },
        "context": {
            "include_history": True,
            "include_git_state": True,
        },
    }

    config_file = config_dir / "config.yaml"
    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    return config_file


def create_sample_command_output(command: str, success: bool = True) -> dict[str, Any]:
    """
    Create sample command execution output for testing.

    Args:
        command: The command that was executed
        success: Whether the command succeeded (default: True)

    Returns:
        dict: Sample command output with stdout, stderr, and exit code
    """
    if success:
        return {
            "command": command,
            "stdout": f"Output from: {command}\n",
            "stderr": "",
            "exit_code": 0,
        }
    else:
        return {
            "command": command,
            "stdout": "",
            "stderr": f"Error executing: {command}\n",
            "exit_code": 1,
        }


def assert_valid_json_response(response: dict[str, Any]) -> None:
    """
    Assert that a response has valid LLM JSON response structure.

    Args:
        response: Response dictionary to validate

    Raises:
        AssertionError: If response structure is invalid
    """
    assert "explanation" in response, "Response missing 'explanation' field"
    assert "command" in response, "Response missing 'command' field"
    assert isinstance(response["explanation"], str), "Explanation must be a string"
    assert isinstance(response["command"], str), "Command must be a string"

    if "confidence" in response:
        assert isinstance(response["confidence"], (int, float)), "Confidence must be numeric"
        assert 0 <= response["confidence"] <= 100, "Confidence must be between 0 and 100"
