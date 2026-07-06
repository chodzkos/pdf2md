"""Integracje z modelami językowymi (Anthropic, OpenAI, Gemini, Ollama)."""

from pdf2md.core.registry import llm_registry
from pdf2md.llm._metadata import (
    PROVIDER_ALIASES,
    PROVIDER_MODEL_FIELDS,
    SDK_PACKAGES,
    missing_sdk_message,
    normalize_provider_key,
    sdk_package_for_provider,
)
from pdf2md.llm.anthropic_provider import AnthropicProvider
from pdf2md.llm.gemini_provider import GeminiProvider
from pdf2md.llm.ollama_provider import OllamaProvider
from pdf2md.llm.openai_provider import OpenAIProvider

llm_registry.register(OllamaProvider())
llm_registry.register(AnthropicProvider())
llm_registry.register(OpenAIProvider())
llm_registry.register(GeminiProvider())

__all__ = [
    "PROVIDER_ALIASES",
    "PROVIDER_MODEL_FIELDS",
    "SDK_PACKAGES",
    "AnthropicProvider",
    "GeminiProvider",
    "OllamaProvider",
    "OpenAIProvider",
    "missing_sdk_message",
    "normalize_provider_key",
    "sdk_package_for_provider",
]
