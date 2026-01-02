"""
Tests for Anthropic provider implementation.
"""

from typing import Any
from unittest.mock import Mock, patch, MagicMock

import pytest

from hai_sh.providers.anthropic import AnthropicProvider, ANTHROPIC_AVAILABLE


# Skip all tests if anthropic is not installed
pytestmark = pytest.mark.skipif(
    not ANTHROPIC_AVAILABLE,
    reason="anthropic package not installed"
)


@pytest.fixture
def valid_config():
    """Valid Anthropic configuration."""
    return {
        "api_key": "sk-ant-test-key-1234567890",
        "model": "claude-sonnet-4-5",
        "timeout": 30,
        "max_tokens": 1000,
        "temperature": 0.7
    }


@pytest.fixture
def minimal_config():
    """Minimal valid Anthropic configuration."""
    return {
        "api_key": "sk-ant-test-key"
    }


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client for testing."""
    with patch('hai_sh.providers.anthropic.Anthropic') as mock:
        yield mock


# ============================================================================
# Configuration Validation Tests
# ============================================================================


@pytest.mark.unit
def test_validate_config_valid(mock_anthropic_client, valid_config):
    """Test validation with valid configuration."""
    provider = AnthropicProvider(valid_config)
    assert provider.validate_config(valid_config) is True


@pytest.mark.unit
def test_validate_config_minimal(mock_anthropic_client, minimal_config):
    """Test validation with minimal valid configuration."""
    provider = AnthropicProvider(minimal_config)
    assert provider.validate_config(minimal_config) is True


@pytest.mark.unit
def test_validate_config_missing_api_key():
    """Test validation fails without API key."""
    config = {"model": "claude-sonnet-4-5"}

    with pytest.raises(ValueError, match="Invalid configuration"):
        AnthropicProvider(config)


@pytest.mark.unit
def test_validate_config_empty_api_key():
    """Test validation fails with empty API key."""
    config = {"api_key": ""}

    with pytest.raises(ValueError, match="Invalid configuration"):
        AnthropicProvider(config)


@pytest.mark.unit
def test_validate_config_invalid_api_key_format():
    """Test validation fails with invalid API key format."""
    config = {"api_key": "invalid-key"}

    with pytest.raises(ValueError, match="Invalid configuration"):
        AnthropicProvider(config)


@pytest.mark.unit
def test_validate_config_invalid_openai_key_format():
    """Test validation fails with OpenAI-style API key."""
    config = {"api_key": "sk-test-key"}  # Missing 'ant' prefix

    with pytest.raises(ValueError, match="Invalid configuration"):
        AnthropicProvider(config)


@pytest.mark.unit
def test_validate_config_invalid_timeout(mock_anthropic_client):
    """Test validation fails with invalid timeout."""
    provider = AnthropicProvider({"api_key": "sk-ant-test"})

    assert provider.validate_config({"api_key": "sk-ant-test", "timeout": -1}) is False
    assert provider.validate_config({"api_key": "sk-ant-test", "timeout": 0}) is False
    assert provider.validate_config({"api_key": "sk-ant-test", "timeout": "30"}) is False


@pytest.mark.unit
def test_validate_config_invalid_max_tokens(mock_anthropic_client):
    """Test validation fails with invalid max_tokens."""
    provider = AnthropicProvider({"api_key": "sk-ant-test"})

    assert provider.validate_config({"api_key": "sk-ant-test", "max_tokens": -1}) is False
    assert provider.validate_config({"api_key": "sk-ant-test", "max_tokens": 0}) is False
    assert provider.validate_config({"api_key": "sk-ant-test", "max_tokens": 1.5}) is False


@pytest.mark.unit
def test_validate_config_invalid_temperature(mock_anthropic_client):
    """Test validation fails with invalid temperature."""
    provider = AnthropicProvider({"api_key": "sk-ant-test"})

    assert provider.validate_config({"api_key": "sk-ant-test", "temperature": -0.1}) is False
    assert provider.validate_config({"api_key": "sk-ant-test", "temperature": 1.1}) is False


@pytest.mark.unit
def test_validate_config_valid_temperature_range(mock_anthropic_client):
    """Test validation succeeds with valid temperature range."""
    provider = AnthropicProvider({"api_key": "sk-ant-test"})

    assert provider.validate_config({"api_key": "sk-ant-test", "temperature": 0.0}) is True
    assert provider.validate_config({"api_key": "sk-ant-test", "temperature": 0.5}) is True
    assert provider.validate_config({"api_key": "sk-ant-test", "temperature": 1.0}) is True


# ============================================================================
# Provider Initialization Tests
# ============================================================================


@pytest.mark.unit
def test_provider_initialization(mock_anthropic_client, valid_config):
    """Test provider initialization with valid config."""
    provider = AnthropicProvider(valid_config)

    assert provider.config == valid_config
    assert provider.model == "claude-sonnet-4-5"
    assert provider.max_tokens == 1000
    assert provider.temperature == 0.7


@pytest.mark.unit
def test_provider_initialization_defaults(mock_anthropic_client, minimal_config):
    """Test provider initialization with default values."""
    provider = AnthropicProvider(minimal_config)

    assert provider.model == "claude-sonnet-4-5"
    assert provider.max_tokens == 1000
    assert provider.temperature == 0.7


@pytest.mark.unit
def test_provider_name(mock_anthropic_client):
    """Test provider name property."""
    provider = AnthropicProvider({"api_key": "sk-ant-test"})

    assert provider.name == "anthropic"


# ============================================================================
# is_available Tests
# ============================================================================


@pytest.mark.unit
def test_is_available_with_api_key(mock_anthropic_client):
    """Test is_available returns True with API key."""
    provider = AnthropicProvider({"api_key": "sk-ant-test"})

    assert provider.is_available() is True


@pytest.mark.unit
def test_is_available_without_api_key(mock_anthropic_client):
    """Test is_available returns False without API key."""
    # This test creates a provider with a key, then checks a config without one
    provider = AnthropicProvider({"api_key": "sk-ant-test"})
    provider.config = {}

    assert provider.is_available() is False


# ============================================================================
# generate() Tests with Mocked API
# ============================================================================


@pytest.mark.unit
def test_generate_simple_prompt(mock_anthropic_client, minimal_config):
    """Test generate with a simple prompt."""
    provider = AnthropicProvider(minimal_config)

    # Mock the Anthropic API response
    mock_response = Mock()
    mock_content_block = Mock()
    mock_content_block.text = "ls -la"
    mock_response.content = [mock_content_block]

    with patch.object(provider.client.messages, 'create', return_value=mock_response):
        response = provider.generate("List files")

        assert response == "ls -la"


@pytest.mark.unit
def test_generate_with_context(mock_anthropic_client, minimal_config):
    """Test generate with context."""
    provider = AnthropicProvider(minimal_config)

    context = {
        "cwd": "/home/user/project",
        "git": {"is_repo": True, "branch": "main", "has_changes": True},
        "env": {"user": "testuser", "shell": "/bin/bash"}
    }

    mock_response = Mock()
    mock_content_block = Mock()
    mock_content_block.text = "git status"
    mock_response.content = [mock_content_block]

    with patch.object(provider.client.messages, 'create', return_value=mock_response) as mock_create:
        response = provider.generate("Check git status", context=context)

        assert response == "git status"

        # Verify API was called with context in system message
        call_args = mock_create.call_args
        system_msg = call_args.kwargs['system']
        assert '/home/user/project' in system_msg
        assert 'main' in system_msg


@pytest.mark.unit
def test_generate_without_context(mock_anthropic_client, minimal_config):
    """Test generate without context."""
    provider = AnthropicProvider(minimal_config)

    mock_response = Mock()
    mock_content_block = Mock()
    mock_content_block.text = "echo hello"
    mock_response.content = [mock_content_block]

    with patch.object(provider.client.messages, 'create', return_value=mock_response) as mock_create:
        response = provider.generate("Say hello")

        assert response == "echo hello"

        # Verify API was called with default system message
        call_args = mock_create.call_args
        system_msg = call_args.kwargs['system']
        assert "helpful terminal assistant" in system_msg


@pytest.mark.unit
def test_generate_uses_config_parameters(mock_anthropic_client, valid_config):
    """Test that generate uses configured parameters."""
    provider = AnthropicProvider(valid_config)

    mock_response = Mock()
    mock_content_block = Mock()
    mock_content_block.text = "response"
    mock_response.content = [mock_content_block]

    with patch.object(provider.client.messages, 'create', return_value=mock_response) as mock_create:
        provider.generate("test")

        call_args = mock_create.call_args
        assert call_args.kwargs['model'] == "claude-sonnet-4-5"
        assert call_args.kwargs['max_tokens'] == 1000
        assert call_args.kwargs['temperature'] == 0.7


@pytest.mark.unit
def test_generate_strips_whitespace(mock_anthropic_client, minimal_config):
    """Test that generate strips leading/trailing whitespace."""
    provider = AnthropicProvider(minimal_config)

    mock_response = Mock()
    mock_content_block = Mock()
    mock_content_block.text = "  ls -la\n  "
    mock_response.content = [mock_content_block]

    with patch.object(provider.client.messages, 'create', return_value=mock_response):
        response = provider.generate("List files")

        assert response == "ls -la"


# ============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.unit
def test_generate_authentication_error(mock_anthropic_client, minimal_config):
    """Test generate handles authentication errors."""
    from anthropic import AuthenticationError

    provider = AnthropicProvider(minimal_config)

    with patch.object(
        provider.client.messages,
        'create',
        side_effect=AuthenticationError("Invalid API key", response=Mock(), body=None)
    ):
        with pytest.raises(RuntimeError, match="authentication failed"):
            provider.generate("test")


@pytest.mark.unit
def test_generate_rate_limit_error(mock_anthropic_client, minimal_config):
    """Test generate handles rate limit errors."""
    from anthropic import RateLimitError

    provider = AnthropicProvider(minimal_config)

    with patch.object(
        provider.client.messages,
        'create',
        side_effect=RateLimitError("Rate limit exceeded", response=Mock(), body=None)
    ):
        with pytest.raises(RuntimeError, match="rate limit exceeded"):
            provider.generate("test")


@pytest.mark.unit
def test_generate_api_error(mock_anthropic_client, minimal_config):
    """Test generate handles API errors."""
    from anthropic import APIError

    provider = AnthropicProvider(minimal_config)

    with patch.object(
        provider.client.messages,
        'create',
        side_effect=APIError("Server error", request=Mock(), body=None)
    ):
        with pytest.raises(RuntimeError, match="API error"):
            provider.generate("test")


@pytest.mark.unit
def test_generate_unexpected_error(mock_anthropic_client, minimal_config):
    """Test generate handles unexpected errors."""
    provider = AnthropicProvider(minimal_config)

    with patch.object(
        provider.client.messages,
        'create',
        side_effect=Exception("Unexpected error")
    ):
        with pytest.raises(RuntimeError, match="Unexpected error"):
            provider.generate("test")


# ============================================================================
# Context Formatting Tests
# ============================================================================


@pytest.mark.unit
def test_format_context_minimal(mock_anthropic_client, minimal_config):
    """Test context formatting with minimal context."""
    provider = AnthropicProvider(minimal_config)

    context = {}
    formatted = provider._format_context(context)

    assert "helpful terminal assistant" in formatted
    assert formatted.count('\n') == 0  # Only base message


@pytest.mark.unit
def test_format_context_with_cwd(mock_anthropic_client, minimal_config):
    """Test context formatting with current directory."""
    provider = AnthropicProvider(minimal_config)

    context = {"cwd": "/home/user/project"}
    formatted = provider._format_context(context)

    assert "Current directory: /home/user/project" in formatted


@pytest.mark.unit
def test_format_context_with_git(mock_anthropic_client, minimal_config):
    """Test context formatting with git information."""
    provider = AnthropicProvider(minimal_config)

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
def test_format_context_with_git_no_changes(mock_anthropic_client, minimal_config):
    """Test context formatting with git but no changes."""
    provider = AnthropicProvider(minimal_config)

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
def test_format_context_with_env(mock_anthropic_client, minimal_config):
    """Test context formatting with environment info."""
    provider = AnthropicProvider(minimal_config)

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
def test_format_context_complete(mock_anthropic_client, minimal_config):
    """Test context formatting with all context types."""
    provider = AnthropicProvider(minimal_config)

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


# ============================================================================
# System Prompt Tests (TDD - New Feature)
# ============================================================================


@pytest.mark.unit
def test_generate_with_system_prompt_parameter(mock_anthropic_client, minimal_config):
    """Test generate accepts system_prompt parameter."""
    provider = AnthropicProvider(minimal_config)

    system_prompt = "You are a bash command generator. Always respond in JSON format."

    mock_response = Mock()
    mock_content_block = Mock()
    mock_content_block.text = '{"command": "ls -la"}'
    mock_response.content = [mock_content_block]

    with patch.object(provider.client.messages, 'create', return_value=mock_response) as mock_create:
        response = provider.generate("List files", system_prompt=system_prompt)

        assert response == '{"command": "ls -la"}'

        # Verify API was called with system_prompt in system message
        call_args = mock_create.call_args
        system_msg = call_args.kwargs['system']
        assert "bash command generator" in system_msg
        assert "JSON format" in system_msg


@pytest.mark.unit
def test_generate_system_prompt_overrides_default(mock_anthropic_client, minimal_config):
    """Test that system_prompt replaces the default system message."""
    provider = AnthropicProvider(minimal_config)

    system_prompt = "Custom system instructions."

    mock_response = Mock()
    mock_content_block = Mock()
    mock_content_block.text = "response"
    mock_response.content = [mock_content_block]

    with patch.object(provider.client.messages, 'create', return_value=mock_response) as mock_create:
        provider.generate("test", system_prompt=system_prompt)

        call_args = mock_create.call_args
        system_msg = call_args.kwargs['system']

        # Should use custom system prompt, not default
        assert "Custom system instructions" in system_msg
        assert "helpful terminal assistant" not in system_msg


@pytest.mark.unit
def test_generate_system_prompt_with_context(mock_anthropic_client, minimal_config):
    """Test system_prompt is combined with context."""
    provider = AnthropicProvider(minimal_config)

    system_prompt = "You are a JSON command generator."
    context = {
        "cwd": "/home/user/project",
        "git": {"is_repo": True, "branch": "main", "has_changes": False}
    }

    mock_response = Mock()
    mock_content_block = Mock()
    mock_content_block.text = '{"command": "git status"}'
    mock_response.content = [mock_content_block]

    with patch.object(provider.client.messages, 'create', return_value=mock_response) as mock_create:
        provider.generate("Check git", system_prompt=system_prompt, context=context)

        call_args = mock_create.call_args
        system_msg = call_args.kwargs['system']

        # Should contain both system prompt and context
        assert "JSON command generator" in system_msg
        assert "/home/user/project" in system_msg
        assert "main" in system_msg


@pytest.mark.unit
def test_generate_without_system_prompt_uses_default(mock_anthropic_client, minimal_config):
    """Test that omitting system_prompt uses default behavior (backward compatibility)."""
    provider = AnthropicProvider(minimal_config)

    mock_response = Mock()
    mock_content_block = Mock()
    mock_content_block.text = "echo hello"
    mock_response.content = [mock_content_block]

    with patch.object(provider.client.messages, 'create', return_value=mock_response) as mock_create:
        # Call without system_prompt parameter
        response = provider.generate("Say hello")

        assert response == "echo hello"

        # Verify API was called with default system message
        call_args = mock_create.call_args
        system_msg = call_args.kwargs['system']
        assert "helpful terminal assistant" in system_msg


@pytest.mark.unit
def test_generate_empty_system_prompt(mock_anthropic_client, minimal_config):
    """Test generate handles empty system_prompt gracefully."""
    provider = AnthropicProvider(minimal_config)

    mock_response = Mock()
    mock_content_block = Mock()
    mock_content_block.text = "response"
    mock_response.content = [mock_content_block]

    with patch.object(provider.client.messages, 'create', return_value=mock_response) as mock_create:
        # Empty string should fall back to default
        provider.generate("test", system_prompt="")

        call_args = mock_create.call_args
        system_msg = call_args.kwargs['system']
        assert "helpful terminal assistant" in system_msg
