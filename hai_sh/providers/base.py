"""
Base abstract class for LLM providers.

This module defines the interface that all LLM providers must implement.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional


class ProviderError(Exception):
    """Base exception for provider-related errors."""

    def __init__(self, message: str, provider_name: str = None):
        self.provider_name = provider_name
        super().__init__(message)


class ProviderUnavailableError(ProviderError):
    """
    Raised when a provider service is not reachable.

    This indicates a transient failure that may warrant fallback to another provider.
    Examples: Ollama not running, API server unreachable, network timeout.
    """
    pass


class ProviderAuthError(ProviderError):
    """
    Raised when authentication fails for a provider.

    This indicates an API key issue that requires user intervention.
    Examples: Invalid API key, expired credentials, missing API key.
    """
    pass


class ProviderRateLimitError(ProviderError):
    """
    Raised when a provider's rate limit is exceeded.

    This indicates the provider is temporarily unavailable due to rate limiting.
    Fallback to another provider may be appropriate.
    """

    def __init__(self, message: str, provider_name: str = None, retry_after: int = None):
        self.retry_after = retry_after
        super().__init__(message, provider_name)


class ProviderConfigError(ProviderError):
    """
    Raised when provider configuration is invalid.

    This indicates a configuration problem that requires user intervention.
    Examples: Missing required fields, invalid values.
    """
    pass


class BaseLLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    All LLM providers (OpenAI, Anthropic, Ollama, local) must inherit
    from this class and implement its abstract methods.

    Example:
        >>> class MyProvider(BaseLLMProvider):
        ...     def generate(self, prompt, context=None):
        ...         return "Generated response"
        ...     def validate_config(self, config):
        ...         return True
        ...     def is_available(self):
        ...         return True
    """

    def __init__(self, config: dict[str, Any]):
        """
        Initialize the provider with configuration.

        Args:
            config: Provider-specific configuration dictionary

        Raises:
            ValueError: If configuration is invalid
        """
        if not self.validate_config(config):
            raise ValueError(f"Invalid configuration for {self.__class__.__name__}")
        self.config = config

    @abstractmethod
    def generate(
        self,
        prompt: str,
        context: Optional[dict[str, Any]] = None,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Generate a response from the LLM.

        This is the main method that sends a prompt to the LLM and
        returns the generated response.

        Args:
            prompt: The input prompt/query to send to the LLM
            context: Optional context dictionary with additional information
                    (e.g., current directory, git state, environment vars)
            system_prompt: Optional system prompt containing instructions for
                          the LLM (e.g., JSON format requirements, role definition).
                          This should be used as a system message, not a user message,
                          to ensure the LLM properly follows format instructions.

        Returns:
            str: The generated response from the LLM

        Raises:
            RuntimeError: If the LLM is not available or request fails

        Example:
            >>> provider = get_provider("openai", config)
            >>> system = "Respond in JSON format with 'command' key."
            >>> response = provider.generate(
            ...     "List files in current directory",
            ...     system_prompt=system
            ... )
            >>> print(response)
            '{"command": "ls -la"}'
        """
        pass

    @abstractmethod
    def validate_config(self, config: dict[str, Any]) -> bool:
        """
        Validate provider configuration.

        Checks that the configuration contains all required fields
        and that values are valid.

        Args:
            config: Configuration dictionary to validate

        Returns:
            bool: True if configuration is valid, False otherwise

        Example:
            >>> config = {"api_key": "sk-test", "model": "gpt-4"}
            >>> provider = OpenAIProvider(config)
            >>> provider.validate_config(config)
            True
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the provider is available and ready to use.

        This method should check:
        - Required dependencies are installed
        - API keys/credentials are configured
        - Service is reachable (for remote APIs)

        For fallback support, this method should:
        - Return False for transient failures (service down, network issues)
          that warrant trying another provider
        - Return True only when the provider is fully ready to generate

        Note: For detailed error information, use check_availability() instead.

        Returns:
            bool: True if provider is available, False otherwise

        Example:
            >>> provider = get_provider("ollama", config)
            >>> if provider.is_available():
            ...     response = provider.generate("help")
            ... else:
            ...     print("Ollama is not running")
        """
        pass

    def check_availability(self) -> tuple[bool, Optional[str]]:
        """
        Check provider availability with detailed error information.

        This method provides more detailed feedback than is_available(),
        useful for fallback logic that needs to report why a provider
        is unavailable.

        Returns:
            tuple[bool, Optional[str]]: (is_available, error_message)
                - is_available: True if provider is ready to use
                - error_message: None if available, otherwise a description
                  of why the provider is unavailable

        Example:
            >>> provider = get_provider("ollama", config)
            >>> available, error = provider.check_availability()
            >>> if not available:
            ...     print(f"Provider unavailable: {error}")
        """
        try:
            if self.is_available():
                return True, None
            else:
                return False, "Provider is not available"
        except Exception as e:
            return False, str(e)

    @property
    def name(self) -> str:
        """
        Get the provider name.

        Returns:
            str: Provider name (e.g., "openai", "anthropic", "ollama")

        Example:
            >>> provider = get_provider("openai", config)
            >>> print(provider.name)
            'openai'
        """
        return self.__class__.__name__.lower().replace("provider", "")

    def __repr__(self) -> str:
        """String representation of the provider."""
        return f"{self.__class__.__name__}(name='{self.name}')"
