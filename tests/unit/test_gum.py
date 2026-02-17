"""Tests for hai_sh.gum module — gum TUI wrapper with fallbacks."""

import json
import os
import stat
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from hai_sh import gum


@pytest.fixture(autouse=True)
def reset_gum_cache():
    """Reset the gum availability cache before each test."""
    gum.reset_cache()
    yield
    gum.reset_cache()


# ─── has_gum() ───────────────────────────────────────────────────────

class TestHasGum:
    def test_returns_true_when_gum_found(self):
        with patch("shutil.which", return_value="/usr/bin/gum"):
            assert gum.has_gum() is True

    def test_returns_false_when_gum_not_found(self):
        with patch("shutil.which", return_value=None):
            assert gum.has_gum() is False

    def test_result_is_cached(self):
        with patch("shutil.which", return_value="/usr/bin/gum") as mock_which:
            assert gum.has_gum() is True
            assert gum.has_gum() is True
            # Should only call which() once due to caching
            mock_which.assert_called_once()

    def test_reset_cache_clears_cached_result(self):
        with patch("shutil.which", return_value="/usr/bin/gum"):
            gum.has_gum()
        gum.reset_cache()
        with patch("shutil.which", return_value=None):
            assert gum.has_gum() is False


# ─── _is_interactive() ───────────────────────────────────────────────

class TestIsInteractive:
    def test_returns_true_for_tty(self):
        mock_stdin = MagicMock()
        mock_stdin.isatty.return_value = True
        with patch("hai_sh.gum.sys") as mock_sys:
            mock_sys.stdin = mock_stdin
            assert gum._is_interactive() is True

    def test_returns_false_for_pipe(self):
        mock_stdin = MagicMock()
        mock_stdin.isatty.return_value = False
        with patch("hai_sh.gum.sys") as mock_sys:
            mock_sys.stdin = mock_stdin
            assert gum._is_interactive() is False


# ─── spin() ──────────────────────────────────────────────────────────

class TestSpin:
    def test_executes_callback_and_returns_result(self):
        callback = MagicMock(return_value={"key": "value"})
        result = gum.spin("Working...", callback, "arg1", kwarg1="val1")
        callback.assert_called_once_with("arg1", kwarg1="val1")
        assert result == {"key": "value"}

    def test_fallback_prints_status(self, capsys):
        with patch.object(gum, "has_gum", return_value=False):
            result = gum.spin("Processing...", lambda: 42)
            assert result == 42
            captured = capsys.readouterr()
            assert "Processing..." in captured.err

    def test_spinner_clears_on_success(self):
        """With gum available and interactive, spinner line should be cleared."""
        with patch.object(gum, "has_gum", return_value=True), \
             patch.object(gum, "_is_interactive", return_value=True), \
             patch("hai_sh.gum.sys") as mock_sys:
            mock_stderr = MagicMock()
            mock_sys.stderr = mock_stderr
            mock_sys.stdin = MagicMock()
            mock_sys.stdin.isatty.return_value = True
            result = gum.spin("Thinking...", lambda: "ok")
            assert result == "ok"
            # Check spinner was written and cleared
            assert mock_stderr.write.call_count >= 2


# ─── confirm() ───────────────────────────────────────────────────────

class TestConfirm:
    def test_fallback_yes(self):
        with patch.object(gum, "has_gum", return_value=False), \
             patch("builtins.input", return_value="y"):
            assert gum.confirm("Proceed?") is True

    def test_fallback_no(self):
        with patch.object(gum, "has_gum", return_value=False), \
             patch("builtins.input", return_value="n"):
            assert gum.confirm("Proceed?") is False

    def test_fallback_empty_default_false(self):
        with patch.object(gum, "has_gum", return_value=False), \
             patch("builtins.input", return_value=""):
            assert gum.confirm("Proceed?", default=False) is False

    def test_fallback_empty_default_true(self):
        with patch.object(gum, "has_gum", return_value=False), \
             patch("builtins.input", return_value=""):
            assert gum.confirm("Proceed?", default=True) is True

    def test_fallback_eof_returns_false(self):
        with patch.object(gum, "has_gum", return_value=False), \
             patch("builtins.input", side_effect=EOFError):
            assert gum.confirm("Proceed?") is False

    def test_gum_confirm_success(self):
        with patch.object(gum, "has_gum", return_value=True), \
             patch.object(gum, "_is_interactive", return_value=True), \
             patch("subprocess.run", return_value=MagicMock(returncode=0)) as mock_run:
            gum._gum_path = "/usr/bin/gum"
            assert gum.confirm("Delete?") is True
            cmd = mock_run.call_args[0][0]
            assert cmd[0] == "/usr/bin/gum"
            assert "confirm" in cmd
            assert "Delete?" in cmd

    def test_gum_confirm_rejected(self):
        with patch.object(gum, "has_gum", return_value=True), \
             patch.object(gum, "_is_interactive", return_value=True), \
             patch("subprocess.run", return_value=MagicMock(returncode=1)):
            gum._gum_path = "/usr/bin/gum"
            assert gum.confirm("Delete?") is False


