"""
Tests for configuration file loading and parsing.
"""

import os
from pathlib import Path

import pytest
import yaml

from hai_sh.config import (
    DEFAULT_CONFIG,
    ConfigError,
    ConfigLoadError,
    expand_env_vars,
    expand_env_vars_recursive,
    get_available_provider,
    get_config_value,
    get_provider_config,
    get_provider_priority_list,
    check_provider_availability,
    load_config,
    load_config_file,
    merge_configs,
    ProviderFallbackResult,
    validate_config,
)


@pytest.mark.unit
def test_expand_env_vars_basic(monkeypatch):
    """Test basic environment variable expansion."""
    monkeypatch.setenv("TEST_VAR", "hello")

    assert expand_env_vars("${TEST_VAR}") == "hello"
    assert expand_env_vars("$TEST_VAR") == "hello"
    assert expand_env_vars("prefix ${TEST_VAR} suffix") == "prefix hello suffix"
    assert expand_env_vars("prefix $TEST_VAR suffix") == "prefix hello suffix"


@pytest.mark.unit
def test_expand_env_vars_missing(monkeypatch):
    """Test expansion of missing environment variables."""
    # Make sure TEST_MISSING doesn't exist
    monkeypatch.delenv("TEST_MISSING", raising=False)

    assert expand_env_vars("${TEST_MISSING}") == ""
    assert expand_env_vars("$TEST_MISSING") == ""
    assert expand_env_vars("prefix ${TEST_MISSING} suffix") == "prefix  suffix"


@pytest.mark.unit
def test_expand_env_vars_multiple(monkeypatch):
    """Test expansion of multiple variables."""
    monkeypatch.setenv("VAR1", "hello")
    monkeypatch.setenv("VAR2", "world")

    result = expand_env_vars("${VAR1} ${VAR2}")
    assert result == "hello world"

    result = expand_env_vars("$VAR1 $VAR2")
    assert result == "hello world"


@pytest.mark.unit
def test_expand_env_vars_non_string():
    """Test that non-string values are returned unchanged."""
    assert expand_env_vars(123) == 123
    assert expand_env_vars(None) is None
    assert expand_env_vars(True) is True


@pytest.mark.unit
def test_expand_env_vars_recursive(monkeypatch):
    """Test recursive environment variable expansion."""
    monkeypatch.setenv("API_KEY", "secret123")
    monkeypatch.setenv("BASE_URL", "http://localhost")

    config = {
        "provider": "openai",
        "api_key": "${API_KEY}",
        "nested": {
            "url": "${BASE_URL}/api",
            "number": 42,
        },
    }

    result = expand_env_vars_recursive(config)

    assert result["api_key"] == "secret123"
    assert result["nested"]["url"] == "http://localhost/api"
    assert result["nested"]["number"] == 42


@pytest.mark.unit
def test_merge_configs_simple():
    """Test simple config merging."""
    base = {"a": 1, "b": 2}
    override = {"b": 3, "c": 4}

    result = merge_configs(base, override)

    assert result == {"a": 1, "b": 3, "c": 4}


@pytest.mark.unit
def test_merge_configs_nested():
    """Test nested config merging."""
    base = {
        "provider": "ollama",
        "providers": {
            "openai": {"model": "gpt-4"},
            "ollama": {"model": "llama3.2"},
        },
    }

    override = {
        "provider": "openai",
        "providers": {
            "openai": {"api_key": "sk-test"},
        },
    }

    result = merge_configs(base, override)

    assert result["provider"] == "openai"
    assert result["providers"]["openai"]["model"] == "gpt-4"
    assert result["providers"]["openai"]["api_key"] == "sk-test"
    assert result["providers"]["ollama"]["model"] == "llama3.2"


@pytest.mark.unit
def test_load_config_file_valid(tmp_path, monkeypatch):
    """Test loading valid config file."""
    config_dir = tmp_path / ".hai"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"

    config_data = {
        "provider": "openai",
    }

    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    monkeypatch.setenv("HOME", str(tmp_path))

    config = load_config_file(config_file)

    assert config["provider"] == "openai"


