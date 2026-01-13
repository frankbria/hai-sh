"""
Tests for provider manager module.

This module tests runtime provider switching and management.
"""

import pytest
from unittest.mock import MagicMock, patch


# --- Import Tests ---


@pytest.mark.unit
def test_provider_manager_importable():
    """Test ProviderManager can be imported."""
    from hai_sh.provider_manager import ProviderManager

    assert ProviderManager is not None


# --- Creation Tests ---


@pytest.mark.unit
def test_provider_manager_creation():
    """Test ProviderManager can be created with config."""
    from hai_sh.provider_manager import ProviderManager
    from hai_sh.schema import HaiConfig

    config = HaiConfig()
    manager = ProviderManager(config)

    assert manager is not None


@pytest.mark.unit
def test_provider_manager_default_provider():
    """Test ProviderManager uses config's default provider."""
    from hai_sh.provider_manager import ProviderManager
    from hai_sh.schema import HaiConfig

    config = HaiConfig(provider="ollama")
    manager = ProviderManager(config)

    assert manager.current_provider_name == "ollama"


# --- List Providers Tests ---


@pytest.mark.unit
def test_list_available_providers():
    """Test listing available providers from config."""
    from hai_sh.provider_manager import ProviderManager
    from hai_sh.schema import HaiConfig

    config = HaiConfig()
    manager = ProviderManager(config)

    providers = manager.list_available_providers()

    # Should include default providers from config
    assert isinstance(providers, list)
    assert len(providers) > 0


@pytest.mark.unit
def test_list_available_providers_includes_configured():
    """Test list includes only configured providers."""
    from hai_sh.provider_manager import ProviderManager
    from hai_sh.schema import HaiConfig

    config = HaiConfig(provider="ollama")
    manager = ProviderManager(config)

    providers = manager.list_available_providers()

    # Should include ollama since it's configured by default
    provider_names = [p["name"] for p in providers]
    assert "ollama" in provider_names


@pytest.mark.unit
def test_provider_info_has_expected_fields():
    """Test provider info has expected fields."""
    from hai_sh.provider_manager import ProviderManager
    from hai_sh.schema import HaiConfig

    config = HaiConfig()
    manager = ProviderManager(config)

    providers = manager.list_available_providers()

    for provider in providers:
        assert "name" in provider
        assert "model" in provider


# --- Get Current Provider Tests ---


@pytest.mark.unit
def test_get_current_provider():
    """Test getting current provider info."""
    from hai_sh.provider_manager import ProviderManager
    from hai_sh.schema import HaiConfig

    config = HaiConfig(provider="ollama")
    manager = ProviderManager(config)

    current = manager.get_current_provider()

    assert current is not None
    assert current["name"] == "ollama"


@pytest.mark.unit
def test_get_current_provider_includes_model():
    """Test current provider includes model info."""
    from hai_sh.provider_manager import ProviderManager
    from hai_sh.schema import HaiConfig

    config = HaiConfig(provider="ollama")
    manager = ProviderManager(config)

    current = manager.get_current_provider()

    assert "model" in current


# --- Switch Provider Tests ---


@pytest.mark.unit
def test_switch_provider_success():
    """Test switching to a valid provider."""
    from hai_sh.provider_manager import ProviderManager
    from hai_sh.schema import HaiConfig

    config = HaiConfig()
    manager = ProviderManager(config)

    # Ollama is configured by default
    success = manager.switch_provider("ollama")

    assert success is True
    assert manager.current_provider_name == "ollama"


@pytest.mark.unit
def test_switch_provider_invalid():
    """Test switching to invalid provider fails."""
    from hai_sh.provider_manager import ProviderManager
    from hai_sh.schema import HaiConfig

    config = HaiConfig()
    manager = ProviderManager(config)

    success = manager.switch_provider("invalid_provider")

    assert success is False


@pytest.mark.unit
def test_switch_provider_not_configured():
    """Test switching to unconfigured provider fails gracefully."""
    from hai_sh.provider_manager import ProviderManager
    from hai_sh.schema import HaiConfig

    config = HaiConfig(provider="ollama")
    manager = ProviderManager(config)

    # Local provider needs explicit config
    success = manager.switch_provider("local")

    # Should fail since local isn't configured
    assert success is False


@pytest.mark.unit
def test_switch_provider_updates_current():
    """Test switching provider updates current provider."""
    from hai_sh.provider_manager import ProviderManager
    from hai_sh.schema import HaiConfig

    config = HaiConfig(provider="ollama")
    manager = ProviderManager(config)

    assert manager.current_provider_name == "ollama"

    # Switch to openai (configured by default)
    manager.switch_provider("openai")

    assert manager.current_provider_name == "openai"


# --- Provider Status Tests ---


@pytest.mark.unit
def test_is_provider_available():
    """Test checking if provider is available."""
    from hai_sh.provider_manager import ProviderManager
    from hai_sh.schema import HaiConfig

    config = HaiConfig()
    manager = ProviderManager(config)

    # Ollama should be configured
    available = manager.is_provider_available("ollama")

    # Returns bool
    assert isinstance(available, bool)


@pytest.mark.unit
def test_is_provider_available_unconfigured():
    """Test availability check for unconfigured provider."""
    from hai_sh.provider_manager import ProviderManager
    from hai_sh.schema import HaiConfig

    config = HaiConfig()
    manager = ProviderManager(config)

    # Local is not configured by default
    available = manager.is_provider_available("local")

    assert available is False


# --- Callback Tests ---


@pytest.mark.unit
def test_on_switch_callback():
    """Test callback is called when provider switches."""
    from hai_sh.provider_manager import ProviderManager
    from hai_sh.schema import HaiConfig

    config = HaiConfig()
    manager = ProviderManager(config)

    callback_data = {"called": False, "provider": None}

    def callback(provider_name):
        callback_data["called"] = True
        callback_data["provider"] = provider_name

    manager.on_switch(callback)
    manager.switch_provider("ollama")

    assert callback_data["called"] is True
    assert callback_data["provider"] == "ollama"


@pytest.mark.unit
def test_multiple_callbacks():
    """Test multiple callbacks can be registered."""
    from hai_sh.provider_manager import ProviderManager
    from hai_sh.schema import HaiConfig

    config = HaiConfig()
    manager = ProviderManager(config)

    results = []

    manager.on_switch(lambda p: results.append(f"cb1:{p}"))
    manager.on_switch(lambda p: results.append(f"cb2:{p}"))

    manager.switch_provider("ollama")

    assert len(results) == 2
    assert "cb1:ollama" in results
    assert "cb2:ollama" in results


# --- Provider Instance Tests ---


@pytest.mark.unit
def test_get_provider_instance():
    """Test getting the actual provider instance."""
    from hai_sh.provider_manager import ProviderManager
    from hai_sh.schema import HaiConfig
    from hai_sh.providers.base import BaseLLMProvider

    config = HaiConfig(provider="ollama")
    manager = ProviderManager(config)

    instance = manager.get_provider_instance()

    # Should return a provider instance or None
    assert instance is None or isinstance(instance, BaseLLMProvider)


# --- Error Handling Tests ---


@pytest.mark.unit
def test_switch_preserves_previous_on_failure():
    """Test failed switch preserves previous provider."""
    from hai_sh.provider_manager import ProviderManager
    from hai_sh.schema import HaiConfig

    config = HaiConfig(provider="ollama")
    manager = ProviderManager(config)

    original = manager.current_provider_name

    # Try to switch to invalid provider
    manager.switch_provider("nonexistent")

    # Should still be on original
    assert manager.current_provider_name == original
