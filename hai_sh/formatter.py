"""
Dual-layer output formatter for hai-sh.

This module provides formatting that separates the conversation layer
(LLM reasoning and explanations) from the execution layer (commands and output).
"""

from typing import Optional

from hai_sh.executor import ExecutionResult
from hai_sh.output import (
    COLORS,
    colorize_text,
    format_result_for_display,
    has_ansi_codes,
    preserve_ansi_codes,
    strip_ansi_codes,
    truncate_output,
)


# Layer headers and separators
CONVERSATION_HEADER = "━━━ Conversation ━━━"
EXECUTION_HEADER = "━━━ Execution ━━━"
SECTION_SEPARATOR = "─" * 50
LAYER_SEPARATOR = "\n" + "═" * 50 + "\n"


def format_conversation_layer(
    explanation: str,
    confidence: Optional[int] = None,
    colorize: bool = True,
    show_header: bool = True,
) -> str:
    """
    Format the conversation layer (LLM explanation/reasoning).

    Args:
        explanation: LLM explanation text
        confidence: Optional confidence score (0-100)
        colorize: Whether to add colors
        show_header: Whether to show layer header

    Returns:
        str: Formatted conversation layer

    Example:
        >>> explanation = "I'll search for large files in your home directory."
        >>> output = format_conversation_layer(explanation, confidence=85)
        >>> "Conversation" in output
        True
    """
    parts = []

    # Add header
    if show_header:
        if colorize:
            header = f"{COLORS['cyan']}{COLORS['bold']}{CONVERSATION_HEADER}{COLORS['reset']}"
        else:
            header = CONVERSATION_HEADER
        parts.append(header)

    # Add explanation
    if explanation:
        explanation_text = explanation.strip()

        # Preserve colors if present, otherwise optionally colorize
        if colorize and not has_ansi_codes(explanation_text):
            explanation_text = f"{COLORS['white']}{explanation_text}{COLORS['reset']}"
        elif has_ansi_codes(explanation_text):
            explanation_text = preserve_ansi_codes(explanation_text)

        parts.append(explanation_text)

    # Add confidence indicator if provided
    if confidence is not None:
        confidence_text = format_confidence(confidence, colorize=colorize)
        parts.append(confidence_text)

    return "\n".join(parts)


def format_execution_layer(
    command: str,
    result: Optional[ExecutionResult] = None,
    colorize: bool = True,
    show_header: bool = True,
    max_output_lines: int = 100,
) -> str:
    """
    Format the execution layer (command and output).

    Args:
        command: The command being executed
        result: Optional execution result
        colorize: Whether to add colors
        show_header: Whether to show layer header
        max_output_lines: Maximum lines of output to show (0 = no limit)

    Returns:
        str: Formatted execution layer

    Example:
        >>> from hai_sh.executor import ExecutionResult
        >>> result = ExecutionResult("ls", 0, "file1.txt\\nfile2.txt\\n", "")
        >>> output = format_execution_layer("ls", result)
        >>> "Execution" in output
        True
    """
    parts = []

    # Add header
    if show_header:
        if colorize:
            header = f"{COLORS['cyan']}{COLORS['bold']}{EXECUTION_HEADER}{COLORS['reset']}"
        else:
            header = EXECUTION_HEADER
        parts.append(header)

    # Add command prompt
    command_prompt = format_command_prompt(command, colorize=colorize)
    parts.append(command_prompt)

    # Add result if provided
    if result:
        output_text = format_execution_result(
            result,
            colorize=colorize,
            max_lines=max_output_lines
        )
        parts.append(output_text)

    return "\n".join(parts)


def format_command_prompt(command: str, colorize: bool = True) -> str:
    """
    Format command with shell prompt prefix.

    Args:
        command: The command to format
        colorize: Whether to add colors

    Returns:
        str: Formatted command with prompt

    Example:
        >>> format_command_prompt("ls -la", colorize=False)
        '$ ls -la'
    """
    if colorize:
        prompt = f"{COLORS['green']}{COLORS['bold']}${COLORS['reset']}"
        command_text = f"{COLORS['white']}{command}{COLORS['reset']}"
        return f"{prompt} {command_text}"
    else:
        return f"$ {command}"


