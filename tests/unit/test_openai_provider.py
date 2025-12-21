"""
Tests for OpenAI provider implementation.
"""

from typing import Any
from unittest.mock import Mock, patch, MagicMock

import pytest

from hai_sh.providers.openai import OpenAIProvider, OPENAI_AVAILABLE


# Skip all tests if openai is not installed
pytestmark = pytest.mark.skipif(
    not OPENAI_AVAILABLE,
    reason="openai package not installed"
)


@pytest.fixture
def valid_config():
    """Valid OpenAI configuration."""
    return {
        "api_key": "sk-test-key-1234567890",
        "model": "gpt-4o-mini",
        "timeout": 30,
        "max_tokens": 1000,
        "temperature": 0.7
    }


@pytest.fixture
def minimal_config():
    """Minimal valid OpenAI configuration."""
    return {
        "api_key": "sk-test-key"
    }


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    with patch('hai_sh.providers.openai.OpenAI') as mock:
        yield mock


# ============================================================================
# Configuration Validation Tests
# ============================================================================


@pytest.mark.unit
def test_validate_config_valid(mock_openai_client, valid_config):
    """Test validation with valid configuration."""
    provider = OpenAIProvider(valid_config)
    assert provider.validate_config(valid_config) is True


@pytest.mark.unit
def test_validate_config_minimal(mock_openai_client, minimal_config):
    """Test validation with minimal valid configuration."""
    provider = OpenAIProvider(minimal_config)
    assert provider.validate_config(minimal_config) is True


@pytest.mark.unit
def test_validate_config_missing_api_key():
    """Test validation fails without API key."""
    config = {"model": "gpt-4"}

    with pytest.raises(ValueError, match="Invalid configuration"):
        OpenAIProvider(config)


@pytest.mark.unit
def test_validate_config_empty_api_key():
    """Test validation fails with empty API key."""
    config = {"api_key": ""}

    with pytest.raises(ValueError, match="Invalid configuration"):
        OpenAIProvider(config)


@pytest.mark.unit
def test_validate_config_invalid_api_key_format():
    """Test validation fails with invalid API key format."""
    config = {"api_key": "invalid-key"}

    with pytest.raises(ValueError, match="Invalid configuration"):
        OpenAIProvider(config)


@pytest.mark.unit
def test_validate_config_invalid_timeout(mock_openai_client):
    """Test validation fails with invalid timeout."""
    provider = OpenAIProvider({"api_key": "sk-test"})

    assert provider.validate_config({"api_key": "sk-test", "timeout": -1}) is False
    assert provider.validate_config({"api_key": "sk-test", "timeout": 0}) is False
    assert provider.validate_config({"api_key": "sk-test", "timeout": "30"}) is False


@pytest.mark.unit
def test_validate_config_invalid_max_tokens(mock_openai_client):
    """Test validation fails with invalid max_tokens."""
    provider = OpenAIProvider({"api_key": "sk-test"})

    assert provider.validate_config({"api_key": "sk-test", "max_tokens": -1}) is False
    assert provider.validate_config({"api_key": "sk-test", "max_tokens": 0}) is False
    assert provider.validate_config({"api_key": "sk-test", "max_tokens": 1.5}) is False


@pytest.mark.unit
def test_validate_config_invalid_temperature(mock_openai_client):
    """Test validation fails with invalid temperature."""
    provider = OpenAIProvider({"api_key": "sk-test"})

    assert provider.validate_config({"api_key": "sk-test", "temperature": -0.1}) is False
    assert provider.validate_config({"api_key": "sk-test", "temperature": 2.1}) is False


@pytest.mark.unit
def test_validate_config_valid_temperature_range(mock_openai_client):
    """Test validation succeeds with valid temperature range."""
    provider = OpenAIProvider({"api_key": "sk-test"})

    assert provider.validate_config({"api_key": "sk-test", "temperature": 0.0}) is True
    assert provider.validate_config({"api_key": "sk-test", "temperature": 1.0}) is True
    assert provider.validate_config({"api_key": "sk-test", "temperature": 2.0}) is True


# ============================================================================
# Provider Initialization Tests
# ============================================================================


@pytest.mark.unit
def test_provider_initialization(mock_openai_client, valid_config):
    """Test provider initialization with valid config."""
    provider = OpenAIProvider(valid_config)

    assert provider.config == valid_config
    assert provider.model == "gpt-4o-mini"
    assert provider.max_tokens == 1000
    assert provider.temperature == 0.7


