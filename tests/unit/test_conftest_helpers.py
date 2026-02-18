"""
Tests for conftest.py helper functions.

Tests the provider availability check functions used by test fixtures
and skip decorators.
"""

from unittest.mock import patch, MagicMock

import pytest
import requests

from tests.conftest import is_ollama_model_available


class TestIsOllamaModelAvailable:
    """Tests for is_ollama_model_available() helper function."""

    @patch("tests.conftest.requests.post")
    def test_returns_true_when_model_exists(self, mock_post):
        """Model available on Ollama server returns True."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        assert is_ollama_model_available("llama3.2") is True
        mock_post.assert_called_once_with(
            "http://localhost:11434/api/show",
            json={"name": "llama3.2"},
            timeout=5,
        )

    @patch("tests.conftest.requests.post")
    def test_returns_false_when_model_not_found(self, mock_post):
        """Model not pulled on Ollama server returns False."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_post.return_value = mock_response

        assert is_ollama_model_available("llama3.2") is False

    @patch("tests.conftest.requests.post")
    def test_returns_false_on_connection_error(self, mock_post):
        """Connection error (server down) returns False."""
        mock_post.side_effect = requests.ConnectionError("Connection refused")

        assert is_ollama_model_available("llama3.2") is False

    @patch("tests.conftest.requests.post")
    def test_returns_false_on_timeout(self, mock_post):
        """Request timeout returns False."""
        mock_post.side_effect = requests.Timeout("Request timed out")

        assert is_ollama_model_available("llama3.2") is False

    @patch("tests.conftest.requests.post")
    def test_returns_false_on_os_error(self, mock_post):
        """OSError (network unreachable) returns False."""
        mock_post.side_effect = OSError("Network unreachable")

        assert is_ollama_model_available("llama3.2") is False

    @patch("tests.conftest.requests.post")
    def test_accepts_any_model_name(self, mock_post):
        """Function works with arbitrary model names."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        assert is_ollama_model_available("mistral") is True
        mock_post.assert_called_once_with(
            "http://localhost:11434/api/show",
            json={"name": "mistral"},
            timeout=5,
        )
