"""Dostawca LLM: Claude (Anthropic API)."""

from __future__ import annotations

import importlib
import importlib.metadata

from loguru import logger

from pdf2md.core.config import get_settings
from pdf2md.core.prompts import POST_PROCESSING_PROMPT
from pdf2md.llm.base import LLMProvider, LLMResult
from pdf2md.llm.base_mixin import PostprocessMixin


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
            importlib.metadata.version("anthropic")
        except importlib.metadata.PackageNotFoundError:
            return False
        return True

    def _call_llm(self, text: str, instructions: str) -> str:
        anthropic = importlib.import_module("anthropic")
        settings = get_settings()
        model = settings.anthropic_model or self.default_model
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
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
        settings = get_settings()
        model = settings.anthropic_model or self.default_model
        logger.info(f"Anthropic post-processing: model={model}, mode={mode}")
        processed = self._postprocess_chunks(markdown, mode, instructions)
        return LLMResult(text=processed, provider_used=self.name)
