"""
Tests for executor module.
"""

import os
import time
from unittest.mock import Mock, patch

import pytest

from hai_sh.executor import (
    CommandExecutionError,
    CommandInterruptedError,
    CommandTimeoutError,
    ExecutionResult,
    check_command_exists,
    execute_command,
    execute_interactive,
    execute_pipeline,
    get_command_path,
    get_shell_info,
    validate_shell_syntax,
)


# ============================================================================
# ExecutionResult Tests
# ============================================================================


@pytest.mark.unit
def test_execution_result_success():
    """Test ExecutionResult with successful execution."""
    result = ExecutionResult(
        command="echo hello",
        exit_code=0,
        stdout="hello\n",
        stderr="",
    )

    assert result.success is True
    assert result.exit_code == 0
    assert result.stdout == "hello\n"
    assert result.stderr == ""
    assert result.timed_out is False
    assert result.interrupted is False


@pytest.mark.unit
def test_execution_result_failure():
    """Test ExecutionResult with failed execution."""
    result = ExecutionResult(
        command="false",
        exit_code=1,
        stdout="",
        stderr="",
    )

    assert result.success is False
    assert result.exit_code == 1


@pytest.mark.unit
def test_execution_result_timeout():
    """Test ExecutionResult with timeout."""
    result = ExecutionResult(
        command="sleep 100",
        exit_code=-1,
        stdout="",
        stderr="",
        timed_out=True,
    )

    assert result.success is False
    assert result.timed_out is True


@pytest.mark.unit
def test_execution_result_interrupted():
    """Test ExecutionResult with interruption."""
    result = ExecutionResult(
        command="sleep 100",
        exit_code=-2,
        stdout="",
        stderr="Command interrupted by user",
        interrupted=True,
    )

    assert result.success is False
    assert result.interrupted is True


@pytest.mark.unit
def test_execution_result_repr():
    """Test ExecutionResult string representation."""
    result = ExecutionResult(
        command="echo test",
        exit_code=0,
        stdout="test\n",
    )

    repr_str = repr(result)
    assert "ExecutionResult" in repr_str
    assert "echo test" in repr_str
    assert "exit_code=0" in repr_str
    assert "success=True" in repr_str


# ============================================================================
# execute_command() Tests
# ============================================================================


@pytest.mark.unit
def test_execute_command_simple():
    """Test basic command execution."""
    result = execute_command("echo 'hello world'")

    assert result.success is True
    assert result.exit_code == 0
    assert "hello world" in result.stdout
    assert result.stderr == ""


@pytest.mark.unit
def test_execute_command_with_exit_code():
    """Test command execution with non-zero exit code."""
    result = execute_command("exit 42")

    assert result.success is False
    assert result.exit_code == 42


@pytest.mark.unit
def test_execute_command_with_stderr():
    """Test command execution with stderr output."""
    result = execute_command("echo 'error message' >&2")

    assert result.exit_code == 0
    assert "error message" in result.stderr


@pytest.mark.unit
def test_execute_command_multiline_output():
    """Test command with multiline output."""
    result = execute_command("echo 'line1'; echo 'line2'; echo 'line3'")

    assert result.success is True
    assert "line1" in result.stdout
    assert "line2" in result.stdout
    assert "line3" in result.stdout


@pytest.mark.unit
def test_execute_command_with_timeout():
    """Test command execution with timeout."""
    # This should complete before timeout
    result = execute_command("echo 'quick'", timeout=5)

    assert result.success is True
    assert "quick" in result.stdout


@pytest.mark.unit
def test_execute_command_timeout_expires():
    """Test command execution when timeout expires."""
    # This should timeout
    result = execute_command("sleep 10", timeout=1)

    assert result.success is False
    assert result.timed_out is True
    assert result.exit_code == -1


@pytest.mark.unit
def test_execute_command_no_timeout():
    """Test command execution with no timeout."""
    result = execute_command("echo 'no timeout'", timeout=None)

    assert result.success is True
    assert "no timeout" in result.stdout


@pytest.mark.unit
def test_execute_command_with_cwd(tmp_path):
    """Test command execution with custom working directory."""
    result = execute_command("pwd", cwd=str(tmp_path))

    assert result.success is True
    assert str(tmp_path) in result.stdout


