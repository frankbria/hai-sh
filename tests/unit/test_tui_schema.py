"""
Tests for TUI-related schema extensions.

This module tests the LLMResponse model and TUI configuration options.
"""

import pytest
from pydantic import ValidationError


# --- LLMResponse Tests ---


@pytest.mark.unit
def test_llm_response_defaults():
    """Test LLMResponse with minimal required fields."""
    from hai_sh.schema import LLMResponse

    response = LLMResponse(
        conversation="I'll help you list files",
        confidence=85,
    )

    assert response.conversation == "I'll help you list files"
    assert response.confidence == 85
    assert response.command is None
    assert response.internal_dialogue is None


@pytest.mark.unit
def test_llm_response_with_all_fields():
    """Test LLMResponse with all fields populated."""
    from hai_sh.schema import LLMResponse

    response = LLMResponse(
        conversation="I'll list all Python files in the current directory",
        command="ls -la *.py",
        confidence=92,
        internal_dialogue="User wants to see Python files. Simple ls command with glob pattern.",
    )

    assert response.conversation == "I'll list all Python files in the current directory"
    assert response.command == "ls -la *.py"
    assert response.confidence == 92
    assert response.internal_dialogue == "User wants to see Python files. Simple ls command with glob pattern."


@pytest.mark.unit
def test_llm_response_question_mode():
    """Test LLMResponse for question mode (no command)."""
    from hai_sh.schema import LLMResponse

    response = LLMResponse(
        conversation="Python 3.9 was released on October 5, 2020.",
        confidence=95,
    )

    assert response.conversation == "Python 3.9 was released on October 5, 2020."
    assert response.command is None
    assert response.confidence == 95


@pytest.mark.unit
def test_llm_response_confidence_validation_bounds():
    """Test LLMResponse confidence must be 0-100."""
    from hai_sh.schema import LLMResponse

    # Valid range
    for confidence in [0, 50, 100]:
        response = LLMResponse(conversation="test", confidence=confidence)
        assert response.confidence == confidence

    # Too low
    with pytest.raises(ValidationError, match="greater than or equal to 0"):
        LLMResponse(conversation="test", confidence=-1)

    # Too high
    with pytest.raises(ValidationError, match="less than or equal to 100"):
        LLMResponse(conversation="test", confidence=101)


@pytest.mark.unit
def test_llm_response_empty_conversation():
    """Test LLMResponse allows empty conversation (edge case)."""
    from hai_sh.schema import LLMResponse

    response = LLMResponse(conversation="", confidence=50)
    assert response.conversation == ""


@pytest.mark.unit
def test_llm_response_from_dict():
    """Test LLMResponse can be created from dictionary."""
    from hai_sh.schema import LLMResponse

    data = {
        "conversation": "Found 3 Python files",
        "command": "find . -name '*.py'",
        "confidence": 88,
        "internal_dialogue": "Simple file search task",
    }

    response = LLMResponse(**data)

    assert response.conversation == data["conversation"]
    assert response.command == data["command"]
    assert response.confidence == data["confidence"]
    assert response.internal_dialogue == data["internal_dialogue"]


@pytest.mark.unit
def test_llm_response_to_dict():
    """Test LLMResponse can be serialized to dictionary."""
    from hai_sh.schema import LLMResponse

    response = LLMResponse(
        conversation="Test response",
        command="echo hello",
        confidence=75,
        internal_dialogue="Meta reasoning",
    )

    data = response.model_dump()

    assert data["conversation"] == "Test response"
    assert data["command"] == "echo hello"
    assert data["confidence"] == 75
    assert data["internal_dialogue"] == "Meta reasoning"


@pytest.mark.unit
def test_llm_response_to_dict_excludes_none():
    """Test LLMResponse serialization with exclude_none."""
    from hai_sh.schema import LLMResponse

    response = LLMResponse(
        conversation="Test",
        confidence=80,
    )

    data = response.model_dump(exclude_none=True)

    assert "conversation" in data
    assert "confidence" in data
    assert "command" not in data
    assert "internal_dialogue" not in data


# --- TUI Configuration Tests ---


@pytest.mark.unit
def test_tui_config_defaults():
    """Test TUIConfig with defaults."""
    from hai_sh.schema import TUIConfig

    config = TUIConfig()

    assert config.enabled is True
    assert config.meta_collapsed_by_default is True
    assert config.show_internal_dialogue is False
    assert config.show_confidence_bar is True


