"""
Tests for Pydantic schema validation.
"""

import pytest
from pydantic import ValidationError

from hai_sh.schema import (
    AnthropicProviderConfig,
    ContextConfig,
    HaiConfig,
    LocalProviderConfig,
    OllamaProviderConfig,
    OpenAIProviderConfig,
    OutputConfig,
    ProvidersConfig,
    validate_config_dict,
)


@pytest.mark.unit
def test_openai_provider_config_defaults():
    """Test OpenAI provider config with defaults."""
    config = OpenAIProviderConfig()

    assert config.model == "gpt-4o-mini"
    assert config.api_key is None
    assert config.base_url is None


@pytest.mark.unit
def test_openai_provider_config_custom():
    """Test OpenAI provider config with custom values."""
    config = OpenAIProviderConfig(
        api_key="sk-test123",
        model="gpt-4o",
        base_url="https://api.custom.com",
    )

    assert config.api_key == "sk-test123"
    assert config.model == "gpt-4o"
    assert config.base_url == "https://api.custom.com"


@pytest.mark.unit
def test_openai_provider_config_model_validation():
    """Test OpenAI model validation allows any string."""
    # Should not raise even with unknown model
    config = OpenAIProviderConfig(model="future-model-v5")
    assert config.model == "future-model-v5"


@pytest.mark.unit
def test_anthropic_provider_config_defaults():
    """Test Anthropic provider config with defaults."""
    config = AnthropicProviderConfig()

    assert config.model == "claude-sonnet-4-5"
    assert config.api_key is None


@pytest.mark.unit
def test_anthropic_provider_config_custom():
    """Test Anthropic provider config with custom values."""
    config = AnthropicProviderConfig(
        api_key="sk-ant-test",
        model="claude-opus-4",
    )

    assert config.api_key == "sk-ant-test"
    assert config.model == "claude-opus-4"


@pytest.mark.unit
def test_anthropic_provider_config_model_validation():
    """Test Anthropic model validation allows any string."""
    # Should not raise even with unknown model
    config = AnthropicProviderConfig(model="claude-future-5")
    assert config.model == "claude-future-5"


@pytest.mark.unit
def test_ollama_provider_config_defaults():
    """Test Ollama provider config with defaults."""
    config = OllamaProviderConfig()

    assert config.base_url == "http://localhost:11434"
    assert config.model == "llama3.2"


@pytest.mark.unit
def test_ollama_provider_config_custom():
    """Test Ollama provider config with custom values."""
    config = OllamaProviderConfig(
        base_url="http://192.168.1.100:11434",
        model="llama3.1",
    )

    assert config.base_url == "http://192.168.1.100:11434"
    assert config.model == "llama3.1"


@pytest.mark.unit
def test_ollama_provider_config_url_validation_valid():
    """Test Ollama URL validation accepts valid URLs."""
    # HTTP
    config = OllamaProviderConfig(base_url="http://localhost:11434")
    assert config.base_url == "http://localhost:11434"

    # HTTPS
    config = OllamaProviderConfig(base_url="https://api.ollama.com")
    assert config.base_url == "https://api.ollama.com"


@pytest.mark.unit
def test_ollama_provider_config_url_validation_invalid():
    """Test Ollama URL validation rejects invalid URLs."""
    with pytest.raises(ValidationError, match="base_url must start with http"):
        OllamaProviderConfig(base_url="ftp://localhost:11434")

    with pytest.raises(ValidationError, match="base_url must start with http"):
        OllamaProviderConfig(base_url="localhost:11434")


@pytest.mark.unit
def test_local_provider_config():
    """Test local provider config."""
    config = LocalProviderConfig(
        model_path="/path/to/model.gguf",
        context_size=8192,
    )

    assert config.model_path == "/path/to/model.gguf"
    assert config.context_size == 8192


@pytest.mark.unit
def test_local_provider_config_context_size_validation():
    """Test local provider context size validation."""
    # Valid range
    config = LocalProviderConfig(model_path="/path/to/model.gguf", context_size=4096)
    assert config.context_size == 4096

    # Too small
    with pytest.raises(ValidationError, match="greater than or equal to 512"):
        LocalProviderConfig(model_path="/path/to/model.gguf", context_size=256)

    # Too large
    with pytest.raises(ValidationError, match="less than or equal to 128000"):
        LocalProviderConfig(model_path="/path/to/model.gguf", context_size=200000)