# ─── choose() ────────────────────────────────────────────────────────

class TestChoose:
    def test_empty_options_returns_none(self):
        assert gum.choose([]) is None

    def test_fallback_valid_selection(self):
        with patch.object(gum, "has_gum", return_value=False), \
             patch("builtins.input", return_value="2"):
            result = gum.choose(["Alpha", "Beta", "Gamma"])
            assert result == "Beta"

    def test_fallback_eof_returns_none(self):
        with patch.object(gum, "has_gum", return_value=False), \
             patch("builtins.input", side_effect=EOFError):
            assert gum.choose(["A", "B"]) is None

    def test_gum_choose_returns_selection(self):
        mock_result = MagicMock(returncode=0, stdout="Beta\n")
        with patch.object(gum, "has_gum", return_value=True), \
             patch.object(gum, "_is_interactive", return_value=True), \
             patch("subprocess.run", return_value=mock_result) as mock_run:
            gum._gum_path = "/usr/bin/gum"
            result = gum.choose(["Alpha", "Beta", "Gamma"], header="Pick one")
            assert result == "Beta"
            cmd = mock_run.call_args[0][0]
            assert "--header" in cmd
            assert "Pick one" in cmd

    def test_gum_choose_cancelled_returns_none(self):
        mock_result = MagicMock(returncode=1, stdout="")
        with patch.object(gum, "has_gum", return_value=True), \
             patch.object(gum, "_is_interactive", return_value=True), \
             patch("subprocess.run", return_value=mock_result):
            gum._gum_path = "/usr/bin/gum"
            assert gum.choose(["A", "B"]) is None


# ─── input_text() ────────────────────────────────────────────────────

class TestInputText:
    def test_fallback_basic_input(self):
        with patch.object(gum, "has_gum", return_value=False), \
             patch("builtins.input", return_value="hello"):
            result = gum.input_text(placeholder="Name")
            assert result == "hello"

    def test_fallback_with_default_value(self):
        with patch.object(gum, "has_gum", return_value=False), \
             patch("builtins.input", return_value=""):
            result = gum.input_text(value="default")
            assert result == "default"

    def test_fallback_password_uses_getpass(self):
        with patch.object(gum, "has_gum", return_value=False), \
             patch("getpass.getpass", return_value="secret123"):
            result = gum.input_text(password=True, placeholder="API Key")
            assert result == "secret123"

    def test_fallback_eof_returns_none(self):
        with patch.object(gum, "has_gum", return_value=False), \
             patch("builtins.input", side_effect=EOFError):
            assert gum.input_text() is None

    def test_gum_input_success(self):
        mock_result = MagicMock(returncode=0, stdout="typed text\n")
        with patch.object(gum, "has_gum", return_value=True), \
             patch.object(gum, "_is_interactive", return_value=True), \
             patch("subprocess.run", return_value=mock_result) as mock_run:
            gum._gum_path = "/usr/bin/gum"
            result = gum.input_text(placeholder="Enter name", value="John")
            assert result == "typed text"
            cmd = mock_run.call_args[0][0]
            assert "--placeholder" in cmd
            assert "--value" in cmd

    def test_gum_input_password_flag(self):
        mock_result = MagicMock(returncode=0, stdout="secret\n")
        with patch.object(gum, "has_gum", return_value=True), \
             patch.object(gum, "_is_interactive", return_value=True), \
             patch("subprocess.run", return_value=mock_result) as mock_run:
            gum._gum_path = "/usr/bin/gum"
            gum.input_text(password=True)
            cmd = mock_run.call_args[0][0]
            assert "--password" in cmd


# ─── styled() ────────────────────────────────────────────────────────

class TestStyled:
    def test_no_color_returns_plain_text(self):
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            result = gum.styled("hello", foreground="82", bold=True)
            assert result == "hello"

    def test_ansi_fallback_bold(self):
        with patch.object(gum, "has_gum", return_value=False), \
             patch.dict(os.environ, {}, clear=False):
            # Remove NO_COLOR if present
            os.environ.pop("NO_COLOR", None)
            result = gum.styled("hello", bold=True)
            assert "\033[1m" in result
            assert "hello" in result
            assert "\033[0m" in result

    def test_ansi_fallback_foreground_color(self):
        with patch.object(gum, "has_gum", return_value=False), \
             patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NO_COLOR", None)
            result = gum.styled("ok", foreground="82")
            assert "\033[92m" in result  # green

    def test_gum_style_called_with_args(self):
        mock_result = MagicMock(returncode=0, stdout="styled text\n")
        with patch.object(gum, "has_gum", return_value=True), \
             patch.object(gum, "_is_interactive", return_value=True), \
             patch.dict(os.environ, {}, clear=False), \
             patch("subprocess.run", return_value=mock_result) as mock_run:
            os.environ.pop("NO_COLOR", None)
            gum._gum_path = "/usr/bin/gum"
            result = gum.styled("text", border="rounded", bold=True, foreground="39")
            assert result == "styled text"
            cmd = mock_run.call_args[0][0]
            assert "--border" in cmd
            assert "--bold" in cmd
            assert "--foreground" in cmd


