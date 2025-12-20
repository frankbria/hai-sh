"""
Tests for Ollama provider implementation.
"""

import json
from typing import Any
from unittest.mock import Mock, patch, MagicMock

import pytest

from hai_sh.providers.ollama import OllamaProvider, REQUESTS_AVAILABLE


# Skip all tests if requests is not installed
pytestmark = pytest.mark.skipif(
    not REQUESTS_AVAILABLE,
    reason="requests package not installed"
)


@pytest.fixture
def valid_config():
    """Valid Ollama configuration."""
    return {
        "base_url": "http://localhost:11434",
        "model": "llama3.2",
        "timeout": 60,
        "stream": True,
        "temperature": 0.7
    }


@pytest.fixture
def minimal_config():
    """Minimal valid Ollama configuration."""
    return {}


@pytest.fixture
def non_streaming_config():
    """Configuration with streaming disabled."""
    return {
        "base_url": "http://localhost:11434",
        "model": "llama3.2",
        "stream": False
    }


# ============================================================================
# Configuration Validation Tests
# ============================================================================


@pytest.mark.unit
def test_validate_config_valid(valid_config):
    """Test validation with valid configuration."""
    provider = OllamaProvider(valid_config)
    assert provider.validate_config(valid_config) is True


@pytest.mark.unit
def test_validate_config_minimal(minimal_config):
    """Test validation with minimal (empty) configuration."""
    provider = OllamaProvider(minimal_config)
    assert provider.validate_config(minimal_config) is True


@pytest.mark.unit
def test_validate_config_invalid_model():
    """Test validation fails with invalid model."""
    provider = OllamaProvider({})

    assert provider.validate_config({"model": ""}) is False
    assert provider.validate_config({"model": "   "}) is False
    assert provider.validate_config({"model": 123}) is False


@pytest.mark.unit
def test_validate_config_invalid_base_url():
    """Test validation fails with invalid base URL."""
    provider = OllamaProvider({})

    assert provider.validate_config({"base_url": ""}) is False
    assert provider.validate_config({"base_url": "   "}) is False
    assert provider.validate_config({"base_url": "localhost:11434"}) is False  # No protocol
    assert provider.validate_config({"base_url": "ftp://localhost:11434"}) is False  # Wrong protocol
    assert provider.validate_config({"base_url": 123}) is False


@pytest.mark.unit
def test_validate_config_valid_base_url():
    """Test validation succeeds with valid base URLs."""
    provider = OllamaProvider({})

    assert provider.validate_config({"base_url": "http://localhost:11434"}) is True
    assert provider.validate_config({"base_url": "https://ollama.example.com"}) is True
    assert provider.validate_config({"base_url": "http://192.168.1.100:11434"}) is True


@pytest.mark.unit
def test_validate_config_invalid_timeout():
    """Test validation fails with invalid timeout."""
    provider = OllamaProvider({})

    assert provider.validate_config({"timeout": -1}) is False
    assert provider.validate_config({"timeout": 0}) is False
    assert provider.validate_config({"timeout": "60"}) is False


@pytest.mark.unit
def test_validate_config_invalid_stream():
    """Test validation fails with invalid stream value."""
    provider = OllamaProvider({})

    assert provider.validate_config({"stream": "true"}) is False
    assert provider.validate_config({"stream": 1}) is False


@pytest.mark.unit
def test_validate_config_invalid_temperature():
    """Test validation fails with invalid temperature."""
    provider = OllamaProvider({})

    assert provider.validate_config({"temperature": -0.1}) is False
    assert provider.validate_config({"temperature": 2.1}) is False
    assert provider.validate_config({"temperature": "0.7"}) is False


@pytest.mark.unit
def test_validate_config_valid_temperature_range():
    """Test validation succeeds with valid temperature range."""
    provider = OllamaProvider({})

    assert provider.validate_config({"temperature": 0.0}) is True
    assert provider.validate_config({"temperature": 1.0}) is True
    assert provider.validate_config({"temperature": 2.0}) is True


# ============================================================================
# Provider Initialization Tests
# ============================================================================


@pytest.mark.unit
def test_provider_initialization(valid_config):
    """Test provider initialization with valid config."""
    provider = OllamaProvider(valid_config)

    assert provider.config == valid_config
    assert provider.base_url == "http://localhost:11434"
    assert provider.model == "llama3.2"
    assert provider.timeout == 60
    assert provider.stream is True
    assert provider.temperature == 0.7


@pytest.mark.unit
def test_provider_initialization_defaults(minimal_config):
    """Test provider initialization with default values."""
    provider = OllamaProvider(minimal_config)

    assert provider.base_url == "http://localhost:11434"
    assert provider.model == "llama3.2"
    assert provider.timeout == 60
    assert provider.stream is True
    assert provider.temperature == 0.7


