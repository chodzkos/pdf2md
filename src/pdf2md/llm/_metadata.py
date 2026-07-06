"""Wspólne metadane providerów LLM."""

SDK_PACKAGES: dict[str, str] = {
    "anthropic": "anthropic",
    "openai": "openai",
    "gemini": "google-genai",
}

PROVIDER_ALIASES: dict[str, str] = {
    "ollama": "ollama",
    "anthropic": "anthropic",
    "claude": "anthropic",
    "openai": "openai",
    "gpt": "openai",
    "gemini": "gemini",
    "google": "gemini",
}

PROVIDER_MODEL_FIELDS: dict[str, str] = {
    "ollama": "ollama_model",
    "anthropic": "anthropic_model",
    "openai": "openai_model",
    "gemini": "gemini_model",
}


def normalize_provider_key(name: str) -> str:
    normalized = name.lower().replace(" ", "").replace("-", "").replace("_", "")
    for alias, provider_key in PROVIDER_ALIASES.items():
        if alias in normalized:
            return provider_key
    return normalized


def sdk_package_for_provider(provider: str) -> str:
    return SDK_PACKAGES[normalize_provider_key(provider)]


def missing_sdk_message(provider: str) -> str:
    package = sdk_package_for_provider(provider)
    return f"{package} nie jest zainstalowany. Uruchom: uv sync --extra llm"