@pytest.mark.unit
def test_provider_initialization_defaults(mock_openai_client, minimal_config):
    """Test provider initialization with default values."""
    provider = OpenAIProvider(minimal_config)

    assert provider.model == "gpt-4o-mini"
    assert provider.max_tokens == 1000
    assert provider.temperature == 0.7


@pytest.mark.unit
def test_provider_name(mock_openai_client):
    """Test provider name property."""
    provider = OpenAIProvider({"api_key": "sk-test"})

    assert provider.name == "openai"


# ============================================================================
# is_available Tests
# ============================================================================


@pytest.mark.unit
def test_is_available_with_api_key(mock_openai_client):
    """Test is_available returns True with API key."""
    provider = OpenAIProvider({"api_key": "sk-test"})

    assert provider.is_available() is True


@pytest.mark.unit
def test_is_available_without_api_key(mock_openai_client):
    """Test is_available returns False without API key."""
    # This test creates a provider with a key, then checks a config without one
    provider = OpenAIProvider({"api_key": "sk-test"})
    provider.config = {}

    assert provider.is_available() is False


# ============================================================================
# generate() Tests with Mocked API
# ============================================================================


@pytest.mark.unit
def test_generate_simple_prompt(mock_openai_client, minimal_config):
    """Test generate with a simple prompt."""
    provider = OpenAIProvider(minimal_config)

    # Mock the OpenAI API response
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "ls -la"

    with patch.object(provider.client.chat.completions, 'create', return_value=mock_response):
        response = provider.generate("List files")

        assert response == "ls -la"


@pytest.mark.unit
def test_generate_with_context(mock_openai_client, minimal_config):
    """Test generate with context."""
    provider = OpenAIProvider(minimal_config)

    context = {
        "cwd": "/home/user/project",
        "git": {"is_repo": True, "branch": "main", "has_changes": True},
        "env": {"user": "testuser", "shell": "/bin/bash"}
    }

    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "git status"

    with patch.object(provider.client.chat.completions, 'create', return_value=mock_response) as mock_create:
        response = provider.generate("Check git status", context=context)

        assert response == "git status"

        # Verify API was called with context in system message
        call_args = mock_create.call_args
        messages = call_args.kwargs['messages']
        assert len(messages) == 2
        assert messages[0]['role'] == 'system'
        assert '/home/user/project' in messages[0]['content']
        assert 'main' in messages[0]['content']


@pytest.mark.unit
def test_generate_without_context(mock_openai_client, minimal_config):
    """Test generate without context."""
    provider = OpenAIProvider(minimal_config)

    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "echo hello"

    with patch.object(provider.client.chat.completions, 'create', return_value=mock_response) as mock_create:
        response = provider.generate("Say hello")

        assert response == "echo hello"

        # Verify API was called without system message
        call_args = mock_create.call_args
        messages = call_args.kwargs['messages']
        assert len(messages) == 1
        assert messages[0]['role'] == 'user'


@pytest.mark.unit
def test_generate_uses_config_parameters(mock_openai_client, valid_config):
    """Test that generate uses configured parameters."""
    provider = OpenAIProvider(valid_config)

    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "response"

    with patch.object(provider.client.chat.completions, 'create', return_value=mock_response) as mock_create:
        provider.generate("test")

        call_args = mock_create.call_args
        assert call_args.kwargs['model'] == "gpt-4o-mini"
        assert call_args.kwargs['max_tokens'] == 1000
        assert call_args.kwargs['temperature'] == 0.7


