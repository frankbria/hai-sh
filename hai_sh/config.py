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
    "model": "llama3.2",
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