@pytest.mark.unit
def test_load_config_file_missing(tmp_path, monkeypatch):
    """Test loading missing config file initializes directory."""
    monkeypatch.setenv("HOME", str(tmp_path))

    # First load should create the config
    config = load_config_file()

    # Config file should now exist
    config_path = tmp_path / ".hai" / "config.yaml"
    assert config_path.exists()


@pytest.mark.unit
def test_load_config_file_invalid_yaml(tmp_path, monkeypatch):
    """Test loading file with invalid YAML."""
    config_dir = tmp_path / ".hai"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"

    # Write invalid YAML
    config_file.write_text("invalid: yaml: content:\n  bad indentation")

    monkeypatch.setenv("HOME", str(tmp_path))

    with pytest.raises(ConfigLoadError, match="Invalid YAML syntax"):
        load_config_file(config_file)


@pytest.mark.unit
def test_load_config_file_not_dict(tmp_path, monkeypatch):
    """Test loading file that doesn't contain a dictionary."""
    config_dir = tmp_path / ".hai"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"

    # Write a list instead of dict
    config_file.write_text("- item1\n- item2\n")

    monkeypatch.setenv("HOME", str(tmp_path))

    with pytest.raises(ConfigLoadError, match="must contain a dictionary"):
        load_config_file(config_file)


@pytest.mark.unit
def test_load_config_file_empty(tmp_path, monkeypatch):
    """Test loading empty config file."""
    config_dir = tmp_path / ".hai"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"

    config_file.write_text("")

    monkeypatch.setenv("HOME", str(tmp_path))

    config = load_config_file(config_file)
    assert config == {}


@pytest.mark.unit
def test_load_config_with_defaults(tmp_path, monkeypatch):
    """Test that load_config applies defaults."""
    config_dir = tmp_path / ".hai"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"

    # Minimal config
    config_file.write_text("provider: openai\n")

    monkeypatch.setenv("HOME", str(tmp_path))

    # Test with Pydantic validation (default)
    config = load_config()
    assert config.provider == "openai"
    assert config.providers is not None
    assert config.context is not None
    assert config.output is not None

    # Test without Pydantic validation (returns dict)
    config_dict = load_config(use_pydantic=False)
    assert config_dict["provider"] == "openai"
    assert "providers" in config_dict
    assert "context" in config_dict
    assert "output" in config_dict


@pytest.mark.unit
def test_load_config_without_defaults(tmp_path, monkeypatch):
    """Test loading config without applying defaults."""
    config_dir = tmp_path / ".hai"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"

    config_file.write_text("provider: openai\n")

    monkeypatch.setenv("HOME", str(tmp_path))

    # Without defaults, we get minimal config - Pydantic will still fill in model defaults
    config = load_config(use_defaults=False, use_pydantic=False)

    # Should only have what's in the file
    assert config["provider"] == "openai"
    assert "providers" not in config


@pytest.mark.unit
def test_load_config_env_expansion(tmp_path, monkeypatch):
    """Test environment variable expansion in config."""
    config_dir = tmp_path / ".hai"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("MY_API_KEY", "secret123")

    config_content = """
provider: openai
providers:
  openai:
    api_key: ${MY_API_KEY}
"""
    config_file.write_text(config_content)

    # Test with Pydantic (default)
    config = load_config()
    assert config.providers.openai.api_key == "secret123"

    # Test without Pydantic (returns dict)
    config_dict = load_config(use_pydantic=False)
    assert config_dict["providers"]["openai"]["api_key"] == "secret123"


@pytest.mark.unit
def test_load_config_no_env_expansion(tmp_path, monkeypatch):
    """Test loading config without env var expansion."""
    config_dir = tmp_path / ".hai"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("MY_API_KEY", "secret123")

    config_content = """
provider: openai
providers:
  openai:
    api_key: ${MY_API_KEY}
"""
    config_file.write_text(config_content)

    # Test without Pydantic (returns dict)
    config = load_config(expand_vars=False, use_pydantic=False)

    assert config["providers"]["openai"]["api_key"] == "${MY_API_KEY}"


