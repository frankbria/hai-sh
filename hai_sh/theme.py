"""
Visual design system for hai-sh TUI.

This module defines the color palette, themes, and styling constants
for the Text User Interface components.
"""

import os
from typing import Dict, Literal


# --- Color Constants ---

COLORS: Dict[str, str] = {
    # Confidence level colors
    "confidence_high": "green",
    "confidence_medium": "yellow",
    "confidence_low": "red",
    # UI element colors
    "command_prompt": "cyan",
    "separator": "dim white",
    "error": "bold red",
    "success": "bold green",
    "warning": "bold yellow",
    "info": "blue",
    "muted": "dim",
    # Panel colors
    "conversation_border": "blue",
    "execution_border": "green",
    "meta_border": "dim cyan",
}


# --- Confidence Level Helpers ---


def get_confidence_color(level: Literal["low", "medium", "high"]) -> str:
    """
    Get color for a confidence level.

    Args:
        level: Confidence level ('low', 'medium', or 'high')

    Returns:
        Color name (e.g., 'green', 'yellow', 'red')
    """
    mapping = {
        "high": "green",
        "medium": "yellow",
        "low": "red",
    }
    return mapping.get(level, "white")


def get_confidence_color_from_score(score: int) -> str:
    """
    Get color directly from confidence score.

    Args:
        score: Confidence score (0-100)

    Returns:
        Color name based on score threshold
    """
    if score >= 80:
        return "green"
    elif score >= 50:
        return "yellow"
    else:
        return "red"


def create_confidence_bar(
    score: int,
    width: int = 10,
    filled_char: str = "█",
    empty_char: str = "░"
) -> str:
    """
    Create a visual confidence bar.

    Args:
        score: Confidence score (0-100)
        width: Total width of the bar
        filled_char: Character for filled portion
        empty_char: Character for empty portion

    Returns:
        String representation of the confidence bar
    """
    filled = int((score / 100) * width)
    empty = width - filled
    return filled_char * filled + empty_char * empty


# --- Panel Styles ---

PANEL_STYLES: Dict[str, Dict] = {
    "conversation": {
        "border": "double",
        "title": "Conversation",
        "border_color": "blue",
        "padding": (1, 2),
    },
    "execution": {
        "border": "rounded",
        "title": "Execution",
        "border_color": "green",
        "padding": (0, 1),
    },
    "meta": {
        "border": "single",
        "title": "Meta",
        "border_color": "dim cyan",
        "padding": (0, 1),
        "collapsible": True,
    },
}


# --- Box Drawing Characters ---

BOX_CHARS: Dict[str, Dict[str, str]] = {
    "double": {
        "top_left": "╔",
        "top_right": "╗",
        "bottom_left": "╚",
        "bottom_right": "╝",
        "horizontal": "═",
        "vertical": "║",
    },
    "single": {
        "top_left": "┌",
        "top_right": "┐",
        "bottom_left": "└",
        "bottom_right": "┘",
        "horizontal": "─",
        "vertical": "│",
    },
    "rounded": {
        "top_left": "╭",
        "top_right": "╮",
        "bottom_left": "╰",
        "bottom_right": "╯",
        "horizontal": "─",
        "vertical": "│",
    },
}


# --- Separators ---

SEPARATORS: Dict[str, str] = {
    "dual_layer": "═" * 60,
    "section": "─" * 40,
    "thin": "·" * 40,
}


# --- Themes ---

THEMES: Dict[str, Dict[str, str]] = {
    "dark": {
        "background": "#1a1a1a",
        "foreground": "#e0e0e0",
        "surface": "#2d2d2d",
        "accent": "#4a9eff",
        "success": "#4ade80",
        "warning": "#facc15",
        "error": "#f87171",
        "muted": "#6b7280",
    },
    "light": {
        "background": "#ffffff",
        "foreground": "#1a1a1a",
        "surface": "#f5f5f5",
        "accent": "#2563eb",
        "success": "#16a34a",
        "warning": "#ca8a04",
        "error": "#dc2626",
        "muted": "#9ca3af",
    },
}


def _detect_terminal_theme() -> Literal["dark", "light"]:
    """
    Attempt to detect terminal theme based on environment.

    Returns:
        'dark' or 'light' based on heuristics
    """
    # Check COLORFGBG environment variable (used by some terminals)
    colorfgbg = os.environ.get("COLORFGBG", "")
    if colorfgbg:
        parts = colorfgbg.split(";")
        if len(parts) >= 2:
            bg = int(parts[-1]) if parts[-1].isdigit() else 0
            if bg in (0, 8):  # Black or dark gray background
                return "dark"
            elif bg in (7, 15):  # White or light gray background
                return "light"

    # Check for common dark terminal indicators
    term_program = os.environ.get("TERM_PROGRAM", "").lower()
    if term_program in ("iterm.app", "alacritty", "hyper", "kitty"):
        return "dark"  # These default to dark themes

    # Default to dark theme
    return "dark"


def get_theme(theme_name: Literal["dark", "light", "auto"]) -> Dict[str, str]:
    """
    Get theme colors by name.

    Args:
        theme_name: Theme name ('dark', 'light', or 'auto')

    Returns:
        Dictionary of theme colors
    """
    if theme_name == "auto":
        detected = _detect_terminal_theme()
        return THEMES[detected]
    return THEMES.get(theme_name, THEMES["dark"])


# --- Rich Style Helpers ---

RICH_STYLES: Dict[str, str] = {
    "conversation": "bold cyan",
    "command": "bold yellow",
    "output": "white",
    "error": "bold red",
    "success": "bold green",
    "warning": "bold yellow",
    "info": "blue",
    "muted": "dim",
    "confidence_high": "bold green",
    "confidence_medium": "bold yellow",
    "confidence_low": "bold red",
    "prompt": "bold cyan",
    "header": "bold underline",
}


def get_rich_style(component: str) -> str:
    """
    Get Rich style string for a component.

    Args:
        component: Component name (e.g., 'conversation', 'command', 'error')

    Returns:
        Rich style string
    """
    return RICH_STYLES.get(component, "default")
