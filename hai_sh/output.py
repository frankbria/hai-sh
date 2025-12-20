"""
Output formatting and display utilities for hai-sh.

This module provides functions to format command execution output for
terminal display with color preservation, truncation, and streaming support.
"""

import os
import re
import sys
from typing import Optional, Tuple

from hai_sh.executor import ExecutionResult

# ANSI color codes
COLORS = {
    'reset': '\033[0m',
    'bold': '\033[1m',
    'dim': '\033[2m',
    'red': '\033[31m',
    'green': '\033[32m',
    'yellow': '\033[33m',
    'blue': '\033[34m',
    'magenta': '\033[35m',
    'cyan': '\033[36m',
    'white': '\033[37m',
}

# ANSI escape sequence pattern
ANSI_ESCAPE_PATTERN = re.compile(r'\x1b\[[0-9;]*m')


def is_tty(stream=None) -> bool:
    """
    Check if output stream is a terminal (TTY).

    Args:
        stream: Stream to check (default: sys.stdout)

    Returns:
        bool: True if stream is a TTY

    Example:
        >>> is_tty()  # Returns True in terminal, False when piped
        True
    """
    if stream is None:
        stream = sys.stdout

    try:
        return stream.isatty()
    except (AttributeError, ValueError):
        return False


def should_use_color(
    force_color: Optional[bool] = None,
    stream=None,
    check_env: bool = True
) -> bool:
    """
    Determine if colors should be used in output.

    Respects:
    - force_color parameter (highest priority)
    - NO_COLOR environment variable
    - FORCE_COLOR environment variable
    - TTY detection (lowest priority)

    Args:
        force_color: Explicitly enable/disable colors (overrides everything)
        stream: Stream to check for TTY (default: sys.stdout)
        check_env: Whether to check environment variables

    Returns:
        bool: True if colors should be used

    Example:
        >>> should_use_color(force_color=True)
        True
        >>> should_use_color(force_color=False)
        False
    """
    # Explicit override
    if force_color is not None:
        return force_color

    # Check environment variables
    if check_env:
        # NO_COLOR takes precedence (https://no-color.org/)
        if os.environ.get('NO_COLOR'):
            return False

        # FORCE_COLOR enables colors even in non-TTY
        if os.environ.get('FORCE_COLOR'):
            return True

        # CLICOLOR=0 disables colors (BSD convention)
        if os.environ.get('CLICOLOR') == '0':
            return False

    # Check if output is a terminal
    return is_tty(stream)


def get_color_mode(
    force_color: Optional[bool] = None,
    stream=None
) -> str:
    """
    Get the color mode for output.

    Args:
        force_color: Explicitly enable/disable colors
        stream: Stream to check

    Returns:
        str: 'always', 'never', or 'auto'

    Example:
        >>> get_color_mode(force_color=True)
        'always'
        >>> get_color_mode(force_color=False)
        'never'
    """
    if force_color is True:
        return 'always'
    elif force_color is False:
        return 'never'
    else:
        return 'auto'


def has_ansi_codes(text: str) -> bool:
    """
    Check if text contains ANSI escape sequences.

    Args:
        text: Text to check

    Returns:
        bool: True if text contains ANSI codes

    Example:
        >>> has_ansi_codes("\\033[31mRed text\\033[0m")
        True
        >>> has_ansi_codes("Plain text")
        False
    """
    if not text or not isinstance(text, str):
        return False
    return ANSI_ESCAPE_PATTERN.search(text) is not None


def strip_ansi_codes(text: str) -> str:
    """
    Remove ANSI escape sequences from text.

    Args:
        text: Text to strip

    Returns:
        str: Text without ANSI codes

    Example:
        >>> strip_ansi_codes("\\033[31mRed text\\033[0m")
        'Red text'
    """
    if not text or not isinstance(text, str):
        return text
    return ANSI_ESCAPE_PATTERN.sub('', text)


def preserve_ansi_codes(text: str) -> str:
    """
    Ensure text is properly terminated with ANSI reset code if it contains colors.

    Args:
        text: Text to process

    Returns:
        str: Text with proper ANSI termination

    Example:
        >>> preserve_ansi_codes("\\033[31mRed text")
        '\\033[31mRed text\\033[0m'
    """
    if not text or not isinstance(text, str):
        return text

    # If text has ANSI codes but doesn't end with reset, add it
    if has_ansi_codes(text) and not text.endswith(COLORS['reset']):
        return text + COLORS['reset']

    return text


def truncate_output(
    text: str,
    max_lines: int = 100,
    head_lines: int = 50,
    tail_lines: int = 50,
    strip_ansi: bool = False
) -> Tuple[str, bool]:
    """
    Truncate output if it exceeds maximum lines.

    Args:
        text: Text to truncate
        max_lines: Maximum number of lines before truncation
        head_lines: Number of lines to keep from beginning
        tail_lines: Number of lines to keep from end
        strip_ansi: Whether to strip ANSI codes before counting lines

    Returns:
        tuple: (truncated_text, was_truncated)

    Example:
        >>> text = "\\n".join([f"Line {i}" for i in range(200)])
        >>> truncated, was_truncated = truncate_output(text, max_lines=100, head_lines=50, tail_lines=50)
        >>> was_truncated
        True
    """
    if not text or not isinstance(text, str):
        return text, False

    # Count lines (optionally without ANSI codes)
    text_for_counting = strip_ansi_codes(text) if strip_ansi else text
    lines = text.splitlines(keepends=True)

    if len(lines) <= max_lines:
        return text, False

    # Truncate: keep head and tail
    head = lines[:head_lines]
    tail = lines[-tail_lines:]

    truncation_msg = f"\n... [{len(lines) - head_lines - tail_lines} lines omitted] ...\n\n"

    truncated = ''.join(head) + truncation_msg + ''.join(tail)

    return truncated, True


