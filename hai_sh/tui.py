"""
TUI (Text User Interface) components for hai-sh.

This module provides Textual-based widgets for the interactive TUI mode,
including panels for conversation, execution, meta information, and menus.
"""

from typing import Any, Dict, List, Optional

from hai_sh.theme import (
    get_confidence_color,
    get_confidence_color_from_score,
    create_confidence_bar,
    PANEL_STYLES,
)


class ConversationPanel:
    """
    Panel widget for displaying LLM conversation/explanation.

    Displays the LLM's reasoning with syntax highlighting and
    optional confidence display.
    """

    def __init__(
        self,
        content: str = "",
        confidence: Optional[int] = None,
    ):
        """
        Initialize ConversationPanel.

        Args:
            content: The conversation/explanation text
            confidence: Optional confidence score (0-100)
        """
        self._content = content
        self._confidence = confidence
        self._style = PANEL_STYLES.get("conversation", {})

    @property
    def content(self) -> str:
        """Get the conversation content."""
        return self._content

    @content.setter
    def content(self, value: str) -> None:
        """Set the conversation content."""
        self._content = value

    @property
    def confidence(self) -> Optional[int]:
        """Get the confidence score."""
        return self._confidence

    @confidence.setter
    def confidence(self, value: Optional[int]) -> None:
        """Set the confidence score."""
        self._confidence = value


class MetaInfoPanel:
    """
    Collapsible panel for displaying meta information.

    Shows confidence level (color-coded) and internal dialogue.
    Collapsed by default to reduce visual clutter.
    """

    def __init__(
        self,
        confidence: int,
        internal_dialogue: Optional[str] = None,
        collapsed: bool = True,
    ):
        """
        Initialize MetaInfoPanel.

        Args:
            confidence: Confidence score (0-100)
            internal_dialogue: Optional internal reasoning text
            collapsed: Whether panel is collapsed (default: True)
        """
        self._confidence = confidence
        self._internal_dialogue = internal_dialogue
        self._collapsed = collapsed
        self._style = PANEL_STYLES.get("meta", {})

    @property
    def confidence(self) -> int:
        """Get the confidence score."""
        return self._confidence

    @property
    def internal_dialogue(self) -> Optional[str]:
        """Get the internal dialogue text."""
        return self._internal_dialogue

    @property
    def collapsed(self) -> bool:
        """Get collapsed state."""
        return self._collapsed

    @collapsed.setter
    def collapsed(self, value: bool) -> None:
        """Set collapsed state."""
        self._collapsed = value

    def toggle(self) -> None:
        """Toggle collapsed state."""
        self._collapsed = not self._collapsed

    def expand(self) -> None:
        """Expand the panel."""
        self._collapsed = False

    def collapse(self) -> None:
        """Collapse the panel."""
        self._collapsed = True


class ExecutionPanel:
    """
    Panel widget for displaying command execution.

    Shows the command prompt, stdout, stderr, and exit status.
    """

    def __init__(
        self,
        command: str,
        stdout: str = "",
        stderr: str = "",
        exit_code: Optional[int] = None,
        timed_out: bool = False,
        interrupted: bool = False,
    ):
        """
        Initialize ExecutionPanel.

        Args:
            command: The command that was executed
            stdout: Standard output from the command
            stderr: Standard error from the command
            exit_code: Exit code from the command
            timed_out: Whether the command timed out
            interrupted: Whether the command was interrupted
        """
        self._command = command
        self._stdout = stdout
        self._stderr = stderr
        self._exit_code = exit_code
        self._timed_out = timed_out
        self._interrupted = interrupted
        self._style = PANEL_STYLES.get("execution", {})

    @property
    def command(self) -> str:
        """Get the command."""
        return self._command

    @property
    def stdout(self) -> str:
        """Get stdout."""
        return self._stdout

    @stdout.setter
    def stdout(self, value: str) -> None:
        """Set stdout."""
        self._stdout = value

    @property
    def stderr(self) -> str:
        """Get stderr."""
        return self._stderr

    @stderr.setter
    def stderr(self, value: str) -> None:
        """Set stderr."""
        self._stderr = value

    @property
    def exit_code(self) -> Optional[int]:
        """Get exit code."""
        return self._exit_code

    @exit_code.setter
    def exit_code(self, value: Optional[int]) -> None:
        """Set exit code."""
        self._exit_code = value

    @property
    def is_success(self) -> bool:
        """Check if command succeeded."""
        return self._exit_code == 0


