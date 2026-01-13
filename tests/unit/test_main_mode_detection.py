"""
Tests for main entry point mode detection.

This module tests the app mode detection and routing in __main__.py.
"""

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
def test_should_use_app_mode_from_flag():
    """Test app mode detection from command line flag."""
    from hai_sh.__main__ import should_use_app_mode

    assert should_use_app_mode(app_mode_flag=True, env_var_set=False) is True


@pytest.mark.unit
def test_should_use_app_mode_from_env():
    """Test app mode detection from environment variable."""
    from hai_sh.__main__ import should_use_app_mode

    assert should_use_app_mode(app_mode_flag=False, env_var_set=True) is True


@pytest.mark.unit
def test_should_use_app_mode_neither():
    """Test app mode disabled when neither flag nor env var."""
    from hai_sh.__main__ import should_use_app_mode

    assert should_use_app_mode(app_mode_flag=False, env_var_set=False) is False


@pytest.mark.unit
def test_should_use_app_mode_flag_overrides():
    """Test flag overrides environment variable."""
    from hai_sh.__main__ import should_use_app_mode

    # Flag false should override env var true
    assert should_use_app_mode(app_mode_flag=False, env_var_set=True) is True
    # But explicit flag takes precedence
    assert should_use_app_mode(app_mode_flag=True, env_var_set=False) is True