@pytest.mark.unit
def test_validate_config_valid():
    """Test validating a valid config."""
    config = {
        "provider": "ollama",
        "providers": {
            "ollama": {"model": "llama3.2"},
        },
    }

    warnings = validate_config(config)
    assert len(warnings) == 0


@pytest.mark.unit
def test_validate_config_unknown_provider():
    """Test validation warns about unknown provider."""
    config = {"provider": "unknown"}

    warnings = validate_config(config)
    assert len(warnings) > 0
    assert any("Unknown provider" in w for w in warnings)


@pytest.mark.unit
def test_validate_config_missing_provider_config():
    """Test validation warns when provider config is missing."""
    config = {
        "provider": "openai",
        "providers": {
            "ollama": {"model": "llama3.2"},
        },
    }

    warnings = validate_config(config)
    assert len(warnings) > 0
    assert any("no configuration found" in w for w in warnings)


@pytest.mark.unit
def test_validate_config_missing_api_key():
    """Test validation warns about missing API keys."""
    config = {
        "provider": "openai",
        "providers": {
            "openai": {"model": "gpt-4"},
        },
    }

    warnings = validate_config(config)
    assert len(warnings) > 0
    assert any("api_key" in w.lower() for w in warnings)


@pytest.mark.unit
def test_get_provider_config_default():
    """Test getting provider config using default provider."""
    config = {
        "provider": "ollama",
        "providers": {
            "ollama": {"base_url": "http://localhost:11434"},
        },
    }

    provider_config = get_provider_config(config)
    assert provider_config["base_url"] == "http://localhost:11434"


@pytest.mark.unit
def test_get_provider_config_specific():
    """Test getting specific provider config."""
    config = {
        "provider": "ollama",
        "providers": {
            "ollama": {"base_url": "http://localhost:11434"},
            "openai": {"api_key": "sk-test"},
        },
    }

    provider_config = get_provider_config(config, "openai")
    assert provider_config["api_key"] == "sk-test"


@pytest.mark.unit
def test_get_provider_config_missing():
    """Test getting missing provider config raises error."""
    config = {
        "provider": "ollama",
        "providers": {},
    }

    with pytest.raises(ConfigError, match="not found"):
        get_provider_config(config)


@pytest.mark.unit
def test_get_provider_config_no_providers():
    """Test error when providers section missing."""
    config = {"provider": "ollama"}

    with pytest.raises(ConfigError, match="No 'providers' section"):
        get_provider_config(config)


@pytest.mark.unit
def test_get_config_value_simple():
    """Test getting simple config value."""
    config = {"provider": "ollama", "provider_priority": None}

    assert get_config_value(config, "provider") == "ollama"
    assert get_config_value(config, "provider_priority") is None


@pytest.mark.unit
def test_get_config_value_nested():
    """Test getting nested config value with dot notation."""
    config = {
        "providers": {
            "ollama": {
                "base_url": "http://localhost:11434",
            }
        }
    }

    assert get_config_value(config, "providers.ollama.base_url") == "http://localhost:11434"


@pytest.mark.unit
def test_get_config_value_missing():
    """Test getting missing config value returns default."""
    config = {"provider": "ollama"}

    assert get_config_value(config, "missing") is None
    assert get_config_value(config, "missing", "default") == "default"
    assert get_config_value(config, "nested.missing.key", 42) == 42


@pytest.mark.unit
def test_default_config_structure():
    """Test that DEFAULT_CONFIG has expected structure."""
    assert "provider" in DEFAULT_CONFIG
    assert "providers" in DEFAULT_CONFIG
    assert "context" in DEFAULT_CONFIG
    assert "output" in DEFAULT_CONFIG

    # Check providers
    assert "openai" in DEFAULT_CONFIG["providers"]
    assert "anthropic" in DEFAULT_CONFIG["providers"]
    assert "ollama" in DEFAULT_CONFIG["providers"]

    # Check context settings
    assert "include_history" in DEFAULT_CONFIG["context"]
    assert "include_git_state" in DEFAULT_CONFIG["context"]

    # Check output settings
    assert "show_conversation" in DEFAULT_CONFIG["output"]
    assert "use_colors" in DEFAULT_CONFIG["output"]


