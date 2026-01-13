"""
Tests for Rich-based formatter enhancements.

This module tests the enhanced formatter functions that use Rich for
better visual output in interactive mode.
"""

import pytest


# --- Rich Formatter Import Tests ---


@pytest.mark.unit
def test_format_rich_conversation_importable():
    """Test format_rich_conversation can be imported."""
    from hai_sh.formatter import format_rich_conversation

    assert format_rich_conversation is not None


@pytest.mark.unit
def test_format_rich_execution_importable():
    """Test format_rich_execution can be imported."""
    from hai_sh.formatter import format_rich_execution

    assert format_rich_execution is not None


@pytest.mark.unit
def test_format_rich_confidence_importable():
    """Test format_rich_confidence can be imported."""
    from hai_sh.formatter import format_rich_confidence

    assert format_rich_confidence is not None


@pytest.mark.unit
def test_format_enhanced_output_importable():
    """Test format_enhanced_output can be imported."""
    from hai_sh.formatter import format_enhanced_output

    assert format_enhanced_output is not None


# --- Rich Conversation Tests ---


@pytest.mark.unit
def test_format_rich_conversation_basic():
    """Test basic Rich conversation formatting."""
    from hai_sh.formatter import format_rich_conversation

    result = format_rich_conversation("I'll list the files for you.")

    # Should return a string
    assert isinstance(result, str)
    # Should contain the explanation text
    assert "list" in result.lower() or "files" in result.lower()


@pytest.mark.unit
def test_format_rich_conversation_with_confidence():
    """Test Rich conversation with confidence."""
    from hai_sh.formatter import format_rich_conversation

    result = format_rich_conversation(
        "I'll run the command.",
        confidence=85
    )

    assert isinstance(result, str)
    # Should include confidence indicator
    assert "85" in result or "%" in result


@pytest.mark.unit
def test_format_rich_conversation_empty():
    """Test Rich conversation with empty content."""
    from hai_sh.formatter import format_rich_conversation

    result = format_rich_conversation("")

    # Should still return a valid string
    assert isinstance(result, str)


# --- Rich Execution Tests ---


@pytest.mark.unit
def test_format_rich_execution_basic():
    """Test basic Rich execution formatting."""
    from hai_sh.formatter import format_rich_execution

    result = format_rich_execution("ls -la")

    assert isinstance(result, str)
    # Should contain the command
    assert "ls" in result


@pytest.mark.unit
def test_format_rich_execution_with_output():
    """Test Rich execution with stdout output."""
    from hai_sh.formatter import format_rich_execution

    result = format_rich_execution(
        "echo hello",
        stdout="hello\n",
        exit_code=0
    )

    assert isinstance(result, str)
    assert "echo" in result or "hello" in result


@pytest.mark.unit
def test_format_rich_execution_with_error():
    """Test Rich execution with error output."""
    from hai_sh.formatter import format_rich_execution

    result = format_rich_execution(
        "invalid_cmd",
        stderr="command not found",
        exit_code=127
    )

    assert isinstance(result, str)
    # Should indicate error
    assert "127" in result or "not found" in result or "error" in result.lower()


@pytest.mark.unit
def test_format_rich_execution_success_indicator():
    """Test Rich execution shows success indicator."""
    from hai_sh.formatter import format_rich_execution

    result = format_rich_execution("ls", exit_code=0)

    assert isinstance(result, str)


@pytest.mark.unit
def test_format_rich_execution_failure_indicator():
    """Test Rich execution shows failure indicator."""
    from hai_sh.formatter import format_rich_execution

    result = format_rich_execution("false", exit_code=1)

    assert isinstance(result, str)


# --- Rich Confidence Tests ---


@pytest.mark.unit
def test_format_rich_confidence_high():
    """Test Rich confidence formatting for high confidence."""
    from hai_sh.formatter import format_rich_confidence

    result = format_rich_confidence(90)

    assert isinstance(result, str)
    assert "90" in result


@pytest.mark.unit
def test_format_rich_confidence_medium():
    """Test Rich confidence formatting for medium confidence."""
    from hai_sh.formatter import format_rich_confidence

    result = format_rich_confidence(65)

    assert isinstance(result, str)
    assert "65" in result


@pytest.mark.unit
def test_format_rich_confidence_low():
    """Test Rich confidence formatting for low confidence."""
    from hai_sh.formatter import format_rich_confidence

    result = format_rich_confidence(30)

    assert isinstance(result, str)
    assert "30" in result