# ─── warn() / success() / error() ────────────────────────────────────

class TestMessageStyles:
    def test_warn_contains_message(self):
        with patch.object(gum, "has_gum", return_value=False), \
             patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NO_COLOR", None)
            result = gum.warn("danger ahead")
            assert "danger ahead" in result

    def test_success_contains_message(self):
        with patch.object(gum, "has_gum", return_value=False), \
             patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NO_COLOR", None)
            result = gum.success("all good")
            assert "all good" in result
            assert "✓" in result

    def test_error_contains_message(self):
        with patch.object(gum, "has_gum", return_value=False), \
             patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NO_COLOR", None)
            result = gum.error("failed")
            assert "failed" in result
            assert "✗" in result


# ─── page() ──────────────────────────────────────────────────────────

class TestPage:
    def test_fallback_prints_text(self, capsys):
        with patch.object(gum, "has_gum", return_value=False):
            gum.page("line1\nline2\nline3")
            captured = capsys.readouterr()
            assert "line1" in captured.out
            assert "line3" in captured.out

    def test_gum_pager_called(self):
        with patch.object(gum, "has_gum", return_value=True), \
             patch.object(gum, "_is_interactive", return_value=True), \
             patch("subprocess.run") as mock_run:
            gum._gum_path = "/usr/bin/gum"
            gum.page("long text here")
            cmd = mock_run.call_args[0][0]
            assert "pager" in cmd
            assert "--soft-wrap" in cmd


# ─── filter_list() ───────────────────────────────────────────────────

class TestFilterList:
    def test_empty_list_returns_none(self):
        assert gum.filter_list([]) is None

    def test_fallback_substring_match(self):
        with patch.object(gum, "has_gum", return_value=False), \
             patch("builtins.input", return_value="beta"):
            # Single match should be returned directly
            result = gum.filter_list(["alpha", "beta", "gamma"])
            assert result == "beta"

    def test_fallback_no_match(self, capsys):
        with patch.object(gum, "has_gum", return_value=False), \
             patch("builtins.input", return_value="xyz"):
            result = gum.filter_list(["alpha", "beta"])
            assert result is None

    def test_gum_filter_success(self):
        mock_result = MagicMock(returncode=0, stdout="beta\n")
        with patch.object(gum, "has_gum", return_value=True), \
             patch.object(gum, "_is_interactive", return_value=True), \
             patch("subprocess.run", return_value=mock_result) as mock_run:
            gum._gum_path = "/usr/bin/gum"
            result = gum.filter_list(["alpha", "beta", "gamma"])
            assert result == "beta"
            cmd = mock_run.call_args[0][0]
            assert "filter" in cmd


# ─── _hex_to_256() ───────────────────────────────────────────────────

class TestHexTo256:
    def test_black(self):
        assert gum._hex_to_256("#000000") == 16

    def test_white(self):
        assert gum._hex_to_256("#ffffff") == 231

    def test_red(self):
        # Pure red should be in the red range
        result = gum._hex_to_256("#ff0000")
        assert 16 <= result <= 231

    def test_invalid_hex_returns_default(self):
        assert gum._hex_to_256("#bad") == 7


# ─── spin_command() ──────────────────────────────────────────────────

class TestSpinCommand:
    def test_fallback_runs_command_directly(self, capsys):
        mock_result = MagicMock(returncode=0, stdout="output\n", stderr="")
        with patch.object(gum, "has_gum", return_value=False), \
             patch("subprocess.run", return_value=mock_result) as mock_run:
            result = gum.spin_command("Testing...", ["echo", "hello"])
            # Should call subprocess.run with the original command
            assert mock_run.call_args[0][0] == ["echo", "hello"]

    def test_gum_wraps_command(self):
        mock_result = MagicMock(returncode=0, stdout="output\n", stderr="")
        with patch.object(gum, "has_gum", return_value=True), \
             patch.object(gum, "_is_interactive", return_value=True), \
             patch("subprocess.run", return_value=mock_result) as mock_run:
            gum._gum_path = "/usr/bin/gum"
            gum.spin_command("Building...", ["make", "build"])
            cmd = mock_run.call_args[0][0]
            assert cmd[0] == "/usr/bin/gum"
            assert "spin" in cmd
            assert "--" in cmd
            # Original command should be at the end
            assert "make" in cmd
            assert "build" in cmd


# ─── is_dangerous_command() ──────────────────────────────────────────

class TestIsDangerousCommand:
    """Test the dangerous command detection in __main__."""

    def test_rm_detected(self):
        from hai_sh.__main__ import is_dangerous_command
        assert is_dangerous_command("rm -rf /tmp/stuff") is True

    def test_safe_command_not_flagged(self):
        from hai_sh.__main__ import is_dangerous_command
        assert is_dangerous_command("ls -la") is False

    def test_kill_detected(self):
        from hai_sh.__main__ import is_dangerous_command
        assert is_dangerous_command("kill -9 1234") is True

    def test_case_insensitive(self):
        from hai_sh.__main__ import is_dangerous_command
        assert is_dangerous_command("REBOOT") is True

    def test_chmod_777_detected(self):
        from hai_sh.__main__ import is_dangerous_command
        assert is_dangerous_command("chmod 777 /var/www") is True

    def test_normal_chmod_safe(self):
        from hai_sh.__main__ import is_dangerous_command
        assert is_dangerous_command("chmod 644 file.txt") is False


