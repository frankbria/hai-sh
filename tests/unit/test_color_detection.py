"""
Tests for color detection and TTY utilities.
"""

import io
import os
import sys
from unittest.mock import Mock, patch

import pytest

from hai_sh.output import (
    get_color_mode,
    is_tty,
    should_use_color,
)


# ============================================================================
# TTY Detection Tests
# ============================================================================


@pytest.mark.unit
def test_is_tty_with_real_stdout():
    """Test TTY detection with real stdout."""
    # Result depends on test environment
    # Just verify it returns a boolean
    result = is_tty()
    assert isinstance(result, bool)


@pytest.mark.unit
def test_is_tty_with_tty_stream():
    """Test TTY detection with TTY stream."""
    mock_stream = Mock()
    mock_stream.isatty.return_value = True

    result = is_tty(mock_stream)

    assert result is True
    mock_stream.isatty.assert_called_once()


@pytest.mark.unit
def test_is_tty_with_non_tty_stream():
    """Test TTY detection with non-TTY stream."""
    mock_stream = Mock()
    mock_stream.isatty.return_value = False

    result = is_tty(mock_stream)

    assert result is False


@pytest.mark.unit
def test_is_tty_with_string_io():
    """Test TTY detection with StringIO (not a TTY)."""
    stream = io.StringIO()

    result = is_tty(stream)

    assert result is False


@pytest.mark.unit
def test_is_tty_with_attribute_error():
    """Test TTY detection with stream lacking isatty()."""
    mock_stream = Mock()
    del mock_stream.isatty

    result = is_tty(mock_stream)

    assert result is False


@pytest.mark.unit
def test_is_tty_with_value_error():
    """Test TTY detection when isatty() raises ValueError."""
    mock_stream = Mock()
    mock_stream.isatty.side_effect = ValueError("Bad file descriptor")

    result = is_tty(mock_stream)

    assert result is False


@pytest.mark.unit
def test_is_tty_defaults_to_stdout():
    """Test that is_tty() defaults to sys.stdout."""
    # Mock sys.stdout
    with patch('sys.stdout') as mock_stdout:
        mock_stdout.isatty.return_value = True

        result = is_tty()

        assert result is True
        mock_stdout.isatty.assert_called_once()


# ============================================================================
# Color Detection Tests
# ============================================================================


@pytest.mark.unit
def test_should_use_color_force_true():
    """Test forcing colors on."""
    result = should_use_color(force_color=True)

    assert result is True


@pytest.mark.unit
def test_should_use_color_force_false():
    """Test forcing colors off."""
    result = should_use_color(force_color=False)

    assert result is False


@pytest.mark.unit
def test_should_use_color_force_overrides_env():
    """Test that force_color overrides environment variables."""
    with patch.dict(os.environ, {'NO_COLOR': '1'}):
        # NO_COLOR should be overridden
        result = should_use_color(force_color=True)
        assert result is True


@pytest.mark.unit
def test_should_use_color_respects_no_color():
    """Test respecting NO_COLOR environment variable."""
    with patch.dict(os.environ, {'NO_COLOR': '1'}, clear=False):
        result = should_use_color(force_color=None)

        assert result is False


@pytest.mark.unit
def test_should_use_color_no_color_empty_string():
    """Test that empty NO_COLOR doesn't disable colors."""
    with patch.dict(os.environ, {'NO_COLOR': ''}, clear=False):
        mock_stream = Mock()
        mock_stream.isatty.return_value = True

        result = should_use_color(stream=mock_stream)

        # Empty string is falsy, so colors should be enabled
        assert result is True


@pytest.mark.unit
def test_should_use_color_respects_force_color_env():
    """Test respecting FORCE_COLOR environment variable."""
    mock_stream = Mock()
    mock_stream.isatty.return_value = False

    with patch.dict(os.environ, {'FORCE_COLOR': '1'}, clear=False):
        result = should_use_color(stream=mock_stream)

        # FORCE_COLOR enables even in non-TTY
        assert result is True