def format_result_for_display(
    result: ExecutionResult,
    max_lines: int = 100,
    show_stderr: bool = True,
    colorize: bool = True,
    preserve_colors: bool = True
) -> str:
    """
    Format ExecutionResult for terminal display.

    Args:
        result: ExecutionResult object to format
        max_lines: Maximum lines before truncation (0 = no limit)
        show_stderr: Whether to include stderr in output
        colorize: Whether to add color to status messages
        preserve_colors: Whether to preserve ANSI codes in output

    Returns:
        str: Formatted output ready for display

    Example:
        >>> from hai_sh.executor import ExecutionResult
        >>> result = ExecutionResult("echo 'test'", 0, "test\\n", "")
        >>> output = format_result_for_display(result)
        >>> "test" in output
        True
    """
    if not isinstance(result, ExecutionResult):
        raise ValueError("result must be an ExecutionResult instance")

    parts = []

    # Add command header
    if colorize:
        parts.append(f"{COLORS['bold']}Command:{COLORS['reset']} {result.command}")
    else:
        parts.append(f"Command: {result.command}")

    # Add status
    if result.success:
        status = f"{COLORS['green']}✓ Success{COLORS['reset']}" if colorize else "✓ Success"
    elif result.timed_out:
        status = f"{COLORS['yellow']}⏱ Timeout{COLORS['reset']}" if colorize else "⏱ Timeout"
    elif result.interrupted:
        status = f"{COLORS['red']}✗ Interrupted{COLORS['reset']}" if colorize else "✗ Interrupted"
    else:
        status = f"{COLORS['red']}✗ Failed (exit code: {result.exit_code}){COLORS['reset']}" if colorize else f"✗ Failed (exit code: {result.exit_code})"

    parts.append(f"Status: {status}\n")

    # Add stdout
    if result.stdout:
        stdout_text = result.stdout

        # Preserve or strip ANSI codes
        if not preserve_colors:
            stdout_text = strip_ansi_codes(stdout_text)
        else:
            stdout_text = preserve_ansi_codes(stdout_text)

        # Truncate if needed
        if max_lines > 0:
            stdout_text, was_truncated = truncate_output(
                stdout_text,
                max_lines=max_lines,
                strip_ansi=not preserve_colors
            )

        if colorize:
            parts.append(f"\n{COLORS['bold']}Output:{COLORS['reset']}")
        else:
            parts.append("\nOutput:")

        parts.append(stdout_text)

    # Add stderr
    if show_stderr and result.stderr:
        stderr_text = result.stderr

        # Preserve or strip ANSI codes
        if not preserve_colors:
            stderr_text = strip_ansi_codes(stderr_text)
        else:
            stderr_text = preserve_ansi_codes(stderr_text)

        # Truncate if needed
        if max_lines > 0:
            stderr_text, was_truncated = truncate_output(
                stderr_text,
                max_lines=max_lines,
                strip_ansi=not preserve_colors
            )

        if colorize:
            parts.append(f"\n{COLORS['bold']}{COLORS['red']}Errors:{COLORS['reset']}")
        else:
            parts.append("\nErrors:")

        parts.append(stderr_text)

    return '\n'.join(parts)


def stream_output(
    result: ExecutionResult,
    stdout_stream=None,
    stderr_stream=None,
    preserve_colors: bool = True
) -> None:
    """
    Stream ExecutionResult output to file-like objects (e.g., sys.stdout).

    This function writes output in real-time simulation by processing
    the result and writing to the specified streams.

    Args:
        result: ExecutionResult to stream
        stdout_stream: Stream for stdout (default: sys.stdout)
        stderr_stream: Stream for stderr (default: sys.stderr)
        preserve_colors: Whether to preserve ANSI codes

    Example:
        >>> from hai_sh.executor import ExecutionResult
        >>> result = ExecutionResult("echo 'test'", 0, "test\\n", "")
        >>> stream_output(result)  # Outputs to sys.stdout
    """
    if stdout_stream is None:
        stdout_stream = sys.stdout
    if stderr_stream is None:
        stderr_stream = sys.stderr

    # Stream stdout
    if result.stdout:
        stdout_text = result.stdout
        if not preserve_colors:
            stdout_text = strip_ansi_codes(stdout_text)
        else:
            stdout_text = preserve_ansi_codes(stdout_text)

        stdout_stream.write(stdout_text)
        stdout_stream.flush()

    # Stream stderr
    if result.stderr:
        stderr_text = result.stderr
        if not preserve_colors:
            stderr_text = strip_ansi_codes(stderr_text)
        else:
            stderr_text = preserve_ansi_codes(stderr_text)

        stderr_stream.write(stderr_text)
        stderr_stream.flush()


def colorize_text(text: str, color: str) -> str:
    """
    Add ANSI color codes to text.

    Args:
        text: Text to colorize
        color: Color name (red, green, yellow, blue, magenta, cyan, white)

    Returns:
        str: Colorized text with reset code

    Example:
        >>> text = colorize_text("Error message", "red")
        >>> "\\033[31m" in text
        True
    """
    if not text or not isinstance(text, str):
        return text

    if color not in COLORS:
        return text

    return f"{COLORS[color]}{text}{COLORS['reset']}"


def get_visible_length(text: str) -> int:
    """
    Get the visible length of text (without ANSI codes).

    Args:
        text: Text to measure

    Returns:
        int: Visible length

    Example:
        >>> get_visible_length("\\033[31mRed text\\033[0m")
        8
        >>> get_visible_length("Plain text")
        10
    """
    if not text or not isinstance(text, str):
        return 0

    return len(strip_ansi_codes(text))
