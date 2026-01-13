"""
Tests for shell history collection functionality.
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from hai_sh.context import (
    get_shell_history,
    format_shell_history,
    _detect_shell_type,
    _get_history_file_path,
    _is_sensitive_command,
)


# ============================================================================
# Shell Type Detection Tests
# ============================================================================


@pytest.mark.unit
def test_detect_shell_type_bash(monkeypatch):
    """Test detecting bash shell."""
    monkeypatch.setenv("SHELL", "/bin/bash")

    shell_type = _detect_shell_type()

    assert shell_type == "bash"


@pytest.mark.unit
def test_detect_shell_type_zsh(monkeypatch):
    """Test detecting zsh shell."""
    monkeypatch.setenv("SHELL", "/usr/bin/zsh")

    shell_type = _detect_shell_type()

    assert shell_type == "zsh"


@pytest.mark.unit
def test_detect_shell_type_fish(monkeypatch):
    """Test detecting fish shell."""
    monkeypatch.setenv("SHELL", "/usr/local/bin/fish")

    shell_type = _detect_shell_type()

    assert shell_type == "fish"


@pytest.mark.unit
def test_detect_shell_type_unknown(monkeypatch):
    """Test detecting unknown shell defaults to bash."""
    monkeypatch.setenv("SHELL", "/bin/unknown-shell")

    shell_type = _detect_shell_type()

    assert shell_type == "unknown"


@pytest.mark.unit
def test_detect_shell_type_missing_env(monkeypatch):
    """Test shell detection when SHELL env var is missing."""
    monkeypatch.delenv("SHELL", raising=False)

    shell_type = _detect_shell_type()

    assert shell_type == "unknown"


# ============================================================================
# History File Path Tests
# ============================================================================


@pytest.mark.unit
def test_get_history_file_path_bash(monkeypatch, tmp_path):
    """Test bash history file path detection."""
    monkeypatch.setenv("HOME", str(tmp_path))

    # Create fake history file
    history_file = tmp_path / ".bash_history"
    history_file.write_text("echo hello\nls -la\n")

    path = _get_history_file_path("bash")

    assert path == history_file


@pytest.mark.unit
def test_get_history_file_path_zsh(monkeypatch, tmp_path):
    """Test zsh history file path detection."""
    monkeypatch.setenv("HOME", str(tmp_path))

    # Create fake history file
    history_file = tmp_path / ".zsh_history"
    history_file.write_text(": 1234567890:0;echo hello\n")

    path = _get_history_file_path("zsh")

    assert path == history_file


@pytest.mark.unit
def test_get_history_file_path_fish(monkeypatch, tmp_path):
    """Test fish history file path detection."""
    monkeypatch.setenv("HOME", str(tmp_path))

    # Create fish history directory and file
    fish_dir = tmp_path / ".local" / "share" / "fish"
    fish_dir.mkdir(parents=True)
    history_file = fish_dir / "fish_history"
    history_file.write_text("- cmd: echo hello\n")

    path = _get_history_file_path("fish")

    assert path == history_file


@pytest.mark.unit
def test_get_history_file_path_file_not_exists(monkeypatch, tmp_path):
    """Test history file path when file doesn't exist."""
    monkeypatch.setenv("HOME", str(tmp_path))

    path = _get_history_file_path("bash")

    assert path is None


@pytest.mark.unit
def test_get_history_file_path_unknown_shell(monkeypatch, tmp_path):
    """Test history file path for unknown shell."""
    monkeypatch.setenv("HOME", str(tmp_path))

    path = _get_history_file_path("unknown")

    assert path is None


# ============================================================================
# Sensitive Command Detection Tests
# ============================================================================


@pytest.mark.unit
def test_is_sensitive_command_password():
    """Test detecting commands containing passwords."""
    assert _is_sensitive_command("mysql -u root -ppassword123") is True
    assert _is_sensitive_command("export PASSWORD=secret") is True
    assert _is_sensitive_command("echo $PASSWORD") is True


@pytest.mark.unit
def test_is_sensitive_command_api_key():
    """Test detecting commands with API keys."""
    assert _is_sensitive_command("export OPENAI_API_KEY=sk-abc123") is True
    assert _is_sensitive_command("curl -H 'Authorization: Bearer token'") is True
    assert _is_sensitive_command("API_KEY=xyz ./run.sh") is True


@pytest.mark.unit
def test_is_sensitive_command_ssh():
    """Test detecting SSH commands with keys."""
    assert _is_sensitive_command("ssh-add ~/.ssh/id_rsa") is True
    assert _is_sensitive_command("ssh -i /path/to/key user@host") is True


@pytest.mark.unit
def test_is_sensitive_command_safe():
    """Test that safe commands are not marked as sensitive."""
    assert _is_sensitive_command("ls -la") is False
    assert _is_sensitive_command("git status") is False
    assert _is_sensitive_command("cd ~/projects") is False
    assert _is_sensitive_command("python script.py") is False
    assert _is_sensitive_command("cat file.txt") is False


