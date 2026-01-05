"""
Pydantic schema models for hai-sh configuration validation.

This module defines the structure and validation rules for configuration files.
"""

from typing import List, Literal, Optional

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


class ExecutionConfig(BaseModel):
    """Command execution configuration."""

    auto_execute: bool = Field(
        default=True,
        description="Automatically execute commands above confidence threshold",
    )
    auto_execute_threshold: int = Field(
        default=85,
        description="Minimum confidence (0-100) for auto-execution",
        ge=0,
        le=100,
    )
    show_explanation: Literal["collapsed", "expanded", "hidden"] = Field(
        default="collapsed",
        description="How to display LLM explanation: collapsed (default), expanded, or hidden",
    )
    require_confirmation: bool = Field(
        default=False,
        description="Always require confirmation regardless of confidence (overrides auto_execute)",
    )

    @field_validator("auto_execute_threshold")
    @classmethod
    def validate_threshold(cls, v: int) -> int:
        """Validate threshold is reasonable."""
        if v < 50:
            # Warn about very low threshold but allow it
            pass
        return v


class HaiConfig(BaseModel):
    """Main hai-sh configuration schema."""

    provider: Literal["openai", "anthropic", "ollama", "local"] = Field(
        default="ollama",
        description="Default LLM provider to use",
    )
    provider_priority: Optional[List[Literal["openai", "anthropic", "ollama", "local"]]] = Field(
        default=None,
        description="Ordered list of providers to try for fallback support. "
                    "If set, overrides the 'provider' field. Providers are tried "
                    "in order until one is available.",
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
    execution: ExecutionConfig = Field(
        default_factory=ExecutionConfig,
        description="Command execution settings",
    )

    @field_validator("provider")
    @classmethod
    def validate_provider_exists(cls, v: str, info) -> str:
        """Validate that selected provider has configuration."""
        # Note: This validator runs before providers field is set,
        # so we can't check it here. Will be validated in post-validation.
        return v

    @field_validator("provider_priority")
    @classmethod
    def validate_provider_priority(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate provider_priority list."""
        if v is None:
            return v
        if len(v) == 0:
            raise ValueError("provider_priority list cannot be empty")
        # Check for duplicates
        if len(v) != len(set(v)):
            raise ValueError("provider_priority list cannot contain duplicates")
        return v

    def model_post_init(self, __context) -> None:
        """Post-initialization validation."""
        # If provider_priority is set, validate those providers have configs
        if self.provider_priority:
            for provider_name in self.provider_priority:
                provider_config = getattr(self.providers, provider_name, None)
                if provider_config is None:
                    raise ValueError(
                        f"Provider '{provider_name}' in provider_priority has no configuration"
                    )
        else:
            # Fall back to single provider validation
            provider_config = getattr(self.providers, self.provider, None)
            if provider_config is None:
                raise ValueError(
                    f"Provider '{self.provider}' is selected but has no configuration"
                )

    def get_provider_list(self) -> List[str]:
        """
        Get the ordered list of providers to try.

        Returns provider_priority if set, otherwise a single-item list
        containing the default provider.

        Returns:
            List[str]: Ordered list of provider names to try
        """
        if self.provider_priority:
            return list(self.provider_priority)
        return [self.provider]

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

        # Warn if both provider and provider_priority are set
        if validated_config.provider_priority and "provider" in config_dict:
            warnings.append(
                "Both 'provider' and 'provider_priority' are configured. "
                "'provider_priority' takes precedence."
            )

        # Get the list of providers to check for API keys
        providers_to_check = validated_config.get_provider_list()

        for provider_name in providers_to_check:
            if provider_name == "openai":
                if not validated_config.providers.openai.api_key:
                    warnings.append(
                        "OpenAI provider in chain but 'api_key' not set. "
                        "Set OPENAI_API_KEY environment variable or add to config."
                    )

            if provider_name == "anthropic":
                if not validated_config.providers.anthropic.api_key:
                    warnings.append(
                        "Anthropic provider in chain but 'api_key' not set. "
                        "Set ANTHROPIC_API_KEY environment variable or add to config."
                    )

            if provider_name == "local":
                if not validated_config.providers.local:
                    warnings.append(
                        "Local provider in chain but no local provider configuration found."
                    )

        return validated_config, warnings

    except Exception as e:
        raise ValueError(f"Configuration validation failed: {e}")