@pytest.mark.unit
def test_provider_initialization_strips_trailing_slash():
    """Test that base_url trailing slash is removed."""
    provider = OllamaProvider({"base_url": "http://localhost:11434/"})

    assert provider.base_url == "http://localhost:11434"


@pytest.mark.unit
def test_provider_name():
    """Test provider name property."""
    provider = OllamaProvider({})

    assert provider.name == "ollama"


# ============================================================================
# is_available Tests
# ============================================================================


@pytest.mark.unit
@patch('hai_sh.providers.ollama.requests.get')
def test_is_available_when_running(mock_get):
    """Test is_available returns True when Ollama is running."""
    provider = OllamaProvider({})

    # Mock successful API response
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    assert provider.is_available() is True
    mock_get.assert_called_once_with("http://localhost:11434/api/tags", timeout=5)


@pytest.mark.unit
@patch('hai_sh.providers.ollama.requests.get')
def test_is_available_when_not_running(mock_get):
    """Test is_available returns False when Ollama is not running."""
    provider = OllamaProvider({})

    # Mock connection error
    mock_get.side_effect = Exception("Connection refused")

    assert provider.is_available() is False


@pytest.mark.unit
@patch('hai_sh.providers.ollama.requests.get')
def test_is_available_with_custom_base_url(mock_get):
    """Test is_available uses custom base URL."""
    provider = OllamaProvider({"base_url": "http://192.168.1.100:11434"})

    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    provider.is_available()

    mock_get.assert_called_once_with("http://192.168.1.100:11434/api/tags", timeout=5)


# ============================================================================
# generate() Tests with Streaming
# ============================================================================


@pytest.mark.unit
@patch('hai_sh.providers.ollama.requests.post')
def test_generate_streaming_simple_prompt(mock_post, valid_config):
    """Test generate with streaming enabled."""
    provider = OllamaProvider(valid_config)

    # Mock streaming response
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.iter_lines = Mock(return_value=[
        b'{"response": "ls", "done": false}',
        b'{"response": " -la", "done": true}'
    ])
    mock_post.return_value = mock_response

    response = provider.generate("List files")

    assert response == "ls -la"
    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert call_args.kwargs['json']['model'] == 'llama3.2'
    assert call_args.kwargs['json']['stream'] is True


@pytest.mark.unit
@patch('hai_sh.providers.ollama.requests.post')
def test_generate_streaming_with_context(mock_post, valid_config):
    """Test generate with streaming and context."""
    provider = OllamaProvider(valid_config)

    context = {
        "cwd": "/home/user/project",
        "git": {"is_repo": True, "branch": "main", "has_changes": False},
        "env": {"user": "testuser", "shell": "/bin/bash"}
    }

    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.iter_lines = Mock(return_value=[
        b'{"response": "git status", "done": true}'
    ])
    mock_post.return_value = mock_response

    response = provider.generate("Check status", context=context)

    assert response == "git status"

    # Verify context was included in prompt
    call_args = mock_post.call_args
    prompt = call_args.kwargs['json']['prompt']
    assert "/home/user/project" in prompt
    assert "main" in prompt
    assert "testuser" in prompt


@pytest.mark.unit
@patch('hai_sh.providers.ollama.requests.post')
def test_generate_streaming_empty_lines(mock_post, valid_config):
    """Test generate handles empty lines in streaming response."""
    provider = OllamaProvider(valid_config)

    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.iter_lines = Mock(return_value=[
        b'{"response": "test", "done": false}',
        b'',  # Empty line
        b'{"response": " response", "done": true}'
    ])
    mock_post.return_value = mock_response

    response = provider.generate("test")

    assert response == "test response"


@pytest.mark.unit
@patch('hai_sh.providers.ollama.requests.post')
def test_generate_streaming_invalid_json(mock_post, valid_config):
    """Test generate handles invalid JSON in streaming response."""
    provider = OllamaProvider(valid_config)

    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.iter_lines = Mock(return_value=[
        b'{"response": "valid", "done": false}',
        b'invalid json',
        b'{"response": " response", "done": true}'
    ])
    mock_post.return_value = mock_response

    response = provider.generate("test")

    # Should skip invalid JSON and continue
    assert response == "valid response"


# ============================================================================
# generate() Tests without Streaming
# ============================================================================


@pytest.mark.unit
@patch('hai_sh.providers.ollama.requests.post')
def test_generate_non_streaming(mock_post, non_streaming_config):
    """Test generate with streaming disabled."""
    provider = OllamaProvider(non_streaming_config)

    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.json = Mock(return_value={"response": "echo hello"})
    mock_post.return_value = mock_response

    response = provider.generate("Say hello")

    assert response == "echo hello"
    call_args = mock_post.call_args
    assert call_args.kwargs['json']['stream'] is False


