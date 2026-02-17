"""Tests for hai_sh.gum module — gum TUI wrapper with fallbacks."""

import os
import subprocess
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
