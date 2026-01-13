"""
Interactive TUI application mode for hai-sh.

This module provides the interactive app mode that can be triggered
via Ctrl+X Ctrl+H from the shell integration or via --app-mode flag.
"""

import os
from typing import Any, Dict, List, Optional

from hai_sh.schema import HaiConfig, LLMResponse, validate_config_dict
from hai_sh.provider_manager import ProviderManager
from hai_sh.tui import MenuBar


# Environment variable for app mode detection
APP_MODE_ENV_VAR = "HAI_APP_MODE"


def is_app_mode(app_mode_flag: Optional[bool] = None) -> bool:
    """
    Determine if app mode should be enabled.

    Args:
        app_mode_flag: Explicit flag from command line (overrides env var)

    Returns:
        True if app mode should be enabled
    """
    # Explicit flag takes precedence
    if app_mode_flag is not None:
        return app_mode_flag

    # Check environment variable
    return os.environ.get(APP_MODE_ENV_VAR, "").lower() in ("1", "true", "yes")


class InteractiveHaiApp:
    """
    Interactive TUI application for hai-sh.

    Provides a full-screen TUI with:
    - Conversation panel (top)
    - Meta info panel (middle, collapsible)
    - Execution panel (bottom)
    - Menu bar (accessible via Ctrl-Tab)
    """

    def __init__(self, config: HaiConfig):
        """
        Initialize InteractiveHaiApp.

        Args:
            config: HaiConfig instance with application configuration
        """
        self._config = config
        self._provider_manager = ProviderManager(config)
        self._menu_bar = MenuBar()
        self._response: Optional[LLMResponse] = None
        self._should_exit = False

    @property
    def config(self) -> HaiConfig:
        """Get the configuration."""
        return self._config

    @property
    def provider_manager(self) -> ProviderManager:
        """Get the provider manager."""
        return self._provider_manager

    @property
    def menu_visible(self) -> bool:
        """Get menu visibility state."""
        return self._menu_bar.visible

    @property
    def response(self) -> Optional[LLMResponse]:
        """Get the current LLM response."""
        return self._response

    @property
    def should_exit(self) -> bool:
        """Check if app should exit."""
        return self._should_exit

    def toggle_menu(self) -> None:
        """Toggle menu visibility."""
        self._menu_bar.toggle()

    def show_menu(self) -> None:
        """Show the menu."""
        self._menu_bar.show()

    def hide_menu(self) -> None:
        """Hide the menu."""
        self._menu_bar.hide()

    def set_response(self, response: LLMResponse) -> None:
        """
        Set the current LLM response.

        Args:
            response: LLMResponse to display
        """
        self._response = response

    def get_menu_items(self) -> List[Dict[str, str]]:
        """
        Get menu items.

        Returns:
            List of menu item dictionaries
        """
        return self._menu_bar.get_items()

    def request_exit(self) -> None:
        """Request app exit."""
        self._should_exit = True

    def handle_menu_action(self, action_id: str) -> None:
        """
        Handle a menu action.

        Args:
            action_id: ID of the menu action to handle
        """
        if action_id == "exit":
            self.request_exit()
        elif action_id == "provider":
            # Show provider switching UI (placeholder)
            pass
        elif action_id == "git":
            # Show git status (placeholder)
            pass
        elif action_id == "status":
            # Show status (placeholder)
            pass


def create_app_from_config(config_dict: Dict[str, Any]) -> InteractiveHaiApp:
    """
    Create an InteractiveHaiApp from a configuration dictionary.

    Args:
        config_dict: Configuration dictionary

    Returns:
        Configured InteractiveHaiApp instance
    """
    validated_config, warnings = validate_config_dict(config_dict)
    return InteractiveHaiApp(validated_config)


def run_app_mode(config: HaiConfig, query: Optional[str] = None) -> int:
    """
    Run the interactive TUI application.

    Args:
        config: HaiConfig instance
        query: Optional initial query

    Returns:
        Exit code (0 for success)
    """
    app = InteractiveHaiApp(config)

    # For now, just display a message that app mode is not fully implemented
    # In a full implementation, this would run a Textual app
    from rich.console import Console
    from rich.panel import Panel

    console = Console()
    console.print(Panel(
        "[bold cyan]hai[/bold cyan] Interactive Mode\n\n"
        "App mode is activated but the full interactive TUI is not yet implemented.\n"
        "Use standard mode with: [bold]hai \"your query\"[/bold]",
        title="hai - Interactive Mode",
        border_style="cyan",
    ))

    return 0
