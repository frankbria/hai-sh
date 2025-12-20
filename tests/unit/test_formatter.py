"""
Tests for formatter module.
"""

import pytest

from hai_sh.executor import ExecutionResult
from hai_sh.formatter import (
    CONVERSATION_HEADER,
    EXECUTION_HEADER,
    LAYER_SEPARATOR,
    format_command_prompt,
    format_confidence,
    format_conversation_layer,
    format_conversation_only,
    format_dual_layer,
    format_execution_layer,
    format_execution_only,
    format_execution_result,
    format_execution_status,
    strip_formatting,
)
from hai_sh.output import has_ansi_codes, strip_ansi_codes


# ============================================================================
# Conversation Layer Tests
# ============================================================================


@pytest.mark.unit
def test_format_conversation_layer_basic():
    """Test basic conversation layer formatting."""
    explanation = "I'll search for large files."
    output = format_conversation_layer(explanation, colorize=False)

    assert CONVERSATION_HEADER in output
    assert explanation in output


@pytest.mark.unit
def test_format_conversation_layer_with_confidence():
    """Test conversation layer with confidence score."""
    explanation = "I'll list files."
    output = format_conversation_layer(explanation, confidence=85, colorize=False)

    assert explanation in output
    assert "Confidence: 85%" in output
    assert "[████████··]" in output


@pytest.mark.unit
def test_format_conversation_layer_without_header():
    """Test conversation layer without header."""
    explanation = "Test explanation"
    output = format_conversation_layer(explanation, show_header=False, colorize=False)

    assert CONVERSATION_HEADER not in output
    assert explanation in output


@pytest.mark.unit
def test_format_conversation_layer_with_colors():
    """Test conversation layer with colors."""
    explanation = "Colored explanation"
    output = format_conversation_layer(explanation, colorize=True)

    assert has_ansi_codes(output)
    assert explanation in strip_ansi_codes(output)


@pytest.mark.unit
def test_format_conversation_layer_empty_explanation():
    """Test conversation layer with empty explanation."""
    output = format_conversation_layer("", colorize=False)

    assert CONVERSATION_HEADER in output


# ============================================================================
# Execution Layer Tests
# ============================================================================


@pytest.mark.unit
def test_format_execution_layer_basic():
    """Test basic execution layer formatting."""
    command = "ls -la"
    output = format_execution_layer(command, colorize=False)

    assert EXECUTION_HEADER in output
    assert "$ ls -la" in output


@pytest.mark.unit
def test_format_execution_layer_with_result():
    """Test execution layer with result."""
    command = "echo test"
    result = ExecutionResult(command, 0, "test\n", "")

    output = format_execution_layer(command, result=result, colorize=False)

    assert "$ echo test" in output
    assert "test" in output


@pytest.mark.unit
def test_format_execution_layer_without_header():
    """Test execution layer without header."""
    command = "pwd"
    output = format_execution_layer(command, show_header=False, colorize=False)

    assert EXECUTION_HEADER not in output
    assert "$ pwd" in output


@pytest.mark.unit
def test_format_execution_layer_with_colors():
    """Test execution layer with colors."""
    command = "ls"
    output = format_execution_layer(command, colorize=True)

    assert has_ansi_codes(output)
    assert "ls" in strip_ansi_codes(output)


# ============================================================================
# Command Prompt Tests
# ============================================================================


@pytest.mark.unit
def test_format_command_prompt_plain():
    """Test command prompt without colors."""
    output = format_command_prompt("ls -la", colorize=False)

    assert output == "$ ls -la"


@pytest.mark.unit
def test_format_command_prompt_colored():
    """Test command prompt with colors."""
    output = format_command_prompt("ls -la", colorize=True)

    assert has_ansi_codes(output)
    assert "ls -la" in strip_ansi_codes(output)
    assert "$" in strip_ansi_codes(output)


# ============================================================================
# Execution Result Tests
# ============================================================================