def format_execution_result(
    result: ExecutionResult,
    colorize: bool = True,
    max_lines: int = 100,
) -> str:
    """
    Format execution result (stdout/stderr).

    Args:
        result: Execution result to format
        colorize: Whether to add colors
        max_lines: Maximum lines to show (0 = no limit)

    Returns:
        str: Formatted result

    Example:
        >>> from hai_sh.executor import ExecutionResult
        >>> result = ExecutionResult("echo test", 0, "test\\n", "")
        >>> output = format_execution_result(result, colorize=False)
        >>> "test" in output
        True
    """
    parts = []

    # Format stdout
    if result.stdout:
        stdout_text = result.stdout

        # Truncate if needed
        if max_lines > 0:
            stdout_text, was_truncated = truncate_output(
                stdout_text,
                max_lines=max_lines,
                strip_ansi=False
            )

        # Preserve colors
        stdout_text = preserve_ansi_codes(stdout_text)
        parts.append(stdout_text.rstrip())

    # Format stderr if present
    if result.stderr:
        stderr_text = result.stderr

        # Truncate if needed
        if max_lines > 0:
            stderr_text, was_truncated = truncate_output(
                stderr_text,
                max_lines=max_lines,
                strip_ansi=False
            )

        # Add error header and colorize
        if colorize:
            error_header = f"\n{COLORS['red']}{COLORS['bold']}Errors:{COLORS['reset']}"
            stderr_text = f"{COLORS['red']}{stderr_text}{COLORS['reset']}"
        else:
            error_header = "\nErrors:"

        parts.append(error_header)
        parts.append(stderr_text.rstrip())

    # Add status indicator if command failed
    if not result.success:
        status = format_execution_status(result, colorize=colorize)
        parts.append(f"\n{status}")

    return "\n".join(parts) if parts else ""


def format_execution_status(result: ExecutionResult, colorize: bool = True) -> str:
    """
    Format execution status message.

    Args:
        result: Execution result
        colorize: Whether to add colors

    Returns:
        str: Status message

    Example:
        >>> from hai_sh.executor import ExecutionResult
        >>> result = ExecutionResult("false", 1, "", "")
        >>> status = format_execution_status(result, colorize=False)
        >>> "exit code: 1" in status
        True
    """
    if result.success:
        return ""

    if result.timed_out:
        msg = "⏱ Command timed out"
    elif result.interrupted:
        msg = "✗ Command interrupted by user"
    else:
        msg = f"✗ Command failed (exit code: {result.exit_code})"

    if colorize:
        return colorize_text(msg, "red")
    else:
        return msg


def format_confidence(confidence: int, colorize: bool = True) -> str:
    """
    Format confidence score with visual indicator.

    Args:
        confidence: Confidence score (0-100)
        colorize: Whether to add colors

    Returns:
        str: Formatted confidence indicator

    Example:
        >>> format_confidence(85, colorize=False)
        'Confidence: 85% [████████··]'
    """
    # Clamp confidence to 0-100
    confidence = max(0, min(100, confidence))

    # Create visual bar (10 segments)
    filled = int(confidence / 10)
    bar = "█" * filled + "·" * (10 - filled)

    text = f"Confidence: {confidence}% [{bar}]"

    if colorize:
        # Color based on confidence level
        if confidence >= 80:
            color = "green"
        elif confidence >= 60:
            color = "yellow"
        else:
            color = "red"

        return colorize_text(text, color)
    else:
        return text


