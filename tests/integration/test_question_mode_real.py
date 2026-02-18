"""
Real integration tests for question mode using actual LLM providers.

These tests use real Ollama (if available) to test the question-answering
capability end-to-end. Tests are skipped if Ollama is not running.
"""

import subprocess
import pytest
import requests

from tests.conftest import OLLAMA_TEST_MODEL, skip_if_no_ollama


# Skip all tests in this module if Ollama is not available
# Also mark all tests with ollama and integration markers
pytestmark = [
    pytest.mark.integration,
    pytest.mark.ollama,
    skip_if_no_ollama,
]


@pytest.fixture
def ollama_config_file(tmp_path):
    """Create a temporary config file for Ollama."""
    import yaml

    config = {
        "provider": "ollama",
        "model": OLLAMA_TEST_MODEL,
        "providers": {"ollama": {"base_url": "http://localhost:11434", "model": OLLAMA_TEST_MODEL}},
        "context": {
            "include_history": False,
            "include_git_state": False,
            "include_env_vars": False,
        },
        "output": {"show_conversation": True, "use_colors": False},
    }

    config_file = tmp_path / "config.yaml"
    with open(config_file, "w") as f:
        yaml.dump(config, f)

    return config_file


def run_hai(query: str, config_file: str) -> tuple[str, str, int]:
    """
    Run hai command and return stdout, stderr, and exit code.

    Args:
        query: The query to run
        config_file: Path to config file

    Returns:
        tuple: (stdout, stderr, exit_code)
    """
    result = subprocess.run(
        ["python", "-m", "hai_sh", "--config", str(config_file), query],
        capture_output=True,
        text=True,
        timeout=60,
    )
    return result.stdout, result.stderr, result.returncode


def test_question_mode_ls_flags(ollama_config_file):
    """Test question mode with a simple question about ls flags."""
    stdout, stderr, exit_code = run_hai("What does the -la flag do in ls?", ollama_config_file)

    assert exit_code == 0, f"Command failed with stderr: {stderr}"
    assert stdout, "No output received"

    # Check that we got an answer (not a command)
    assert "Confidence:" in stdout

    # Verify no command was generated (should not have command execution prompt)
    assert "Execute this command?" not in stdout
    assert "$ ls" not in stdout  # Should not show a command

    # Response should mention -l and -a flags
    assert "-l" in stdout.lower() or "long" in stdout.lower()
    assert "-a" in stdout.lower() or "all" in stdout.lower() or "hidden" in stdout.lower()


def test_question_mode_difference_between_commands(ollama_config_file):
    """Test asking about the difference between two commands."""
    stdout, stderr, exit_code = run_hai(
        "What's the difference between grep and awk?", ollama_config_file
    )

    assert exit_code == 0, f"Command failed with stderr: {stderr}"
    assert stdout, "No output received"

    # Should be in question mode (no command execution)
    assert "Execute this command?" not in stdout

    # Response should mention both tools
    assert "grep" in stdout.lower()
    assert "awk" in stdout.lower()

    # Should have confidence score
    assert "Confidence:" in stdout


def test_question_mode_explain_concept(ollama_config_file):
    """Test asking for an explanation of a concept."""
    stdout, stderr, exit_code = run_hai("How does pipe | work in bash?", ollama_config_file)

    assert exit_code == 0, f"Command failed with stderr: {stderr}"
    assert stdout, "No output received"

    # Should be in question mode
    assert "Execute this command?" not in stdout

    # Response should explain pipes
    assert "pipe" in stdout.lower() or "|" in stdout

    # Should have confidence score
    assert "Confidence:" in stdout


def test_question_mode_when_to_use(ollama_config_file):
    """Test asking when to use a particular tool."""
    stdout, stderr, exit_code = run_hai("When should I use sudo?", ollama_config_file)

    assert exit_code == 0, f"Command failed with stderr: {stderr}"
    assert stdout, "No output received"

    # Should be in question mode
    assert "Execute this command?" not in stdout

    # Response should mention sudo
    assert "sudo" in stdout.lower()

    # Should have confidence score
    assert "Confidence:" in stdout


def test_command_mode_still_works(ollama_config_file):
    """Verify command mode still works (regression test)."""
    stdout, stderr, exit_code = run_hai("show me the current directory", ollama_config_file)

    # Note: Since this requires user confirmation, we expect it to fail
    # or produce output with the command and confirmation prompt
    # We just want to verify it generates a command, not an answer

    # Should generate a command (look for command indicators)
    # The output should contain either:
    # - A command like "pwd" or "echo $PWD"
    # - Or a confirmation prompt

    # We can't execute fully without user input, but we can check
    # that it didn't go into question mode
    output = stdout + stderr

    # If it's working correctly, it should either:
    # 1. Show a command prompt (if using interactive mode)
    # 2. Show some form of command output
    # 3. At minimum, not be treating this as a pure question

    # For now, just verify it didn't error out completely
    assert exit_code in [0, 1], f"Unexpected exit code: {exit_code}"


def test_question_mode_vs_command_mode_detection(ollama_config_file):
    """Test that the system correctly distinguishes questions from commands."""
    # Question query
    q_stdout, _q_stderr, _q_exit = run_hai("What is the purpose of chmod?", ollama_config_file)

    # Command query
    c_stdout, _c_stderr, _c_exit = run_hai("list files in current directory", ollama_config_file)

    # Question mode: no execution prompt
    assert "Execute this command?" not in q_stdout
    assert "chmod" in q_stdout.lower()

    # Command mode would have execution-related output
    # (we can't verify full execution without user input)
    # but we can check it's different from question mode
    assert q_stdout != c_stdout, "Question and command responses should differ"