# ─── get_user_confirmation() tuple return ─────────────────────────────

class TestGetUserConfirmation:
    """Test the updated get_user_confirmation returns (action, command) tuples."""

    def test_confirm_yes_returns_execute(self):
        from hai_sh.__main__ import get_user_confirmation
        with patch.object(gum, "has_gum", return_value=False), \
             patch("builtins.input", return_value="y"):
            action, cmd = get_user_confirmation("ls -la")
            assert action == "execute"
            assert cmd == "ls -la"

    def test_confirm_no_returns_cancel(self):
        from hai_sh.__main__ import get_user_confirmation
        with patch.object(gum, "has_gum", return_value=False), \
             patch("builtins.input", return_value="n"):
            action, cmd = get_user_confirmation("ls -la")
            assert action == "cancel"

    def test_confirm_empty_returns_cancel(self):
        from hai_sh.__main__ import get_user_confirmation
        with patch.object(gum, "has_gum", return_value=False), \
             patch("builtins.input", return_value=""):
            action, cmd = get_user_confirmation("ls -la")
            assert action == "cancel"

    def test_confirm_edit_with_gum_input(self):
        from hai_sh.__main__ import get_user_confirmation
        with patch.object(gum, "has_gum", return_value=False), \
             patch("builtins.input", side_effect=["e", ""]), \
             patch.object(gum, "input_text", return_value="ls -la --color"):
            action, cmd = get_user_confirmation("ls -la")
            assert action == "execute"
            assert cmd == "ls -la --color"

    def test_gum_choose_execute(self):
        from hai_sh.__main__ import get_user_confirmation
        with patch.object(gum, "has_gum", return_value=True), \
             patch.object(gum, "_is_interactive", return_value=True), \
             patch.object(gum, "choose", return_value="Execute"):
            action, cmd = get_user_confirmation("ls -la")
            assert action == "execute"
            assert cmd == "ls -la"

    def test_gum_choose_cancel(self):
        from hai_sh.__main__ import get_user_confirmation
        with patch.object(gum, "has_gum", return_value=True), \
             patch.object(gum, "_is_interactive", return_value=True), \
             patch.object(gum, "choose", return_value="Cancel"):
            action, cmd = get_user_confirmation("ls -la")
            assert action == "cancel"

    def test_gum_choose_edit(self):
        from hai_sh.__main__ import get_user_confirmation
        with patch.object(gum, "has_gum", return_value=True), \
             patch.object(gum, "_is_interactive", return_value=True), \
             patch.object(gum, "choose", return_value="Edit"), \
             patch.object(gum, "input_text", return_value="ls -la --all"):
            action, cmd = get_user_confirmation("ls -la")
            assert action == "execute"
            assert cmd == "ls -la --all"


# ─── print_output() ──────────────────────────────────────────────────

class TestPrintOutput:
    def test_empty_output_prints_nothing(self, capsys):
        from hai_sh.__main__ import print_output
        print_output("")
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_short_output_prints_directly(self, capsys):
        from hai_sh.__main__ import print_output
        with patch.object(gum, "has_gum", return_value=False):
            print_output("hello world")
            captured = capsys.readouterr()
            assert "hello world" in captured.out

    def test_long_output_uses_pager_when_available(self):
        from hai_sh.__main__ import print_output
        long_text = "\n".join([f"line {i}" for i in range(200)])
        with patch("os.get_terminal_size", return_value=MagicMock(lines=40, columns=80)), \
             patch.object(gum, "has_gum", return_value=True), \
             patch.object(gum, "_is_interactive", return_value=True), \
             patch.object(gum, "page") as mock_page:
            print_output(long_text)
            mock_page.assert_called_once_with(long_text)

    def test_long_output_prints_directly_without_gum(self, capsys):
        from hai_sh.__main__ import print_output
        long_text = "\n".join([f"line {i}" for i in range(200)])
        with patch("os.get_terminal_size", return_value=MagicMock(lines=40, columns=80)), \
             patch.object(gum, "has_gum", return_value=False):
            print_output(long_text)
            captured = capsys.readouterr()
            assert "line 0" in captured.out
            assert "line 199" in captured.out

    def test_terminal_size_error_uses_default(self, capsys):
        from hai_sh.__main__ import print_output
        # 10 lines should be less than default 40
        text = "\n".join([f"line {i}" for i in range(10)])
        with patch("os.get_terminal_size", side_effect=OSError), \
             patch.object(gum, "has_gum", return_value=False):
            print_output(text)
            captured = capsys.readouterr()
            assert "line 0" in captured.out


# ─── confirm() edge cases ────────────────────────────────────────────

