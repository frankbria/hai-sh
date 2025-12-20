"""
Tests for output module.
"""

import io
import sys
from unittest.mock import Mock

import pytest

from hai_sh.executor import ExecutionResult
from hai_sh.output import (
    ANSI_ESCAPE_PATTERN,
    COLORS,
    colorize_text,
    format_result_for_display,
    get_visible_length,
    has_ansi_codes,
    preserve_ansi_codes,
    stream_output,
    strip_ansi_codes,
    truncate_output,
)


# ============================================================================
# ANSI Code Detection Tests
# ============================================================================


@pytest.mark.unit
def test_has_ansi_codes_with_colors():
    """Test detection of ANSI codes in colored text."""
    text = "\033[31mRed text\033[0m"
    assert has_ansi_codes(text) is True


@pytest.mark.unit
def test_has_ansi_codes_plain_text():
    """Test detection of ANSI codes in plain text."""
    text = "Plain text without colors"
    assert has_ansi_codes(text) is False


@pytest.mark.unit
def test_has_ansi_codes_empty_string():
    """Test detection with empty string."""
    assert has_ansi_codes("") is False


@pytest.mark.unit
def test_has_ansi_codes_none():
    """Test detection with None."""
    assert has_ansi_codes(None) is False


@pytest.mark.unit
def test_has_ansi_codes_multiple_colors():
    """Test detection with multiple color codes."""
    text = "\033[31mRed\033[0m and \033[32mGreen\033[0m"
    assert has_ansi_codes(text) is True


# ============================================================================
# ANSI Code Stripping Tests
# ============================================================================


@pytest.mark.unit
def test_strip_ansi_codes_with_colors():
    """Test stripping ANSI codes from colored text."""
    text = "\033[31mRed text\033[0m"
    result = strip_ansi_codes(text)
    assert result == "Red text"


@pytest.mark.unit
def test_strip_ansi_codes_plain_text():
    """Test stripping ANSI codes from plain text."""
    text = "Plain text"
    result = strip_ansi_codes(text)
    assert result == "Plain text"


@pytest.mark.unit
def test_strip_ansi_codes_empty_string():
    """Test stripping ANSI codes from empty string."""
    result = strip_ansi_codes("")
    assert result == ""


@pytest.mark.unit
def test_strip_ansi_codes_none():
    """Test stripping ANSI codes from None."""
    result = strip_ansi_codes(None)
    assert result is None


@pytest.mark.unit
def test_strip_ansi_codes_multiple_colors():
    """Test stripping multiple ANSI codes."""
    text = "\033[31mRed\033[0m and \033[32mGreen\033[0m text"
    result = strip_ansi_codes(text)
    assert result == "Red and Green text"


@pytest.mark.unit
def test_strip_ansi_codes_bold_and_colors():
    """Test stripping bold and color codes."""
    text = "\033[1m\033[31mBold Red\033[0m"
    result = strip_ansi_codes(text)
    assert result == "Bold Red"


# ============================================================================
# ANSI Code Preservation Tests
# ============================================================================


@pytest.mark.unit
def test_preserve_ansi_codes_with_reset():
    """Test preservation when text already has reset code."""
    text = "\033[31mRed text\033[0m"
    result = preserve_ansi_codes(text)
    assert result == "\033[31mRed text\033[0m"


@pytest.mark.unit
def test_preserve_ansi_codes_without_reset():
    """Test preservation when text lacks reset code."""
    text = "\033[31mRed text"
    result = preserve_ansi_codes(text)
    assert result == "\033[31mRed text\033[0m"


@pytest.mark.unit
def test_preserve_ansi_codes_plain_text():
    """Test preservation with plain text."""
    text = "Plain text"
    result = preserve_ansi_codes(text)
    assert result == "Plain text"


@pytest.mark.unit
def test_preserve_ansi_codes_empty_string():
    """Test preservation with empty string."""
    result = preserve_ansi_codes("")
    assert result == ""