@pytest.mark.unit
def test_format_rich_confidence_includes_bar():
    """Test Rich confidence includes visual bar."""
    from hai_sh.formatter import format_rich_confidence

    result = format_rich_confidence(50)

    assert isinstance(result, str)
    # Should have some kind of visual indicator
    assert "█" in result or "%" in result or "bar" in result.lower()


# --- Enhanced Output Tests ---


@pytest.mark.unit
def test_format_enhanced_output_basic():
    """Test enhanced output with basic input."""
    from hai_sh.formatter import format_enhanced_output
    from hai_sh.schema import LLMResponse

    response = LLMResponse(
        conversation="I'll list files",
        command="ls",
        confidence=85
    )

    result = format_enhanced_output(response)

    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.unit
def test_format_enhanced_output_no_command():
    """Test enhanced output for question-only response."""
    from hai_sh.formatter import format_enhanced_output
    from hai_sh.schema import LLMResponse

    response = LLMResponse(
        conversation="Python is a programming language.",
        confidence=95
    )

    result = format_enhanced_output(response)

    assert isinstance(result, str)
    assert "Python" in result


@pytest.mark.unit
def test_format_enhanced_output_with_internal_dialogue():
    """Test enhanced output shows internal dialogue when enabled."""
    from hai_sh.formatter import format_enhanced_output
    from hai_sh.schema import LLMResponse

    response = LLMResponse(
        conversation="I'll help you",
        command="ls",
        confidence=85,
        internal_dialogue="Simple file listing task"
    )

    result = format_enhanced_output(response, show_internal_dialogue=True)

    assert isinstance(result, str)
    # Should include internal dialogue
    assert "Simple" in result or "listing" in result


@pytest.mark.unit
def test_format_enhanced_output_hides_internal_dialogue_by_default():
    """Test enhanced output hides internal dialogue by default."""
    from hai_sh.formatter import format_enhanced_output
    from hai_sh.schema import LLMResponse

    response = LLMResponse(
        conversation="I'll help you",
        command="ls",
        confidence=85,
        internal_dialogue="SECRET_INTERNAL_TEXT"
    )

    result = format_enhanced_output(response, show_internal_dialogue=False)

    assert isinstance(result, str)
    # Should NOT include internal dialogue
    assert "SECRET_INTERNAL_TEXT" not in result


@pytest.mark.unit
def test_format_enhanced_output_with_execution_result():
    """Test enhanced output with execution result."""
    from hai_sh.formatter import format_enhanced_output
    from hai_sh.schema import LLMResponse
    from hai_sh.executor import ExecutionResult

    response = LLMResponse(
        conversation="Listing files",
        command="ls",
        confidence=90
    )

    result_obj = ExecutionResult("ls", 0, "file1.txt\nfile2.txt\n", "")

    result = format_enhanced_output(response, execution_result=result_obj)

    assert isinstance(result, str)
    # Should include execution output
    assert "file1" in result or "file2" in result


# --- Console Output Tests ---


@pytest.mark.unit
def test_get_rich_console():
    """Test getting Rich console for output."""
    from hai_sh.formatter import get_rich_console

    console = get_rich_console()

    # Should be a Rich Console instance
    assert console is not None
    assert hasattr(console, "print")


@pytest.mark.unit
def test_get_rich_console_no_color():
    """Test getting Rich console with color disabled."""
    from hai_sh.formatter import get_rich_console

    console = get_rich_console(force_color=False)

    assert console is not None
    # Should have color disabled
    assert console.no_color is True


@pytest.mark.unit
def test_get_rich_console_force_color():
    """Test getting Rich console with color forced."""
    from hai_sh.formatter import get_rich_console

    console = get_rich_console(force_color=True)

    assert console is not None
    # Should have color enabled (check private attr)
    assert console._force_terminal is True


# --- Panel Creation Tests ---


@pytest.mark.unit
def test_create_conversation_panel():
    """Test creating Rich panel for conversation."""
    from hai_sh.formatter import create_conversation_panel

    panel = create_conversation_panel("Test content")

    # Should return a Rich Panel
    assert panel is not None
    assert hasattr(panel, "renderable")


@pytest.mark.unit
def test_create_execution_panel():
    """Test creating Rich panel for execution."""
    from hai_sh.formatter import create_execution_panel

    panel = create_execution_panel("ls -la", stdout="output")

    assert panel is not None


@pytest.mark.unit
def test_create_meta_panel():
    """Test creating Rich panel for meta info."""
    from hai_sh.formatter import create_meta_panel

    panel = create_meta_panel(confidence=85, internal_dialogue="test")

    assert panel is not None
