"""
Tests for LLM provider abstraction layer.
"""

from typing import Any, Optional

import pytest

from hai_sh.providers import (
    BaseLLMProvider,
    ProviderRegistry,
    get_provider,
    list_providers,
    register_provider,
)
from hai_sh.providers.registry import get_registry


# Test implementation of BaseLLMProvider
class MockProvider(BaseLLMProvider):
    """Mock provider for testing."""

    def generate(self, prompt: str, context: Optional[dict[str, Any]] = None) -> str:
        """Mock generate method."""
        if context:
            return f"Mock response for '{prompt}' with context"
        return f"Mock response for '{prompt}'"

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Mock validate method."""
        # Require 'api_key' in config
        return "api_key" in config

    def is_available(self) -> bool:
        """Mock is_available method."""
        return True


class BrokenProvider(BaseLLMProvider):
    """Provider with invalid config for testing."""

    def generate(self, prompt: str, context: Optional[dict[str, Any]] = None) -> str:
        return "broken"

    def validate_config(self, config: dict[str, Any]) -> bool:
        # Always returns False
        return False

    def is_available(self) -> bool:
        return False


class UnavailableProvider(BaseLLMProvider):
    """Provider that is not available."""

    def generate(self, prompt: str, context: Optional[dict[str, Any]] = None) -> str:
        raise RuntimeError("Provider not available")

    def validate_config(self, config: dict[str, Any]) -> bool:
        return True

    def is_available(self) -> bool:
        return False


# ============================================================================
# BaseLLMProvider Tests
# ============================================================================


@pytest.mark.unit
def test_base_provider_abstract():
    """Test that BaseLLMProvider cannot be instantiated directly."""
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        BaseLLMProvider({"api_key": "test"})


@pytest.mark.unit
def test_mock_provider_valid_config():
    """Test MockProvider with valid configuration."""
    config = {"api_key": "test_key"}
    provider = MockProvider(config)

    assert provider.config == config
    assert provider.is_available() is True
    assert provider.validate_config(config) is True


@pytest.mark.unit
def test_mock_provider_invalid_config():
    """Test MockProvider with invalid configuration."""
    config = {"model": "test"}  # Missing api_key

    with pytest.raises(ValueError, match="Invalid configuration"):
        MockProvider(config)


@pytest.mark.unit
def test_provider_generate():
    """Test provider generate method."""
    provider = MockProvider({"api_key": "test"})

    response = provider.generate("test prompt")
    assert response == "Mock response for 'test prompt'"


@pytest.mark.unit
def test_provider_generate_with_context():
    """Test provider generate with context."""
    provider = MockProvider({"api_key": "test"})

    response = provider.generate("test prompt", {"cwd": "/home/user"})
    assert "with context" in response


@pytest.mark.unit
def test_provider_name():
    """Test provider name property."""
    provider = MockProvider({"api_key": "test"})

    assert provider.name == "mock"


@pytest.mark.unit
def test_provider_repr():
    """Test provider string representation."""
    provider = MockProvider({"api_key": "test"})

    repr_str = repr(provider)
    assert "MockProvider" in repr_str
    assert "mock" in repr_str


# ============================================================================
# ProviderRegistry Tests
# ============================================================================


@pytest.mark.unit
def test_registry_create():
    """Test creating a provider registry."""
    registry = ProviderRegistry()

    assert registry.list() == []


@pytest.mark.unit
def test_registry_register():
    """Test registering a provider."""
    registry = ProviderRegistry()
    registry.register("mock", MockProvider)

    assert "mock" in registry.list()
    assert registry.is_registered("mock") is True


@pytest.mark.unit
def test_registry_register_duplicate():
    """Test registering duplicate provider raises error."""
    registry = ProviderRegistry()
    registry.register("mock", MockProvider)

    with pytest.raises(ValueError, match="already registered"):
        registry.register("mock", MockProvider)


@pytest.mark.unit
def test_registry_register_invalid_class():
    """Test registering non-provider class raises error."""
    registry = ProviderRegistry()

    class NotAProvider:
        pass

    with pytest.raises(ValueError, match="must inherit from BaseLLMProvider"):
        registry.register("invalid", NotAProvider)


@pytest.mark.unit
def test_registry_get():
    """Test getting a provider class."""
    registry = ProviderRegistry()
    registry.register("mock", MockProvider)

    provider_class = registry.get("mock")
    assert provider_class == MockProvider


@pytest.mark.unit
def test_registry_get_not_found():
    """Test getting non-existent provider raises error."""
    registry = ProviderRegistry()

    with pytest.raises(KeyError, match="Provider 'nonexistent' not found"):
        registry.get("nonexistent")


@pytest.mark.unit
def test_registry_list():
    """Test listing registered providers."""
    registry = ProviderRegistry()
    registry.register("mock1", MockProvider)
    registry.register("mock2", MockProvider)

    providers = registry.list()
    assert len(providers) == 2
    assert "mock1" in providers
    assert "mock2" in providers


@pytest.mark.unit
def test_registry_is_registered():
    """Test checking if provider is registered."""
    registry = ProviderRegistry()
    registry.register("mock", MockProvider)

    assert registry.is_registered("mock") is True
    assert registry.is_registered("nonexistent") is False


@pytest.mark.unit
def test_registry_unregister():
    """Test unregistering a provider."""
    registry = ProviderRegistry()
    registry.register("mock", MockProvider)

    assert registry.is_registered("mock") is True

    registry.unregister("mock")

    assert registry.is_registered("mock") is False


@pytest.mark.unit
def test_registry_unregister_not_found():
    """Test unregistering non-existent provider raises error."""
    registry = ProviderRegistry()

    with pytest.raises(KeyError, match="not registered"):
        registry.unregister("nonexistent")


# ============================================================================
# Global Registry Tests
# ============================================================================


@pytest.mark.unit
def test_register_provider_global():
    """Test registering provider in global registry."""
    # Clean up first
    try:
        get_registry().unregister("test_mock")
    except KeyError:
        pass

    register_provider("test_mock", MockProvider)

    assert "test_mock" in list_providers()

    # Cleanup
    get_registry().unregister("test_mock")


@pytest.mark.unit
def test_list_providers_global():
    """Test listing providers from global registry."""
    # Clean up first
    try:
        get_registry().unregister("test_mock")
    except KeyError:
        pass

    register_provider("test_mock", MockProvider)

    providers = list_providers()
    assert "test_mock" in providers

    # Cleanup
    get_registry().unregister("test_mock")


@pytest.mark.unit
def test_get_provider_global():
    """Test getting provider from global registry."""
    # Clean up first
    try:
        get_registry().unregister("test_mock")
    except KeyError:
        pass

    register_provider("test_mock", MockProvider)

    provider = get_provider("test_mock", {"api_key": "test"})
    assert isinstance(provider, MockProvider)
    assert provider.is_available() is True

    # Cleanup
    get_registry().unregister("test_mock")


@pytest.mark.unit
def test_get_provider_without_config():
    """Test getting provider without config."""
    # Clean up first
    try:
        get_registry().unregister("test_broken")
    except KeyError:
        pass

    register_provider("test_broken", BrokenProvider)

    # Should fail because config is invalid (empty)
    with pytest.raises(ValueError, match="Invalid configuration"):
        get_provider("test_broken")

    # Cleanup
    get_registry().unregister("test_broken")


@pytest.mark.unit
def test_get_provider_not_found():
    """Test getting non-existent provider raises error."""
    with pytest.raises(KeyError, match="not found"):
        get_provider("nonexistent_provider")


@pytest.mark.unit
def test_get_registry():
    """Test getting global registry instance."""
    registry1 = get_registry()
    registry2 = get_registry()

    # Should be same instance
    assert registry1 is registry2


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.unit
def test_provider_lifecycle():
    """Test complete provider lifecycle."""
    # Clean up first
    try:
        get_registry().unregister("lifecycle")
    except KeyError:
        pass

    # Register
    register_provider("lifecycle", MockProvider)
    assert "lifecycle" in list_providers()

    # Get and use
    provider = get_provider("lifecycle", {"api_key": "test"})
    assert provider.is_available() is True

    response = provider.generate("test")
    assert "Mock response" in response

    # Unregister
    get_registry().unregister("lifecycle")
    assert "lifecycle" not in list_providers()


@pytest.mark.unit
def test_multiple_providers():
    """Test registering and using multiple providers."""
    # Clean up first
    for name in ["multi1", "multi2", "multi3"]:
        try:
            get_registry().unregister(name)
        except KeyError:
            pass

    # Register multiple
    register_provider("multi1", MockProvider)
    register_provider("multi2", MockProvider)
    register_provider("multi3", UnavailableProvider)

    providers = list_providers()
    assert "multi1" in providers
    assert "multi2" in providers
    assert "multi3" in providers

    # Use them
    p1 = get_provider("multi1", {"api_key": "test"})
    p2 = get_provider("multi2", {"api_key": "test"})
    p3 = get_provider("multi3", {"api_key": "test"})

    assert p1.is_available() is True
    assert p2.is_available() is True
    assert p3.is_available() is False

    # Cleanup
    for name in ["multi1", "multi2", "multi3"]:
        get_registry().unregister(name)