@pytest.mark.unit
def test_is_sensitive_command_case_insensitive():
    """Test sensitivity detection is case-insensitive."""
    assert _is_sensitive_command("export password=secret") is True
    assert _is_sensitive_command("export PASSWORD=secret") is True
    assert _is_sensitive_command("export PaSsWoRd=secret") is True


# ============================================================================
# Shell History Collection Tests
# ============================================================================


@pytest.mark.unit
def test_get_shell_history_basic(monkeypatch, tmp_path):
    """Test basic shell history collection."""
    monkeypatch.setenv("SHELL", "/bin/bash")
    monkeypatch.setenv("HOME", str(tmp_path))

    # Create history file
    history_file = tmp_path / ".bash_history"
    history_file.write_text("ls -la\ncd projects\ngit status\n")

    context = get_shell_history(length=10)

    assert "commands" in context
    assert "shell_type" in context
    assert "total_count" in context
    assert "filtered_count" in context
    assert "error" in context

    assert context["shell_type"] == "bash"
    assert len(context["commands"]) == 3
    assert context["total_count"] == 3
    assert context["error"] is None


@pytest.mark.unit
def test_get_shell_history_respects_length(monkeypatch, tmp_path):
    """Test that history collection respects length parameter."""
    monkeypatch.setenv("SHELL", "/bin/bash")
    monkeypatch.setenv("HOME", str(tmp_path))

    # Create history file with many commands
    commands = [f"command{i}" for i in range(50)]
    history_file = tmp_path / ".bash_history"
    history_file.write_text("\n".join(commands) + "\n")

    context = get_shell_history(length=5)

    assert len(context["commands"]) == 5
    # Should get the last 5 commands
    assert context["commands"][-1] == "command49"


@pytest.mark.unit
def test_get_shell_history_filters_sensitive(monkeypatch, tmp_path):
    """Test that sensitive commands are filtered out."""
    monkeypatch.setenv("SHELL", "/bin/bash")
    monkeypatch.setenv("HOME", str(tmp_path))

    # Create history with sensitive and non-sensitive commands
    history_content = """ls -la
export API_KEY=secret123
git status
mysql -u root -ppassword
cd projects
"""
    history_file = tmp_path / ".bash_history"
    history_file.write_text(history_content)

    context = get_shell_history(length=10)

    # Should filter out sensitive commands
    commands = context["commands"]
    assert "ls -la" in commands
    assert "git status" in commands
    assert "cd projects" in commands
    assert "export API_KEY=secret123" not in commands
    assert "mysql -u root -ppassword" not in commands
    assert context["filtered_count"] == 2


@pytest.mark.unit
def test_get_shell_history_empty_file(monkeypatch, tmp_path):
    """Test history collection with empty history file."""
    monkeypatch.setenv("SHELL", "/bin/bash")
    monkeypatch.setenv("HOME", str(tmp_path))

    # Create empty history file
    history_file = tmp_path / ".bash_history"
    history_file.write_text("")

    context = get_shell_history(length=10)

    assert context["commands"] == []
    assert context["total_count"] == 0
    assert context["error"] is None


@pytest.mark.unit
def test_get_shell_history_file_not_found(monkeypatch, tmp_path):
    """Test history collection when history file doesn't exist."""
    monkeypatch.setenv("SHELL", "/bin/bash")
    monkeypatch.setenv("HOME", str(tmp_path))

    # Don't create history file
    context = get_shell_history(length=10)

    assert context["commands"] == []
    assert "not found" in context["error"].lower() or context["error"] is None


@pytest.mark.unit
def test_get_shell_history_permission_error(monkeypatch, tmp_path):
    """Test history collection when file is not readable."""
    monkeypatch.setenv("SHELL", "/bin/bash")
    monkeypatch.setenv("HOME", str(tmp_path))

    # Create history file
    history_file = tmp_path / ".bash_history"
    history_file.write_text("command1\n")

    # Mock open to raise PermissionError
    def mock_open(*args, **kwargs):
        raise PermissionError("Permission denied")

    with patch("builtins.open", mock_open):
        context = get_shell_history(length=10)

    assert context["error"] is not None
    assert "permission" in context["error"].lower()


@pytest.mark.unit
def test_get_shell_history_zsh_format(monkeypatch, tmp_path):
    """Test history collection with zsh extended history format."""
    monkeypatch.setenv("SHELL", "/usr/bin/zsh")
    monkeypatch.setenv("HOME", str(tmp_path))

    # Zsh extended history format: `: timestamp:0;command`
    history_content = """: 1234567890:0;ls -la
: 1234567891:0;git status
: 1234567892:0;cd projects
"""
    history_file = tmp_path / ".zsh_history"
    history_file.write_text(history_content)

    context = get_shell_history(length=10)

    assert context["shell_type"] == "zsh"
    assert len(context["commands"]) == 3
    # Commands should be extracted without the timestamp prefix
    assert "ls -la" in context["commands"]