@pytest.mark.unit
def test_should_use_color_respects_clicolor_0():
    """Test respecting CLICOLOR=0 environment variable."""
    with patch.dict(os.environ, {'CLICOLOR': '0'}, clear=False):
        result = should_use_color()

        assert result is False


@pytest.mark.unit
def test_should_use_color_clicolor_1():
    """Test that CLICOLOR=1 doesn't force colors (defers to TTY)."""
    mock_stream = Mock()
    mock_stream.isatty.return_value = True

    with patch.dict(os.environ, {'CLICOLOR': '1'}, clear=False):
        result = should_use_color(stream=mock_stream)

        # CLICOLOR=1 doesn't force, just allows (defers to TTY)
        assert result is True


@pytest.mark.unit
def test_should_use_color_env_priority():
    """Test environment variable priority: NO_COLOR > FORCE_COLOR."""
    with patch.dict(os.environ, {
        'NO_COLOR': '1',
        'FORCE_COLOR': '1'
    }, clear=False):
        result = should_use_color()

        # NO_COLOR has higher priority
        assert result is False


@pytest.mark.unit
def test_should_use_color_with_tty():
    """Test color detection with TTY stream."""
    mock_stream = Mock()
    mock_stream.isatty.return_value = True

    # Clear environment
    with patch.dict(os.environ, {}, clear=True):
        result = should_use_color(stream=mock_stream)

        assert result is True


@pytest.mark.unit
def test_should_use_color_without_tty():
    """Test color detection with non-TTY stream."""
    mock_stream = Mock()
    mock_stream.isatty.return_value = False

    # Clear environment
    with patch.dict(os.environ, {}, clear=True):
        result = should_use_color(stream=mock_stream)

        assert result is False


@pytest.mark.unit
def test_should_use_color_check_env_false():
    """Test disabling environment variable checks."""
    with patch.dict(os.environ, {'NO_COLOR': '1'}, clear=False):
        mock_stream = Mock()
        mock_stream.isatty.return_value = True

        result = should_use_color(stream=mock_stream, check_env=False)

        # NO_COLOR ignored, defers to TTY
        assert result is True


@pytest.mark.unit
def test_should_use_color_defaults_to_stdout():
    """Test that should_use_color() defaults to sys.stdout."""
    with patch('sys.stdout') as mock_stdout:
        mock_stdout.isatty.return_value = True

        with patch.dict(os.environ, {}, clear=True):
            result = should_use_color()

            assert result is True


# ============================================================================
# Color Mode Tests
# ============================================================================


@pytest.mark.unit
def test_get_color_mode_always():
    """Test color mode with force_color=True."""
    result = get_color_mode(force_color=True)

    assert result == 'always'


@pytest.mark.unit
def test_get_color_mode_never():
    """Test color mode with force_color=False."""
    result = get_color_mode(force_color=False)

    assert result == 'never'


@pytest.mark.unit
def test_get_color_mode_auto():
    """Test color mode with force_color=None."""
    result = get_color_mode(force_color=None)

    assert result == 'auto'


@pytest.mark.unit
def test_get_color_mode_auto_default():
    """Test color mode defaults to auto."""
    result = get_color_mode()

    assert result == 'auto'


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.unit
def test_integration_no_color_workflow():
    """Test complete workflow with NO_COLOR set."""
    with patch.dict(os.environ, {'NO_COLOR': '1'}, clear=False):
        # Check detection
        use_color = should_use_color()
        assert use_color is False

        # Check mode
        mode = get_color_mode()
        assert mode == 'auto'


@pytest.mark.unit
def test_integration_force_color_workflow():
    """Test complete workflow with FORCE_COLOR set."""
    mock_stream = Mock()
    mock_stream.isatty.return_value = False

    with patch.dict(os.environ, {'FORCE_COLOR': '1'}, clear=False):
        # Even though stream is not TTY, colors should be enabled
        use_color = should_use_color(stream=mock_stream)
        assert use_color is True


