"""
Tests for system prompt and response formatting.
"""

import json

import pytest

from hai_sh.prompt import (
    SYSTEM_PROMPT_TEMPLATE,
    build_system_prompt,
    parse_response,
    validate_command,
    format_command_output,
    _format_context,
)


# ============================================================================
# System Prompt Tests
# ============================================================================


@pytest.mark.unit
def test_system_prompt_template_exists():
    """Test that system prompt template is defined."""
    assert SYSTEM_PROMPT_TEMPLATE
    assert isinstance(SYSTEM_PROMPT_TEMPLATE, str)
    assert len(SYSTEM_PROMPT_TEMPLATE) > 100


@pytest.mark.unit
def test_system_prompt_contains_json_format():
    """Test that system prompt includes JSON format specification."""
    assert "JSON" in SYSTEM_PROMPT_TEMPLATE or "json" in SYSTEM_PROMPT_TEMPLATE
    assert "explanation" in SYSTEM_PROMPT_TEMPLATE
    assert "command" in SYSTEM_PROMPT_TEMPLATE
    assert "confidence" in SYSTEM_PROMPT_TEMPLATE


@pytest.mark.unit
def test_system_prompt_contains_safety_guidelines():
    """Test that system prompt includes safety guidelines."""
    assert "safety" in SYSTEM_PROMPT_TEMPLATE.lower() or "safe" in SYSTEM_PROMPT_TEMPLATE.lower()
    assert "DO NOT" in SYSTEM_PROMPT_TEMPLATE or "don't" in SYSTEM_PROMPT_TEMPLATE.lower()


@pytest.mark.unit
def test_system_prompt_contains_examples():
    """Test that system prompt includes examples."""
    # Should have multiple examples
    assert SYSTEM_PROMPT_TEMPLATE.count("User:") >= 2
    assert SYSTEM_PROMPT_TEMPLATE.count("Response:") >= 2


@pytest.mark.unit
def test_build_system_prompt_no_context():
    """Test building system prompt without context."""
    prompt = build_system_prompt()

    assert isinstance(prompt, str)
    assert len(prompt) > 100
    assert "hai" in prompt.lower()
    assert "{context}" not in prompt  # Should be replaced


@pytest.mark.unit
def test_build_system_prompt_with_cwd():
    """Test building system prompt with current directory context."""
    context = {"cwd": "/home/user/project"}
    prompt = build_system_prompt(context)

    assert "/home/user/project" in prompt
    assert "Current directory:" in prompt


@pytest.mark.unit
def test_build_system_prompt_with_git():
    """Test building system prompt with git context."""
    context = {
        "cwd": "/home/user/project",
        "git": {
            "is_repo": True,
            "branch": "main",
            "has_changes": True,
            "staged_files": ["file1.py"],
            "unstaged_files": ["file2.py"]
        }
    }
    prompt = build_system_prompt(context)

    assert "main" in prompt
    assert "Git branch:" in prompt


@pytest.mark.unit
def test_build_system_prompt_with_env():
    """Test building system prompt with environment context."""
    context = {
        "env": {
            "user": "testuser",
            "shell": "/bin/bash"
        }
    }
    prompt = build_system_prompt(context)

    assert "testuser" in prompt
    assert "/bin/bash" in prompt


@pytest.mark.unit
def test_build_system_prompt_complete_context():
    """Test building system prompt with all context types."""
    context = {
        "cwd": "/home/user/project",
        "git": {
            "is_repo": True,
            "branch": "feature-x",
            "has_changes": False
        },
        "env": {
            "user": "testuser",
            "shell": "/bin/zsh"
        }
    }
    prompt = build_system_prompt(context)

    assert "/home/user/project" in prompt
    assert "feature-x" in prompt
    assert "testuser" in prompt
    assert "/bin/zsh" in prompt


# ============================================================================
# Context Formatting Tests
# ============================================================================


@pytest.mark.unit
def test_format_context_empty():
    """Test formatting empty context."""
    context = {}
    formatted = _format_context(context)

    assert formatted == "No specific context provided."


@pytest.mark.unit
def test_format_context_cwd_only():
    """Test formatting context with only CWD."""
    context = {"cwd": "/home/user"}
    formatted = _format_context(context)

    assert "Current directory: /home/user" in formatted


@pytest.mark.unit
def test_format_context_git_not_repo():
    """Test formatting context when not in git repo."""
    context = {
        "cwd": "/home/user",
        "git": {"is_repo": False}
    }
    formatted = _format_context(context)

    # Should only show CWD, not git info
    assert "Current directory:" in formatted
    assert "Git" not in formatted


