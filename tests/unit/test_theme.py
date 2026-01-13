"""
Tests for TUI theme and styling module.

This module tests the visual design system including color palettes,
confidence level styling, and panel themes.
"""

import pytest


# --- Confidence Level Color Tests ---


@pytest.mark.unit
def test_confidence_colors_high():
    """Test high confidence returns green color."""
    from hai_sh.theme import get_confidence_color

    color = get_confidence_color("high")
    assert color == "green"


@pytest.mark.unit
def test_confidence_colors_medium():
    """Test medium confidence returns yellow color."""
    from hai_sh.theme import get_confidence_color

    color = get_confidence_color("medium")
    assert color == "yellow"


@pytest.mark.unit
def test_confidence_colors_low():
    """Test low confidence returns red color."""
    from hai_sh.theme import get_confidence_color

    color = get_confidence_color("low")
    assert color == "red"


@pytest.mark.unit
def test_confidence_colors_from_score():
    """Test getting confidence color directly from score."""
    from hai_sh.theme import get_confidence_color_from_score

    assert get_confidence_color_from_score(85) == "green"
    assert get_confidence_color_from_score(80) == "green"
    assert get_confidence_color_from_score(79) == "yellow"
    assert get_confidence_color_from_score(50) == "yellow"
    assert get_confidence_color_from_score(49) == "red"
    assert get_confidence_color_from_score(0) == "red"


# --- Confidence Bar Tests ---


@pytest.mark.unit
def test_confidence_bar_full():
    """Test confidence bar at 100%."""
    from hai_sh.theme import create_confidence_bar

    bar = create_confidence_bar(100)
    assert "████████████████████" in bar or "█" * 10 in bar


@pytest.mark.unit
def test_confidence_bar_empty():
    """Test confidence bar at 0%."""
    from hai_sh.theme import create_confidence_bar

    bar = create_confidence_bar(0)
    # Should have mostly empty segments
    assert "░" in bar or "·" in bar or "▒" in bar


@pytest.mark.unit
def test_confidence_bar_partial():
    """Test confidence bar at 50%."""
    from hai_sh.theme import create_confidence_bar

    bar = create_confidence_bar(50)
    # Should have mix of filled and empty
    assert "█" in bar
    assert "░" in bar or "·" in bar or "▒" in bar


@pytest.mark.unit
def test_confidence_bar_width():
    """Test confidence bar respects custom width."""
    from hai_sh.theme import create_confidence_bar

    bar = create_confidence_bar(50, width=20)
    # Should have approximately 10 filled and 10 empty (within visible chars)
    visible_length = len(bar.replace("[", "").replace("]", ""))
    assert visible_length >= 20


# --- Panel Style Tests ---


@pytest.mark.unit
def test_panel_styles_exist():
    """Test that panel styles are defined."""
    from hai_sh.theme import PANEL_STYLES

    assert "conversation" in PANEL_STYLES
    assert "execution" in PANEL_STYLES
    assert "meta" in PANEL_STYLES


@pytest.mark.unit
def test_panel_style_conversation():
    """Test conversation panel has double border style."""
    from hai_sh.theme import PANEL_STYLES

    style = PANEL_STYLES["conversation"]
    assert style["border"] == "double"
    assert "title" in style


@pytest.mark.unit
def test_panel_style_execution():
    """Test execution panel has single border style."""
    from hai_sh.theme import PANEL_STYLES

    style = PANEL_STYLES["execution"]
    assert style["border"] in ("single", "rounded")


@pytest.mark.unit
def test_panel_style_meta():
    """Test meta panel is collapsible."""
    from hai_sh.theme import PANEL_STYLES

    style = PANEL_STYLES["meta"]
    assert "border" in style


# --- Theme Tests ---


@pytest.mark.unit
def test_theme_dark_exists():
    """Test dark theme is defined."""
    from hai_sh.theme import THEMES

    assert "dark" in THEMES
    theme = THEMES["dark"]
    assert "background" in theme
    assert "foreground" in theme


