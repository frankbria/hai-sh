"""
Tests for main entry point mode detection.

This module tests the app mode detection and routing in __main__.py.
"""

import os
import pytest
from unittest.mock import patch, MagicMock


# --- Parser Tests ---


@pytest.mark.unit
def test_parser_has_app_mode_flag():
    """Test argument parser has --app-mode flag."""
    from hai_sh.__main__ import create_parser

    parser = create_parser()
    args = parser.parse_args(["--app-mode", "test query"])

    assert args.app_mode is True


@pytest.mark.unit
def test_parser_app_mode_default_false():
    """Test app mode defaults to False."""
    from hai_sh.__main__ import create_parser

    parser = create_parser()
    args = parser.parse_args(["test query"])

    assert args.app_mode is False


# --- Mode Detection Tests ---


@pytest.mark.unit
def test_is_app_mode_from_flag():
    """Test app mode detection from command line flag."""
    from hai_sh.app_mode import is_app_mode

    assert is_app_mode(app_mode_flag=True) is True


@pytest.mark.unit
def test_is_app_mode_from_env():
    """Test app mode detection from environment variable."""
    from hai_sh.app_mode import is_app_mode

    with patch.dict(os.environ, {"HAI_APP_MODE": "1"}):
        assert is_app_mode(app_mode_flag=None) is True


@pytest.mark.unit
def test_is_app_mode_neither():
    """Test app mode disabled when neither flag nor env var."""
    from hai_sh.app_mode import is_app_mode

    with patch.dict(os.environ, {"HAI_APP_MODE": ""}, clear=False):
        # Ensure HAI_APP_MODE is not set
        os.environ.pop("HAI_APP_MODE", None)
        assert is_app_mode(app_mode_flag=None) is False
        assert is_app_mode(app_mode_flag=False) is False


@pytest.mark.unit
def test_is_app_mode_flag_overrides_env():
    """Test explicit flag overrides environment variable."""
    from hai_sh.app_mode import is_app_mode

    # Explicit True flag takes precedence even if env not set
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("HAI_APP_MODE", None)
        assert is_app_mode(app_mode_flag=True) is True

    # Explicit False flag takes precedence even if env is set
    with patch.dict(os.environ, {"HAI_APP_MODE": "1"}):
        assert is_app_mode(app_mode_flag=False) is False
