"""Dostawca LLM: OpenAI API (GPT)."""

from __future__ import annotations

import importlib
import importlib.metadata

from loguru import logger

from pdf2md.core.config import get_settings
from pdf2md.core.prompts import POST_PROCESSING_PROMPT
from pdf2md.llm.base import LLMProvider, LLMResult
from pdf2md.llm.base_mixin import PostprocessMixin


class OpenAIProvider(PostprocessMixin, LLMProvider):
    """Dostawca LLM korzystający z OpenAI API."""

    name = "OpenAI (GPT)"
    description = "Modele GPT przez OpenAI API — wymaga klucza OPENAI_API_KEY."
    requires_api_key = True
    default_model = "gpt-4o-mini"

    def is_available(self) -> bool:
        """Zwraca True jeśli klucz API ustawiony i pakiet openai zainstalowany."""
        if not get_settings().openai_api_key:
            return False
        try:
            importlib.metadata.version("openai")
        except importlib.metadata.PackageNotFoundError:
            return False
        return True

    def _call_llm(self, text: str, instructions: str) -> str:
        openai = importlib.import_module("openai")
        settings = get_settings()
        model = settings.openai_model or self.default_model
        client = openai.OpenAI(api_key=settings.openai_api_key)
        user_content = f"{instructions}\n\n{text}" if instructions else text
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": POST_PROCESSING_PROMPT},
                {"role": "user", "content": user_content},
            ],
        )
        return str(response.choices[0].message.content)

    def postprocess(
        self,
        markdown: str,
        mode: str = "whole_document",
        instructions: str = "",
    ) -> LLMResult:
        settings = get_settings()
        model = settings.openai_model or self.default_model
        logger.info(f"OpenAI post-processing: model={model}, mode={mode}")
        processed = self._postprocess_chunks(markdown, mode, instructions)
        return LLMResult(text=processed, provider_used=self.name)

    def correct(self, text: str, *, system_prompt: str, temperature: float = 0.0) -> str:
        """Korekta: system=system_prompt, user=text, bez POST_PROCESSING_PROMPT."""
        openai = importlib.import_module("openai")
        settings = get_settings()
        model = settings.openai_model or self.default_model
        client = openai.OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
        )
        return str(response.choices[0].message.content)