@pytest.mark.unit
def test_preserve_ansi_codes_none():
    """Test preservation with None."""
    result = preserve_ansi_codes(None)
    assert result is None


# ============================================================================
# Output Truncation Tests
# ============================================================================


@pytest.mark.unit
def test_truncate_output_short_text():
    """Test truncation with text shorter than max_lines."""
    text = "\n".join([f"Line {i}" for i in range(50)])
    result, was_truncated = truncate_output(text, max_lines=100)

    assert was_truncated is False
    assert result == text


@pytest.mark.unit
def test_truncate_output_long_text():
    """Test truncation with text longer than max_lines."""
    text = "\n".join([f"Line {i}" for i in range(200)])
    result, was_truncated = truncate_output(text, max_lines=100, head_lines=50, tail_lines=50)

    assert was_truncated is True
    assert "Line 0" in result  # First line
    assert "Line 49" in result  # Last head line
    assert "Line 150" in result  # First tail line
    assert "Line 199" in result  # Last line
    assert "lines omitted" in result


@pytest.mark.unit
def test_truncate_output_exact_max():
    """Test truncation with text exactly at max_lines."""
    text = "\n".join([f"Line {i}" for i in range(100)])
    result, was_truncated = truncate_output(text, max_lines=100)

    assert was_truncated is False
    assert result == text


@pytest.mark.unit
def test_truncate_output_empty_string():
    """Test truncation with empty string."""
    result, was_truncated = truncate_output("")

    assert was_truncated is False
    assert result == ""


@pytest.mark.unit
def test_truncate_output_none():
    """Test truncation with None."""
    result, was_truncated = truncate_output(None)

    assert was_truncated is False
    assert result is None


@pytest.mark.unit
def test_truncate_output_with_ansi_codes():
    """Test truncation with ANSI codes."""
    lines = [f"\033[31mLine {i}\033[0m" for i in range(200)]
    text = "\n".join(lines)
    result, was_truncated = truncate_output(text, max_lines=100, head_lines=50, tail_lines=50, strip_ansi=True)

    assert was_truncated is True
    assert has_ansi_codes(result)  # ANSI codes preserved


# ============================================================================
# Result Formatting Tests
# ============================================================================


@pytest.mark.unit
def test_format_result_success():
    """Test formatting successful execution result."""
    result = ExecutionResult(
        command="echo 'test'",
        exit_code=0,
        stdout="test\n",
        stderr=""
    )

    output = format_result_for_display(result, colorize=False)

    assert "echo 'test'" in output
    assert "✓ Success" in output
    assert "test" in output


@pytest.mark.unit
def test_format_result_failure():
    """Test formatting failed execution result."""
    result = ExecutionResult(
        command="exit 1",
        exit_code=1,
        stdout="",
        stderr="Error message"
    )

    output = format_result_for_display(result, colorize=False, show_stderr=True)

    assert "exit 1" in output
    assert "✗ Failed" in output
    assert "exit code: 1" in output
    assert "Error message" in output


@pytest.mark.unit
def test_format_result_timeout():
    """Test formatting timed out result."""
    result = ExecutionResult(
        command="sleep 100",
        exit_code=-1,
        stdout="",
        stderr="",
        timed_out=True
    )

    output = format_result_for_display(result, colorize=False)

    assert "sleep 100" in output
    assert "⏱ Timeout" in output


@pytest.mark.unit
def test_format_result_interrupted():
    """Test formatting interrupted result."""
    result = ExecutionResult(
        command="sleep 100",
        exit_code=-2,
        stdout="",
        stderr="Command interrupted by user",
        interrupted=True
    )

    output = format_result_for_display(result, colorize=False)

    assert "sleep 100" in output
    assert "✗ Interrupted" in output


@pytest.mark.unit
def test_format_result_with_colors():
    """Test formatting with colorization enabled."""
    result = ExecutionResult(
        command="echo 'test'",
        exit_code=0,
        stdout="test\n",
        stderr=""
    )

    output = format_result_for_display(result, colorize=True)

    assert has_ansi_codes(output)
    assert "echo 'test'" in output