@pytest.mark.unit
def test_generate_uses_max_completion_tokens_for_o1_models(mock_openai_client):
    """Test that o1 series models use max_completion_tokens parameter."""
    # Test with o1-preview
    config_o1_preview = {
        "api_key": "sk-test",
        "model": "o1-preview",
        "max_tokens": 1000
    }
    provider = OpenAIProvider(config_o1_preview)

    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "response"

    with patch.object(provider.client.chat.completions, 'create', return_value=mock_response) as mock_create:
        provider.generate("test")

        call_args = mock_create.call_args
        assert call_args.kwargs['model'] == "o1-preview"
        assert 'max_completion_tokens' in call_args.kwargs
        assert call_args.kwargs['max_completion_tokens'] == 1000
        assert 'max_tokens' not in call_args.kwargs

    # Test with o1-mini
    config_o1_mini = {
        "api_key": "sk-test",
        "model": "o1-mini",
        "max_tokens": 500
    }
    provider = OpenAIProvider(config_o1_mini)

    with patch.object(provider.client.chat.completions, 'create', return_value=mock_response) as mock_create:
        provider.generate("test")

        call_args = mock_create.call_args
        assert call_args.kwargs['model'] == "o1-mini"
        assert 'max_completion_tokens' in call_args.kwargs
        assert call_args.kwargs['max_completion_tokens'] == 500
        assert 'max_tokens' not in call_args.kwargs

    # Test with gpt-5-nano
    config_gpt5_nano = {
        "api_key": "sk-test",
        "model": "gpt-5-nano",
        "max_tokens": 750
    }
    provider = OpenAIProvider(config_gpt5_nano)

    with patch.object(provider.client.chat.completions, 'create', return_value=mock_response) as mock_create:
        provider.generate("test")

        call_args = mock_create.call_args
        assert call_args.kwargs['model'] == "gpt-5-nano"
        assert 'max_completion_tokens' in call_args.kwargs
        assert call_args.kwargs['max_completion_tokens'] == 750
        assert 'max_tokens' not in call_args.kwargs

    # Test with gpt-4.1-mini
    config_gpt41_mini = {
        "api_key": "sk-test",
        "model": "gpt-4.1-mini",
        "max_tokens": 800
    }
    provider = OpenAIProvider(config_gpt41_mini)

    with patch.object(provider.client.chat.completions, 'create', return_value=mock_response) as mock_create:
        provider.generate("test")

        call_args = mock_create.call_args
        assert call_args.kwargs['model'] == "gpt-4.1-mini"
        assert 'max_completion_tokens' in call_args.kwargs
        assert call_args.kwargs['max_completion_tokens'] == 800
        assert 'max_tokens' not in call_args.kwargs


@pytest.mark.unit
def test_generate_uses_max_tokens_for_legacy_models(mock_openai_client):
    """Test that legacy models use max_tokens parameter."""
    # Test with gpt-4
    config_gpt4 = {
        "api_key": "sk-test",
        "model": "gpt-4",
        "max_tokens": 1000
    }
    provider = OpenAIProvider(config_gpt4)

    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "response"

    with patch.object(provider.client.chat.completions, 'create', return_value=mock_response) as mock_create:
        provider.generate("test")

        call_args = mock_create.call_args
        assert call_args.kwargs['model'] == "gpt-4"
        assert 'max_tokens' in call_args.kwargs
        assert call_args.kwargs['max_tokens'] == 1000
        assert 'max_completion_tokens' not in call_args.kwargs

    # Test with gpt-3.5-turbo
    config_gpt35 = {
        "api_key": "sk-test",
        "model": "gpt-3.5-turbo",
        "max_tokens": 500
    }
    provider = OpenAIProvider(config_gpt35)

    with patch.object(provider.client.chat.completions, 'create', return_value=mock_response) as mock_create:
        provider.generate("test")

        call_args = mock_create.call_args
        assert call_args.kwargs['model'] == "gpt-3.5-turbo"
        assert 'max_tokens' in call_args.kwargs
        assert call_args.kwargs['max_tokens'] == 500
        assert 'max_completion_tokens' not in call_args.kwargs

    # Test with gpt-4o-mini (default)
    config_gpt4o_mini = {
        "api_key": "sk-test",
        "model": "gpt-4o-mini",
        "max_tokens": 750
    }
    provider = OpenAIProvider(config_gpt4o_mini)

    with patch.object(provider.client.chat.completions, 'create', return_value=mock_response) as mock_create:
        provider.generate("test")

        call_args = mock_create.call_args
        assert call_args.kwargs['model'] == "gpt-4o-mini"
        assert 'max_tokens' in call_args.kwargs
        assert call_args.kwargs['max_tokens'] == 750
        assert 'max_completion_tokens' not in call_args.kwargs


# ============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.unit
def test_generate_authentication_error(mock_openai_client, minimal_config):
    """Test generate handles authentication errors."""
    from openai import AuthenticationError

    provider = OpenAIProvider(minimal_config)

    mock_response = Mock()
    mock_response.status_code = 401

    with patch.object(
        provider.client.chat.completions,
        'create',
        side_effect=AuthenticationError("Invalid API key", response=mock_response, body=None)
    ):
        with pytest.raises(RuntimeError, match="authentication failed"):
            provider.generate("test")


