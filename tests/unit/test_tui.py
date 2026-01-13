"""
Tests for TUI components module.

This module tests the Textual-based TUI widgets and their behavior.
"""

import pytest
from unittest.mock import MagicMock


# --- Widget Import Tests ---


@pytest.mark.unit
def test_conversation_panel_importable():
    """Test ConversationPanel can be imported."""
    from hai_sh.tui import ConversationPanel

    assert ConversationPanel is not None


@pytest.mark.unit
def test_meta_info_panel_importable():
    """Test MetaInfoPanel can be imported."""
    from hai_sh.tui import MetaInfoPanel

    assert MetaInfoPanel is not None


@pytest.mark.unit
def test_execution_panel_importable():
    """Test ExecutionPanel can be imported."""
    from hai_sh.tui import ExecutionPanel

    assert ExecutionPanel is not None


@pytest.mark.unit
def test_menu_bar_importable():
    """Test MenuBar can be imported."""
    from hai_sh.tui import MenuBar

    assert MenuBar is not None


# --- ConversationPanel Tests ---


@pytest.mark.unit
def test_conversation_panel_creation():
    """Test ConversationPanel can be created with content."""
    from hai_sh.tui import ConversationPanel

    panel = ConversationPanel(content="Test explanation")
    assert panel is not None
    assert panel.content == "Test explanation"


@pytest.mark.unit
def test_conversation_panel_empty_content():
    """Test ConversationPanel handles empty content."""
    from hai_sh.tui import ConversationPanel

    panel = ConversationPanel(content="")
    assert panel.content == ""


@pytest.mark.unit
def test_conversation_panel_with_confidence():
    """Test ConversationPanel with confidence display."""
    from hai_sh.tui import ConversationPanel

    panel = ConversationPanel(content="Test", confidence=85)
    assert panel.confidence == 85


# --- MetaInfoPanel Tests ---


@pytest.mark.unit
def test_meta_info_panel_creation():
    """Test MetaInfoPanel can be created."""
    from hai_sh.tui import MetaInfoPanel

    panel = MetaInfoPanel(confidence=85)
    assert panel is not None
    assert panel.confidence == 85


@pytest.mark.unit
def test_meta_info_panel_with_internal_dialogue():
    """Test MetaInfoPanel with internal dialogue."""
    from hai_sh.tui import MetaInfoPanel

    panel = MetaInfoPanel(
        confidence=90,
        internal_dialogue="Thinking about the command structure..."
    )
    assert panel.internal_dialogue == "Thinking about the command structure..."


@pytest.mark.unit
def test_meta_info_panel_collapsed_by_default():
    """Test MetaInfoPanel is collapsed by default."""
    from hai_sh.tui import MetaInfoPanel

    panel = MetaInfoPanel(confidence=75)
    assert panel.collapsed is True


@pytest.mark.unit
def test_meta_info_panel_can_expand():
    """Test MetaInfoPanel can be expanded."""
    from hai_sh.tui import MetaInfoPanel

    panel = MetaInfoPanel(confidence=75, collapsed=False)
    assert panel.collapsed is False


@pytest.mark.unit
def test_meta_info_panel_toggle():
    """Test MetaInfoPanel toggle functionality."""
    from hai_sh.tui import MetaInfoPanel

    panel = MetaInfoPanel(confidence=75)
    assert panel.collapsed is True

    panel.toggle()
    assert panel.collapsed is False

    panel.toggle()
    assert panel.collapsed is True


# --- ExecutionPanel Tests ---


@pytest.mark.unit
def test_execution_panel_creation():
    """Test ExecutionPanel can be created."""
    from hai_sh.tui import ExecutionPanel

    panel = ExecutionPanel(command="ls -la")
    assert panel is not None
    assert panel.command == "ls -la"


@pytest.mark.unit
def test_execution_panel_with_output():
    """Test ExecutionPanel with command output."""
    from hai_sh.tui import ExecutionPanel

    panel = ExecutionPanel(
        command="echo hello",
        stdout="hello\n",
        exit_code=0
    )
    assert panel.stdout == "hello\n"
    assert panel.exit_code == 0


@pytest.mark.unit
def test_execution_panel_with_error():
    """Test ExecutionPanel with error output."""
    from hai_sh.tui import ExecutionPanel

    panel = ExecutionPanel(
        command="invalid_cmd",
        stderr="command not found",
        exit_code=127
    )
    assert panel.stderr == "command not found"
    assert panel.exit_code == 127


