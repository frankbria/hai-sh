"""
Gum TUI wrapper for hai-sh.

Provides thin wrappers around charmbracelet/gum for interactive terminal
elements (spinners, confirmations, styled output, etc.) with graceful
fallback to plain text when gum is not installed.

gum is an optional runtime dependency. All functions degrade cleanly
to basic terminal I/O without it.

See: https://github.com/charmbracelet/gum
"""

import os
import shutil
import subprocess
import sys
from typing import Callable, List, Optional


# Cache the gum availability check
_gum_path: Optional[str] = None
_gum_checked: bool = False


def has_gum() -> bool:
    """Check if gum is installed and available on PATH. Result is cached."""
    global _gum_path, _gum_checked
    if not _gum_checked:
        _gum_path = shutil.which("gum")
        _gum_checked = True
    return _gum_path is not None


def _is_interactive() -> bool:
    """Check if we're in an interactive TTY (gum requires this)."""
    return hasattr(sys.stdin, "isatty") and sys.stdin.isatty()


def spin(title: str, callback: Callable, *args, **kwargs):
    """
    Show a spinner while executing a callback function.

    If gum is available, displays an animated spinner. Otherwise, prints
    the title and runs the callback directly.

    Args:
        title: Text to display next to the spinner
        callback: Function to execute
        *args, **kwargs: Arguments passed to the callback

    Returns:
        Whatever the callback returns
    """
    if has_gum() and _is_interactive():
        # gum spin runs a command, but we need to run a Python function.
        # Show spinner title, run the callback, then clear the spinner line.
        # We use a simple approach: print spinner-style message, run function.
        sys.stderr.write(f"\033[2m⠋ {title}\033[0m")
        sys.stderr.flush()
        try:
            result = callback(*args, **kwargs)
        finally:
            # Clear the spinner line
            sys.stderr.write(f"\r\033[K")
            sys.stderr.flush()
        return result
    else:
        # Fallback: just print status and run
        print(f"⏳ {title}", file=sys.stderr)
        return callback(*args, **kwargs)


def spin_command(title: str, command: List[str], **kwargs) -> subprocess.CompletedProcess:
    """
    Show a gum spinner while running an external command.

    Unlike spin(), this wraps an actual shell command, which gum spin
    handles natively.

    Args:
        title: Text to display next to the spinner
        command: Command to run as list of strings
        **kwargs: Additional args passed to subprocess.run

    Returns:
        subprocess.CompletedProcess result
    """
    if has_gum() and _is_interactive():
        gum_cmd = [
            _gum_path, "spin",
            "--spinner", "dot",
            "--title", title,
            "--",
        ] + command
        return subprocess.run(gum_cmd, capture_output=True, text=True, **kwargs)
    else:
        print(f"⏳ {title}", file=sys.stderr)
        return subprocess.run(command, capture_output=True, text=True, **kwargs)