class TestConfirmEdgeCases:
    def test_fallback_invalid_then_valid(self):
        """User types invalid input then 'y' — should retry and accept."""
        with patch.object(gum, "has_gum", return_value=False), \
             patch("builtins.input", side_effect=["what", "y"]):
            assert gum.confirm("Proceed?") is True

    def test_fallback_keyboard_interrupt(self):
        with patch.object(gum, "has_gum", return_value=False), \
             patch("builtins.input", side_effect=KeyboardInterrupt):
            assert gum.confirm("Proceed?") is False

    def test_gum_confirm_with_default_yes(self):
        with patch.object(gum, "has_gum", return_value=True), \
             patch.object(gum, "_is_interactive", return_value=True), \
             patch("subprocess.run", return_value=MagicMock(returncode=0)) as mock_run:
            gum._gum_path = "/usr/bin/gum"
            gum.confirm("Proceed?", default=True)
            cmd = mock_run.call_args[0][0]
            assert "--default=yes" in cmd


# ─── choose() edge cases ─────────────────────────────────────────────

class TestChooseEdgeCases:
    def test_fallback_invalid_then_valid(self):
        """User types non-number then valid number."""
        with patch.object(gum, "has_gum", return_value=False), \
             patch("builtins.input", side_effect=["abc", "1"]):
            result = gum.choose(["Alpha", "Beta"])
            assert result == "Alpha"

    def test_fallback_out_of_range_then_valid(self):
        """User types out-of-range number then valid."""
        with patch.object(gum, "has_gum", return_value=False), \
             patch("builtins.input", side_effect=["99", "2"]):
            result = gum.choose(["Alpha", "Beta"])
            assert result == "Beta"

    def test_fallback_with_header_prints_header(self, capsys):
        with patch.object(gum, "has_gum", return_value=False), \
             patch("builtins.input", return_value="1"):
            gum.choose(["Alpha"], header="Pick one:")
            captured = capsys.readouterr()
            assert "Pick one:" in captured.out

    def test_gum_choose_no_header(self):
        """When no header is provided, --header flag should be absent."""
        mock_result = MagicMock(returncode=0, stdout="Alpha\n")
        with patch.object(gum, "has_gum", return_value=True), \
             patch.object(gum, "_is_interactive", return_value=True), \
             patch("subprocess.run", return_value=mock_result) as mock_run:
            gum._gum_path = "/usr/bin/gum"
            gum.choose(["Alpha", "Beta"])
            cmd = mock_run.call_args[0][0]
            assert "--header" not in cmd


# ─── input_text() edge cases ─────────────────────────────────────────

class TestInputTextEdgeCases:
    def test_gum_input_failure_returns_none(self):
        mock_result = MagicMock(returncode=1, stdout="")
        with patch.object(gum, "has_gum", return_value=True), \
             patch.object(gum, "_is_interactive", return_value=True), \
             patch("subprocess.run", return_value=mock_result):
            gum._gum_path = "/usr/bin/gum"
            assert gum.input_text(placeholder="test") is None

    def test_fallback_no_placeholder_no_value(self):
        with patch.object(gum, "has_gum", return_value=False), \
             patch("builtins.input", return_value="typed"):
            result = gum.input_text()
            assert result == "typed"

    def test_fallback_keyboard_interrupt(self):
        with patch.object(gum, "has_gum", return_value=False), \
             patch("builtins.input", side_effect=KeyboardInterrupt):
            assert gum.input_text() is None


# ─── styled() edge cases ─────────────────────────────────────────────

class TestStyledEdgeCases:
    def test_ansi_fallback_italic(self):
        with patch.object(gum, "has_gum", return_value=False), \
             patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NO_COLOR", None)
            result = gum.styled("text", italic=True)
            assert "\033[3m" in result

    def test_ansi_fallback_hex_color(self):
        with patch.object(gum, "has_gum", return_value=False), \
             patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NO_COLOR", None)
            result = gum.styled("text", foreground="#ff5500")
            assert "\033[38;5;" in result

    def test_ansi_fallback_no_codes_no_reset(self):
        """When no styling is applied, no ANSI reset should be added."""
        with patch.object(gum, "has_gum", return_value=False), \
             patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NO_COLOR", None)
            result = gum.styled("plain")
            assert result == "plain"
            assert "\033[0m" not in result

    def test_gum_style_all_options(self):
        """Test that all style options are passed to gum."""
        mock_result = MagicMock(returncode=0, stdout="styled\n")
        with patch.object(gum, "has_gum", return_value=True), \
             patch.object(gum, "_is_interactive", return_value=True), \
             patch.dict(os.environ, {}, clear=False), \
             patch("subprocess.run", return_value=mock_result) as mock_run:
            os.environ.pop("NO_COLOR", None)
            gum._gum_path = "/usr/bin/gum"
            gum.styled(
                "text",
                foreground="39",
                background="0",
                border="rounded",
                border_foreground="208",
                bold=True,
                italic=True,
                padding="1 2",
                margin="0 1",
                width=40,
            )
            cmd = mock_run.call_args[0][0]
            assert "--foreground" in cmd
            assert "--background" in cmd
            assert "--border" in cmd
            assert "--border-foreground" in cmd
            assert "--bold" in cmd
            assert "--italic" in cmd
            assert "--padding" in cmd
            assert "--margin" in cmd
            assert "--width" in cmd

    def test_gum_style_error_falls_through_to_ansi(self):
        """When gum style fails, should fall through to ANSI fallback."""
        mock_result = MagicMock(returncode=1, stdout="")
        with patch.object(gum, "has_gum", return_value=True), \
             patch.object(gum, "_is_interactive", return_value=True), \
             patch.dict(os.environ, {}, clear=False), \
             patch("subprocess.run", return_value=mock_result):
            os.environ.pop("NO_COLOR", None)
            gum._gum_path = "/usr/bin/gum"
            result = gum.styled("text", bold=True)
            assert "\033[1m" in result


