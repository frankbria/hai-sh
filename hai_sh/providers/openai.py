"""
OpenAI provider implementation.

This module provides integration with OpenAI's API using the official SDK.
"""

from typing import Any, Optional

from hai_sh.providers.base import BaseLLMProvider

try:
    from openai import OpenAI, OpenAIError, APIError, RateLimitError, AuthenticationError
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI API provider implementation.

    Supports GPT-4, GPT-3.5, o1 series, and other OpenAI models via the official API.
    Automatically uses the correct API parameters (max_tokens vs max_completion_tokens)
    based on the model being used.

    Example:
        >>> config = {
        ...     "api_key": "sk-...",
        ...     "model": "gpt-4o-mini",
        ...     "timeout": 30
        ... }
        >>> provider = OpenAIProvider(config)
        >>> response = provider.generate("List files")
        >>> print(response)
    """

    def __init__(self, config: dict[str, Any]):
        """
        Initialize OpenAI provider.

        Args:
            config: Configuration dictionary with:
                - api_key: OpenAI API key (required)
                - model: Model name (default: "gpt-4o-mini")
                - timeout: Request timeout in seconds (default: 30)
                - max_tokens: Maximum tokens in response (default: 1000)
                  Note: Automatically mapped to max_completion_tokens for o1 series models
                - temperature: Sampling temperature 0-2 (default: 0.7)

        Raises:
            ValueError: If configuration is invalid
            RuntimeError: If openai package is not installed
        """
        if not OPENAI_AVAILABLE:
            raise RuntimeError(
                "OpenAI provider requires the 'openai' package. "
                "Install it with: pip install openai"
            )

        super().__init__(config)

        # Initialize OpenAI client
        self.client = OpenAI(
            api_key=self.config["api_key"],
            timeout=self.config.get("timeout", 30)
        )

        # Store model configuration
        self.model = self.config.get("model", "gpt-4o-mini")
        self.max_tokens = self.config.get("max_tokens", 1000)
        self.temperature = self.config.get("temperature", 0.7)

    def _uses_max_completion_tokens(self) -> bool:
        """
        Determine if the current model requires max_completion_tokens parameter.

        OpenAI's newer models (o1, gpt-5, gpt-4.1 series) require max_completion_tokens
        instead of the deprecated max_tokens parameter.

        Returns:
            bool: True if model requires max_completion_tokens, False otherwise
        """
        # o1 series models require max_completion_tokens
        if self.model.startswith("o1-") or self.model.startswith("o1"):
            return True

        # GPT-5 series models require max_completion_tokens
        if self.model.startswith("gpt-5"):
            return True

        # GPT-4.1 series models require max_completion_tokens
        if self.model.startswith("gpt-4.1"):
            return True

        # All other models use max_tokens
        return False

    def generate(
        self,
        prompt: str,
        context: Optional[dict[str, Any]] = None,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Generate a response using OpenAI's API.

        Args:
            prompt: The input prompt/query
            context: Optional context dictionary (e.g., cwd, git state)
            system_prompt: Optional system prompt with JSON format instructions

        Returns:
            str: Generated response from OpenAI

        Raises:
            RuntimeError: If API request fails
        """
        try:
            # Build messages
            messages = []

            # Build system message
            # Priority: system_prompt > context > default
            if system_prompt and system_prompt.strip():
                # Use provided system prompt as base
                system_content = system_prompt
                # Append context if provided
                if context:
                    context_info = self._format_context(context, include_base=False)
                    if context_info:
                        system_content = f"{system_prompt}\n\n{context_info}"
                messages.append({
                    "role": "system",
                    "content": system_content
                })
            elif context:
                # Fall back to context-based system message
                system_content = self._format_context(context)
                messages.append({
                    "role": "system",
                    "content": system_content
                })
            else:
                # Fall back to default
                messages.append({
                    "role": "system",
                    "content": "You are a helpful terminal assistant."
                })

            # Add user prompt
            messages.append({
                "role": "user",
                "content": prompt
            })

            # Build API request parameters
            # Newer models (o1, gpt-5 series) have different parameter requirements
            api_params = {
                "model": self.model,
                "messages": messages
            }

            # Some models (o1, gpt-5) don't support temperature parameter
            # Only add temperature if the model supports it
            if not (self.model.startswith("o1") or self.model.startswith("gpt-5")):
                api_params["temperature"] = self.temperature

            # Use appropriate token limit parameter based on model
            if self._uses_max_completion_tokens():
                api_params["max_completion_tokens"] = self.max_tokens
            else:
                api_params["max_tokens"] = self.max_tokens

            # Make API request
            response = self.client.chat.completions.create(**api_params)

            # Extract and return response
            return response.choices[0].message.content.strip()

        except AuthenticationError as e:
            raise RuntimeError(f"OpenAI authentication failed: {e}")
        except RateLimitError as e:
            raise RuntimeError(f"OpenAI rate limit exceeded: {e}")
        except APIError as e:
            raise RuntimeError(f"OpenAI API error: {e}")
        except OpenAIError as e:
            raise RuntimeError(f"OpenAI error: {e}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error calling OpenAI: {e}")

    def validate_config(self, config: dict[str, Any]) -> bool:
        """
        Validate OpenAI provider configuration.

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

        # API key should start with 'sk-'
        if not api_key.startswith("sk-"):
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
            if temperature < 0 or temperature > 2:
                return False

        return True

    def is_available(self) -> bool:
        """
        Check if OpenAI provider is available.

        Returns:
            bool: True if openai package is installed and API key is configured
        """
        if not OPENAI_AVAILABLE:
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
