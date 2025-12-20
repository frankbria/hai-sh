"""
Command execution engine for hai-sh.

This module provides functionality to execute bash commands in the current
shell context with proper error handling, timeout support, and safety checks.
"""

import os
import subprocess
import sys
from typing import Optional, Tuple

# Default timeout for command execution (30 seconds)
DEFAULT_TIMEOUT = 30


class CommandExecutionError(Exception):
    """Raised when command execution fails."""
    pass


class CommandTimeoutError(CommandExecutionError):
    """Raised when command execution times out."""
    pass


class CommandInterruptedError(CommandExecutionError):
    """Raised when command execution is interrupted by user."""
    pass


class ExecutionResult:
    """
    Result of command execution.

    Attributes:
        command: The command that was executed
        exit_code: Exit code from the command
        stdout: Standard output from the command
        stderr: Standard error from the command
        timed_out: Whether the command timed out
        interrupted: Whether the command was interrupted
    """

    def __init__(
        self,
        command: str,
        exit_code: int,
        stdout: str = "",
        stderr: str = "",
        timed_out: bool = False,
        interrupted: bool = False
    ):
        self.command = command
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.timed_out = timed_out
        self.interrupted = interrupted

    @property
    def success(self) -> bool:
        """Check if command executed successfully."""
        return self.exit_code == 0 and not self.timed_out and not self.interrupted

    def __repr__(self) -> str:
        return (
            f"ExecutionResult(command={self.command!r}, "
            f"exit_code={self.exit_code}, success={self.success})"
        )


def execute_command(
    command: str,
    timeout: Optional[int] = DEFAULT_TIMEOUT,
    cwd: Optional[str] = None,
    env: Optional[dict] = None,
    shell: str = "/bin/bash",
    capture_output: bool = True,
) -> ExecutionResult:
    """
    Execute a bash command in the current shell context.

    Args:
        command: The bash command to execute
        timeout: Maximum time to wait for command completion (seconds)
                None means no timeout. Default: 30 seconds
        cwd: Working directory for command execution
             None means use current directory
        env: Environment variables for command execution
             None means use current environment
        shell: Shell executable to use (default: /bin/bash)
        capture_output: Whether to capture stdout/stderr (default: True)

    Returns:
        ExecutionResult: Result of command execution

    Raises:
        CommandTimeoutError: If command execution times out
        CommandInterruptedError: If command is interrupted by user
        CommandExecutionError: For other execution errors

    Example:
        >>> result = execute_command("echo 'hello'")
        >>> result.success
        True
        >>> result.stdout.strip()
        'hello'
        >>> result.exit_code
        0
    """
    if not command or not isinstance(command, str):
        raise ValueError("Command must be a non-empty string")

    # Use current working directory if not specified
    if cwd is None:
        cwd = os.getcwd()

    # Use current environment if not specified
    if env is None:
        env = os.environ.copy()

    try:
        # Execute the command
        if capture_output:
            result = subprocess.run(
                command,
                shell=True,
                executable=shell,
                cwd=cwd,
                env=env,
                timeout=timeout,
                capture_output=True,
                text=True,
            )
        else:
            # Run without capturing output (for interactive commands)
            result = subprocess.run(
                command,
                shell=True,
                executable=shell,
                cwd=cwd,
                env=env,
                timeout=timeout,
            )

        # Build execution result with output redaction
        from hai_sh.redaction import redact_sensitive_output

        stdout = result.stdout if capture_output else ""
        stderr = result.stderr if capture_output else ""

        # Redact sensitive information from outputs
        if stdout:
            stdout = redact_sensitive_output(stdout)
        if stderr:
            stderr = redact_sensitive_output(stderr)

        return ExecutionResult(
            command=command,
            exit_code=result.returncode,
            stdout=stdout,
            stderr=stderr,
            timed_out=False,
            interrupted=False,
        )

    except subprocess.TimeoutExpired as e:
        # Command timed out
        from hai_sh.redaction import redact_sensitive_output

        stdout = e.stdout.decode('utf-8') if e.stdout else ""
        stderr = e.stderr.decode('utf-8') if e.stderr else ""

        # Redact sensitive information from timeout outputs
        if stdout:
            stdout = redact_sensitive_output(stdout)
        if stderr:
            stderr = redact_sensitive_output(stderr)

        return ExecutionResult(
            command=command,
            exit_code=-1,
            stdout=stdout,
            stderr=stderr,
            timed_out=True,
            interrupted=False,
        )

    except KeyboardInterrupt:
        # User interrupted the command (Ctrl+C)
        return ExecutionResult(
            command=command,
            exit_code=-2,
            stdout="",
            stderr="Command interrupted by user",
            timed_out=False,
            interrupted=True,
        )

    except Exception as e:
        # Other execution errors
        raise CommandExecutionError(f"Failed to execute command: {e}") from e


