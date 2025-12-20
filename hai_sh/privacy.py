"""
Privacy protection and warnings for hai-sh.

This module provides privacy-related functionality including:
- Warnings for cloud LLM usage
- Privacy risk assessment
- Configuration validation
"""

import sys
from typing import Optional


def check_privacy_risks(provider_name: str, config: Optional[dict] = None) -> tuple[bool, list[str]]:
    """
    Check for privacy risks based on provider and configuration.

    Args:
        provider_name: Name of the LLM provider
        config: Configuration dictionary

    Returns:
        tuple: (has_risks, list of warning messages)
    """
    warnings = []
    has_risks = False

    # Check if using cloud LLM provider
    cloud_providers = ["openai", "anthropic", "openaiProvider", "anthropicProvider"]
    is_cloud = any(cloud in provider_name.lower() for cloud in cloud_providers)

    if is_cloud:
        has_risks = True

        # Check if user prefers local LLM
        if config:
            privacy_settings = config.get("privacy", {})
            prefer_local = privacy_settings.get("prefer_local_llm", True)

            if prefer_local:
                warnings.append(
                    "⚠️  WARNING: Using cloud LLM provider. Consider Ollama for privacy."
                )
                warnings.append(
                    "   Your commands and context will be sent to third-party servers."
                )
                warnings.append(
                    "   Set privacy.prefer_local_llm=false in config to disable this warning."
                )

    return has_risks, warnings


def warn_privacy_risks(provider_name: str, config: Optional[dict] = None, stream=sys.stderr):
    """
    Display privacy warnings if applicable.

    Args:
        provider_name: Name of the LLM provider
        config: Configuration dictionary
        stream: Output stream for warnings (default: stderr)
    """
    has_risks, warnings = check_privacy_risks(provider_name, config)

    if has_risks and warnings:
        for warning in warnings:
            print(warning, file=stream)
        print(file=stream)  # Empty line for readability


def get_privacy_recommendations(provider_name: str) -> list[str]:
    """
    Get privacy recommendations based on provider.

    Args:
        provider_name: Name of the LLM provider

    Returns:
        list: Privacy recommendations
    """
    recommendations = []

    cloud_providers = ["openai", "anthropic"]
    is_cloud = any(cloud in provider_name.lower() for cloud in cloud_providers)

    if is_cloud:
        recommendations.extend([
            "• Consider using Ollama with local models for complete privacy",
            "• Review what context is sent to the LLM (disable history if sensitive)",
            "• Be aware that command outputs may be used for model training",
            "• Avoid using hai for sensitive operations (passwords, API keys, etc.)",
        ])
    else:
        recommendations.extend([
            "• Local LLM (Ollama) provides maximum privacy",
            "• Data stays on your machine - no third-party access",
            "• Still be cautious with sensitive information in command outputs",
        ])

    return recommendations


def validate_privacy_config(config: dict) -> tuple[bool, list[str]]:
    """
    Validate privacy-related configuration settings.

    Args:
        config: Configuration dictionary

    Returns:
        tuple: (is_valid, list of validation errors)
    """
    errors = []

    if "privacy" not in config:
        # Privacy settings are optional, so no error
        return True, errors

    privacy = config["privacy"]

    # Validate redact_output
    if "redact_output" in privacy:
        if not isinstance(privacy["redact_output"], bool):
            errors.append("privacy.redact_output must be a boolean")

    # Validate filter_env_vars
    if "filter_env_vars" in privacy:
        if not isinstance(privacy["filter_env_vars"], bool):
            errors.append("privacy.filter_env_vars must be a boolean")

    # Validate log_commands
    if "log_commands" in privacy:
        if not isinstance(privacy["log_commands"], bool):
            errors.append("privacy.log_commands must be a boolean")

    # Validate send_minimal_context
    if "send_minimal_context" in privacy:
        if not isinstance(privacy["send_minimal_context"], bool):
            errors.append("privacy.send_minimal_context must be a boolean")

    # Validate prefer_local_llm
    if "prefer_local_llm" in privacy:
        if not isinstance(privacy["prefer_local_llm"], bool):
            errors.append("privacy.prefer_local_llm must be a boolean")

    is_valid = len(errors) == 0
    return is_valid, errors