def format_dual_layer(
    explanation: str,
    command: str,
    result: Optional[ExecutionResult] = None,
    confidence: Optional[int] = None,
    colorize: bool = True,
    show_headers: bool = True,
    max_output_lines: int = 100,
) -> str:
    """
    Format output with dual-layer separation.

    Combines conversation layer (explanation) and execution layer (command/output)
    with clear visual separation.

    Args:
        explanation: LLM explanation/reasoning
        command: Command to execute
        result: Optional execution result
        confidence: Optional confidence score
        colorize: Whether to add colors
        show_headers: Whether to show layer headers
        max_output_lines: Maximum output lines (0 = no limit)

    Returns:
        str: Formatted dual-layer output

    Example:
        >>> from hai_sh.executor import ExecutionResult
        >>> explanation = "I'll list the files in the current directory."
        >>> command = "ls"
        >>> result = ExecutionResult("ls", 0, "file1.txt\\nfile2.txt\\n", "")
        >>> output = format_dual_layer(explanation, command, result, confidence=90)
        >>> "Conversation" in output and "Execution" in output
        True
    """
    parts = []

    # Conversation layer
    conversation = format_conversation_layer(
        explanation,
        confidence=confidence,
        colorize=colorize,
        show_header=show_headers
    )
    parts.append(conversation)

    # Layer separator
    if colorize:
        separator = f"{COLORS['dim']}{LAYER_SEPARATOR}{COLORS['reset']}"
    else:
        separator = LAYER_SEPARATOR
    parts.append(separator)

    # Execution layer
    execution = format_execution_layer(
        command,
        result=result,
        colorize=colorize,
        show_header=show_headers,
        max_output_lines=max_output_lines
    )
    parts.append(execution)

    return "\n".join(parts)


def format_conversation_only(
    explanation: str,
    confidence: Optional[int] = None,
    colorize: bool = True,
) -> str:
    """
    Format conversation-only output (no execution).

    Use when showing LLM response without executing a command.

    Args:
        explanation: LLM explanation
        confidence: Optional confidence score
        colorize: Whether to add colors

    Returns:
        str: Formatted output

    Example:
        >>> output = format_conversation_only("This command is unsafe.", confidence=95)
        >>> "unsafe" in output
        True
    """
    return format_conversation_layer(
        explanation,
        confidence=confidence,
        colorize=colorize,
        show_header=False  # No header for conversation-only
    )


def format_execution_only(
    command: str,
    result: Optional[ExecutionResult] = None,
    colorize: bool = True,
    max_output_lines: int = 100,
) -> str:
    """
    Format execution-only output (no conversation).

    Use when executing a command without LLM explanation.

    Args:
        command: Command being executed
        result: Optional execution result
        colorize: Whether to add colors
        max_output_lines: Maximum output lines

    Returns:
        str: Formatted output

    Example:
        >>> from hai_sh.executor import ExecutionResult
        >>> result = ExecutionResult("pwd", 0, "/home/user\\n", "")
        >>> output = format_execution_only("pwd", result, colorize=False)
        >>> "$ pwd" in output
        True
    """
    return format_execution_layer(
        command,
        result=result,
        colorize=colorize,
        show_header=False,  # No header for execution-only
        max_output_lines=max_output_lines
    )


def strip_formatting(text: str) -> str:
    """
    Remove all formatting (colors, headers) from output.

    Useful for logging or non-terminal output.

    Args:
        text: Formatted text

    Returns:
        str: Plain text without formatting

    Example:
        >>> formatted = format_conversation_only("Test", colorize=True)
        >>> plain = strip_formatting(formatted)
        >>> "\\033[" not in plain
        True
    """
    # Remove ANSI codes
    text = strip_ansi_codes(text)

    # Remove layer separators
    text = text.replace(LAYER_SEPARATOR, "\n")

    # Remove headers (without ANSI codes)
    text = text.replace(CONVERSATION_HEADER, "")
    text = text.replace(EXECUTION_HEADER, "")
    text = text.replace(SECTION_SEPARATOR, "")

    # Clean up extra whitespace
    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines)

    # Remove multiple consecutive blank lines
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")

    return text.strip()
