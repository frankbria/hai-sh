"""
Configuration file loading and parsing for hai-sh.

This module handles loading configuration from ~/.hai/config.yaml,
applying defaults, and validating settings.
"""

import os
import re
from pathlib import Path
from typing import Any, Optional, Union

import yaml

from hai_sh.init import get_config_path, init_hai_directory

try:
    from hai_sh.schema import HaiConfig, validate_config_dict

    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    HaiConfig = None  # type: ignore
    validate_config_dict = None  # type: ignore


# Default configuration values
DEFAULT_CONFIG = {
    "provider": "ollama",
    "provider_priority": None,  # Optional: list of providers to try in order
    "providers": {
        "openai": {
            "model": "gpt-4o-mini",
            "base_url": None,
        },
        "anthropic": {
            "model": "claude-sonnet-4-5",
        },
        "ollama": {
            "base_url": "http://localhost:11434",
            "model": "llama3.2",
        },
    },
    "context": {
        "include_history": True,
        "history_length": 10,
        "include_env_vars": True,
        "include_git_state": True,
    },
    "output": {
        "show_conversation": True,
        "show_reasoning": True,
        "use_colors": True,
    },
}


class ConfigError(Exception):
    """Base exception for configuration errors."""

    pass


class ConfigLoadError(ConfigError):
    """Exception raised when config file cannot be loaded."""

    pass


class ConfigValidationError(ConfigError):
    """Exception raised when config validation fails."""

    pass


def expand_env_vars(value: str) -> str:
    """
    Expand environment variables in a string.

    Supports both ${VAR} and $VAR syntax.
    Falls back to empty string if variable doesn't exist.

    Args:
        value: String potentially containing environment variables

    Returns:
        str: String with environment variables expanded

    Example:
        >>> os.environ['TEST_VAR'] = 'hello'
        >>> expand_env_vars('${TEST_VAR} world')
        'hello world'
        >>> expand_env_vars('$TEST_VAR world')
        'hello world'
    """
    if not isinstance(value, str):
        return value

    # Pattern matches ${VAR} or $VAR
    pattern = r'\$\{([^}]+)\}|\$([A-Za-z_][A-Za-z0-9_]*)'

    def replace_var(match):
        var_name = match.group(1) or match.group(2)
        return os.environ.get(var_name, "")

    return re.sub(pattern, replace_var, value)


def expand_env_vars_recursive(config: dict) -> dict:
    """
    Recursively expand environment variables in config dictionary.

    Args:
        config: Configuration dictionary

    Returns:
        dict: Configuration with environment variables expanded

    Example:
        >>> os.environ['API_KEY'] = 'secret'
        >>> cfg = {'openai': {'api_key': '${API_KEY}'}}
        >>> expand_env_vars_recursive(cfg)
        {'openai': {'api_key': 'secret'}}
    """
    result = {}
    for key, value in config.items():
        if isinstance(value, dict):
            result[key] = expand_env_vars_recursive(value)
        elif isinstance(value, str):
            result[key] = expand_env_vars(value)
        else:
            result[key] = value
    return result


def merge_configs(base: dict, override: dict) -> dict:
    """
    Deep merge two configuration dictionaries.

    The override dict takes precedence over base dict.
    Nested dictionaries are merged recursively.

    Args:
        base: Base configuration (defaults)
        override: Override configuration (user settings)

    Returns:
        dict: Merged configuration

    Example:
        >>> base = {'a': 1, 'b': {'c': 2}}
        >>> override = {'b': {'c': 3, 'd': 4}}
        >>> merge_configs(base, override)
        {'a': 1, 'b': {'c': 3, 'd': 4}}
    """
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursively merge nested dicts
            result[key] = merge_configs(result[key], value)
        else:
            # Override value
            result[key] = value

    return result


