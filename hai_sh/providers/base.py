"""
Base abstract class for LLM providers.

This module defines the interface that all LLM providers must implement.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional


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
    def generate(self, prompt: str, context: Optional[dict[str, Any]] = None) -> str:
        """
        Generate a response from the LLM.

        This is the main method that sends a prompt to the LLM and
        returns the generated response.

        Args:
            prompt: The input prompt/query to send to the LLM
            context: Optional context dictionary with additional information
                    (e.g., current directory, git state, environment vars)

        Returns:
            str: The generated response from the LLM

        Raises:
            RuntimeError: If the LLM is not available or request fails

        Example:
            >>> provider = get_provider("openai", config)
            >>> response = provider.generate("List files in current directory")
            >>> print(response)
            'ls -la'
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