@pytest.mark.unit
def test_providers_config_defaults():
    """Test ProvidersConfig with defaults."""
    config = ProvidersConfig()

    assert config.openai is not None
    assert config.openai.model == "gpt-4o-mini"
    assert config.anthropic is not None
    assert config.anthropic.model == "claude-sonnet-4-5"
    assert config.ollama is not None
    assert config.ollama.model == "llama3.2"
    assert config.local is None


@pytest.mark.unit
def test_providers_config_custom():
    """Test ProvidersConfig with custom values."""
    config = ProvidersConfig(
        openai=OpenAIProviderConfig(api_key="sk-test"),
        anthropic=AnthropicProviderConfig(api_key="sk-ant-test"),
        ollama=OllamaProviderConfig(model="llama3.1"),
        local=LocalProviderConfig(model_path="/models/test.gguf"),
    )

    assert config.openai.api_key == "sk-test"
    assert config.anthropic.api_key == "sk-ant-test"
    assert config.ollama.model == "llama3.1"
    assert config.local.model_path == "/models/test.gguf"


@pytest.mark.unit
def test_context_config_defaults():
    """Test ContextConfig with defaults."""
    config = ContextConfig()

    assert config.include_history is True
    assert config.history_length == 10
    assert config.include_env_vars is True
    assert config.include_git_state is True


@pytest.mark.unit
def test_context_config_custom():
    """Test ContextConfig with custom values."""
    config = ContextConfig(
        include_history=False,
        history_length=20,
        include_env_vars=False,
        include_git_state=False,
    )

    assert config.include_history is False
    assert config.history_length == 20
    assert config.include_env_vars is False
    assert config.include_git_state is False


@pytest.mark.unit
def test_context_config_history_length_validation():
    """Test context config history length validation."""
    # Valid range
    config = ContextConfig(history_length=50)
    assert config.history_length == 50

    # Minimum
    config = ContextConfig(history_length=0)
    assert config.history_length == 0

    # Maximum
    config = ContextConfig(history_length=100)
    assert config.history_length == 100

    # Too large
    with pytest.raises(ValidationError, match="less than or equal to 100"):
        ContextConfig(history_length=101)


@pytest.mark.unit
def test_output_config_defaults():
    """Test OutputConfig with defaults."""
    config = OutputConfig()

    assert config.show_conversation is True
    assert config.show_reasoning is True
    assert config.use_colors is True


@pytest.mark.unit
def test_output_config_custom():
    """Test OutputConfig with custom values."""
    config = OutputConfig(
        show_conversation=False,
        show_reasoning=False,
        use_colors=False,
    )

    assert config.show_conversation is False
    assert config.show_reasoning is False
    assert config.use_colors is False


@pytest.mark.unit
def test_hai_config_defaults():
    """Test HaiConfig with defaults."""
    config = HaiConfig()

    assert config.provider == "ollama"
    assert config.model == "llama3.2"
    assert config.providers is not None
    assert config.context is not None
    assert config.output is not None


@pytest.mark.unit
def test_hai_config_custom():
    """Test HaiConfig with custom values."""
    config = HaiConfig(
        provider="openai",
        model="gpt-4o",
        providers=ProvidersConfig(
            openai=OpenAIProviderConfig(api_key="sk-test"),
        ),
    )

    assert config.provider == "openai"
    assert config.model == "gpt-4o"
    assert config.providers.openai.api_key == "sk-test"


@pytest.mark.unit
def test_hai_config_provider_validation():
    """Test HaiConfig provider must be valid literal."""
    # Valid providers (except local which needs special config)
    for provider in ["openai", "anthropic", "ollama"]:
        config = HaiConfig(provider=provider)
        assert config.provider == provider

    # Local provider needs configuration
    config = HaiConfig(
        provider="local",
        providers=ProvidersConfig(
            local=LocalProviderConfig(model_path="/models/test.gguf"),
        ),
    )
    assert config.provider == "local"

    # Invalid provider
    with pytest.raises(ValidationError, match="Input should be"):
        HaiConfig(provider="invalid")


@pytest.mark.unit
def test_hai_config_forbids_extra_fields():
    """Test HaiConfig forbids extra fields."""
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        HaiConfig(unknown_field="value")


