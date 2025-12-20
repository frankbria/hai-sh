"""
Provider registry and factory for managing LLM providers.

This module provides a registry system for discovering and instantiating
LLM providers.
"""

from typing import Any, Optional, Type

from hai_sh.providers.base import BaseLLMProvider


class ProviderRegistry:
    """
    Registry for LLM providers.

    Manages registration and discovery of available LLM providers.
    Providers can be registered and retrieved by name.

    Example:
        >>> registry = ProviderRegistry()
        >>> registry.register("openai", OpenAIProvider)
        >>> provider_class = registry.get("openai")
        >>> provider = provider_class(config)
    """

    def __init__(self):
        """Initialize an empty provider registry."""
        self._providers: dict[str, Type[BaseLLMProvider]] = {}

    def register(
        self, name: str, provider_class: Type[BaseLLMProvider]
    ) -> None:
        """
        Register a provider class.

        Args:
            name: Provider name (e.g., "openai", "anthropic")
            provider_class: Provider class that inherits from BaseLLMProvider

        Raises:
            ValueError: If provider class doesn't inherit from BaseLLMProvider
            ValueError: If provider name is already registered

        Example:
            >>> registry = ProviderRegistry()
            >>> registry.register("openai", OpenAIProvider)
        """
        if not issubclass(provider_class, BaseLLMProvider):
            raise ValueError(
                f"{provider_class.__name__} must inherit from BaseLLMProvider"
            )

        if name in self._providers:
            raise ValueError(f"Provider '{name}' is already registered")

        self._providers[name] = provider_class

    def get(self, name: str) -> Type[BaseLLMProvider]:
        """
        Get a provider class by name.

        Args:
            name: Provider name

        Returns:
            Type[BaseLLMProvider]: Provider class

        Raises:
            KeyError: If provider not found

        Example:
            >>> registry = ProviderRegistry()
            >>> provider_class = registry.get("openai")
        """
        if name not in self._providers:
            raise KeyError(
                f"Provider '{name}' not found. "
                f"Available providers: {', '.join(self.list())}"
            )

        return self._providers[name]

    def list(self) -> list[str]:
        """
        List all registered provider names.

        Returns:
            list[str]: List of provider names

        Example:
            >>> registry = ProviderRegistry()
            >>> print(registry.list())
            ['openai', 'anthropic', 'ollama']
        """
        return list(self._providers.keys())

    def is_registered(self, name: str) -> bool:
        """
        Check if a provider is registered.

        Args:
            name: Provider name

        Returns:
            bool: True if provider is registered

        Example:
            >>> registry = ProviderRegistry()
            >>> registry.is_registered("openai")
            True
        """
        return name in self._providers

    def unregister(self, name: str) -> None:
        """
        Unregister a provider.

        Args:
            name: Provider name to unregister

        Raises:
            KeyError: If provider not found

        Example:
            >>> registry = ProviderRegistry()
            >>> registry.unregister("openai")
        """
        if name not in self._providers:
            raise KeyError(f"Provider '{name}' not registered")

        del self._providers[name]


# Global provider registry
_global_registry = ProviderRegistry()


def register_provider(
    name: str, provider_class: Type[BaseLLMProvider]
) -> None:
    """
    Register a provider in the global registry.

    Args:
        name: Provider name
        provider_class: Provider class

    Example:
        >>> from hai_sh.providers import register_provider
        >>> register_provider("openai", OpenAIProvider)
    """
    _global_registry.register(name, provider_class)


def get_provider(
    name: str, config: Optional[dict[str, Any]] = None
) -> BaseLLMProvider:
    """
    Get and instantiate a provider from the global registry.

    Args:
        name: Provider name
        config: Optional provider configuration

    Returns:
        BaseLLMProvider: Instantiated provider

    Raises:
        KeyError: If provider not found
        ValueError: If configuration is invalid

    Example:
        >>> from hai_sh.providers import get_provider
        >>> provider = get_provider("openai", {"api_key": "sk-test"})
        >>> response = provider.generate("help")
    """
    provider_class = _global_registry.get(name)

    if config is None:
        config = {}

    return provider_class(config)


def list_providers() -> list[str]:
    """
    List all registered providers in the global registry.

    Returns:
        list[str]: List of provider names

    Example:
        >>> from hai_sh.providers import list_providers
        >>> print(list_providers())
        ['openai', 'anthropic', 'ollama']
    """
    return _global_registry.list()


def get_registry() -> ProviderRegistry:
    """
    Get the global provider registry.

    Returns:
        ProviderRegistry: Global registry instance

    Example:
        >>> from hai_sh.providers import get_registry
        >>> registry = get_registry()
        >>> print(registry.list())
    """
    return _global_registry
