"""
Tests for app mode module.

This module tests the interactive TUI application mode.
"""

import pytest
from unittest.mock import MagicMock, patch


# --- Import Tests ---


@pytest.mark.unit
def test_interactive_hai_app_importable():
    """Test InteractiveHaiApp can be imported."""
    from hai_sh.app_mode import InteractiveHaiApp

    assert InteractiveHaiApp is not None


@pytest.mark.unit
def test_run_app_mode_importable():
    """Test run_app_mode function can be imported."""
    from hai_sh.app_mode import run_app_mode

    assert run_app_mode is not None


@pytest.mark.unit
def test_is_app_mode_importable():
    """Test is_app_mode function can be imported."""
    from hai_sh.app_mode import is_app_mode

    assert is_app_mode is not None


# --- App Detection Tests ---


@pytest.mark.unit
def test_is_app_mode_from_env():
    """Test app mode detection from environment variable."""
    from hai_sh.app_mode import is_app_mode

    with patch.dict("os.environ", {"HAI_APP_MODE": "1"}):
        assert is_app_mode() is True


@pytest.mark.unit
def test_is_app_mode_from_env_false():
    """Test app mode detection when env var is not set."""
    from hai_sh.app_mode import is_app_mode

    with patch.dict("os.environ", {}, clear=True):
        # Remove HAI_APP_MODE if present
        import os
        if "HAI_APP_MODE" in os.environ:
            del os.environ["HAI_APP_MODE"]
        assert is_app_mode() is False


@pytest.mark.unit
def test_is_app_mode_from_flag():
    """Test app mode detection from explicit flag."""
    from hai_sh.app_mode import is_app_mode

    assert is_app_mode(app_mode_flag=True) is True


@pytest.mark.unit
def test_is_app_mode_flag_overrides_env():
    """Test explicit flag overrides environment variable."""
    from hai_sh.app_mode import is_app_mode

    with patch.dict("os.environ", {"HAI_APP_MODE": "1"}):
        # Flag False should override env var
        assert is_app_mode(app_mode_flag=False) is False


# --- App Creation Tests ---


@pytest.mark.unit
def test_interactive_hai_app_creation():
    """Test InteractiveHaiApp can be created."""
    from hai_sh.app_mode import InteractiveHaiApp
    from hai_sh.schema import HaiConfig

    config = HaiConfig()
    app = InteractiveHaiApp(config)

    assert app is not None


@pytest.mark.unit
def test_interactive_hai_app_has_config():
    """Test app stores configuration."""
    from hai_sh.app_mode import InteractiveHaiApp
    from hai_sh.schema import HaiConfig

    config = HaiConfig(provider="ollama")
    app = InteractiveHaiApp(config)

    assert app.config.provider == "ollama"


@pytest.mark.unit
def test_interactive_hai_app_has_provider_manager():
    """Test app has provider manager."""
    from hai_sh.app_mode import InteractiveHaiApp
    from hai_sh.schema import HaiConfig

    config = HaiConfig()
    app = InteractiveHaiApp(config)

    assert app.provider_manager is not None


# --- App State Tests ---


@pytest.mark.unit
def test_app_initial_state():
    """Test app starts in correct initial state."""
    from hai_sh.app_mode import InteractiveHaiApp
    from hai_sh.schema import HaiConfig

    config = HaiConfig()
    app = InteractiveHaiApp(config)

    assert app.menu_visible is False
    assert app.response is None


@pytest.mark.unit
def test_app_toggle_menu():
    """Test menu toggle functionality."""
    from hai_sh.app_mode import InteractiveHaiApp
    from hai_sh.schema import HaiConfig

    config = HaiConfig()
    app = InteractiveHaiApp(config)

    assert app.menu_visible is False
    app.toggle_menu()
    assert app.menu_visible is True
    app.toggle_menu()
    assert app.menu_visible is False


@pytest.mark.unit
def test_app_set_response():
    """Test setting response updates app state."""
    from hai_sh.app_mode import InteractiveHaiApp
    from hai_sh.schema import HaiConfig, LLMResponse

    config = HaiConfig()
    app = InteractiveHaiApp(config)

    response = LLMResponse(
        conversation="Test response",
        confidence=85
    )

    app.set_response(response)

    assert app.response is not None
    assert app.response.conversation == "Test response"


# --- Menu Actions Tests ---


@pytest.mark.unit
def test_app_get_menu_items():
    """Test getting menu items."""
    from hai_sh.app_mode import InteractiveHaiApp
    from hai_sh.schema import HaiConfig

    config = HaiConfig()
    app = InteractiveHaiApp(config)

    items = app.get_menu_items()

    assert isinstance(items, list)
    assert len(items) > 0


@pytest.mark.unit
def test_app_menu_has_provider_option():
    """Test menu has provider switching option."""
    from hai_sh.app_mode import InteractiveHaiApp
    from hai_sh.schema import HaiConfig

    config = HaiConfig()
    app = InteractiveHaiApp(config)

    items = app.get_menu_items()
    item_ids = [item["id"] for item in items]

    assert "provider" in item_ids


@pytest.mark.unit
def test_app_menu_has_exit_option():
    """Test menu has exit option."""
    from hai_sh.app_mode import InteractiveHaiApp
    from hai_sh.schema import HaiConfig

    config = HaiConfig()
    app = InteractiveHaiApp(config)

    items = app.get_menu_items()
    item_ids = [item["id"] for item in items]

    assert "exit" in item_ids


# --- Exit Tests ---


@pytest.mark.unit
def test_app_exit_sets_flag():
    """Test exit action sets exit flag."""
    from hai_sh.app_mode import InteractiveHaiApp
    from hai_sh.schema import HaiConfig

    config = HaiConfig()
    app = InteractiveHaiApp(config)

    assert app.should_exit is False
    app.request_exit()
    assert app.should_exit is True


# --- Helper Function Tests ---


@pytest.mark.unit
def test_create_app_from_config():
    """Test creating app from config dictionary."""
    from hai_sh.app_mode import create_app_from_config

    config_dict = {
        "provider": "ollama",
    }

    app = create_app_from_config(config_dict)

    assert app is not None
    assert app.config.provider == "ollama"


@pytest.mark.unit
def test_get_app_mode_env_var_name():
    """Test getting the environment variable name."""
    from hai_sh.app_mode import APP_MODE_ENV_VAR

    assert APP_MODE_ENV_VAR == "HAI_APP_MODE"