@pytest.mark.unit
def test_execute_command_with_env():
    """Test command execution with custom environment."""
    env = os.environ.copy()
    env['TEST_VAR'] = 'test_value'

    result = execute_command("echo $TEST_VAR", env=env)

    assert result.success is True
    assert "test_value" in result.stdout


@pytest.mark.unit
def test_execute_command_preserves_cwd():
    """Test that execution preserves current working directory."""
    original_cwd = os.getcwd()

    result = execute_command("cd /tmp && pwd")

    # CWD should be unchanged after execution
    assert os.getcwd() == original_cwd
    assert result.success is True


@pytest.mark.unit
def test_execute_command_empty_command():
    """Test execute_command with empty command."""
    with pytest.raises(ValueError, match="non-empty string"):
        execute_command("")


@pytest.mark.unit
def test_execute_command_invalid_command_type():
    """Test execute_command with invalid command type."""
    with pytest.raises(ValueError, match="non-empty string"):
        execute_command(None)


@pytest.mark.unit
def test_execute_command_command_not_found():
    """Test execution of non-existent command."""
    result = execute_command("nonexistent_command_xyz_123")

    assert result.success is False
    assert result.exit_code != 0


@pytest.mark.unit
def test_execute_command_syntax_error():
    """Test execution of command with syntax error."""
    result = execute_command("echo 'unclosed quote")

    # Bash will report syntax error
    assert result.success is False
    assert result.exit_code != 0


# ============================================================================
# execute_interactive() Tests
# ============================================================================


@pytest.mark.unit
def test_execute_interactive_simple():
    """Test interactive command execution."""
    exit_code = execute_interactive("echo 'hello'")

    assert exit_code == 0


@pytest.mark.unit
def test_execute_interactive_with_failure():
    """Test interactive execution with failure."""
    exit_code = execute_interactive("exit 1")

    assert exit_code == 1


# ============================================================================
# check_command_exists() Tests
# ============================================================================


@pytest.mark.unit
def test_check_command_exists_true():
    """Test checking for existing commands."""
    assert check_command_exists("ls") is True
    assert check_command_exists("echo") is True
    assert check_command_exists("bash") is True


@pytest.mark.unit
def test_check_command_exists_false():
    """Test checking for non-existent commands."""
    assert check_command_exists("nonexistent_command_xyz_123") is False
    assert check_command_exists("fake_command_abc") is False


@pytest.mark.unit
def test_check_command_exists_empty():
    """Test checking for empty command name."""
    assert check_command_exists("") is False


# ============================================================================
# get_command_path() Tests
# ============================================================================


@pytest.mark.unit
def test_get_command_path_exists():
    """Test getting path for existing commands."""
    path = get_command_path("ls")

    assert path is not None
    assert "ls" in path
    assert path.startswith("/")


@pytest.mark.unit
def test_get_command_path_not_exists():
    """Test getting path for non-existent command."""
    path = get_command_path("nonexistent_command_xyz")

    assert path is None


@pytest.mark.unit
def test_get_command_path_builtin():
    """Test getting path for shell builtin."""
    # Some shells have 'echo' as both builtin and external
    path = get_command_path("echo")

    # May be builtin or external, but should have a path
    assert path is not None


# ============================================================================
# validate_shell_syntax() Tests
# ============================================================================


@pytest.mark.unit
def test_validate_shell_syntax_valid():
    """Test syntax validation for valid commands."""
    is_valid, error = validate_shell_syntax("echo 'hello'")

    assert is_valid is True
    assert error is None


@pytest.mark.unit
def test_validate_shell_syntax_valid_complex():
    """Test syntax validation for complex valid commands."""
    is_valid, error = validate_shell_syntax("for i in 1 2 3; do echo $i; done")

    assert is_valid is True
    assert error is None


@pytest.mark.unit
def test_validate_shell_syntax_invalid():
    """Test syntax validation for invalid commands."""
    is_valid, error = validate_shell_syntax("echo 'unclosed quote")

    assert is_valid is False
    assert error is not None
    assert len(error) > 0