@pytest.mark.unit
def test_load_config_warnings(tmp_path, monkeypatch):
    """Test that config warnings are included in result."""
    config_dir = tmp_path / ".hai"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"

    # Config with issues that should generate warnings (without Pydantic)
    config_content = """
provider: unknown_provider
"""
    config_file.write_text(config_content)

    monkeypatch.setenv("HOME", str(tmp_path))

    # With Pydantic validation (default), invalid provider raises error
    from hai_sh.config import ConfigValidationError

    with pytest.raises(ConfigValidationError, match="Configuration validation failed"):
        load_config()

    # Without Pydantic, warnings are included in dict
    config = load_config(use_pydantic=False)
    assert "_warnings" in config
    assert len(config["_warnings"]) > 0


@pytest.mark.unit
def test_load_config_deprecated_model_field_warning(tmp_path, monkeypatch):
    """Test that deprecated top-level model field triggers a warning."""
    import warnings

    config_dir = tmp_path / ".hai"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"

    # Config with deprecated top-level model field
    config_content = """
provider: ollama
model: llama3.2
"""
    config_file.write_text(config_content)

    monkeypatch.setenv("HOME", str(tmp_path))

    # Capture deprecation warnings
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        config = load_config()

        # Verify a DeprecationWarning was raised
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)

        # Verify warning message contains expected guidance
        warning_message = str(w[0].message)
        assert "top-level 'model' field" in warning_message
        assert "deprecated" in warning_message
        assert "providers.ollama.model" in warning_message

    # Verify the model field was removed from the config (no attribute error)
    assert not hasattr(config, "model") or "model" not in dir(config)
    # Verify config still works correctly
    assert config.provider == "ollama"


@pytest.mark.unit
def test_load_config_deprecated_model_field_removed(tmp_path, monkeypatch):
    """Test that deprecated top-level model field is removed from config."""
    import warnings

    config_dir = tmp_path / ".hai"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"

    # Config with deprecated top-level model field and custom provider
    config_content = """
provider: openai
model: gpt-4
providers:
  openai:
    api_key: sk-test
    model: gpt-4o-mini
"""
    config_file.write_text(config_content)

    monkeypatch.setenv("HOME", str(tmp_path))

    # Suppress the warning and just check the config
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        config = load_config()

    # Verify config loaded successfully without the deprecated field
    assert config.provider == "openai"
    # Provider-specific model should still work
    assert config.providers.openai.model == "gpt-4o-mini"


# --- Provider Priority List Tests ---


@pytest.mark.unit
def test_get_provider_priority_list_with_priority():
    """Test get_provider_priority_list with provider_priority set."""
    config = {
        "provider_priority": ["ollama", "openai", "anthropic"],
        "provider": "local",
    }
    result = get_provider_priority_list(config)
    assert result == ["ollama", "openai", "anthropic"]


@pytest.mark.unit
def test_get_provider_priority_list_without_priority():
    """Test get_provider_priority_list falls back to provider field."""
    config = {
        "provider": "anthropic",
    }
    result = get_provider_priority_list(config)
    assert result == ["anthropic"]


@pytest.mark.unit
def test_get_provider_priority_list_default():
    """Test get_provider_priority_list defaults to ollama."""
    config = {}
    result = get_provider_priority_list(config)
    assert result == ["ollama"]


@pytest.mark.unit
def test_default_config_includes_provider_priority():
    """Test that DEFAULT_CONFIG includes provider_priority field."""
    assert "provider_priority" in DEFAULT_CONFIG
    assert DEFAULT_CONFIG["provider_priority"] is None


# --- Check Provider Availability Tests ---


@pytest.mark.unit
def test_check_provider_availability_missing_provider():
    """Test check_provider_availability with unregistered provider."""
    success, provider, error = check_provider_availability("nonexistent", {})
    assert success is False
    assert provider is None
    assert "not registered" in error.lower() or "not found" in error.lower()


@pytest.mark.unit
def test_check_provider_availability_invalid_config():
    """Test check_provider_availability with invalid config."""
    # OpenAI requires API key starting with sk-
    success, provider, error = check_provider_availability(
        "openai",
        {"api_key": "invalid-key"}
    )
    assert success is False
    assert provider is None
    assert error is not None