@pytest.mark.unit
def test_format_execution_result_success():
    """Test formatting successful execution result."""
    result = ExecutionResult("echo test", 0, "test\n", "")
    output = format_execution_result(result, colorize=False)

    assert "test" in output
    assert "exit code" not in output  # Success doesn't show exit code


@pytest.mark.unit
def test_format_execution_result_failure():
    """Test formatting failed execution result."""
    result = ExecutionResult("false", 1, "", "")
    output = format_execution_result(result, colorize=False)

    assert "exit code: 1" in output


@pytest.mark.unit
def test_format_execution_result_with_stderr():
    """Test formatting result with stderr."""
    result = ExecutionResult("test", 1, "output", "error message")
    output = format_execution_result(result, colorize=False)

    assert "output" in output
    assert "Errors:" in output
    assert "error message" in output


@pytest.mark.unit
def test_format_execution_result_timeout():
    """Test formatting timed out result."""
    result = ExecutionResult("sleep 100", -1, "", "", timed_out=True)
    output = format_execution_result(result, colorize=False)

    assert "timed out" in output.lower()


@pytest.mark.unit
def test_format_execution_result_interrupted():
    """Test formatting interrupted result."""
    result = ExecutionResult("sleep 100", -2, "", "", interrupted=True)
    output = format_execution_result(result, colorize=False)

    assert "interrupted" in output.lower()


@pytest.mark.unit
def test_format_execution_result_with_truncation():
    """Test formatting with output truncation."""
    long_output = "\n".join([f"Line {i}" for i in range(200)])
    result = ExecutionResult("test", 0, long_output, "")

    output = format_execution_result(result, max_lines=100, colorize=False)

    assert "Line 0" in output
    assert "lines omitted" in output


# ============================================================================
# Execution Status Tests
# ============================================================================


@pytest.mark.unit
def test_format_execution_status_success():
    """Test status formatting for successful execution."""
    result = ExecutionResult("true", 0, "", "")
    status = format_execution_status(result, colorize=False)

    assert status == ""  # No status for success


@pytest.mark.unit
def test_format_execution_status_failure():
    """Test status formatting for failed execution."""
    result = ExecutionResult("false", 1, "", "")
    status = format_execution_status(result, colorize=False)

    assert "exit code: 1" in status
    assert "✗" in status


@pytest.mark.unit
def test_format_execution_status_timeout():
    """Test status formatting for timeout."""
    result = ExecutionResult("sleep 100", -1, "", "", timed_out=True)
    status = format_execution_status(result, colorize=False)

    assert "timed out" in status.lower()
    assert "⏱" in status


@pytest.mark.unit
def test_format_execution_status_interrupted():
    """Test status formatting for interrupted execution."""
    result = ExecutionResult("sleep 100", -2, "", "", interrupted=True)
    status = format_execution_status(result, colorize=False)

    assert "interrupted" in status.lower()


# ============================================================================
# Confidence Formatting Tests
# ============================================================================


@pytest.mark.unit
def test_format_confidence_high():
    """Test confidence formatting for high confidence."""
    output = format_confidence(95, colorize=False)

    assert "95%" in output
    assert "█████████·" in output  # 9 filled, 1 empty


@pytest.mark.unit
def test_format_confidence_medium():
    """Test confidence formatting for medium confidence."""
    output = format_confidence(65, colorize=False)

    assert "65%" in output
    assert "██████····" in output  # 6 filled, 4 empty


@pytest.mark.unit
def test_format_confidence_low():
    """Test confidence formatting for low confidence."""
    output = format_confidence(25, colorize=False)

    assert "25%" in output
    assert "██········" in output  # 2 filled, 8 empty


@pytest.mark.unit
def test_format_confidence_boundaries():
    """Test confidence formatting at boundaries."""
    # 0%
    output0 = format_confidence(0, colorize=False)
    assert "0%" in output0
    assert "··········" in output0

    # 100%
    output100 = format_confidence(100, colorize=False)
    assert "100%" in output100
    assert "██████████" in output100


