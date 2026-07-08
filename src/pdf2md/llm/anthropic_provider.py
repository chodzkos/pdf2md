"""Dostawca LLM: Claude (Anthropic API)."""

from __future__ import annotations

import importlib
import importlib.metadata

from loguru import logger

from pdf2md.core.config import get_settings
from pdf2md.core.prompts import POST_PROCESSING_PROMPT
from pdf2md.llm import SDK_PACKAGES, missing_sdk_message
from pdf2md.llm.base import LLMProvider, LLMResult
from pdf2md.llm.base_mixin import PostprocessMixin

PROVIDER_KEY = "anthropic"


class AnthropicProvider(PostprocessMixin, LLMProvider):
    """Dostawca LLM korzystający z Claude przez Anthropic API."""

    name = "Claude (Anthropic)"
    description = "Modele Claude przez Anthropic API — wymaga klucza ANTHROPIC_API_KEY."
    requires_api_key = True
    default_model = "claude-sonnet-4-5"

    def is_available(self) -> bool:
        """Zwraca True jeśli klucz API ustawiony i pakiet anthropic zainstalowany."""
        if not get_settings().anthropic_api_key:
            return False
        try:
            importlib.metadata.version(SDK_PACKAGES[PROVIDER_KEY])
        except importlib.metadata.PackageNotFoundError:
            return False
        return True

    def _settings_model(self) -> str | None:
        return get_settings().anthropic_model

    def _call_llm(self, text: str, instructions: str) -> str:
        try:
            anthropic = importlib.import_module("anthropic")
        except ImportError as exc:
            raise RuntimeError(missing_sdk_message(PROVIDER_KEY)) from exc
        model = self._resolve_model()
        client = anthropic.Anthropic(api_key=get_settings().anthropic_api_key)
        user_content = f"{instructions}\n\n{text}" if instructions else text
        message = client.messages.create(
            model=model,
            max_tokens=8192,
            system=POST_PROCESSING_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )
        return str(message.content[0].text)

    def postprocess(
        self,
        markdown: str,
        mode: str = "whole_document",
        instructions: str = "",
    ) -> LLMResult:
        model = self._resolve_model()
        logger.info(f"Anthropic post-processing: model={model}, mode={mode}")
        processed = self._postprocess_chunks(markdown, mode, instructions)
        return LLMResult(text=processed, provider_used=self.name)

    def correct(self, text: str, *, system_prompt: str, temperature: float = 0.0) -> str:
        """Korekta: system=system_prompt, user=text, bez POST_PROCESSING_PROMPT."""
        try:
            anthropic = importlib.import_module("anthropic")
        except ImportError as exc:
            raise RuntimeError(missing_sdk_message(PROVIDER_KEY)) from exc
        model = self._resolve_model()
        client = anthropic.Anthropic(api_key=get_settings().anthropic_api_key)
        message = client.messages.create(
            model=model,
            max_tokens=8192,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": text}],
        )
        return str(message.content[0].text)