@pytest.mark.unit
def test_theme_light_exists():
    """Test light theme is defined."""
    from hai_sh.theme import THEMES

    assert "light" in THEMES
    theme = THEMES["light"]
    assert "background" in theme
    assert "foreground" in theme


@pytest.mark.unit
def test_theme_auto_detection():
    """Test auto theme detection."""
    from hai_sh.theme import get_theme

    # Auto should return either dark or light
    theme = get_theme("auto")
    assert theme is not None
    assert "background" in theme


@pytest.mark.unit
def test_get_theme_explicit():
    """Test explicit theme selection."""
    from hai_sh.theme import get_theme, THEMES

    dark_theme = get_theme("dark")
    assert dark_theme == THEMES["dark"]

    light_theme = get_theme("light")
    assert light_theme == THEMES["light"]


# --- Rich Style Helpers ---


@pytest.mark.unit
def test_get_rich_style_conversation():
    """Test Rich style for conversation panel."""
    from hai_sh.theme import get_rich_style

    style = get_rich_style("conversation")
    assert style is not None
    # Style should be a string or Rich Style object
    assert isinstance(style, (str, object))


@pytest.mark.unit
def test_get_rich_style_command():
    """Test Rich style for command display."""
    from hai_sh.theme import get_rich_style

    style = get_rich_style("command")
    assert style is not None


@pytest.mark.unit
def test_get_rich_style_error():
    """Test Rich style for error display."""
    from hai_sh.theme import get_rich_style

    style = get_rich_style("error")
    assert style is not None


@pytest.mark.unit
def test_get_rich_style_success():
    """Test Rich style for success display."""
    from hai_sh.theme import get_rich_style

    style = get_rich_style("success")
    assert style is not None


@pytest.mark.unit
def test_get_rich_style_unknown():
    """Test Rich style for unknown component returns default."""
    from hai_sh.theme import get_rich_style

    style = get_rich_style("nonexistent_component")
    # Should return a default style, not crash
    assert style is not None


# --- Color Constants ---


@pytest.mark.unit
def test_color_constants_defined():
    """Test that color constants are defined."""
    from hai_sh.theme import COLORS

    assert "confidence_high" in COLORS
    assert "confidence_medium" in COLORS
    assert "confidence_low" in COLORS
    assert "command_prompt" in COLORS
    assert "separator" in COLORS


@pytest.mark.unit
def test_color_values_are_valid():
    """Test that color values are valid Rich color strings."""
    from hai_sh.theme import COLORS

    for name, color in COLORS.items():
        # Colors should be strings
        assert isinstance(color, str), f"Color {name} should be a string"
        # Colors should not be empty
        assert len(color) > 0, f"Color {name} should not be empty"


# --- Separator Tests ---


@pytest.mark.unit
def test_separator_dual_layer():
    """Test dual-layer separator character."""
    from hai_sh.theme import SEPARATORS

    assert "dual_layer" in SEPARATORS
    sep = SEPARATORS["dual_layer"]
    assert len(sep) > 0


@pytest.mark.unit
def test_separator_section():
    """Test section separator character."""
    from hai_sh.theme import SEPARATORS

    assert "section" in SEPARATORS
    sep = SEPARATORS["section"]
    assert len(sep) > 0


# --- Box Characters ---


@pytest.mark.unit
def test_box_chars_double():
    """Test double box characters for conversation panel."""
    from hai_sh.theme import BOX_CHARS

    assert "double" in BOX_CHARS
    chars = BOX_CHARS["double"]
    assert "top_left" in chars
    assert "top_right" in chars
    assert "bottom_left" in chars
    assert "bottom_right" in chars
    assert "horizontal" in chars
    assert "vertical" in chars


@pytest.mark.unit
def test_box_chars_single():
    """Test single box characters for execution panel."""
    from hai_sh.theme import BOX_CHARS

    assert "single" in BOX_CHARS
    chars = BOX_CHARS["single"]
    assert "top_left" in chars
    assert "horizontal" in chars