@pytest.mark.unit
def test_format_result_without_stderr():
    """Test formatting with stderr hidden."""
    result = ExecutionResult(
        command="test",
        exit_code=1,
        stdout="output",
        stderr="error"
    )

    output = format_result_for_display(result, show_stderr=False)

    assert "output" in output
    assert "error" not in output


@pytest.mark.unit
def test_format_result_preserve_colors():
    """Test formatting with color preservation."""
    result = ExecutionResult(
        command="test",
        exit_code=0,
        stdout="\033[31mRed output\033[0m\n",
        stderr=""
    )

    output = format_result_for_display(result, preserve_colors=True)

    assert has_ansi_codes(output)
    assert "Red output" in strip_ansi_codes(output)


@pytest.mark.unit
def test_format_result_strip_colors():
    """Test formatting with color stripping."""
    result = ExecutionResult(
        command="test",
        exit_code=0,
        stdout="\033[31mRed output\033[0m\n",
        stderr=""
    )

    output = format_result_for_display(result, preserve_colors=False, colorize=False)

    # Output should not have the original ANSI codes from stdout
    # (but may have codes from status if colorize=True)
    assert "Red output" in output


@pytest.mark.unit
def test_format_result_with_truncation():
    """Test formatting with output truncation."""
    long_output = "\n".join([f"Line {i}" for i in range(200)])
    result = ExecutionResult(
        command="test",
        exit_code=0,
        stdout=long_output,
        stderr=""
    )

    output = format_result_for_display(result, max_lines=100)

    assert "Line 0" in output
    assert "lines omitted" in output


@pytest.mark.unit
def test_format_result_invalid_type():
    """Test formatting with invalid result type."""
    with pytest.raises(ValueError, match="ExecutionResult"):
        format_result_for_display("not a result")


# ============================================================================
# Output Streaming Tests
# ============================================================================


@pytest.mark.unit
def test_stream_output_stdout():
    """Test streaming stdout."""
    result = ExecutionResult(
        command="echo 'test'",
        exit_code=0,
        stdout="test output\n",
        stderr=""
    )

    stdout_stream = io.StringIO()
    stream_output(result, stdout_stream=stdout_stream)

    output = stdout_stream.getvalue()
    assert "test output" in output


@pytest.mark.unit
def test_stream_output_stderr():
    """Test streaming stderr."""
    result = ExecutionResult(
        command="test",
        exit_code=1,
        stdout="",
        stderr="error message\n"
    )

    stderr_stream = io.StringIO()
    stream_output(result, stderr_stream=stderr_stream)

    output = stderr_stream.getvalue()
    assert "error message" in output


@pytest.mark.unit
def test_stream_output_both_streams():
    """Test streaming both stdout and stderr."""
    result = ExecutionResult(
        command="test",
        exit_code=0,
        stdout="output\n",
        stderr="warning\n"
    )

    stdout_stream = io.StringIO()
    stderr_stream = io.StringIO()
    stream_output(result, stdout_stream=stdout_stream, stderr_stream=stderr_stream)

    assert "output" in stdout_stream.getvalue()
    assert "warning" in stderr_stream.getvalue()


@pytest.mark.unit
def test_stream_output_preserve_colors():
    """Test streaming with color preservation."""
    result = ExecutionResult(
        command="test",
        exit_code=0,
        stdout="\033[31mRed text\033[0m\n",
        stderr=""
    )

    stdout_stream = io.StringIO()
    stream_output(result, stdout_stream=stdout_stream, preserve_colors=True)

    output = stdout_stream.getvalue()
    assert has_ansi_codes(output)