@pytest.mark.unit
def test_format_context_git_with_changes():
    """Test formatting context with git changes."""
    context = {
        "git": {
            "is_repo": True,
            "branch": "main",
            "has_changes": True,
            "staged_files": ["a.py", "b.py"],
            "unstaged_files": ["c.py"]
        }
    }
    formatted = _format_context(context)

    assert "Git branch: main" in formatted
    assert "Uncommitted changes present" in formatted
    assert "Staged files: 2" in formatted
    assert "Unstaged files: 1" in formatted


# ============================================================================
# Response Parsing Tests
# ============================================================================


@pytest.mark.unit
def test_parse_response_valid_json():
    """Test parsing valid JSON response."""
    response = json.dumps({
        "explanation": "List files in current directory",
        "command": "ls -la",
        "confidence": 90
    })

    parsed = parse_response(response)

    assert parsed["explanation"] == "List files in current directory"
    assert parsed["command"] == "ls -la"
    assert parsed["confidence"] == 90


@pytest.mark.unit
def test_parse_response_with_whitespace():
    """Test parsing JSON response with extra whitespace."""
    response = """
    {
        "explanation": "Show disk usage",
        "command": "df -h",
        "confidence": 85
    }
    """

    parsed = parse_response(response)

    assert parsed["command"] == "df -h"
    assert parsed["confidence"] == 85


@pytest.mark.unit
def test_parse_response_from_markdown_code_block():
    """Test parsing JSON from markdown code block."""
    response = """Here's the command:
```json
{
    "explanation": "Find large files",
    "command": "find . -size +100M",
    "confidence": 80
}
```
"""

    parsed = parse_response(response)

    assert parsed["command"] == "find . -size +100M"
    assert parsed["confidence"] == 80


@pytest.mark.unit
def test_parse_response_from_code_block_no_lang():
    """Test parsing JSON from code block without language specifier."""
    response = """```
{
    "explanation": "Test command",
    "command": "echo test",
    "confidence": 95
}
```"""

    parsed = parse_response(response)

    assert parsed["command"] == "echo test"


@pytest.mark.unit
def test_parse_response_invalid_json():
    """Test parsing invalid JSON raises error."""
    response = "This is not JSON"

    with pytest.raises(ValueError, match="not valid JSON"):
        parse_response(response)


@pytest.mark.unit
def test_parse_response_missing_explanation():
    """Test parsing JSON missing explanation field."""
    response = json.dumps({
        "command": "ls",
        "confidence": 90
    })

    with pytest.raises(ValueError, match="Missing required fields.*explanation"):
        parse_response(response)


@pytest.mark.unit
def test_parse_response_missing_command():
    """Test parsing JSON missing command field."""
    response = json.dumps({
        "explanation": "Test",
        "confidence": 90
    })

    with pytest.raises(ValueError, match="Missing required fields.*command"):
        parse_response(response)


@pytest.mark.unit
def test_parse_response_missing_confidence():
    """Test parsing JSON missing confidence field."""
    response = json.dumps({
        "explanation": "Test",
        "command": "ls"
    })

    with pytest.raises(ValueError, match="Missing required fields.*confidence"):
        parse_response(response)


@pytest.mark.unit
def test_parse_response_invalid_explanation_type():
    """Test parsing JSON with non-string explanation."""
    response = json.dumps({
        "explanation": 123,
        "command": "ls",
        "confidence": 90
    })

    with pytest.raises(ValueError, match="explanation.*must be a string"):
        parse_response(response)


@pytest.mark.unit
def test_parse_response_invalid_command_type():
    """Test parsing JSON with non-string command."""
    response = json.dumps({
        "explanation": "Test",
        "command": ["ls", "-la"],
        "confidence": 90
    })

    with pytest.raises(ValueError, match="command.*must be a string"):
        parse_response(response)


@pytest.mark.unit
def test_parse_response_invalid_confidence_type():
    """Test parsing JSON with non-numeric confidence."""
    response = json.dumps({
        "explanation": "Test",
        "command": "ls",
        "confidence": "high"
    })

    with pytest.raises(ValueError, match="confidence.*must be a number"):
        parse_response(response)


@pytest.mark.unit
def test_parse_response_confidence_out_of_range_low():
    """Test parsing JSON with confidence below 0."""
    response = json.dumps({
        "explanation": "Test",
        "command": "ls",
        "confidence": -10
    })

    with pytest.raises(ValueError, match="confidence.*between 0 and 100"):
        parse_response(response)


@pytest.mark.unit
def test_parse_response_confidence_out_of_range_high():
    """Test parsing JSON with confidence above 100."""
    response = json.dumps({
        "explanation": "Test",
        "command": "ls",
        "confidence": 150
    })

    with pytest.raises(ValueError, match="confidence.*between 0 and 100"):
        parse_response(response)