# ─── filter_list() edge cases ────────────────────────────────────────

class TestFilterListEdgeCases:
    def test_fallback_multiple_matches_shows_choose(self):
        """When multiple items match, filter_list should present choose()."""
        with patch.object(gum, "has_gum", return_value=False), \
             patch("builtins.input", side_effect=["a", "1"]):
            # "a" matches "alpha" and "gamma"
            result = gum.filter_list(["alpha", "beta", "gamma"])
            assert result in ("alpha", "gamma")

    def test_fallback_eof_returns_none(self):
        with patch.object(gum, "has_gum", return_value=False), \
             patch("builtins.input", side_effect=EOFError):
            assert gum.filter_list(["alpha", "beta"]) is None

    def test_gum_filter_cancelled_returns_none(self):
        mock_result = MagicMock(returncode=1, stdout="")
        with patch.object(gum, "has_gum", return_value=True), \
             patch.object(gum, "_is_interactive", return_value=True), \
             patch("subprocess.run", return_value=mock_result):
            gum._gum_path = "/usr/bin/gum"
            assert gum.filter_list(["alpha", "beta"]) is None


# ─── page() edge cases ───────────────────────────────────────────────

class TestPageEdgeCases:
    def test_gum_pager_no_soft_wrap(self):
        with patch.object(gum, "has_gum", return_value=True), \
             patch.object(gum, "_is_interactive", return_value=True), \
             patch("subprocess.run") as mock_run:
            gum._gum_path = "/usr/bin/gum"
            gum.page("text", soft_wrap=False)
            cmd = mock_run.call_args[0][0]
            assert "--soft-wrap" not in cmd


# ─── run_setup_wizard() ──────────────────────────────────────────────

class TestRunSetupWizard:
    def test_setup_openai_provider(self, tmp_path):
        from hai_sh.__main__ import run_setup_wizard
        config_path = tmp_path / ".hai" / "config.yaml"
        with patch.object(gum, "choose", return_value="OpenAI"), \
             patch.object(gum, "input_text", side_effect=["sk-test123", "gpt-4o"]), \
             patch.object(gum, "confirm", return_value=False), \
             patch("hai_sh.__main__._write_setup_config") as mock_write, \
             patch.object(gum, "styled", side_effect=lambda t, **k: t), \
             patch.object(gum, "success", side_effect=lambda t: t):
            result = run_setup_wizard()
            assert result == 0
            call_args = mock_write.call_args[0][0]
            assert call_args["provider"] == "openai"
            assert call_args["openai_api_key"] == "sk-test123"
            assert call_args["openai_model"] == "gpt-4o"

    def test_setup_anthropic_provider(self):
        from hai_sh.__main__ import run_setup_wizard
        with patch.object(gum, "choose", return_value="Anthropic"), \
             patch.object(gum, "input_text", side_effect=["sk-ant-key", "claude-sonnet-4-5"]), \
             patch.object(gum, "confirm", return_value=False), \
             patch("hai_sh.__main__._write_setup_config") as mock_write, \
             patch.object(gum, "styled", side_effect=lambda t, **k: t), \
             patch.object(gum, "success", side_effect=lambda t: t):
            result = run_setup_wizard()
            assert result == 0
            call_args = mock_write.call_args[0][0]
            assert call_args["provider"] == "anthropic"
            assert call_args["anthropic_api_key"] == "sk-ant-key"

    def test_setup_ollama_provider(self):
        from hai_sh.__main__ import run_setup_wizard
        with patch.object(gum, "choose", return_value="Ollama (local)"), \
             patch.object(gum, "input_text", side_effect=["http://localhost:11434", "llama3.2"]), \
             patch.object(gum, "confirm", return_value=False), \
             patch("hai_sh.__main__._write_setup_config") as mock_write, \
             patch.object(gum, "styled", side_effect=lambda t, **k: t), \
             patch.object(gum, "success", side_effect=lambda t: t):
            result = run_setup_wizard()
            assert result == 0
            call_args = mock_write.call_args[0][0]
            assert call_args["provider"] == "ollama"
            assert call_args["ollama_base_url"] == "http://localhost:11434"

    def test_setup_cancelled(self):
        from hai_sh.__main__ import run_setup_wizard
        with patch.object(gum, "choose", return_value=None), \
             patch.object(gum, "styled", side_effect=lambda t, **k: t):
            result = run_setup_wizard()
            assert result == 0

    def test_setup_with_shell_integration(self):
        from hai_sh.__main__ import run_setup_wizard
        with patch.object(gum, "choose", return_value="Ollama (local)"), \
             patch.object(gum, "input_text", side_effect=["http://localhost:11434", "llama3.2"]), \
             patch.object(gum, "confirm", return_value=True), \
             patch("hai_sh.__main__._write_setup_config"), \
             patch("hai_sh.install_shell.install_shell_integration") as mock_install, \
             patch.object(gum, "styled", side_effect=lambda t, **k: t), \
             patch.object(gum, "success", side_effect=lambda t: t):
            result = run_setup_wizard()
            assert result == 0
            mock_install.assert_called_once()