# ============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.unit
@patch('hai_sh.providers.ollama.requests.post')
def test_generate_connection_error(mock_post, valid_config):
    """Test generate handles connection errors."""
    import requests

    provider = OllamaProvider(valid_config)

    mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")

    with pytest.raises(RuntimeError, match="Cannot connect to Ollama"):
        provider.generate("test")


@pytest.mark.unit
@patch('hai_sh.providers.ollama.requests.post')
def test_generate_timeout_error(mock_post, valid_config):
    """Test generate handles timeout errors."""
    import requests

    provider = OllamaProvider(valid_config)

    mock_post.side_effect = requests.exceptions.Timeout("Timeout")

    with pytest.raises(RuntimeError, match="timed out"):
        provider.generate("test")


@pytest.mark.unit
@patch('hai_sh.providers.ollama.requests.post')
def test_generate_http_error(mock_post, valid_config):
    """Test generate handles HTTP errors."""
    import requests

    provider = OllamaProvider(valid_config)

    mock_response = Mock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")
    mock_post.return_value = mock_response

    with pytest.raises(RuntimeError, match="HTTP error"):
        provider.generate("test")


@pytest.mark.unit
@patch('hai_sh.providers.ollama.requests.post')
def test_generate_request_exception(mock_post, valid_config):
    """Test generate handles generic request exceptions."""
    import requests

    provider = OllamaProvider(valid_config)

    mock_post.side_effect = requests.exceptions.RequestException("Request failed")

    with pytest.raises(RuntimeError, match="request failed"):
        provider.generate("test")


@pytest.mark.unit
@patch('hai_sh.providers.ollama.requests.post')
def test_generate_unexpected_error(mock_post, valid_config):
    """Test generate handles unexpected errors."""
    provider = OllamaProvider(valid_config)

    mock_post.side_effect = Exception("Unexpected error")

    with pytest.raises(RuntimeError, match="Unexpected error"):
        provider.generate("test")


# ============================================================================
# Prompt Formatting Tests
# ============================================================================


@pytest.mark.unit
def test_format_prompt_no_context():
    """Test prompt formatting without context."""
    provider = OllamaProvider({})

    formatted = provider._format_prompt("test prompt", None)

    assert formatted == "test prompt"


@pytest.mark.unit
def test_format_prompt_with_cwd():
    """Test prompt formatting with current directory."""
    provider = OllamaProvider({})

    context = {"cwd": "/home/user/project"}
    formatted = provider._format_prompt("test", context)

    assert "Current directory: /home/user/project" in formatted
    assert "test" in formatted


@pytest.mark.unit
def test_format_prompt_with_git():
    """Test prompt formatting with git information."""
    provider = OllamaProvider({})

    context = {
        "git": {
            "is_repo": True,
            "branch": "feature-branch",
            "has_changes": True
        }
    }
    formatted = provider._format_prompt("test", context)

    assert "Git branch: feature-branch" in formatted
    assert "uncommitted changes" in formatted


@pytest.mark.unit
def test_format_prompt_with_git_no_changes():
    """Test prompt formatting with git but no changes."""
    provider = OllamaProvider({})

    context = {
        "git": {
            "is_repo": True,
            "branch": "main",
            "has_changes": False
        }
    }
    formatted = provider._format_prompt("test", context)

    assert "Git branch: main" in formatted
    assert "uncommitted changes" not in formatted


@pytest.mark.unit
def test_format_prompt_with_env():
    """Test prompt formatting with environment info."""
    provider = OllamaProvider({})

    context = {
        "env": {
            "user": "testuser",
            "shell": "/bin/bash"
        }
    }
    formatted = provider._format_prompt("test", context)

    assert "User: testuser" in formatted
    assert "Shell: /bin/bash" in formatted


@pytest.mark.unit
def test_format_prompt_complete():
    """Test prompt formatting with all context types."""
    provider = OllamaProvider({})

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
    formatted = provider._format_prompt("test prompt", context)

    assert "Current directory: /home/user/project" in formatted
    assert "Git branch: main" in formatted
    assert "User: testuser" in formatted
    assert "Shell: /bin/zsh" in formatted
    assert "test prompt" in formatted


@pytest.mark.unit
def test_format_prompt_git_not_repo():
    """Test prompt formatting when not in git repo."""
    provider = OllamaProvider({})

    context = {
        "git": {
            "is_repo": False
        }
    }
    formatted = provider._format_prompt("test", context)

    # Should not include git info when not in a repo
    assert "Git" not in formatted
    assert formatted == "test"