def load_config_file(config_path: Optional[Path] = None) -> dict:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to config file (default: ~/.hai/config.yaml)

    Returns:
        dict: Parsed configuration dictionary

    Raises:
        ConfigLoadError: If file cannot be read or parsed

    Example:
        >>> config = load_config_file()
        >>> print(config['provider'])
        'ollama'
    """
    if config_path is None:
        config_path = get_config_path()

    try:
        if not config_path.exists():
            # Initialize directory if it doesn't exist
            init_hai_directory()

            # Try again after initialization
            if not config_path.exists():
                raise ConfigLoadError(f"Config file not found: {config_path}")

        with open(config_path, "r") as f:
            content = f.read()

        # Parse YAML
        try:
            config = yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise ConfigLoadError(f"Invalid YAML syntax in {config_path}: {e}")

        if config is None:
            # Empty file
            return {}

        if not isinstance(config, dict):
            raise ConfigLoadError(
                f"Config file must contain a dictionary, got {type(config).__name__}"
            )

        return config

    except ConfigLoadError:
        raise
    except FileNotFoundError:
        raise ConfigLoadError(f"Config file not found: {config_path}")
    except PermissionError:
        raise ConfigLoadError(f"Permission denied reading config: {config_path}")
    except Exception as e:
        raise ConfigLoadError(f"Error loading config from {config_path}: {e}")


def validate_config(config: dict) -> list[str]:
    """
    Validate configuration and return list of warnings.

    Args:
        config: Configuration dictionary to validate

    Returns:
        list[str]: List of warning messages (empty if no issues)

    Example:
        >>> config = {'provider': 'openai'}
        >>> warnings = validate_config(config)
        >>> if warnings:
        ...     print("Warnings:", warnings)
    """
    warnings = []

    # Check provider is valid
    if "provider" in config:
        valid_providers = ["openai", "anthropic", "ollama", "local"]
        if config["provider"] not in valid_providers:
            warnings.append(
                f"Unknown provider '{config['provider']}'. "
                f"Valid providers: {', '.join(valid_providers)}"
            )

    # Check if provider has configuration
    if "provider" in config and "providers" in config:
        provider = config["provider"]
        if provider not in config["providers"]:
            warnings.append(
                f"Provider '{provider}' selected but no configuration found in 'providers' section"
            )

    # Check for API keys in OpenAI/Anthropic configs
    if "providers" in config:
        if "openai" in config["providers"]:
            if "api_key" not in config["providers"]["openai"]:
                warnings.append(
                    "OpenAI provider configured but 'api_key' not set. "
                    "Set OPENAI_API_KEY environment variable or add to config."
                )

        if "anthropic" in config["providers"]:
            if "api_key" not in config["providers"]["anthropic"]:
                warnings.append(
                    "Anthropic provider configured but 'api_key' not set. "
                    "Set ANTHROPIC_API_KEY environment variable or add to config."
                )

    return warnings


def load_config(
    config_path: Optional[Path] = None,
    use_defaults: bool = True,
    expand_vars: bool = True,
    use_pydantic: bool = True,
) -> Union[dict, "HaiConfig"]:
    """
    Load and parse configuration file with defaults.

    This is the main entry point for loading configuration.
    It handles loading the file, applying defaults, expanding
    environment variables, and validation.

    Args:
        config_path: Path to config file (default: ~/.hai/config.yaml)
        use_defaults: Whether to merge with default config (default: True)
        expand_vars: Whether to expand environment variables (default: True)
        use_pydantic: Whether to use Pydantic validation (default: True)

    Returns:
        Union[dict, HaiConfig]: Complete configuration with defaults applied
            - Returns HaiConfig instance if use_pydantic=True and Pydantic available
            - Returns dict otherwise

    Raises:
        ConfigLoadError: If config cannot be loaded or parsed
        ConfigValidationError: If Pydantic validation fails

    Example:
        >>> config = load_config()
        >>> print(f"Using provider: {config['provider']}")
        >>> print(f"Model: {config['model']}")

        >>> # With Pydantic validation
        >>> config = load_config(use_pydantic=True)
        >>> print(f"Using provider: {config.provider}")
        >>> print(f"Model: {config.model}")
    """
    try:
        # Load config file
        user_config = load_config_file(config_path)

    except ConfigLoadError:
        # If file doesn't exist or can't be read, use defaults
        if use_defaults:
            user_config = {}
        else:
            raise

    # Check for deprecated top-level model field
    if "model" in user_config:
        import warnings

        provider = user_config.get("provider", "ollama")
        warnings.warn(
            f"The top-level 'model' field in config.yaml is deprecated and unused. "
            f"Model selection is controlled by providers.{provider}.model instead. "
            f"Please remove the top-level 'model' field from your config.",
            DeprecationWarning,
            stacklevel=2,
        )
        # Remove it to prevent Pydantic validation errors
        del user_config["model"]

    # Merge with defaults
    if use_defaults:
        config = merge_configs(DEFAULT_CONFIG, user_config)
    else:
        config = user_config

    # Expand environment variables
    if expand_vars:
        config = expand_env_vars_recursive(config)

    # Use Pydantic validation if requested and available
    if use_pydantic and PYDANTIC_AVAILABLE:
        try:
            validated_config, warnings = validate_config_dict(config)
            # Store warnings in the config object
            if warnings:
                # For Pydantic model, we can't add arbitrary attributes
                # So we'll store warnings in a special way
                object.__setattr__(validated_config, "_warnings", warnings)
            return validated_config
        except ValueError as e:
            raise ConfigValidationError(str(e))

    # Fallback to basic validation
    warnings = validate_config(config)
    if warnings:
        # Store warnings in config for caller to handle
        config["_warnings"] = warnings

    return config


def get_provider_config(config: dict, provider: Optional[str] = None) -> dict:
    """
    Get configuration for a specific provider.

    Args:
        config: Full configuration dictionary
        provider: Provider name (default: use config['provider'])

    Returns:
        dict: Provider-specific configuration

    Raises:
        ConfigError: If provider not found in config

    Example:
        >>> config = load_config()
        >>> ollama_config = get_provider_config(config, 'ollama')
        >>> print(ollama_config['base_url'])
        'http://localhost:11434'
    """
    if provider is None:
        provider = config.get("provider")

    if not provider:
        raise ConfigError("No provider specified in configuration")

    if "providers" not in config:
        raise ConfigError("No 'providers' section in configuration")

    if provider not in config["providers"]:
        raise ConfigError(f"Provider '{provider}' not found in configuration")

    return config["providers"][provider]


def get_config_value(config: dict, key_path: str, default: Any = None) -> Any:
    """
    Get a configuration value using dot notation.

    Args:
        config: Configuration dictionary
        key_path: Dot-separated key path (e.g., "context.include_history")
        default: Default value if key not found

    Returns:
        Any: Configuration value or default

    Example:
        >>> config = load_config()
        >>> include_history = get_config_value(config, "context.include_history")
        >>> base_url = get_config_value(config, "providers.ollama.base_url")
    """
    keys = key_path.split(".")
    value = config

    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default

    return value


def get_provider_priority_list(config: dict) -> list[str]:
    """
    Get the ordered list of providers to try.

    Uses provider_priority if set, otherwise creates a single-item list
    from the provider field.

    Args:
        config: Configuration dictionary

    Returns:
        list[str]: Ordered list of provider names to try

    Example:
        >>> config = {"provider_priority": ["ollama", "openai"]}
        >>> get_provider_priority_list(config)
        ['ollama', 'openai']
        >>> config = {"provider": "anthropic"}
        >>> get_provider_priority_list(config)
        ['anthropic']
    """
    provider_priority = config.get("provider_priority")
    if provider_priority:
        return list(provider_priority)
    return [config.get("provider", "ollama")]


def check_provider_availability(
    provider_name: str,
    provider_config: dict
) -> tuple[bool, Optional[Any], Optional[str]]:
    """
    Check if a provider is available and return details.

    Attempts to instantiate the provider and check its availability.

    Args:
        provider_name: Name of the provider (e.g., "ollama", "openai")
        provider_config: Provider-specific configuration dictionary

    Returns:
        tuple: (success, provider_instance, error_message)
            - success: True if provider is available
            - provider_instance: The instantiated provider if successful, None otherwise
            - error_message: Description of failure if unsuccessful, None otherwise

    Example:
        >>> success, provider, error = check_provider_availability(
        ...     "ollama",
        ...     {"base_url": "http://localhost:11434", "model": "llama3.2"}
        ... )
        >>> if success:
        ...     response = provider.generate("hello")
    """
    # Import here to avoid circular imports
    from hai_sh.providers import get_provider

    try:
        # Attempt to instantiate the provider
        provider = get_provider(provider_name, provider_config)

        # Check availability using detailed method if available
        if hasattr(provider, 'check_availability'):
            available, error = provider.check_availability()
            if available:
                return True, provider, None
            else:
                return False, None, error or f"{provider_name} is not available"
        else:
            # Fall back to is_available()
            if provider.is_available():
                return True, provider, None
            else:
                return False, None, f"{provider_name} is not available"

    except KeyError as e:
        return False, None, f"Provider '{provider_name}' not registered: {e}"
    except ValueError as e:
        return False, None, f"Invalid configuration for {provider_name}: {e}"
    except RuntimeError as e:
        return False, None, f"{provider_name} runtime error: {e}"
    except ConnectionError as e:
        return False, None, f"Cannot connect to {provider_name}: {e}"
    except TimeoutError as e:
        return False, None, f"Timeout connecting to {provider_name}: {e}"
    except Exception as e:
        return False, None, f"{provider_name} error: {e}"


class ProviderFallbackResult:
    """
    Result of provider fallback selection.

    Contains the selected provider and information about failed attempts.
    """

    def __init__(
        self,
        provider: Any,
        provider_name: str,
        failed_providers: list[tuple[str, str]]
    ):
        """
        Initialize fallback result.

        Args:
            provider: The successfully selected provider instance
            provider_name: Name of the selected provider
            failed_providers: List of (provider_name, error_message) for failed attempts
        """
        self.provider = provider
        self.provider_name = provider_name
        self.failed_providers = failed_providers

    @property
    def had_fallback(self) -> bool:
        """Whether fallback to a non-primary provider occurred."""
        return len(self.failed_providers) > 0


def get_available_provider(
    config: dict,
    debug_mode: bool = False,
    on_fallback: Optional[callable] = None
) -> ProviderFallbackResult:
    """
    Get the first available provider from the priority chain.

    Iterates through the provider priority list, attempting to initialize
    and validate each provider until one succeeds. Provides detailed
    feedback about fallback attempts.

    Args:
        config: Full configuration dictionary
        debug_mode: If True, print debug information about provider attempts
        on_fallback: Optional callback function called when fallback occurs.
                     Receives (failed_provider_name, error_message, next_provider_name)

    Returns:
        ProviderFallbackResult: Contains the selected provider and fallback info

    Raises:
        ConfigError: If no providers are available after trying all in the chain

    Example:
        >>> config = load_config()
        >>> result = get_available_provider(config)
        >>> if result.had_fallback:
        ...     print(f"Using {result.provider_name} after fallback")
        >>> response = result.provider.generate("hello")

    Example with callback:
        >>> def handle_fallback(failed, error, next_provider):
        ...     print(f"Provider {failed} failed: {error}")
        >>> result = get_available_provider(config, on_fallback=handle_fallback)
    """
    import sys

    provider_list = get_provider_priority_list(config)
    providers_config = config.get("providers", {})
    failed_providers = []

    for i, provider_name in enumerate(provider_list):
        provider_config = providers_config.get(provider_name, {})

        if debug_mode:
            print(f"Debug: Trying provider '{provider_name}'...", file=sys.stderr)

        success, provider, error = check_provider_availability(
            provider_name, provider_config
        )

        if success:
            if debug_mode:
                print(f"Debug: Using provider '{provider_name}'", file=sys.stderr)

            return ProviderFallbackResult(
                provider=provider,
                provider_name=provider_name,
                failed_providers=failed_providers
            )
        else:
            failed_providers.append((provider_name, error))

            # Call fallback callback if provided
            if on_fallback and i < len(provider_list) - 1:
                next_provider = provider_list[i + 1]
                on_fallback(provider_name, error, next_provider)

            if debug_mode:
                print(
                    f"Debug: Provider '{provider_name}' unavailable: {error}",
                    file=sys.stderr
                )

    # All providers failed
    error_details = "\n".join(
        f"  - {name}: {error}" for name, error in failed_providers
    )
    raise ConfigError(
        f"No providers available. Tried {len(provider_list)} provider(s):\n{error_details}\n"
        f"Check your configuration and ensure at least one provider is properly configured."
    )