@pytest.mark.unit
def test_execution_panel_success_status():
    """Test ExecutionPanel shows success status."""
    from hai_sh.tui import ExecutionPanel

    panel = ExecutionPanel(command="ls", exit_code=0)
    assert panel.is_success is True


@pytest.mark.unit
def test_execution_panel_failure_status():
    """Test ExecutionPanel shows failure status."""
    from hai_sh.tui import ExecutionPanel

    panel = ExecutionPanel(command="invalid", exit_code=1)
    assert panel.is_success is False


# --- MenuBar Tests ---


@pytest.mark.unit
def test_menu_bar_creation():
    """Test MenuBar can be created."""
    from hai_sh.tui import MenuBar

    menu = MenuBar()
    assert menu is not None


@pytest.mark.unit
def test_menu_bar_has_items():
    """Test MenuBar has expected menu items."""
    from hai_sh.tui import MenuBar

    menu = MenuBar()
    items = menu.get_items()

    assert "provider" in [item["id"] for item in items]
    assert "status" in [item["id"] for item in items]
    assert "git" in [item["id"] for item in items]
    assert "exit" in [item["id"] for item in items]


@pytest.mark.unit
def test_menu_bar_visibility():
    """Test MenuBar visibility toggle."""
    from hai_sh.tui import MenuBar

    menu = MenuBar()
    assert menu.visible is False  # Hidden by default

    menu.show()
    assert menu.visible is True

    menu.hide()
    assert menu.visible is False


@pytest.mark.unit
def test_menu_bar_toggle():
    """Test MenuBar toggle functionality."""
    from hai_sh.tui import MenuBar

    menu = MenuBar()
    assert menu.visible is False

    menu.toggle()
    assert menu.visible is True

    menu.toggle()
    assert menu.visible is False


# --- Widget Factory Tests ---


@pytest.mark.unit
def test_create_response_widgets():
    """Test creating widgets from LLMResponse."""
    from hai_sh.tui import create_response_widgets
    from hai_sh.schema import LLMResponse

    response = LLMResponse(
        conversation="I'll list your files",
        command="ls -la",
        confidence=85,
        internal_dialogue="Simple directory listing task"
    )

    widgets = create_response_widgets(response)

    assert "conversation_panel" in widgets
    assert "meta_panel" in widgets


@pytest.mark.unit
def test_create_response_widgets_no_command():
    """Test creating widgets for question-only response."""
    from hai_sh.tui import create_response_widgets
    from hai_sh.schema import LLMResponse

    response = LLMResponse(
        conversation="Python 3.9 was released October 2020",
        confidence=95
    )

    widgets = create_response_widgets(response)

    assert "conversation_panel" in widgets
    assert "meta_panel" in widgets


# --- Confidence Badge Tests ---


@pytest.mark.unit
def test_confidence_badge_creation():
    """Test confidence badge can be created."""
    from hai_sh.tui import ConfidenceBadge

    badge = ConfidenceBadge(confidence=85)
    assert badge is not None
    assert badge.confidence == 85


@pytest.mark.unit
def test_confidence_badge_level_high():
    """Test confidence badge level for high confidence."""
    from hai_sh.tui import ConfidenceBadge

    badge = ConfidenceBadge(confidence=85)
    assert badge.level == "high"


@pytest.mark.unit
def test_confidence_badge_level_medium():
    """Test confidence badge level for medium confidence."""
    from hai_sh.tui import ConfidenceBadge

    badge = ConfidenceBadge(confidence=65)
    assert badge.level == "medium"


@pytest.mark.unit
def test_confidence_badge_level_low():
    """Test confidence badge level for low confidence."""
    from hai_sh.tui import ConfidenceBadge

    badge = ConfidenceBadge(confidence=30)
    assert badge.level == "low"


# --- Layout Tests ---


@pytest.mark.unit
def test_main_layout_exists():
    """Test main layout function exists."""
    from hai_sh.tui import create_main_layout

    layout = create_main_layout()
    assert layout is not None


@pytest.mark.unit
def test_main_layout_has_sections():
    """Test main layout has expected sections."""
    from hai_sh.tui import create_main_layout

    layout = create_main_layout()

    # Layout should define the three main sections
    assert hasattr(layout, "sections") or isinstance(layout, dict)