@pytest.mark.unit
def test_check_provider_availability_ollama_not_running():
    """Test check_provider_availability with unavailable Ollama."""
    # Use a port that shouldn't have Ollama running
    success, provider, error = check_provider_availability(
        "ollama",
        {"base_url": "http://localhost:99999", "model": "test"}
    )
    assert success is False
    assert provider is None
    # Error should mention unavailability
    assert error is not None


# --- Provider Fallback Result Tests ---


@pytest.mark.unit
def test_provider_fallback_result_no_fallback():
    """Test ProviderFallbackResult when no fallback occurred."""
    result = ProviderFallbackResult(
        provider="mock_provider",
        provider_name="ollama",
        failed_providers=[]
    )
    assert result.had_fallback is False
    assert result.provider_name == "ollama"


@pytest.mark.unit
def test_provider_fallback_result_with_fallback():
    """Test ProviderFallbackResult when fallback occurred."""
    result = ProviderFallbackResult(
        provider="mock_provider",
        provider_name="openai",
        failed_providers=[
            ("ollama", "Cannot connect to Ollama"),
        ]
    )
    assert result.had_fallback is True
    assert result.provider_name == "openai"
    assert len(result.failed_providers) == 1


@pytest.mark.unit
def test_provider_fallback_result_multiple_failures():
    """Test ProviderFallbackResult with multiple failures."""
    result = ProviderFallbackResult(
        provider="mock_provider",
        provider_name="anthropic",
        failed_providers=[
            ("ollama", "Cannot connect to Ollama"),
            ("openai", "Invalid API key"),
        ]
    )
    assert result.had_fallback is True
    assert result.provider_name == "anthropic"
    assert len(result.failed_providers) == 2


# --- Get Available Provider Tests ---


@pytest.mark.unit
def test_get_available_provider_all_fail():
    """Test get_available_provider raises when all providers fail."""
    config = {
        "provider_priority": ["ollama"],
        "providers": {
            "ollama": {
                "base_url": "http://localhost:99999",  # Invalid port
                "model": "test",
            }
        }
    }
    with pytest.raises(ConfigError, match="No providers available"):
        get_available_provider(config)


@pytest.mark.unit
def test_get_available_provider_single_provider_fails():
    """Test get_available_provider with single unavailable provider."""
    config = {
        "provider": "ollama",
        "providers": {
            "ollama": {
                "base_url": "http://localhost:99999",  # Invalid port
                "model": "test",
            }
        }
    }
    with pytest.raises(ConfigError, match="No providers available"):
        get_available_provider(config)


@pytest.mark.unit
def test_get_available_provider_callback_called():
    """Test get_available_provider calls on_fallback callback."""
    fallback_calls = []

    def on_fallback(failed, error, next_provider):
        fallback_calls.append((failed, next_provider))

    config = {
        "provider_priority": ["ollama", "openai"],
        "providers": {
            "ollama": {
                "base_url": "http://localhost:99999",
                "model": "test",
            },
            "openai": {
                "api_key": "invalid",  # Will fail validation
            }
        }
    }

    # Both should fail, but callback should be called when first fails
    try:
        get_available_provider(config, on_fallback=on_fallback)
    except ConfigError:
        pass

    # Callback should have been called when ollama failed
    assert len(fallback_calls) >= 1
    assert fallback_calls[0][0] == "ollama"
    assert fallback_calls[0][1] == "openai"


@pytest.mark.unit
def test_get_available_provider_error_message_details():
    """Test get_available_provider includes details in error message."""
    config = {
        "provider_priority": ["ollama", "openai"],
        "providers": {
            "ollama": {
                "base_url": "http://localhost:99999",
                "model": "test",
            },
            "openai": {
                "api_key": "invalid",
            }
        }
    }

    with pytest.raises(ConfigError) as exc_info:
        get_available_provider(config)

    error_message = str(exc_info.value)
    # Should list both providers that were tried
    assert "ollama" in error_message.lower()
    assert "openai" in error_message.lower()
    assert "Tried 2 provider" in error_message
