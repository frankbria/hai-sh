"""
Provider manager for hai-sh TUI.

This module handles runtime provider switching and management
for the interactive TUI mode.
"""

from typing import Callable, Dict, List, Optional, Any

from hai_sh.schema import HaiConfig
from hai_sh.providers.base import BaseLLMProvider


class ProviderManager:
    """
    Manager for LLM provider switching at runtime.

    Handles listing available providers, switching between them,
    and notifying callbacks when the provider changes.
    """

    # Valid provider names
    VALID_PROVIDERS = ["openai", "anthropic", "ollama", "local"]

    def __init__(self, config: HaiConfig):
        """
        Initialize ProviderManager.

        Args:
            config: HaiConfig instance with provider configurations
        """
        self._config = config
        self._current_provider_name = config.provider
        self._provider_instance: Optional[BaseLLMProvider] = None
        self._callbacks: List[Callable[[str], None]] = []

    @property
    def current_provider_name(self) -> str:
        """Get the current provider name."""
        return self._current_provider_name

    def list_available_providers(self) -> List[Dict[str, Any]]:
        """
        List all available providers from configuration.

        Returns:
            List of dictionaries with provider info (name, model, status)
        """
        providers = []

        # Check OpenAI
        if self._config.providers.openai is not None:
            providers.append({
                "name": "openai",
                "model": self._config.providers.openai.model,
                "has_api_key": self._config.providers.openai.api_key is not None,
            })

        # Check Anthropic
        if self._config.providers.anthropic is not None:
            providers.append({
                "name": "anthropic",
                "model": self._config.providers.anthropic.model,
                "has_api_key": self._config.providers.anthropic.api_key is not None,
            })

        # Check Ollama
        if self._config.providers.ollama is not None:
            providers.append({
                "name": "ollama",
                "model": self._config.providers.ollama.model,
                "base_url": self._config.providers.ollama.base_url,
            })

        # Check Local
        if self._config.providers.local is not None:
            providers.append({
                "name": "local",
                "model": self._config.providers.local.model_path,
                "context_size": self._config.providers.local.context_size,
            })

        return providers

    def get_current_provider(self) -> Dict[str, Any]:
        """
        Get information about the current provider.

        Returns:
            Dictionary with current provider info
        """
        providers = self.list_available_providers()

        for provider in providers:
            if provider["name"] == self._current_provider_name:
                return provider

        # Return basic info if not found in list
        return {
            "name": self._current_provider_name,
            "model": "unknown",
        }

    def switch_provider(self, provider_name: str) -> bool:
        """
        Switch to a different provider.

        Args:
            provider_name: Name of the provider to switch to

        Returns:
            True if switch was successful, False otherwise
        """
        # Validate provider name
        if provider_name not in self.VALID_PROVIDERS:
            return False

        # Check if provider is configured
        if not self.is_provider_available(provider_name):
            return False

        # Update current provider
        self._current_provider_name = provider_name

        # Reset provider instance to force re-creation
        self._provider_instance = None

        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(provider_name)
            except Exception:
                # Don't let callback errors break the switch
                pass

        return True

    def is_provider_available(self, provider_name: str) -> bool:
        """
        Check if a provider is available (configured).

        Args:
            provider_name: Name of the provider to check

        Returns:
            True if provider is configured and available
        """
        if provider_name not in self.VALID_PROVIDERS:
            return False

        provider_config = getattr(self._config.providers, provider_name, None)
        return provider_config is not None

    def on_switch(self, callback: Callable[[str], None]) -> None:
        """
        Register a callback to be called when provider switches.

        Args:
            callback: Function to call with new provider name
        """
        self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[str], None]) -> None:
        """
        Remove a previously registered callback.

        Args:
            callback: Callback function to remove
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def get_provider_instance(self) -> Optional[BaseLLMProvider]:
        """
        Get the current provider instance.

        Returns:
            BaseLLMProvider instance or None if not created
        """
        return self._provider_instance

    def set_provider_instance(self, instance: BaseLLMProvider) -> None:
        """
        Set the provider instance.

        Args:
            instance: BaseLLMProvider instance
        """
        self._provider_instance = instance

    def get_provider_config(self, provider_name: str) -> Optional[Any]:
        """
        Get configuration for a specific provider.

        Args:
            provider_name: Name of the provider

        Returns:
            Provider configuration or None
        """
        return getattr(self._config.providers, provider_name, None)