@pytest.mark.unit
def test_generate_rate_limit_error(mock_openai_client, minimal_config):
    """Test generate handles rate limit errors."""
    from openai import RateLimitError

    provider = OpenAIProvider(minimal_config)

    mock_response = Mock()
    mock_response.status_code = 429

    with patch.object(
        provider.client.chat.completions,
        'create',
        side_effect=RateLimitError("Rate limit exceeded", response=mock_response, body=None)
    ):
        with pytest.raises(RuntimeError, match="rate limit exceeded"):
            provider.generate("test")


@pytest.mark.unit
def test_generate_api_error(mock_openai_client, minimal_config):
    """Test generate handles API errors."""
    from openai import APIError

    provider = OpenAIProvider(minimal_config)

    mock_response = Mock()
    mock_response.status_code = 500

    with patch.object(
        provider.client.chat.completions,
        'create',
        side_effect=APIError("Server error", request=Mock(), body=None)
    ):
        with pytest.raises(RuntimeError, match="API error"):
            provider.generate("test")


@pytest.mark.unit
def test_generate_generic_openai_error(mock_openai_client, minimal_config):
    """Test generate handles generic OpenAI errors."""
    from openai import OpenAIError

    provider = OpenAIProvider(minimal_config)

    with patch.object(
        provider.client.chat.completions,
        'create',
        side_effect=OpenAIError("Unknown error")
    ):
        with pytest.raises(RuntimeError, match="OpenAI error"):
            provider.generate("test")


@pytest.mark.unit
def test_generate_unexpected_error(mock_openai_client, minimal_config):
    """Test generate handles unexpected errors."""
    provider = OpenAIProvider(minimal_config)

    with patch.object(
        provider.client.chat.completions,
        'create',
        side_effect=Exception("Unexpected error")
    ):
        with pytest.raises(RuntimeError, match="Unexpected error"):
            provider.generate("test")


# ============================================================================
# Context Formatting Tests
# ============================================================================


@pytest.mark.unit
def test_format_context_minimal(mock_openai_client, minimal_config):
    """Test context formatting with minimal context."""
    provider = OpenAIProvider(minimal_config)

    context = {}
    formatted = provider._format_context(context)

    assert "helpful terminal assistant" in formatted
    assert formatted.count('\n') == 0  # Only base message


@pytest.mark.unit
def test_format_context_with_cwd(mock_openai_client, minimal_config):
    """Test context formatting with current directory."""
    provider = OpenAIProvider(minimal_config)

    context = {"cwd": "/home/user/project"}
    formatted = provider._format_context(context)

    assert "Current directory: /home/user/project" in formatted


@pytest.mark.unit
def test_format_context_with_git(mock_openai_client, minimal_config):
    """Test context formatting with git information."""
    provider = OpenAIProvider(minimal_config)

    context = {
        "git": {
            "is_repo": True,
            "branch": "feature-branch",
            "has_changes": True
        }
    }
    formatted = provider._format_context(context)

    assert "Git branch: feature-branch" in formatted
    assert "uncommitted changes" in formatted


@pytest.mark.unit
def test_format_context_with_git_no_changes(mock_openai_client, minimal_config):
    """Test context formatting with git but no changes."""
    provider = OpenAIProvider(minimal_config)

    context = {
        "git": {
            "is_repo": True,
            "branch": "main",
            "has_changes": False
        }
    }
    formatted = provider._format_context(context)

    assert "Git branch: main" in formatted
    assert "uncommitted changes" not in formatted


@pytest.mark.unit
def test_format_context_with_env(mock_openai_client, minimal_config):
    """Test context formatting with environment info."""
    provider = OpenAIProvider(minimal_config)

    context = {
        "env": {
            "user": "testuser",
            "shell": "/bin/bash"
        }
    }
    formatted = provider._format_context(context)

    assert "User: testuser" in formatted
    assert "Shell: /bin/bash" in formatted


@pytest.mark.unit
def test_format_context_complete(mock_openai_client, minimal_config):
    """Test context formatting with all context types."""
    provider = OpenAIProvider(minimal_config)

    context = {
        "cwd": "/home/user/project",
        "git": {
            "is_repo": True,
            "branch": "main",
            "has_changes": False
        },
        "env": {
            "user": "testuser",
            "shell": "/bin/zsh"
        }
    }
    formatted = provider._format_context(context)

    assert "Current directory: /home/user/project" in formatted
    assert "Git branch: main" in formatted
    assert "User: testuser" in formatted
    assert "Shell: /bin/zsh" in formatted
