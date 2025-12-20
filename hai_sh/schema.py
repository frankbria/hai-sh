"""
Pydantic schema models for hai-sh configuration validation.

This module defines the structure and validation rules for configuration files.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class OpenAIProviderConfig(BaseModel):
    """OpenAI provider configuration."""

    api_key: Optional[str] = Field(
        None,
        description="OpenAI API key (or use OPENAI_API_KEY env var)",
    )
    model: str = Field(
        default="gpt-4o-mini",
        description="OpenAI model to use",
    )
    base_url: Optional[str] = Field(
        None,
        description="Custom API endpoint (optional)",
    )

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        """Validate OpenAI model name."""
        valid_models = [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-4",
            "gpt-3.5-turbo",
        ]
        if v not in valid_models:
            # Just warn, don't fail - new models may be added
            pass
        return v


class AnthropicProviderConfig(BaseModel):
    """Anthropic provider configuration."""

    api_key: Optional[str] = Field(
        None,
        description="Anthropic API key (or use ANTHROPIC_API_KEY env var)",
    )
    model: str = Field(
        default="claude-sonnet-4-5",
        description="Anthropic model to use",
    )

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        """Validate Anthropic model name."""
        valid_prefixes = ["claude-", "claude-3-", "claude-sonnet", "claude-opus"]
        if not any(v.startswith(prefix) for prefix in valid_prefixes):
            # Just warn, don't fail
            pass
        return v


class OllamaProviderConfig(BaseModel):
    """Ollama provider configuration."""

    base_url: str = Field(
        default="http://localhost:11434",
        description="Ollama API endpoint",
    )
    model: str = Field(
        default="llama3.2",
        description="Ollama model to use",
    )

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Validate base URL format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("base_url must start with http:// or https://")
        return v


class LocalProviderConfig(BaseModel):
    """Local model provider configuration."""

    model_path: str = Field(
        description="Path to local model file",
    )
    context_size: int = Field(
        default=4096,
        description="Context window size",
        ge=512,  # Minimum 512 tokens
        le=128000,  # Maximum 128k tokens
    )


class ProvidersConfig(BaseModel):
    """Configuration for all LLM providers."""

    openai: Optional[OpenAIProviderConfig] = Field(
        default_factory=OpenAIProviderConfig,
        description="OpenAI configuration",
    )
    anthropic: Optional[AnthropicProviderConfig] = Field(
        default_factory=AnthropicProviderConfig,
        description="Anthropic configuration",
    )
    ollama: Optional[OllamaProviderConfig] = Field(
        default_factory=OllamaProviderConfig,
        description="Ollama configuration",
    )
    local: Optional[LocalProviderConfig] = Field(
        None,
        description="Local model configuration",
    )


class ContextConfig(BaseModel):
    """Context collection configuration."""

    include_history: bool = Field(
        default=True,
        description="Include command history in context",
    )
    history_length: int = Field(
        default=10,
        description="Number of recent commands to include",
        ge=0,
        le=100,
    )
    include_env_vars: bool = Field(
        default=True,
        description="Include environment variables",
    )
    include_git_state: bool = Field(
        default=True,
        description="Include git repository state",
    )


class OutputConfig(BaseModel):
    """Output formatting configuration."""

    show_conversation: bool = Field(
        default=True,
        description="Show LLM conversation/reasoning",
    )
    show_reasoning: bool = Field(
        default=True,
        description="Show LLM reasoning process",
    )
    use_colors: bool = Field(
        default=True,
        description="Use ANSI colors in output",
    )


class HaiConfig(BaseModel):
    """Main hai-sh configuration schema."""

    provider: Literal["openai", "anthropic", "ollama", "local"] = Field(
        default="ollama",
        description="Default LLM provider to use",
    )
    model: str = Field(
        default="llama3.2",
        description="Default model name",
    )
    providers: ProvidersConfig = Field(
        default_factory=ProvidersConfig,
        description="Provider-specific configurations",
    )
    context: ContextConfig = Field(
        default_factory=ContextConfig,
        description="Context collection settings",
    )
    output: OutputConfig = Field(
        default_factory=OutputConfig,
        description="Output formatting settings",
    )

    @field_validator("provider")
    @classmethod
    def validate_provider_exists(cls, v: str, info) -> str:
        """Validate that selected provider has configuration."""
        # Note: This validator runs before providers field is set,
        # so we can't check it here. Will be validated in post-validation.
        return v

    def model_post_init(self, __context) -> None:
        """Post-initialization validation."""
        # Check that selected provider has configuration
        provider_config = getattr(self.providers, self.provider, None)
        if provider_config is None:
            raise ValueError(
                f"Provider '{self.provider}' is selected but has no configuration"
            )

    class Config:
        """Pydantic configuration."""

        extra = "forbid"  # Don't allow extra fields
        validate_assignment = True  # Validate on attribute assignment


def validate_config_dict(config_dict: dict) -> tuple[HaiConfig, list[str]]:
    """
    Validate configuration dictionary and return validated config with warnings.

    Args:
        config_dict: Raw configuration dictionary

    Returns:
        tuple: (validated_config, warnings)
            - validated_config: Validated HaiConfig instance
            - warnings: List of warning messages

    Raises:
        ValueError: If config validation fails

    Example:
        >>> config_dict = {"provider": "ollama"}
        >>> config, warnings = validate_config_dict(config_dict)
        >>> print(config.provider)
        'ollama'
    """
    warnings = []

    try:
        # Validate with Pydantic
        validated_config = HaiConfig(**config_dict)

        # Check for missing API keys
        if validated_config.provider == "openai":
            if not validated_config.providers.openai.api_key:
                warnings.append(
                    "OpenAI provider selected but 'api_key' not set. "
                    "Set OPENAI_API_KEY environment variable or add to config."
                )

        if validated_config.provider == "anthropic":
            if not validated_config.providers.anthropic.api_key:
                warnings.append(
                    "Anthropic provider selected but 'api_key' not set. "
                    "Set ANTHROPIC_API_KEY environment variable or add to config."
                )

        if validated_config.provider == "local":
            if not validated_config.providers.local:
                warnings.append(
                    "Local provider selected but no local provider configuration found."
                )

        return validated_config, warnings

    except Exception as e:
        raise ValueError(f"Configuration validation failed: {e}")