@pytest.mark.unit
def test_tui_config_custom():
    """Test TUIConfig with custom values."""
    from hai_sh.schema import TUIConfig

    config = TUIConfig(
        enabled=False,
        meta_collapsed_by_default=False,
        show_internal_dialogue=True,
        show_confidence_bar=False,
    )

    assert config.enabled is False
    assert config.meta_collapsed_by_default is False
    assert config.show_internal_dialogue is True
    assert config.show_confidence_bar is False


@pytest.mark.unit
def test_tui_config_theme():
    """Test TUIConfig theme setting."""
    from hai_sh.schema import TUIConfig

    config = TUIConfig(theme="dark")
    assert config.theme == "dark"

    config = TUIConfig(theme="light")
    assert config.theme == "light"


@pytest.mark.unit
def test_tui_config_theme_validation():
    """Test TUIConfig theme must be valid literal."""
    from hai_sh.schema import TUIConfig

    # Valid themes
    for theme in ["dark", "light", "auto"]:
        config = TUIConfig(theme=theme)
        assert config.theme == theme

    # Invalid theme
    with pytest.raises(ValidationError, match="Input should be"):
        TUIConfig(theme="invalid")


# --- Output Config TUI Integration Tests ---


@pytest.mark.unit
def test_output_config_has_tui_settings():
    """Test OutputConfig includes TUI configuration."""
    from hai_sh.schema import OutputConfig

    config = OutputConfig()

    assert hasattr(config, "tui")
    assert config.tui is not None


@pytest.mark.unit
def test_output_config_tui_nested():
    """Test OutputConfig with nested TUI configuration."""
    from hai_sh.schema import OutputConfig, TUIConfig

    config = OutputConfig(
        tui=TUIConfig(
            enabled=True,
            meta_collapsed_by_default=False,
            show_internal_dialogue=True,
        )
    )

    assert config.tui.enabled is True
    assert config.tui.meta_collapsed_by_default is False
    assert config.tui.show_internal_dialogue is True


@pytest.mark.unit
def test_hai_config_tui_settings():
    """Test HaiConfig includes TUI settings via output."""
    from hai_sh.schema import HaiConfig

    config = HaiConfig()

    assert config.output.tui is not None
    assert config.output.tui.enabled is True


@pytest.mark.unit
def test_validate_config_dict_with_tui():
    """Test validate_config_dict handles TUI configuration."""
    from hai_sh.schema import validate_config_dict

    config_dict = {
        "provider": "ollama",
        "output": {
            "use_colors": True,
            "tui": {
                "enabled": True,
                "meta_collapsed_by_default": False,
                "show_internal_dialogue": True,
                "theme": "dark",
            },
        },
    }

    validated_config, warnings = validate_config_dict(config_dict)

    assert validated_config.output.tui.enabled is True
    assert validated_config.output.tui.meta_collapsed_by_default is False
    assert validated_config.output.tui.show_internal_dialogue is True
    assert validated_config.output.tui.theme == "dark"


# --- Confidence Level Helper Tests ---


@pytest.mark.unit
def test_llm_response_confidence_level_high():
    """Test confidence level classification for high confidence."""
    from hai_sh.schema import LLMResponse

    response = LLMResponse(conversation="test", confidence=85)
    assert response.confidence_level == "high"

    response = LLMResponse(conversation="test", confidence=100)
    assert response.confidence_level == "high"

    response = LLMResponse(conversation="test", confidence=80)
    assert response.confidence_level == "high"


@pytest.mark.unit
def test_llm_response_confidence_level_medium():
    """Test confidence level classification for medium confidence."""
    from hai_sh.schema import LLMResponse

    response = LLMResponse(conversation="test", confidence=79)
    assert response.confidence_level == "medium"

    response = LLMResponse(conversation="test", confidence=50)
    assert response.confidence_level == "medium"


@pytest.mark.unit
def test_llm_response_confidence_level_low():
    """Test confidence level classification for low confidence."""
    from hai_sh.schema import LLMResponse

    response = LLMResponse(conversation="test", confidence=49)
    assert response.confidence_level == "low"

    response = LLMResponse(conversation="test", confidence=0)
    assert response.confidence_level == "low"