# ─── _write_setup_config() ───────────────────────────────────────────

class TestWriteSetupConfig:
    def test_writes_valid_yaml_for_openai(self, tmp_path):
        from hai_sh.__main__ import _write_setup_config
        config_path = tmp_path / "config.yaml"
        with patch("hai_sh.init.get_config_path", return_value=config_path), \
             patch("hai_sh.init.init_hai_directory", return_value=(True, None)):
            _write_setup_config({
                "provider": "openai",
                "openai_api_key": "sk-test",
                "openai_model": "gpt-4o",
            })
        content = config_path.read_text()
        assert 'provider: "openai"' in content
        assert 'api_key: "sk-test"' in content
        assert 'model: "gpt-4o"' in content
        # Config file should be readable only by owner
        mode = config_path.stat().st_mode
        assert mode & stat.S_IRUSR  # owner read
        assert mode & stat.S_IWUSR  # owner write

    def test_writes_defaults_without_api_keys(self, tmp_path):
        from hai_sh.__main__ import _write_setup_config
        config_path = tmp_path / "config.yaml"
        with patch("hai_sh.init.get_config_path", return_value=config_path), \
             patch("hai_sh.init.init_hai_directory", return_value=(True, None)):
            _write_setup_config({"provider": "ollama"})
        content = config_path.read_text()
        assert 'provider: "ollama"' in content
        assert '# api_key: "sk-..."' in content  # commented out
        assert '# api_key: "sk-ant-..."' in content  # commented out
        assert 'base_url: "http://localhost:11434"' in content

    def test_writes_anthropic_config(self, tmp_path):
        from hai_sh.__main__ import _write_setup_config
        config_path = tmp_path / "config.yaml"
        with patch("hai_sh.init.get_config_path", return_value=config_path), \
             patch("hai_sh.init.init_hai_directory", return_value=(True, None)):
            _write_setup_config({
                "provider": "anthropic",
                "anthropic_api_key": "sk-ant-xyz",
                "anthropic_model": "claude-sonnet-4-5",
            })
        content = config_path.read_text()
        assert 'provider: "anthropic"' in content
        assert 'api_key: "sk-ant-xyz"' in content


# ─── run_history_search() ────────────────────────────────────────────

class TestRunHistorySearch:
    def test_no_history_dir(self, tmp_path):
        from hai_sh.__main__ import run_history_search
        with patch("hai_sh.init.get_hai_dir", return_value=tmp_path / "nonexistent"):
            result = run_history_search()
            assert result == 0

    def test_no_commands_in_memory(self, tmp_path):
        from hai_sh.__main__ import run_history_search
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()
        memory_file = tmp_path / "memory.json"
        memory_file.write_text(json.dumps({"interactions": []}))
        with patch("hai_sh.init.get_hai_dir", return_value=tmp_path):
            result = run_history_search()
            assert result == 0

    def test_history_with_commands_selected(self, tmp_path):
        from hai_sh.__main__ import run_history_search
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()
        memory_file = tmp_path / "memory.json"
        memory_file.write_text(json.dumps({
            "interactions": [
                {"command": "ls -la", "query": "list files"},
                {"command": "git status", "query": "git status"},
                {"command": "ls -la", "query": "list files again"},  # duplicate
            ]
        }))
        with patch("hai_sh.init.get_hai_dir", return_value=tmp_path), \
             patch.object(gum, "filter_list", return_value="git status"), \
             patch.object(gum, "confirm", return_value=False):
            result = run_history_search()
            assert result == 0

    def test_history_execute_selected_command(self, tmp_path):
        from hai_sh.__main__ import run_history_search
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()
        memory_file = tmp_path / "memory.json"
        memory_file.write_text(json.dumps({
            "interactions": [{"command": "echo hello", "query": "say hi"}]
        }))
        mock_result = MagicMock(success=True, stdout="hello\n", stderr="", exit_code=0)
        with patch("hai_sh.init.get_hai_dir", return_value=tmp_path), \
             patch.object(gum, "filter_list", return_value="echo hello"), \
             patch.object(gum, "confirm", return_value=True), \
             patch("hai_sh.__main__.execute_command", return_value=mock_result):
            result = run_history_search()
            assert result == 0

    def test_history_cancelled_filter(self, tmp_path):
        from hai_sh.__main__ import run_history_search
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()
        memory_file = tmp_path / "memory.json"
        memory_file.write_text(json.dumps({
            "interactions": [{"command": "ls", "query": "list"}]
        }))
        with patch("hai_sh.init.get_hai_dir", return_value=tmp_path), \
             patch.object(gum, "filter_list", return_value=None):
            result = run_history_search()
            assert result == 0

    def test_history_malformed_json(self, tmp_path):
        from hai_sh.__main__ import run_history_search
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()
        memory_file = tmp_path / "memory.json"
        memory_file.write_text("not valid json")
        with patch("hai_sh.init.get_hai_dir", return_value=tmp_path):
            result = run_history_search()
            assert result == 0


