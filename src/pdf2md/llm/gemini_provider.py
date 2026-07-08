"""Dostawca LLM: Google Gemini API (google-genai SDK)."""

from __future__ import annotations

import importlib
import importlib.metadata

from loguru import logger

from pdf2md.core.config import get_settings
from pdf2md.core.prompts import POST_PROCESSING_PROMPT
from pdf2md.llm import SDK_PACKAGES, missing_sdk_message
from pdf2md.llm.base import LLMProvider, LLMResult
from pdf2md.llm.base_mixin import PostprocessMixin

PROVIDER_KEY = "gemini"


class GeminiProvider(PostprocessMixin, LLMProvider):
    """Dostawca LLM korzystający z Google Gemini API."""

    name = "Gemini (Google)"
    description = "Modele Gemini przez Google AI API — wymaga klucza GEMINI_API_KEY."
    requires_api_key = True
    default_model = "gemini-2.5-flash"

    def is_available(self) -> bool:
        """Zwraca True jeśli klucz API ustawiony i pakiet google-genai zainstalowany."""
        if not get_settings().gemini_api_key:
            return False
        try:
            importlib.metadata.version(SDK_PACKAGES[PROVIDER_KEY])
        except importlib.metadata.PackageNotFoundError:
            return False
        return True

    def _settings_model(self) -> str | None:
        return get_settings().gemini_model

    def _call_llm(self, text: str, instructions: str) -> str:
        try:
            genai = importlib.import_module("google.genai")
            types = importlib.import_module("google.genai.types")
        except ImportError as exc:
            raise RuntimeError(missing_sdk_message(PROVIDER_KEY)) from exc
        model_name = self._resolve_model()
        client = genai.Client(api_key=get_settings().gemini_api_key)
        user_content = f"{instructions}\n\n{text}" if instructions else text
        contents = f"{POST_PROCESSING_PROMPT}\n\n{user_content}"
        resp = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=types.GenerateContentConfig(temperature=0.1),
        )
        return str(resp.text)

    def postprocess(
        self,
        markdown: str,
        mode: str = "whole_document",
        instructions: str = "",
    ) -> LLMResult:
        model = self._resolve_model()
        logger.info(f"Gemini post-processing: model={model}, mode={mode}")
        processed = self._postprocess_chunks(markdown, mode, instructions)
        return LLMResult(text=processed, provider_used=self.name)

    def correct(self, text: str, *, system_prompt: str, temperature: float = 0.0) -> str:
        """Korekta: system_instruction=system_prompt, contents=text, bez POST_PROCESSING_PROMPT."""
        try:
            genai = importlib.import_module("google.genai")
            types = importlib.import_module("google.genai.types")
        except ImportError as exc:
            raise RuntimeError(missing_sdk_message(PROVIDER_KEY)) from exc
        model_name = self._resolve_model()
        client = genai.Client(api_key=get_settings().gemini_api_key)
        resp = client.models.generate_content(
            model=model_name,
            contents=text,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=temperature,
            ),
        )
        return str(resp.text)