@pytest.mark.unit
def test_validate_shell_syntax_invalid_brace():
    """Test syntax validation for unmatched braces."""
    is_valid, error = validate_shell_syntax("if [ true; then echo 'test'")

    assert is_valid is False
    assert error is not None


@pytest.mark.unit
def test_validate_shell_syntax_empty():
    """Test syntax validation for empty command."""
    is_valid, error = validate_shell_syntax("")

    # Empty command is technically valid
    assert is_valid is True


# ============================================================================
# execute_pipeline() Tests
# ============================================================================


@pytest.mark.unit
def test_execute_pipeline_simple():
    """Test simple pipeline execution."""
    commands = ["echo 'hello'", "echo 'world'"]
    results = execute_pipeline(commands)

    assert len(results) == 2
    assert all(r.success for r in results)
    assert "hello" in results[0].stdout
    assert "world" in results[1].stdout


@pytest.mark.unit
def test_execute_pipeline_empty():
    """Test pipeline with empty command list."""
    results = execute_pipeline([])

    assert results == []


@pytest.mark.unit
def test_execute_pipeline_stops_on_failure():
    """Test that pipeline stops on first failure."""
    commands = [
        "echo 'first'",
        "exit 1",  # This fails
        "echo 'third'",  # This should not execute
    ]
    results = execute_pipeline(commands)

    assert len(results) == 2  # Only first two commands
    assert results[0].success is True
    assert results[1].success is False


@pytest.mark.unit
def test_execute_pipeline_with_timeout():
    """Test pipeline with timeout."""
    commands = ["echo 'quick'", "echo 'fast'"]
    results = execute_pipeline(commands, timeout=5)

    assert len(results) == 2
    assert all(r.success for r in results)


# ============================================================================
# get_shell_info() Tests
# ============================================================================


@pytest.mark.unit
def test_get_shell_info():
    """Test getting shell information."""
    info = get_shell_info()

    assert 'shell' in info
    assert 'version' in info
    assert 'cwd' in info
    assert 'user' in info
    assert 'home' in info

    # Shell should be a path
    assert info['shell'].startswith('/')

    # CWD should be a valid path
    assert os.path.exists(info['cwd'])

    # User should not be empty
    assert len(info['user']) > 0


@pytest.mark.unit
def test_get_shell_info_cwd():
    """Test that shell info includes current working directory."""
    info = get_shell_info()

    assert info['cwd'] == os.getcwd()


@pytest.mark.unit
def test_get_shell_info_home():
    """Test that shell info includes home directory."""
    info = get_shell_info()

    assert os.path.exists(info['home'])
    assert info['home'].startswith('/')


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.unit
def test_integration_command_with_pipe():
    """Test execution of command with pipe."""
    result = execute_command("echo 'hello world' | grep 'world'")

    assert result.success is True
    assert "world" in result.stdout


@pytest.mark.unit
def test_integration_command_with_redirect():
    """Test execution of command with output redirection."""
    # Create a temp file path
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        temp_file = f.name

    try:
        result = execute_command(f"echo 'test output' > {temp_file}")

        assert result.success is True

        # Verify file was created
        with open(temp_file, 'r') as f:
            content = f.read()
            assert "test output" in content

    finally:
        # Cleanup
        if os.path.exists(temp_file):
            os.remove(temp_file)


@pytest.mark.unit
def test_integration_command_chain():
    """Test execution of chained commands."""
    result = execute_command("echo 'first' && echo 'second' && echo 'third'")

    assert result.success is True
    assert "first" in result.stdout
    assert "second" in result.stdout
    assert "third" in result.stdout


@pytest.mark.unit
def test_integration_command_with_variables():
    """Test execution with shell variables."""
    result = execute_command("VAR='test'; echo $VAR")

    assert result.success is True
    assert "test" in result.stdout


@pytest.mark.unit
def test_integration_full_workflow():
    """Test complete workflow: check, validate, execute."""
    command = "echo 'workflow test'"

    # Check syntax
    is_valid, error = validate_shell_syntax(command)
    assert is_valid is True

    # Execute
    result = execute_command(command)
    assert result.success is True
    assert "workflow test" in result.stdout

    # Verify result
    assert result.exit_code == 0
    assert not result.timed_out
    assert not result.interrupted
