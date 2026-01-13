"""
Tests for empty response handling from LLM providers.

These tests verify that the system properly handles edge cases where
the LLM provider returns empty or null responses, which can happen due
to API issues, network problems, or model errors.
"""

import pytest
from unittest.mock import Mock

from hai_sh.prompt import parse_response, generate_with_retry


# ============================================================================
# Empty Response Parsing Tests
# ============================================================================


@pytest.mark.unit
def test_parse_response_empty_string():
    """Test that parse_response raises ValueError for empty string."""
    with pytest.raises(ValueError, match="LLM returned empty response"):
        parse_response("")


@pytest.mark.unit
def test_parse_response_whitespace_only():
    """Test that parse_response raises ValueError for whitespace-only response."""
    with pytest.raises(ValueError, match="LLM returned empty response"):
        parse_response("   ")


@pytest.mark.unit
def test_parse_response_tabs_and_newlines():
    """Test that parse_response raises ValueError for tabs and newlines only."""
    with pytest.raises(ValueError, match="LLM returned empty response"):
        parse_response("\t\n  \n\t")


@pytest.mark.unit
def test_parse_response_none():
    """Test that parse_response handles None gracefully."""
    with pytest.raises((ValueError, AttributeError)):
        parse_response(None)


# ============================================================================
# Empty Response Retry Logic Tests
# ============================================================================


@pytest.mark.unit
def test_generate_with_retry_empty_response():
    """Test that generate_with_retry retries on empty responses."""
    provider = Mock()
    provider.generate.side_effect = [
        "",  # First attempt: empty
        "",  # Second attempt: still empty
        '{"explanation": "List files", "command": "ls", "confidence": 90}'  # Third: success
    ]

    result = generate_with_retry(provider, "list files", max_retries=3)

    assert result["command"] == "ls"
    assert provider.generate.call_count == 3


@pytest.mark.unit
def test_generate_with_retry_all_empty_responses():
    """Test that generate_with_retry fails after all retries return empty."""
    provider = Mock()
    provider.generate.return_value = ""

    with pytest.raises(ValueError, match="Failed to generate valid response"):
        generate_with_retry(provider, "test", max_retries=3)

    assert provider.generate.call_count == 3


@pytest.mark.unit
def test_generate_with_retry_whitespace_responses():
    """Test that generate_with_retry treats whitespace-only as invalid."""
    provider = Mock()
    provider.generate.side_effect = [
        "   ",  # Whitespace
        "\t\n",  # Tabs and newlines
        '{"explanation": "Test", "command": "echo test", "confidence": 90}'
    ]

    result = generate_with_retry(provider, "test", max_retries=3)

    assert result["command"] == "echo test"
    assert provider.generate.call_count == 3


@pytest.mark.unit
def test_generate_with_retry_none_response():
    """Test that generate_with_retry handles None responses."""
    provider = Mock()
    provider.generate.side_effect = [
        None,  # None response  
        '{"explanation": "Test", "command": "ls", "confidence": 90}'
    ]

    # parse_response will fail on None with AttributeError, generate_with_retry should retry
    result = generate_with_retry(provider, "test", max_retries=2)
    
    # Should succeed on second attempt
    assert result["command"] == "ls"
    assert provider.generate.call_count == 2


# ============================================================================
# Integration with Provider Tests  
# ============================================================================


@pytest.mark.unit  
def test_openai_provider_empty_content_handling():
    """Test that OpenAI provider handles empty message content."""
    from hai_sh.providers.openai import OpenAIProvider, OPENAI_AVAILABLE
    from unittest.mock import patch, Mock
    
    if not OPENAI_AVAILABLE:
        pytest.skip("openai package not installed")
    
    config = {"api_key": "sk-test"}
    
    with patch('hai_sh.providers.openai.OpenAI') as mock_openai:
        provider = OpenAIProvider(config)
        
        # Mock response with empty content
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = ""
        
        with patch.object(provider.client.chat.completions, 'create', return_value=mock_response):
            result = provider.generate("test")
            
            # Provider returns empty string
            assert result == ""
            
            # This should be caught by parse_response in generate_with_retry
            with pytest.raises(ValueError, match="LLM returned empty response"):
                parse_response(result)


@pytest.mark.unit
def test_openai_provider_none_content_handling():
    """Test that OpenAI provider handles None message content."""
    from hai_sh.providers.openai import OpenAIProvider, OPENAI_AVAILABLE
    from unittest.mock import patch, Mock
    
    if not OPENAI_AVAILABLE:
        pytest.skip("openai package not installed")
    
    config = {"api_key": "sk-test"}
    
    with patch('hai_sh.providers.openai.OpenAI') as mock_openai:
        provider = OpenAIProvider(config)
        
        # Mock response with None content
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = None
        
        with patch.object(provider.client.chat.completions, 'create', return_value=mock_response):
            # Provider should raise RuntimeError for None content
            with pytest.raises(RuntimeError, match="OpenAI returned None content"):
                provider.generate("test")