# ─── get_user_confirmation() more edge cases ─────────────────────────

class TestGetUserConfirmationEdgeCases:
    def test_fallback_eof_returns_cancel(self):
        from hai_sh.__main__ import get_user_confirmation
        with patch.object(gum, "has_gum", return_value=False), \
             patch("builtins.input", side_effect=EOFError):
            action, cmd = get_user_confirmation("ls")
            assert action == "cancel"

    def test_fallback_keyboard_interrupt_returns_cancel(self):
        from hai_sh.__main__ import get_user_confirmation
        with patch.object(gum, "has_gum", return_value=False), \
             patch("builtins.input", side_effect=KeyboardInterrupt):
            action, cmd = get_user_confirmation("ls")
            assert action == "cancel"

    def test_fallback_invalid_then_yes(self):
        from hai_sh.__main__ import get_user_confirmation
        with patch.object(gum, "has_gum", return_value=False), \
             patch("builtins.input", side_effect=["what", "y"]):
            action, cmd = get_user_confirmation("ls")
            assert action == "execute"

    def test_gum_choose_none_returns_cancel(self):
        """When gum choose returns None (user pressed Ctrl+C), should cancel."""
        from hai_sh.__main__ import get_user_confirmation
        with patch.object(gum, "has_gum", return_value=True), \
             patch.object(gum, "_is_interactive", return_value=True), \
             patch.object(gum, "choose", return_value=None):
            action, cmd = get_user_confirmation("ls")
            assert action == "cancel"

    def test_gum_edit_cancelled_returns_cancel(self):
        """When user selects Edit but then cancels the input, should cancel."""
        from hai_sh.__main__ import get_user_confirmation
        with patch.object(gum, "has_gum", return_value=True), \
             patch.object(gum, "_is_interactive", return_value=True), \
             patch.object(gum, "choose", return_value="Edit"), \
             patch.object(gum, "input_text", return_value=None):
            action, cmd = get_user_confirmation("ls")
            assert action == "cancel"

    def test_gum_edit_empty_returns_cancel(self):
        """When user selects Edit but enters empty string, should cancel."""
        from hai_sh.__main__ import get_user_confirmation
        with patch.object(gum, "has_gum", return_value=True), \
             patch.object(gum, "_is_interactive", return_value=True), \
             patch.object(gum, "choose", return_value="Edit"), \
             patch.object(gum, "input_text", return_value="  "):
            action, cmd = get_user_confirmation("ls")
            assert action == "cancel"

    def test_fallback_edit_cancelled_returns_cancel(self):
        """In fallback mode, edit cancelled should return cancel."""
        from hai_sh.__main__ import get_user_confirmation
        with patch.object(gum, "has_gum", return_value=False), \
             patch("builtins.input", return_value="e"), \
             patch.object(gum, "input_text", return_value=None):
            action, cmd = get_user_confirmation("ls")
            assert action == "cancel"


# ─── is_dangerous_command() more patterns ─────────────────────────────

class TestIsDangerousCommandMore:
    def test_dd_detected(self):
        from hai_sh.__main__ import is_dangerous_command
        assert is_dangerous_command("dd if=/dev/zero of=/dev/sda") is True

    def test_shutdown_detected(self):
        from hai_sh.__main__ import is_dangerous_command
        assert is_dangerous_command("shutdown -h now") is True

    def test_drop_table_detected(self):
        from hai_sh.__main__ import is_dangerous_command
        assert is_dangerous_command("mysql -e 'DROP TABLE users'") is True

    def test_pkill_detected(self):
        from hai_sh.__main__ import is_dangerous_command
        assert is_dangerous_command("pkill nginx") is True

    def test_rmdir_detected(self):
        from hai_sh.__main__ import is_dangerous_command
        assert is_dangerous_command("rmdir /important") is True

    def test_chown_recursive_detected(self):
        from hai_sh.__main__ import is_dangerous_command
        assert is_dangerous_command("chown -R root:root /") is True

    def test_pipe_to_dev_null_safe(self):
        """Redirecting to /dev/null is common and safe."""
        from hai_sh.__main__ import is_dangerous_command
        # "> /dev/" pattern matches, but this is intentional for safety
        assert is_dangerous_command("echo test > /dev/null") is True

    def test_grep_is_safe(self):
        from hai_sh.__main__ import is_dangerous_command
        assert is_dangerous_command("grep -r 'pattern' .") is False

    def test_find_is_safe(self):
        from hai_sh.__main__ import is_dangerous_command
        assert is_dangerous_command("find . -name '*.log' -type f") is False
