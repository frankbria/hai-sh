"""
Tests for helper functions in __main__.py.
"""

import pytest

from hai_sh.__main__ import (
    format_collapsed_explanation,
    gather_context_parallel,
    should_auto_execute,
)


@pytest.mark.unit
def test_should_auto_execute_high_confidence():
    """Test auto-execute with high confidence."""
    config = {
        'execution': {
            'auto_execute': True,
            'auto_execute_threshold': 85,
            'require_confirmation': False
        }
    }

    assert should_auto_execute(90, config) is True
    assert should_auto_execute(85, config) is True
    assert should_auto_execute(84, config) is False


@pytest.mark.unit
def test_should_auto_execute_disabled():
    """Test auto-execute when disabled."""
    config = {
        'execution': {
            'auto_execute': False,
            'auto_execute_threshold': 85,
            'require_confirmation': False
        }
    }

    assert should_auto_execute(100, config) is False
    assert should_auto_execute(85, config) is False


@pytest.mark.unit
def test_should_auto_execute_require_confirmation():
    """Test require_confirmation overrides auto_execute."""
    config = {
        'execution': {
            'auto_execute': True,
            'auto_execute_threshold': 50,
            'require_confirmation': True
        }
    }

    assert should_auto_execute(100, config) is False
    assert should_auto_execute(90, config) is False


@pytest.mark.unit
def test_should_auto_execute_default_config():
    """Test auto-execute with empty/default config."""
    # Empty config should use defaults
    assert should_auto_execute(90, {}) is True  # Default threshold is 85
    assert should_auto_execute(80, {}) is False


@pytest.mark.unit
def test_should_auto_execute_custom_threshold():
    """Test auto-execute with custom threshold."""
    config = {
        'execution': {
            'auto_execute': True,
            'auto_execute_threshold': 95,
        }
    }

    assert should_auto_execute(95, config) is True
    assert should_auto_execute(94, config) is False
    assert should_auto_execute(100, config) is True


@pytest.mark.unit
def test_format_collapsed_explanation_short():
    """Test formatting short explanation."""
    explanation = "This command lists files."
    result = format_collapsed_explanation(explanation, use_colors=False)

    assert "Explanation:" in result
    assert "This command lists files." in result


@pytest.mark.unit
def test_format_collapsed_explanation_long():
    """Test formatting long explanation gets truncated."""
    explanation = "A" * 150  # Long explanation
    result = format_collapsed_explanation(explanation, use_colors=False)

    assert "..." in result
    assert len(result) < len(explanation) + 50  # Should be truncated


@pytest.mark.unit
def test_format_collapsed_explanation_with_newlines():
    """Test newlines are removed in collapsed view."""
    explanation = "Line 1\nLine 2\nLine 3"
    result = format_collapsed_explanation(explanation, use_colors=False)

    assert "\n" not in result.replace("[", "").replace("]", "")
    # The result should have newlines removed within the content


@pytest.mark.unit
def test_format_collapsed_explanation_with_colors():
    """Test formatting with colors includes ANSI codes."""
    explanation = "Test explanation"
    result = format_collapsed_explanation(explanation, use_colors=True)

    # Should contain ANSI escape codes
    assert "\033[" in result


@pytest.mark.unit
def test_gather_context_parallel_returns_all_keys():
    """Test parallel context gathering returns expected keys."""
    context = gather_context_parallel()

    assert 'cwd' in context
    assert 'git' in context
    assert 'env' in context


@pytest.mark.unit
def test_gather_context_parallel_cwd_valid():
    """Test parallel context gathering has valid CWD."""
    context = gather_context_parallel()

    assert context['cwd'] is not None
    assert 'cwd' in context['cwd'] or context['cwd'] == {}


@pytest.mark.unit
def test_gather_context_parallel_env_valid():
    """Test parallel context gathering has valid env."""
    context = gather_context_parallel()

    assert context['env'] is not None
    # Env context should have user info if available
    if context['env']:
        # Should be a dict with env info
        assert isinstance(context['env'], dict)