@pytest.mark.unit
def test_get_shell_history_fish_format(monkeypatch, tmp_path):
    """Test history collection with fish shell format."""
    monkeypatch.setenv("SHELL", "/usr/bin/fish")
    monkeypatch.setenv("HOME", str(tmp_path))

    # Fish history is YAML-like format
    fish_dir = tmp_path / ".local" / "share" / "fish"
    fish_dir.mkdir(parents=True)
    history_file = fish_dir / "fish_history"
    history_content = """- cmd: ls -la
  when: 1234567890
- cmd: git status
  when: 1234567891
- cmd: cd projects
  when: 1234567892
"""
    history_file.write_text(history_content)

    context = get_shell_history(length=10)

    assert context["shell_type"] == "fish"
    assert len(context["commands"]) == 3
    assert "ls -la" in context["commands"]


@pytest.mark.unit
def test_get_shell_history_deduplication(monkeypatch, tmp_path):
    """Test that duplicate consecutive commands are handled."""
    monkeypatch.setenv("SHELL", "/bin/bash")
    monkeypatch.setenv("HOME", str(tmp_path))

    # Create history with duplicates
    history_content = """ls -la
ls -la
ls -la
git status
git status
cd projects
"""
    history_file = tmp_path / ".bash_history"
    history_file.write_text(history_content)

    context = get_shell_history(length=10)

    # Should include all commands (no deduplication by default)
    assert context["total_count"] == 6


# ============================================================================
# Format Shell History Tests
# ============================================================================


@pytest.mark.unit
def test_format_shell_history_basic():
    """Test formatting shell history context."""
    context = {
        "commands": ["ls -la", "git status", "cd projects"],
        "shell_type": "bash",
        "total_count": 3,
        "filtered_count": 0,
        "error": None,
    }

    formatted = format_shell_history(context)

    assert "Recent Commands" in formatted or "Shell History" in formatted
    assert "ls -la" in formatted
    assert "git status" in formatted
    assert "bash" in formatted.lower() or "3" in formatted


@pytest.mark.unit
def test_format_shell_history_empty():
    """Test formatting empty shell history."""
    context = {
        "commands": [],
        "shell_type": "bash",
        "total_count": 0,
        "filtered_count": 0,
        "error": None,
    }

    formatted = format_shell_history(context)

    assert "empty" in formatted.lower() or "no history" in formatted.lower() or formatted == ""


@pytest.mark.unit
def test_format_shell_history_with_filtered():
    """Test formatting when some commands were filtered."""
    context = {
        "commands": ["ls -la", "git status"],
        "shell_type": "zsh",
        "total_count": 5,
        "filtered_count": 3,
        "error": None,
    }

    formatted = format_shell_history(context)

    # Should indicate filtering occurred
    assert "filtered" in formatted.lower() or "3" in formatted


@pytest.mark.unit
def test_format_shell_history_with_error():
    """Test formatting shell history with error."""
    context = {
        "commands": [],
        "shell_type": "bash",
        "total_count": 0,
        "filtered_count": 0,
        "error": "History file not found",
    }

    formatted = format_shell_history(context)

    assert "error" in formatted.lower() or "not found" in formatted.lower()


@pytest.mark.unit
def test_format_shell_history_limits_display():
    """Test that formatting limits number of displayed commands."""
    context = {
        "commands": [f"command{i}" for i in range(100)],
        "shell_type": "bash",
        "total_count": 100,
        "filtered_count": 0,
        "error": None,
    }

    formatted = format_shell_history(context)

    # Should not be excessively long (reasonable limit)
    lines = formatted.split("\n")
    # Reasonable limit: header + some commands
    assert len(lines) <= 25


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.unit
def test_get_shell_history_integration(monkeypatch, tmp_path):
    """Integration test for shell history collection and formatting."""
    monkeypatch.setenv("SHELL", "/bin/bash")
    monkeypatch.setenv("HOME", str(tmp_path))

    # Create realistic history
    history_content = """cd ~/projects
git clone https://github.com/user/repo
ls -la
pip install -r requirements.txt
python -m pytest
git status
git add .
git commit -m "Initial commit"
git push origin main
"""
    history_file = tmp_path / ".bash_history"
    history_file.write_text(history_content)

    # Get history
    context = get_shell_history(length=5)

    assert context["shell_type"] == "bash"
    assert len(context["commands"]) == 5
    assert context["error"] is None

    # Format and verify
    formatted = format_shell_history(context)
    assert isinstance(formatted, str)
    assert len(formatted) > 0
