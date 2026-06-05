"""Dostawca LLM: Google Gemini API."""

from __future__ import annotations

import importlib
import importlib.metadata

from loguru import logger

from pdf2md.core.config import get_settings
from pdf2md.core.prompts import POST_PROCESSING_PROMPT
from pdf2md.llm.base import LLMProvider, LLMResult
from pdf2md.llm.base_mixin import PostprocessMixin


class GeminiProvider(PostprocessMixin, LLMProvider):
    """Dostawca LLM korzystający z Google Gemini API."""

    name = "Gemini (Google)"
    description = "Modele Gemini przez Google AI API — wymaga klucza GEMINI_API_KEY."
    requires_api_key = True
    default_model = "gemini-2.0-flash"

    def is_available(self) -> bool:
        """Zwraca True jeśli klucz API ustawiony i pakiet google-generativeai zainstalowany."""
        if not get_settings().gemini_api_key:
            return False
        try:
            importlib.metadata.version("google-generativeai")
        except importlib.metadata.PackageNotFoundError:
            return False
        return True

    def _call_llm(self, text: str, instructions: str) -> str:
        genai = importlib.import_module("google.generativeai")
        settings = get_settings()
        model_name = settings.gemini_model or self.default_model
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=POST_PROCESSING_PROMPT,
        )
        user_content = f"{instructions}\n\n{text}" if instructions else text
        response = model.generate_content(user_content)
        return str(response.text)

    def postprocess(
        self,
        markdown: str,
        mode: str = "whole_document",
        instructions: str = "",
    ) -> LLMResult:
        settings = get_settings()
        model = settings.gemini_model or self.default_model
        logger.info(f"Gemini post-processing: model={model}, mode={mode}")
        processed = self._postprocess_chunks(markdown, mode, instructions)
        return LLMResult(text=processed, provider_used=self.name)