@pytest.mark.unit
def test_parse_response_float_confidence():
    """Test parsing JSON with float confidence (should convert to int)."""
    response = json.dumps({
        "explanation": "Test",
        "command": "ls",
        "confidence": 85.5
    })

    parsed = parse_response(response)
    assert parsed["confidence"] == 85
    assert isinstance(parsed["confidence"], int)


# ============================================================================
# Command Validation Tests
# ============================================================================


@pytest.mark.unit
def test_validate_command_safe_ls():
    """Test validation of safe ls command."""
    is_safe, error = validate_command("ls -la")

    assert is_safe is True
    assert error is None


@pytest.mark.unit
def test_validate_command_safe_find():
    """Test validation of safe find command."""
    is_safe, error = validate_command("find . -name '*.py'")

    assert is_safe is True
    assert error is None


@pytest.mark.unit
def test_validate_command_safe_git():
    """Test validation of safe git command."""
    is_safe, error = validate_command("git status")

    assert is_safe is True
    assert error is None


@pytest.mark.unit
def test_validate_command_dangerous_rm():
    """Test validation rejects rm command."""
    is_safe, error = validate_command("rm -rf /tmp/test")

    assert is_safe is False
    assert "rm" in error.lower()


@pytest.mark.unit
def test_validate_command_dangerous_rmdir():
    """Test validation rejects rmdir command."""
    is_safe, error = validate_command("rmdir /tmp/test")

    assert is_safe is False
    assert "rmdir" in error.lower()


@pytest.mark.unit
def test_validate_command_dangerous_dd():
    """Test validation rejects dd command."""
    is_safe, error = validate_command("dd if=/dev/zero of=/dev/sda")

    assert is_safe is False
    assert "dd" in error.lower()


@pytest.mark.unit
def test_validate_command_dangerous_chmod_777():
    """Test validation rejects chmod 777."""
    is_safe, error = validate_command("chmod 777 script.sh")

    assert is_safe is False
    assert "chmod" in error.lower()


@pytest.mark.unit
def test_validate_command_dangerous_system_path():
    """Test validation rejects modifications to /etc."""
    is_safe, error = validate_command("echo 'test' > /etc/hosts")

    assert is_safe is False
    assert "/etc/" in error.lower()


@pytest.mark.unit
def test_validate_command_dangerous_reboot():
    """Test validation rejects reboot command."""
    is_safe, error = validate_command("reboot")

    assert is_safe is False
    assert "reboot" in error.lower()


@pytest.mark.unit
def test_validate_command_dangerous_shutdown():
    """Test validation rejects shutdown command."""
    is_safe, error = validate_command("shutdown -h now")

    assert is_safe is False
    assert "shutdown" in error.lower()


@pytest.mark.unit
def test_validate_command_case_insensitive():
    """Test validation is case-insensitive."""
    is_safe, error = validate_command("RM -rf /tmp/test")

    assert is_safe is False
    assert "rm" in error.lower()


# ============================================================================
# Output Formatting Tests
# ============================================================================


@pytest.mark.unit
def test_format_command_output_no_colors():
    """Test formatting output without colors."""
    output = format_command_output(
        "List files",
        "ls -la",
        90,
        use_colors=False
    )

    assert "Explanation: List files" in output
    assert "Command: ls -la" in output
    assert "Confidence: 90%" in output
    assert "\033[" not in output  # No ANSI codes


@pytest.mark.unit
def test_format_command_output_with_colors():
    """Test formatting output with colors."""
    output = format_command_output(
        "List files",
        "ls -la",
        90,
        use_colors=True
    )

    assert "Explanation:" in output
    assert "ls -la" in output
    assert "90%" in output
    assert "\033[" in output  # Has ANSI codes


@pytest.mark.unit
def test_format_command_output_high_confidence():
    """Test formatting output with high confidence (green)."""
    output = format_command_output(
        "Test",
        "echo test",
        95,
        use_colors=True
    )

    # High confidence should use green color code
    assert "\033[92m" in output


@pytest.mark.unit
def test_format_command_output_medium_confidence():
    """Test formatting output with medium confidence (yellow)."""
    output = format_command_output(
        "Test",
        "echo test",
        70,
        use_colors=True
    )

    # Medium confidence should use yellow color code
    assert "\033[93m" in output


@pytest.mark.unit
def test_format_command_output_low_confidence():
    """Test formatting output with low confidence (red)."""
    output = format_command_output(
        "Test",
        "echo test",
        50,
        use_colors=True
    )

    # Low confidence should use red color code
    assert "\033[91m" in output
