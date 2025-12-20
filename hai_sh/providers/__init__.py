"""
LLM provider abstraction layer for hai-sh.

This module provides an abstract interface for different LLM providers
(OpenAI, Anthropic, Ollama, local models) allowing easy switching between
backends.
"""

from hai_sh.providers.base import BaseLLMProvider
from hai_sh.providers.openai import OpenAIProvider
from hai_sh.providers.registry import (
    ProviderRegistry,
    get_provider,
    list_providers,
    register_provider,
)

__all__ = [
    "BaseLLMProvider",
    "OpenAIProvider",
    "ProviderRegistry",
    "get_provider",
    "register_provider",
    "list_providers",
]
