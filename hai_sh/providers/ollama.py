"""
Ollama provider implementation.

This module provides integration with Ollama for local LLM execution.
"""

from typing import Any, Optional
import json

from hai_sh.providers.base import BaseLLMProvider

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class OllamaProvider(BaseLLMProvider):
    """
    Ollama local model provider implementation.

    Supports local model execution via Ollama's REST API.
    Ollama must be running on the configured host.

    Example:
        >>> config = {
        ...     "base_url": "http://localhost:11434",
        ...     "model": "llama3.2",
        ...     "timeout": 60
        ... }
        >>> provider = OllamaProvider(config)
        >>> response = provider.generate("List files")
        >>> print(response)
    """

    def __init__(self, config: dict[str, Any]):
        """
        Initialize Ollama provider.

        Args:
            config: Configuration dictionary with:
                - base_url: Ollama API URL (default: "http://localhost:11434")
                - model: Model name (default: "llama3.2")
                - timeout: Request timeout in seconds (default: 60)
                - stream: Enable streaming (default: True)
                - temperature: Sampling temperature (default: 0.7)

        Raises:
            ValueError: If configuration is invalid
            RuntimeError: If requests package is not installed
        """
        if not REQUESTS_AVAILABLE:
            raise RuntimeError(
                "Ollama provider requires the 'requests' package. "
                "Install it with: pip install requests"
            )

        super().__init__(config)

        # Store configuration
        self.base_url = self.config.get("base_url", "http://localhost:11434").rstrip("/")
        self.model = self.config.get("model", "llama3.2")
        self.timeout = self.config.get("timeout", 60)
        self.stream = self.config.get("stream", True)
        self.temperature = self.config.get("temperature", 0.7)

    def generate(
        self,
        prompt: str,
        context: Optional[dict[str, Any]] = None,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Generate a response using Ollama's API.

        Args:
            prompt: The input prompt/query
            context: Optional context dictionary (e.g., cwd, git state)
            system_prompt: Optional system prompt with JSON format instructions

        Returns:
            str: Generated response from Ollama

        Raises:
            RuntimeError: If Ollama is not running or request fails
        """
        try:
            # Build the full prompt with system prompt and context
            full_prompt = self._format_prompt(prompt, context, system_prompt)

            # Prepare API request
            url = f"{self.base_url}/api/generate"
            payload = {
                "model": self.model,
                "prompt": full_prompt,
                "stream": self.stream,
                "options": {
                    "temperature": self.temperature
                }
            }

            # Make API request
            response = requests.post(
                url,
                json=payload,
                timeout=self.timeout,
                stream=self.stream
            )

            # Check for HTTP errors
            response.raise_for_status()

            # Handle streaming vs non-streaming responses
            if self.stream:
                return self._handle_streaming_response(response)
            else:
                return self._handle_non_streaming_response(response)

        except requests.exceptions.ConnectionError as e:
            raise RuntimeError(
                f"Cannot connect to Ollama at {self.base_url}. "
                f"Is Ollama running? Error: {e}"
            )
        except requests.exceptions.Timeout as e:
            raise RuntimeError(f"Ollama request timed out after {self.timeout}s: {e}")
        except requests.exceptions.HTTPError as e:
            raise RuntimeError(f"Ollama HTTP error: {e}")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Ollama request failed: {e}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error calling Ollama: {e}")

    def validate_config(self, config: dict[str, Any]) -> bool:
        """
        Validate Ollama provider configuration.

        Args:
            config: Configuration dictionary to validate

        Returns:
            bool: True if configuration is valid
        """
        # Model is not strictly required (has default), but if provided must be non-empty
        if "model" in config:
            model = config["model"]
            if not isinstance(model, str) or not model.strip():
                return False

        # Validate base_url if provided
        if "base_url" in config:
            base_url = config["base_url"]
            if not isinstance(base_url, str) or not base_url.strip():
                return False
            # Should start with http:// or https://
            if not base_url.startswith(("http://", "https://")):
                return False

        # Validate timeout if provided
        if "timeout" in config:
            timeout = config["timeout"]
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                return False

        # Validate stream if provided
        if "stream" in config:
            stream = config["stream"]
            if not isinstance(stream, bool):
                return False

        # Validate temperature if provided
        if "temperature" in config:
            temperature = config["temperature"]
            if not isinstance(temperature, (int, float)):
                return False
            if temperature < 0 or temperature > 2:
                return False

        return True

    def is_available(self) -> bool:
        """
        Check if Ollama provider is available.

        Tests connection to Ollama API and checks if the model is available.

        Returns:
            bool: True if Ollama is running and accessible
        """
        if not REQUESTS_AVAILABLE:
            return False

        try:
            # Try to ping the Ollama API
            url = f"{self.base_url}/api/tags"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return True
        except Exception:
            return False

    def _format_prompt(
        self,
        prompt: str,
        context: Optional[dict[str, Any]] = None,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Format prompt with optional system prompt and context.

        Args:
            prompt: User prompt
            context: Optional context dictionary
            system_prompt: Optional system prompt with format instructions

        Returns:
            str: Formatted prompt with system prompt and context
        """
        parts = []

        # Add system prompt first if provided
        if system_prompt and system_prompt.strip():
            parts.append(system_prompt)

        # Build context info if provided
        if context:
            context_parts = []

            if "cwd" in context:
                context_parts.append(f"Current directory: {context['cwd']}")

            if "git" in context and context["git"].get("is_repo"):
                git_info = context["git"]
                context_parts.append(f"Git branch: {git_info.get('branch', 'unknown')}")
                if git_info.get("has_changes"):
                    context_parts.append("Git status: uncommitted changes")

            if "env" in context:
                env_info = context["env"]
                if "user" in env_info:
                    context_parts.append(f"User: {env_info['user']}")
                if "shell" in env_info:
                    context_parts.append(f"Shell: {env_info['shell']}")

            if context_parts:
                parts.extend(context_parts)

        # Add user prompt last
        parts.append(prompt)

        return "\n\n".join(parts)

    def _handle_streaming_response(self, response: requests.Response) -> str:
        """
        Handle streaming response from Ollama.

        Args:
            response: Streaming HTTP response

        Returns:
            str: Complete response text
        """
        full_response = []

        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line)
                    if "response" in data:
                        full_response.append(data["response"])

                    # Check if done
                    if data.get("done", False):
                        break
                except json.JSONDecodeError:
                    continue

        return "".join(full_response).strip()

    def _handle_non_streaming_response(self, response: requests.Response) -> str:
        """
        Handle non-streaming response from Ollama.

        Args:
            response: HTTP response

        Returns:
            str: Response text
        """
        data = response.json()
        return data.get("response", "").strip()