@pytest.mark.unit
def test_hai_config_provider_exists_validation():
    """Test HaiConfig validates selected provider has configuration."""
    # Valid: ollama is configured by default
    config = HaiConfig(provider="ollama")
    assert config.provider == "ollama"

    # Valid: local provider with configuration
    config = HaiConfig(
        provider="local",
        providers=ProvidersConfig(
            local=LocalProviderConfig(model_path="/models/test.gguf"),
        ),
    )
    assert config.provider == "local"

    # Invalid: local provider without configuration
    with pytest.raises(ValueError, match="is selected but has no configuration"):
        HaiConfig(
            provider="local",
            providers=ProvidersConfig(local=None),
        )


@pytest.mark.unit
def test_validate_config_dict_valid():
    """Test validate_config_dict with valid config."""
    config_dict = {
        "provider": "ollama",
        "model": "llama3.2",
    }

    validated_config, warnings = validate_config_dict(config_dict)

    assert isinstance(validated_config, HaiConfig)
    assert validated_config.provider == "ollama"
    assert validated_config.model == "llama3.2"
    assert len(warnings) == 0


@pytest.mark.unit
def test_validate_config_dict_with_nested():
    """Test validate_config_dict with nested configuration."""
    config_dict = {
        "provider": "openai",
        "providers": {
            "openai": {
                "api_key": "sk-test",
                "model": "gpt-4o",
            }
        },
    }

    validated_config, warnings = validate_config_dict(config_dict)

    assert validated_config.provider == "openai"
    assert validated_config.providers.openai.api_key == "sk-test"
    assert validated_config.providers.openai.model == "gpt-4o"
    assert len(warnings) == 0


@pytest.mark.unit
def test_validate_config_dict_missing_openai_api_key():
    """Test validate_config_dict warns about missing OpenAI API key."""
    config_dict = {
        "provider": "openai",
        "providers": {
            "openai": {
                "model": "gpt-4o",
            }
        },
    }

    validated_config, warnings = validate_config_dict(config_dict)

    assert len(warnings) == 1
    assert "api_key" in warnings[0].lower()
    assert "openai" in warnings[0].lower()


@pytest.mark.unit
def test_validate_config_dict_missing_anthropic_api_key():
    """Test validate_config_dict warns about missing Anthropic API key."""
    config_dict = {
        "provider": "anthropic",
        "providers": {
            "anthropic": {
                "model": "claude-opus-4",
            }
        },
    }

    validated_config, warnings = validate_config_dict(config_dict)

    assert len(warnings) == 1
    assert "api_key" in warnings[0].lower()
    assert "anthropic" in warnings[0].lower()


@pytest.mark.unit
def test_validate_config_dict_local_provider_missing_config():
    """Test validate_config_dict warns about missing local provider config."""
    config_dict = {
        "provider": "local",
        "providers": {
            "local": None,
        },
    }

    # Should raise ValueError, not just warn
    with pytest.raises(ValueError, match="Configuration validation failed"):
        validate_config_dict(config_dict)


@pytest.mark.unit
def test_validate_config_dict_invalid_raises():
    """Test validate_config_dict raises on invalid config."""
    # Invalid provider
    with pytest.raises(ValueError, match="Configuration validation failed"):
        validate_config_dict({"provider": "invalid"})

    # Invalid type
    with pytest.raises(ValueError, match="Configuration validation failed"):
        validate_config_dict({"provider": 123})

    # Extra fields
    with pytest.raises(ValueError, match="Configuration validation failed"):
        validate_config_dict({"provider": "ollama", "unknown_field": "value"})


@pytest.mark.unit
def test_validate_config_dict_all_providers():
    """Test validate_config_dict with all providers configured."""
    config_dict = {
        "provider": "anthropic",
        "providers": {
            "openai": {
                "api_key": "sk-openai",
                "model": "gpt-4o",
            },
            "anthropic": {
                "api_key": "sk-ant",
                "model": "claude-opus-4",
            },
            "ollama": {
                "base_url": "http://localhost:11434",
                "model": "llama3.2",
            },
            "local": {
                "model_path": "/models/test.gguf",
                "context_size": 8192,
            },
        },
        "context": {
            "include_history": True,
            "history_length": 20,
        },
        "output": {
            "show_conversation": True,
            "use_colors": False,
        },
    }

    validated_config, warnings = validate_config_dict(config_dict)

    assert validated_config.provider == "anthropic"
    assert validated_config.providers.openai.api_key == "sk-openai"
    assert validated_config.providers.anthropic.api_key == "sk-ant"
    assert validated_config.providers.ollama.base_url == "http://localhost:11434"
    assert validated_config.providers.local.model_path == "/models/test.gguf"
    assert validated_config.context.history_length == 20
    assert validated_config.output.use_colors is False
    assert len(warnings) == 0