@pytest.mark.unit
def test_integration_tty_workflow():
    """Test complete workflow with TTY detection."""
    mock_stream = Mock()
    mock_stream.isatty.return_value = True

    with patch.dict(os.environ, {}, clear=True):
        # Check TTY
        is_terminal = is_tty(mock_stream)
        assert is_terminal is True

        # Check color usage
        use_color = should_use_color(stream=mock_stream)
        assert use_color is True


@pytest.mark.unit
def test_integration_piped_output_workflow():
    """Test complete workflow with piped output."""
    stream = io.StringIO()

    with patch.dict(os.environ, {}, clear=True):
        # Check TTY
        is_terminal = is_tty(stream)
        assert is_terminal is False

        # Check color usage
        use_color = should_use_color(stream=stream)
        assert use_color is False


@pytest.mark.unit
def test_integration_override_workflow():
    """Test that force_color overrides all other settings."""
    stream = io.StringIO()

    with patch.dict(os.environ, {
        'NO_COLOR': '1',
        'CLICOLOR': '0'
    }, clear=False):
        # TTY is False, env vars say no color
        is_terminal = is_tty(stream)
        assert is_terminal is False

        # But force_color=True overrides everything
        use_color = should_use_color(force_color=True, stream=stream)
        assert use_color is True

        # And force_color=False overrides everything
        use_color = should_use_color(force_color=False, stream=stream)
        assert use_color is False


@pytest.mark.unit
def test_integration_env_var_combinations():
    """Test various environment variable combinations."""
    mock_stream = Mock()
    mock_stream.isatty.return_value = True

    # Test 1: NO_COLOR alone
    with patch.dict(os.environ, {'NO_COLOR': '1'}, clear=True):
        assert should_use_color(stream=mock_stream) is False

    # Test 2: FORCE_COLOR alone
    mock_stream.isatty.return_value = False
    with patch.dict(os.environ, {'FORCE_COLOR': '1'}, clear=True):
        assert should_use_color(stream=mock_stream) is True

    # Test 3: Both set (NO_COLOR wins)
    with patch.dict(os.environ, {
        'NO_COLOR': '1',
        'FORCE_COLOR': '1'
    }, clear=True):
        assert should_use_color(stream=mock_stream) is False

    # Test 4: CLICOLOR=0 alone
    with patch.dict(os.environ, {'CLICOLOR': '0'}, clear=True):
        assert should_use_color(stream=mock_stream) is False

    # Test 5: No env vars, TTY
    mock_stream.isatty.return_value = True
    with patch.dict(os.environ, {}, clear=True):
        assert should_use_color(stream=mock_stream) is True

    # Test 6: No env vars, non-TTY
    mock_stream.isatty.return_value = False
    with patch.dict(os.environ, {}, clear=True):
        assert should_use_color(stream=mock_stream) is False


@pytest.mark.unit
def test_integration_real_world_terminal():
    """Test with real terminal-like conditions."""
    # Simulate real terminal
    mock_stream = Mock()
    mock_stream.isatty.return_value = True

    with patch.dict(os.environ, {}, clear=True):
        # Should use colors in terminal
        assert should_use_color(stream=mock_stream) is True
        assert get_color_mode() == 'auto'


@pytest.mark.unit
def test_integration_real_world_pipe():
    """Test with real pipe-like conditions."""
    # Simulate piped output
    stream = io.StringIO()

    with patch.dict(os.environ, {}, clear=True):
        # Should not use colors when piped
        assert is_tty(stream) is False
        assert should_use_color(stream=stream) is False


@pytest.mark.unit
def test_integration_ci_environment():
    """Test with CI environment variables."""
    # Many CI systems set NO_COLOR
    with patch.dict(os.environ, {'NO_COLOR': '1'}, clear=False):
        mock_stream = Mock()
        mock_stream.isatty.return_value = True

        # Even in TTY, NO_COLOR should disable
        assert should_use_color(stream=mock_stream) is False