@pytest.mark.unit
def test_stream_output_strip_colors():
    """Test streaming with color stripping."""
    result = ExecutionResult(
        command="test",
        exit_code=0,
        stdout="\033[31mRed text\033[0m\n",
        stderr=""
    )

    stdout_stream = io.StringIO()
    stream_output(result, stdout_stream=stdout_stream, preserve_colors=False)

    output = stdout_stream.getvalue()
    assert not has_ansi_codes(output)
    assert "Red text" in output


@pytest.mark.unit
def test_stream_output_default_streams():
    """Test streaming with default sys.stdout/stderr."""
    result = ExecutionResult(
        command="test",
        exit_code=0,
        stdout="test\n",
        stderr=""
    )

    # This should not raise an error
    # (actual output goes to sys.stdout)
    stream_output(result)


# ============================================================================
# Text Colorization Tests
# ============================================================================


@pytest.mark.unit
def test_colorize_text_red():
    """Test colorizing text in red."""
    text = colorize_text("Error", "red")

    assert has_ansi_codes(text)
    assert COLORS['red'] in text
    assert COLORS['reset'] in text
    assert "Error" in text


@pytest.mark.unit
def test_colorize_text_green():
    """Test colorizing text in green."""
    text = colorize_text("Success", "green")

    assert has_ansi_codes(text)
    assert COLORS['green'] in text
    assert "Success" in text


@pytest.mark.unit
def test_colorize_text_invalid_color():
    """Test colorizing with invalid color."""
    text = colorize_text("Text", "invalid_color")

    assert text == "Text"
    assert not has_ansi_codes(text)


@pytest.mark.unit
def test_colorize_text_empty_string():
    """Test colorizing empty string."""
    text = colorize_text("", "red")

    assert text == ""


@pytest.mark.unit
def test_colorize_text_none():
    """Test colorizing None."""
    text = colorize_text(None, "red")

    assert text is None


# ============================================================================
# Visible Length Tests
# ============================================================================


@pytest.mark.unit
def test_get_visible_length_plain_text():
    """Test getting visible length of plain text."""
    length = get_visible_length("Hello World")

    assert length == 11


@pytest.mark.unit
def test_get_visible_length_with_ansi():
    """Test getting visible length of text with ANSI codes."""
    text = "\033[31mRed text\033[0m"
    length = get_visible_length(text)

    assert length == 8  # "Red text"


@pytest.mark.unit
def test_get_visible_length_empty_string():
    """Test getting visible length of empty string."""
    length = get_visible_length("")

    assert length == 0


@pytest.mark.unit
def test_get_visible_length_none():
    """Test getting visible length of None."""
    length = get_visible_length(None)

    assert length == 0


@pytest.mark.unit
def test_get_visible_length_multiple_colors():
    """Test getting visible length with multiple colors."""
    text = "\033[31mRed\033[0m and \033[32mGreen\033[0m"
    length = get_visible_length(text)

    assert length == 13  # "Red and Green"


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.unit
def test_integration_full_workflow():
    """Test complete workflow: format, colorize, truncate."""
    # Create a result with long output
    long_output = "\n".join([f"\033[31mLine {i}\033[0m" for i in range(200)])
    result = ExecutionResult(
        command="test command",
        exit_code=0,
        stdout=long_output,
        stderr=""
    )

    # Format with all features
    output = format_result_for_display(
        result,
        max_lines=100,
        show_stderr=True,
        colorize=True,
        preserve_colors=True
    )

    # Verify features
    assert "test command" in output
    assert has_ansi_codes(output)
    assert "Line 0" in output
    assert "lines omitted" in output


@pytest.mark.unit
def test_integration_stream_and_format():
    """Test streaming and formatting the same result."""
    result = ExecutionResult(
        command="echo 'test'",
        exit_code=0,
        stdout="test output\n",
        stderr=""
    )

    # Stream it
    stdout_stream = io.StringIO()
    stream_output(result, stdout_stream=stdout_stream)
    streamed = stdout_stream.getvalue()

    # Format it
    formatted = format_result_for_display(result, colorize=False)

    # Both should contain the output
    assert "test output" in streamed
    assert "test output" in formatted