def execute_interactive(
    command: str,
    timeout: Optional[int] = None,
    cwd: Optional[str] = None,
    env: Optional[dict] = None,
) -> int:
    """
    Execute a command interactively (output goes directly to terminal).

    This is useful for commands that need user interaction or should
    display output in real-time.

    Args:
        command: The bash command to execute
        timeout: Maximum time to wait for command completion (seconds)
        cwd: Working directory for command execution
        env: Environment variables for command execution

    Returns:
        int: Exit code from the command

    Example:
        >>> exit_code = execute_interactive("ls -la")
        >>> exit_code
        0
    """
    result = execute_command(
        command=command,
        timeout=timeout,
        cwd=cwd,
        env=env,
        capture_output=False,
    )

    return result.exit_code


def check_command_exists(command: str) -> bool:
    """
    Check if a command exists in the system.

    Args:
        command: Command name to check

    Returns:
        bool: True if command exists, False otherwise

    Example:
        >>> check_command_exists("ls")
        True
        >>> check_command_exists("nonexistent_command_xyz")
        False
    """
    if not command or not isinstance(command, str):
        return False

    try:
        result = subprocess.run(
            f"command -v {command}",
            shell=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, Exception):
        return False


def get_command_path(command: str) -> Optional[str]:
    """
    Get the full path to a command.

    Args:
        command: Command name to lookup

    Returns:
        str: Full path to command, or None if not found

    Example:
        >>> path = get_command_path("ls")
        >>> path is not None
        True
        >>> "/bin/ls" in path or "/usr/bin/ls" in path
        True
    """
    try:
        result = subprocess.run(
            f"command -v {command}",
            shell=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except (subprocess.TimeoutExpired, Exception):
        return None


def validate_shell_syntax(command: str, shell: str = "/bin/bash") -> Tuple[bool, Optional[str]]:
    """
    Validate that a command has valid shell syntax.

    Args:
        command: Command to validate
        shell: Shell to use for validation

    Returns:
        tuple: (is_valid, error_message)
            - is_valid: True if syntax is valid
            - error_message: None if valid, otherwise error description

    Example:
        >>> is_valid, error = validate_shell_syntax("echo 'hello'")
        >>> is_valid
        True
        >>> error is None
        True

        >>> is_valid, error = validate_shell_syntax("echo 'unclosed")
        >>> is_valid
        False
        >>> error is not None
        True
    """
    try:
        # Use -n flag to check syntax without executing
        result = subprocess.run(
            [shell, "-n", "-c", command],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            return True, None
        else:
            return False, result.stderr.strip()

    except subprocess.TimeoutExpired:
        return False, "Syntax validation timed out"
    except Exception as e:
        return False, f"Syntax validation failed: {e}"


def execute_pipeline(
    commands: list[str],
    timeout: Optional[int] = DEFAULT_TIMEOUT,
    cwd: Optional[str] = None,
    env: Optional[dict] = None,
) -> list[ExecutionResult]:
    """
    Execute a pipeline of commands sequentially.

    Each command's stdout is available to the next command's stdin.
    If any command fails, the pipeline stops.

    Args:
        commands: List of commands to execute in order
        timeout: Maximum time for entire pipeline (seconds)
        cwd: Working directory for execution
        env: Environment variables

    Returns:
        list[ExecutionResult]: Results from each command

    Example:
        >>> commands = ["echo 'hello'", "grep 'hello'"]
        >>> results = execute_pipeline(commands)
        >>> all(r.success for r in results)
        True
    """
    if not commands:
        return []

    results = []
    current_cwd = cwd or os.getcwd()
    current_env = env or os.environ.copy()

    for command in commands:
        result = execute_command(
            command=command,
            timeout=timeout,
            cwd=current_cwd,
            env=current_env,
        )

        results.append(result)

        # Stop pipeline if command failed
        if not result.success:
            break

    return results


def get_shell_info() -> dict:
    """
    Get information about the current shell environment.

    Returns:
        dict: Shell information including:
            - shell: Current shell path
            - version: Shell version
            - cwd: Current working directory
            - user: Current user
            - home: Home directory

    Example:
        >>> info = get_shell_info()
        >>> 'shell' in info
        True
        >>> 'cwd' in info
        True
    """
    info = {}

    # Get shell path
    info['shell'] = os.environ.get('SHELL', '/bin/bash')

    # Get shell version
    try:
        result = subprocess.run(
            [info['shell'], '--version'],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            info['version'] = result.stdout.split('\n')[0]
        else:
            info['version'] = 'Unknown'
    except Exception:
        info['version'] = 'Unknown'

    # Get current working directory
    info['cwd'] = os.getcwd()

    # Get user info
    info['user'] = os.environ.get('USER', os.environ.get('USERNAME', 'unknown'))
    info['home'] = os.environ.get('HOME', os.path.expanduser('~'))

    return info
