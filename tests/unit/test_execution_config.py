"""
Tests for new execution configuration and auto-execute functionality.
"""

import pytest

from hai_sh.schema import ExecutionConfig, HaiConfig


@pytest.mark.unit
def test_execution_config_defaults():
    """Test ExecutionConfig has sensible defaults."""
    config = ExecutionConfig()

    assert config.auto_execute is True
    assert config.auto_execute_threshold == 85
    assert config.show_explanation == "collapsed"
    assert config.require_confirmation is False


@pytest.mark.unit
def test_execution_config_threshold_validation():
    """Test threshold validation."""
    # Valid thresholds
    config = ExecutionConfig(auto_execute_threshold=0)
    assert config.auto_execute_threshold == 0

    config = ExecutionConfig(auto_execute_threshold=100)
    assert config.auto_execute_threshold == 100

    config = ExecutionConfig(auto_execute_threshold=50)
    assert config.auto_execute_threshold == 50


@pytest.mark.unit
def test_execution_config_threshold_out_of_range():
    """Test threshold rejects out of range values."""
    with pytest.raises(ValueError):
        ExecutionConfig(auto_execute_threshold=-1)

    with pytest.raises(ValueError):
        ExecutionConfig(auto_execute_threshold=101)


@pytest.mark.unit
def test_execution_config_show_explanation_options():
    """Test show_explanation accepts valid options."""
    config = ExecutionConfig(show_explanation="collapsed")
    assert config.show_explanation == "collapsed"

    config = ExecutionConfig(show_explanation="expanded")
    assert config.show_explanation == "expanded"

    config = ExecutionConfig(show_explanation="hidden")
    assert config.show_explanation == "hidden"


@pytest.mark.unit
def test_execution_config_show_explanation_invalid():
    """Test show_explanation rejects invalid options."""
    with pytest.raises(ValueError):
        ExecutionConfig(show_explanation="invalid")


@pytest.mark.unit
def test_hai_config_includes_execution():
    """Test HaiConfig includes execution settings."""
    config = HaiConfig()

    assert hasattr(config, 'execution')
    assert isinstance(config.execution, ExecutionConfig)
    assert config.execution.auto_execute is True


@pytest.mark.unit
def test_hai_config_custom_execution():
    """Test HaiConfig accepts custom execution settings."""
    config = HaiConfig(
        execution=ExecutionConfig(
            auto_execute=False,
            auto_execute_threshold=90,
            show_explanation="hidden",
            require_confirmation=True
        )
    )

    assert config.execution.auto_execute is False
    assert config.execution.auto_execute_threshold == 90
    assert config.execution.show_explanation == "hidden"
    assert config.execution.require_confirmation is True