@pytest.mark.unit
def test_format_confidence_clamping():
    """Test confidence clamping to 0-100 range."""
    # Below 0
    output_low = format_confidence(-10, colorize=False)
    assert "0%" in output_low

    # Above 100
    output_high = format_confidence(150, colorize=False)
    assert "100%" in output_high


@pytest.mark.unit
def test_format_confidence_with_colors():
    """Test confidence formatting with colors."""
    # High confidence - green
    output_high = format_confidence(85, colorize=True)
    assert has_ansi_codes(output_high)

    # Medium confidence - yellow
    output_med = format_confidence(65, colorize=True)
    assert has_ansi_codes(output_med)

    # Low confidence - red
    output_low = format_confidence(45, colorize=True)
    assert has_ansi_codes(output_low)


# ============================================================================
# Dual Layer Tests
# ============================================================================


@pytest.mark.unit
def test_format_dual_layer_basic():
    """Test basic dual layer formatting."""
    explanation = "I'll list files."
    command = "ls"

    output = format_dual_layer(explanation, command, colorize=False)

    assert CONVERSATION_HEADER in output
    assert EXECUTION_HEADER in output
    assert explanation in output
    assert "$ ls" in output
    assert LAYER_SEPARATOR.strip() in output


@pytest.mark.unit
def test_format_dual_layer_with_result():
    """Test dual layer with execution result."""
    explanation = "I'll echo a test message."
    command = "echo test"
    result = ExecutionResult(command, 0, "test\n", "")

    output = format_dual_layer(explanation, command, result=result, colorize=False)

    assert explanation in output
    assert "$ echo test" in output
    assert "test" in output


@pytest.mark.unit
def test_format_dual_layer_with_confidence():
    """Test dual layer with confidence score."""
    explanation = "I'll show the current directory."
    command = "pwd"

    output = format_dual_layer(
        explanation,
        command,
        confidence=90,
        colorize=False
    )

    assert "Confidence: 90%" in output


@pytest.mark.unit
def test_format_dual_layer_without_headers():
    """Test dual layer without headers."""
    explanation = "Test"
    command = "test"

    output = format_dual_layer(
        explanation,
        command,
        show_headers=False,
        colorize=False
    )

    assert CONVERSATION_HEADER not in output
    assert EXECUTION_HEADER not in output
    assert explanation in output
    assert "$ test" in output


@pytest.mark.unit
def test_format_dual_layer_with_colors():
    """Test dual layer with colors."""
    explanation = "Colored output test"
    command = "ls"

    output = format_dual_layer(explanation, command, colorize=True)

    assert has_ansi_codes(output)


@pytest.mark.unit
def test_format_dual_layer_with_failure():
    """Test dual layer with failed execution."""
    explanation = "This command will fail."
    command = "false"
    result = ExecutionResult(command, 1, "", "")

    output = format_dual_layer(explanation, command, result=result, colorize=False)

    assert "exit code: 1" in output


# ============================================================================
# Conversation Only Tests
# ============================================================================


@pytest.mark.unit
def test_format_conversation_only_basic():
    """Test conversation-only formatting."""
    explanation = "This is a conversation response."

    output = format_conversation_only(explanation, colorize=False)

    assert explanation in output
    assert CONVERSATION_HEADER not in output  # No header for conversation-only


@pytest.mark.unit
def test_format_conversation_only_with_confidence():
    """Test conversation-only with confidence."""
    explanation = "Response with confidence."

    output = format_conversation_only(explanation, confidence=75, colorize=False)

    assert explanation in output
    assert "Confidence: 75%" in output


# ============================================================================
# Execution Only Tests
# ============================================================================


@pytest.mark.unit
def test_format_execution_only_basic():
    """Test execution-only formatting."""
    command = "ls -la"

    output = format_execution_only(command, colorize=False)

    assert "$ ls -la" in output
    assert EXECUTION_HEADER not in output  # No header for execution-only