def confirm(prompt: str, default: bool = False) -> bool:
    """
    Ask user for yes/no confirmation.

    Uses gum confirm if available, falls back to input().

    Args:
        prompt: The question to ask
        default: Default answer if user presses Enter

    Returns:
        True if user confirmed, False otherwise
    """
    if has_gum() and _is_interactive():
        cmd = [_gum_path, "confirm", prompt]
        if default:
            cmd.append("--default=yes")
        result = subprocess.run(cmd)
        return result.returncode == 0
    else:
        # Fallback
        suffix = "[Y/n]" if default else "[y/N]"
        while True:
            try:
                response = input(f"{prompt} {suffix}: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print()
                return False
            if response in ("y", "yes"):
                return True
            elif response in ("n", "no"):
                return False
            elif response == "":
                return default
            print("Please answer 'y' or 'n'")


def choose(options: List[str], header: str = "") -> Optional[str]:
    """
    Present a list of options for the user to select from.

    Uses gum choose if available, falls back to numbered list + input().

    Args:
        options: List of option strings
        header: Optional header text above the choices

    Returns:
        The selected option string, or None if cancelled
    """
    if not options:
        return None

    if has_gum() and _is_interactive():
        cmd = [_gum_path, "choose"]
        if header:
            cmd.extend(["--header", header])
        cmd.extend(options)
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        return None
    else:
        # Fallback: numbered list
        if header:
            print(header)
        for i, option in enumerate(options, 1):
            print(f"  {i}) {option}")
        while True:
            try:
                response = input("Select [1-{}]: ".format(len(options))).strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return None
            try:
                idx = int(response) - 1
                if 0 <= idx < len(options):
                    return options[idx]
            except ValueError:
                pass
            print(f"Please enter a number between 1 and {len(options)}")


def input_text(
    placeholder: str = "",
    value: str = "",
    password: bool = False,
    prompt_str: str = "> ",
) -> Optional[str]:
    """
    Get text input from the user.

    Uses gum input if available, falls back to input() / getpass.

    Args:
        placeholder: Placeholder text shown when empty
        value: Pre-filled value
        password: If True, mask the input
        prompt_str: Prompt string for fallback mode

    Returns:
        The entered text, or None if cancelled
    """
    if has_gum() and _is_interactive():
        cmd = [_gum_path, "input"]
        if placeholder:
            cmd.extend(["--placeholder", placeholder])
        if value:
            cmd.extend(["--value", value])
        if password:
            cmd.append("--password")
        cmd.extend(["--prompt", prompt_str])
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    else:
        # Fallback
        try:
            if password:
                import getpass
                display = placeholder if placeholder else "Enter value"
                return getpass.getpass(f"{display}: ")
            else:
                display = f" ({placeholder})" if placeholder else ""
                if value:
                    return input(f"{prompt_str}[{value}]{display}: ").strip() or value
                else:
                    return input(f"{prompt_str}{display}: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return None


def styled(
    text: str,
    foreground: str = "",
    background: str = "",
    border: str = "",
    border_foreground: str = "",
    bold: bool = False,
    italic: bool = False,
    padding: str = "",
    margin: str = "",
    width: int = 0,
) -> str:
    """
    Style text with colors, borders, and formatting.

    Uses gum style if available, falls back to ANSI codes for basic styling.

    Args:
        text: Text to style
        foreground: Foreground color (hex like '#04b575' or ANSI number)
        background: Background color
        border: Border style (none, rounded, double, thick, hidden)
        border_foreground: Border color
        bold: Bold text
        italic: Italic text
        padding: Padding (e.g. "0 1" or "1 2")
        margin: Margin (e.g. "0 1")
        width: Fixed width (0 = auto)

    Returns:
        Styled text string
    """
    if has_gum() and _is_interactive() and not os.environ.get("NO_COLOR"):
        cmd = [_gum_path, "style"]
        if foreground:
            cmd.extend(["--foreground", foreground])
        if background:
            cmd.extend(["--background", background])
        if border:
            cmd.extend(["--border", border])
        if border_foreground:
            cmd.extend(["--border-foreground", border_foreground])
        if bold:
            cmd.append("--bold")
        if italic:
            cmd.append("--italic")
        if padding:
            cmd.extend(["--padding", padding])
        if margin:
            cmd.extend(["--margin", margin])
        if width:
            cmd.extend(["--width", str(width)])
        cmd.append(text)
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.rstrip("\n")
        # Fall through to ANSI fallback on error

    # ANSI fallback
    if os.environ.get("NO_COLOR"):
        return text

    codes = []
    if bold:
        codes.append("\033[1m")
    if italic:
        codes.append("\033[3m")
    if foreground:
        # Map common colors to ANSI
        color_map = {
            "212": "\033[38;5;212m",  # pink
            "39": "\033[96m",          # cyan
            "208": "\033[38;5;208m",   # orange
            "196": "\033[91m",         # red
            "82": "\033[92m",          # green
            "226": "\033[93m",         # yellow
        }
        if foreground in color_map:
            codes.append(color_map[foreground])
        elif foreground.startswith("#"):
            # Convert hex to 256-color approximation
            codes.append(f"\033[38;5;{_hex_to_256(foreground)}m")

    prefix = "".join(codes)
    reset = "\033[0m" if codes else ""
    return f"{prefix}{text}{reset}"


def page(text: str, soft_wrap: bool = True) -> None:
    """
    Display long text in a scrollable pager.

    Uses gum pager if available, falls back to printing directly.

    Args:
        text: Text to display
        soft_wrap: Whether to soft-wrap long lines
    """
    if has_gum() and _is_interactive():
        cmd = [_gum_path, "pager"]
        if soft_wrap:
            cmd.append("--soft-wrap")
        subprocess.run(cmd, input=text, text=True)
    else:
        print(text)


def filter_list(items: List[str], placeholder: str = "Filter...") -> Optional[str]:
    """
    Fuzzy-filter a list of items.

    Uses gum filter if available, falls back to simple substring search.

    Args:
        items: List of items to filter
        placeholder: Placeholder text in the filter input

    Returns:
        Selected item, or None if cancelled
    """
    if not items:
        return None

    if has_gum() and _is_interactive():
        cmd = [_gum_path, "filter", "--placeholder", placeholder]
        input_text_data = "\n".join(items)
        result = subprocess.run(cmd, input=input_text_data, capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        return None
    else:
        # Fallback: simple search
        try:
            query = input(f"{placeholder}: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return None
        matches = [item for item in items if query in item.lower()]
        if not matches:
            print("No matches found")
            return None
        if len(matches) == 1:
            return matches[0]
        return choose(matches[:10], header=f"Found {len(matches)} matches:")


def warn(message: str) -> str:
    """
    Format a warning message with visual emphasis.

    Uses gum style with orange/yellow styling if available.

    Args:
        message: Warning text

    Returns:
        Styled warning string
    """
    return styled(
        f"⚠  {message}",
        foreground="208",
        bold=True,
        border="rounded",
        border_foreground="208",
        padding="0 1",
    )


def success(message: str) -> str:
    """
    Format a success message.

    Args:
        message: Success text

    Returns:
        Styled success string
    """
    return styled(f"✓ {message}", foreground="82", bold=True)


def error(message: str) -> str:
    """
    Format an error message.

    Args:
        message: Error text

    Returns:
        Styled error string
    """
    return styled(f"✗ {message}", foreground="196", bold=True)


def _hex_to_256(hex_color: str) -> int:
    """Convert a hex color to the nearest xterm-256 color index."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return 7  # default white
    r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    # Map to 6x6x6 cube (indices 16-231)
    ri = round(r / 255 * 5)
    gi = round(g / 255 * 5)
    bi = round(b / 255 * 5)
    return 16 + 36 * ri + 6 * gi + bi


def reset_cache() -> None:
    """Reset the gum availability cache. Useful for testing."""
    global _gum_path, _gum_checked
    _gum_path = None
    _gum_checked = False