class MenuBar:
    """
    Menu bar widget accessible via Ctrl-Tab.

    Provides options for provider switching, status, git status, and exit.
    """

    DEFAULT_ITEMS = [
        {"id": "provider", "label": "Provider", "description": "Switch LLM provider"},
        {"id": "status", "label": "Status", "description": "Show checkpoint status"},
        {"id": "git", "label": "Git Status", "description": "Show git repository status"},
        {"id": "exit", "label": "Exit", "description": "Exit app mode"},
    ]

    def __init__(self, items: Optional[List[Dict[str, str]]] = None):
        """
        Initialize MenuBar.

        Args:
            items: Optional list of menu items. Uses defaults if not provided.
        """
        self._items = items if items is not None else self.DEFAULT_ITEMS.copy()
        self._visible = False
        self._selected_index = 0

    @property
    def visible(self) -> bool:
        """Get visibility state."""
        return self._visible

    @visible.setter
    def visible(self, value: bool) -> None:
        """Set visibility state."""
        self._visible = value

    def show(self) -> None:
        """Show the menu bar."""
        self._visible = True

    def hide(self) -> None:
        """Hide the menu bar."""
        self._visible = False

    def toggle(self) -> None:
        """Toggle menu visibility."""
        self._visible = not self._visible

    def get_items(self) -> List[Dict[str, str]]:
        """Get menu items."""
        return self._items

    @property
    def selected_index(self) -> int:
        """Get selected item index."""
        return self._selected_index

    def select_next(self) -> None:
        """Select next item."""
        self._selected_index = (self._selected_index + 1) % len(self._items)

    def select_previous(self) -> None:
        """Select previous item."""
        self._selected_index = (self._selected_index - 1) % len(self._items)

    def get_selected(self) -> Dict[str, str]:
        """Get currently selected item."""
        return self._items[self._selected_index]


class ConfidenceBadge:
    """
    Badge widget for displaying confidence score.

    Shows a color-coded badge with the confidence level.
    """

    def __init__(self, confidence: int):
        """
        Initialize ConfidenceBadge.

        Args:
            confidence: Confidence score (0-100)
        """
        self._confidence = confidence

    @property
    def confidence(self) -> int:
        """Get the confidence score."""
        return self._confidence

    @property
    def level(self) -> str:
        """Get the confidence level (high/medium/low)."""
        if self._confidence >= 80:
            return "high"
        elif self._confidence >= 50:
            return "medium"
        else:
            return "low"

    @property
    def color(self) -> str:
        """Get the color for this confidence level."""
        return get_confidence_color_from_score(self._confidence)

    def get_bar(self, width: int = 10) -> str:
        """Get a visual confidence bar."""
        return create_confidence_bar(self._confidence, width=width)


def create_response_widgets(response) -> Dict[str, Any]:
    """
    Create TUI widgets from an LLMResponse.

    Args:
        response: LLMResponse object with conversation, command, confidence, etc.

    Returns:
        Dictionary of widget instances keyed by name
    """
    widgets = {}

    # Create conversation panel
    widgets["conversation_panel"] = ConversationPanel(
        content=response.conversation,
        confidence=response.confidence,
    )

    # Create meta info panel
    widgets["meta_panel"] = MetaInfoPanel(
        confidence=response.confidence,
        internal_dialogue=response.internal_dialogue,
    )

    # Create execution panel if command exists
    if response.command:
        widgets["execution_panel"] = ExecutionPanel(
            command=response.command,
        )

    return widgets


class MainLayout:
    """
    Main layout definition for the TUI.

    Defines the three-section layout:
    - Conversation (top)
    - Meta info (middle, collapsible)
    - Execution (bottom)
    """

    SECTIONS = ["conversation", "meta", "execution"]

    def __init__(self):
        """Initialize MainLayout."""
        self._sections = self.SECTIONS.copy()

    @property
    def sections(self) -> List[str]:
        """Get layout sections."""
        return self._sections


def create_main_layout() -> MainLayout:
    """
    Create the main TUI layout.

    Returns:
        MainLayout instance defining the section structure
    """
    return MainLayout()
