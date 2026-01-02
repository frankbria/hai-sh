"""
Anthropic provider implementation.

This module provides integration with Anthropic's API using the official SDK.
"""

from typing import Any, Optional

from hai_sh.providers.base import BaseLLMProvider

try:
    from anthropic import Anthropic, APIError, AuthenticationError, RateLimitError
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


class AnthropicProvider(BaseLLMProvider):
    """
    Anthropic API provider implementation.

    Supports Claude models (Opus, Sonnet, Haiku) via the official API.

    Example:
        >>> config = {
        ...     "api_key": "sk-ant-...",
        ...     "model": "claude-sonnet-4-5",
        ...     "timeout": 30
        ... }
        >>> provider = AnthropicProvider(config)
        >>> response = provider.generate("List files")
        >>> print(response)
    """

    def __init__(self, config: dict[str, Any]):
        """
        Initialize Anthropic provider.

        Args:
            config: Configuration dictionary with:
                - api_key: Anthropic API key (required)
                - model: Model name (default: "claude-sonnet-4-5")
                - timeout: Request timeout in seconds (default: 30)
                - max_tokens: Maximum tokens in response (default: 1000)
                - temperature: Sampling temperature 0-1 (default: 0.7)

        Raises:
            ValueError: If configuration is invalid
            RuntimeError: If anthropic package is not installed
        """
        if not ANTHROPIC_AVAILABLE:
            raise RuntimeError(
                "Anthropic provider requires the 'anthropic' package. "
                "Install it with: pip install anthropic"
            )

        super().__init__(config)

        # Initialize Anthropic client
        self.client = Anthropic(
            api_key=self.config["api_key"],
            timeout=self.config.get("timeout", 30)
        )

        # Store model configuration
        self.model = self.config.get("model", "claude-sonnet-4-5")
        self.max_tokens = self.config.get("max_tokens", 1000)
        self.temperature = self.config.get("temperature", 0.7)

    def generate(
        self,
        prompt: str,
        context: Optional[dict[str, Any]] = None,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Generate a response using Anthropic's API.

        Args:
            prompt: The input prompt/query
            context: Optional context dictionary (e.g., cwd, git state)
            system_prompt: Optional system prompt with JSON format instructions

        Returns:
            str: Generated response from Anthropic

        Raises:
            RuntimeError: If API request fails
        """
        try:
            # Build system message
            # Priority: system_prompt > context > default
            if system_prompt and system_prompt.strip():
                # Use provided system prompt as base
                system_message = system_prompt
                # Append context if provided
                if context:
                    context_info = self._format_context(context, include_base=False)
                    if context_info:
                        system_message = f"{system_prompt}\n\n{context_info}"
            elif context:
                # Fall back to context-based system message
                system_message = self._format_context(context)
            else:
                # Fall back to default
                system_message = "You are a helpful terminal assistant."

            # Make API request using Messages API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_message,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # Extract and return response
            # Anthropic API returns a list of content blocks
            return response.content[0].text.strip()

        except AuthenticationError as e:
            raise RuntimeError(f"Anthropic authentication failed: {e}")
        except RateLimitError as e:
            raise RuntimeError(f"Anthropic rate limit exceeded: {e}")
        except APIError as e:
            raise RuntimeError(f"Anthropic API error: {e}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error calling Anthropic: {e}")

    def validate_config(self, config: dict[str, Any]) -> bool:
        """
        Validate Anthropic provider configuration.

        Args:
            config: Configuration dictionary to validate

        Returns:
            bool: True if configuration is valid
        """
        # API key is required
        if "api_key" not in config:
            return False

        api_key = config["api_key"]

        # API key must be a non-empty string
        if not isinstance(api_key, str) or not api_key.strip():
            return False

        # API key should start with 'sk-ant-'
        if not api_key.startswith("sk-ant-"):
            return False

        # Validate optional fields
        if "timeout" in config:
            timeout = config["timeout"]
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                return False

        if "max_tokens" in config:
            max_tokens = config["max_tokens"]
            if not isinstance(max_tokens, int) or max_tokens <= 0:
                return False

        if "temperature" in config:
            temperature = config["temperature"]
            if not isinstance(temperature, (int, float)):
                return False
            if temperature < 0 or temperature > 1:
                return False

        return True

    def is_available(self) -> bool:
        """
        Check if Anthropic provider is available.

        Returns:
            bool: True if anthropic package is installed and API key is configured
        """
        if not ANTHROPIC_AVAILABLE:
            return False

        # Check if API key is configured
        return "api_key" in self.config and bool(self.config["api_key"])

    def _format_context(self, context: dict[str, Any], include_base: bool = True) -> str:
        """
        Format context dictionary into a system message.

        Args:
            context: Context dictionary with cwd, git, env info
            include_base: Whether to include base "helpful assistant" message

        Returns:
            str: Formatted system message
        """
        parts = []

        if include_base:
            parts.append("You are a helpful terminal assistant.")

        if "cwd" in context:
            parts.append(f"Current directory: {context['cwd']}")

        if "git" in context and context["git"].get("is_repo"):
            git_info = context["git"]
            parts.append(f"Git branch: {git_info.get('branch', 'unknown')}")
            if git_info.get("has_changes"):
                parts.append("Git status: uncommitted changes")

        if "env" in context:
            env_info = context["env"]
            if "user" in env_info:
                parts.append(f"User: {env_info['user']}")
            if "shell" in env_info:
                parts.append(f"Shell: {env_info['shell']}")

        return "\n".join(parts)