@pytest.mark.unit
def test_format_execution_only_with_result():
    """Test execution-only with result."""
    command = "pwd"
    result = ExecutionResult(command, 0, "/home/user\n", "")

    output = format_execution_only(command, result=result, colorize=False)

    assert "$ pwd" in output
    assert "/home/user" in output


# ============================================================================
# Strip Formatting Tests
# ============================================================================


@pytest.mark.unit
def test_strip_formatting_removes_ansi():
    """Test stripping ANSI codes."""
    formatted = format_dual_layer("Test", "ls", colorize=True)
    plain = strip_formatting(formatted)

    assert not has_ansi_codes(plain)
    assert "Test" in plain
    assert "ls" in plain


@pytest.mark.unit
def test_strip_formatting_removes_headers():
    """Test stripping layer headers."""
    formatted = format_dual_layer("Test", "ls", colorize=False)
    plain = strip_formatting(formatted)

    assert CONVERSATION_HEADER not in plain
    assert EXECUTION_HEADER not in plain
    assert "Test" in plain
    assert "ls" in plain


@pytest.mark.unit
def test_strip_formatting_cleans_whitespace():
    """Test stripping excess whitespace."""
    formatted = format_dual_layer("Test", "ls", colorize=False)
    plain = strip_formatting(formatted)

    # Should not have triple newlines
    assert "\n\n\n" not in plain


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.unit
def test_integration_full_workflow():
    """Test complete formatting workflow."""
    explanation = "I'll search for large files in your home directory using find."
    command = "find ~ -type f -size +100M"
    result = ExecutionResult(
        command,
        0,
        "/home/user/large_file.iso\n/home/user/video.mp4\n",
        ""
    )

    output = format_dual_layer(
        explanation,
        command,
        result=result,
        confidence=85,
        colorize=False
    )

    # Check conversation layer
    assert CONVERSATION_HEADER in output
    assert explanation in output
    assert "Confidence: 85%" in output

    # Check separator
    assert LAYER_SEPARATOR.strip() in output

    # Check execution layer
    assert EXECUTION_HEADER in output
    assert f"$ {command}" in output
    assert "large_file.iso" in output
    assert "video.mp4" in output


@pytest.mark.unit
def test_integration_failure_workflow():
    """Test formatting workflow with failure."""
    explanation = "This command will fail because the file doesn't exist."
    command = "cat nonexistent.txt"
    result = ExecutionResult(
        command,
        1,
        "",
        "cat: nonexistent.txt: No such file or directory\n"
    )

    output = format_dual_layer(
        explanation,
        command,
        result=result,
        confidence=95,
        colorize=False
    )

    assert explanation in output
    assert f"$ {command}" in output
    assert "Errors:" in output
    assert "No such file or directory" in output
    assert "exit code: 1" in output


@pytest.mark.unit
def test_integration_colored_workflow():
    """Test complete workflow with colors."""
    explanation = "Listing files with colors."
    command = "ls --color"
    result = ExecutionResult(command, 0, "file1.txt\nfile2.txt\n", "")

    output = format_dual_layer(
        explanation,
        command,
        result=result,
        confidence=90,
        colorize=True
    )

    assert has_ansi_codes(output)

    # Strip and verify content
    plain = strip_formatting(output)
    assert "Listing files" in plain
    assert "ls --color" in plain
    assert "file1.txt" in plain


@pytest.mark.unit
def test_integration_strip_and_restore():
    """Test that stripping removes formatting but preserves content."""
    explanation = "This is a detailed explanation with multiple sentences."
    command = "echo 'test output'"
    result = ExecutionResult(command, 0, "test output\n", "")

    formatted = format_dual_layer(
        explanation,
        command,
        result=result,
        confidence=75,
        colorize=True
    )

    plain = strip_formatting(formatted)

    # All content should be preserved
    assert explanation in plain
    assert "test output" in plain

    # Formatting should be removed
    assert not has_ansi_codes(plain)
    assert CONVERSATION_HEADER not in plain
    assert EXECUTION_HEADER not in plain
