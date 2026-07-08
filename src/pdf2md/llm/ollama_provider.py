"""Dostawca LLM: Ollama (lokalne modele)."""

from __future__ import annotations

import json
import urllib.request

from loguru import logger

from pdf2md.core.config import get_settings
from pdf2md.core.prompts import POST_PROCESSING_PROMPT
from pdf2md.llm.base import LLMProvider, LLMResult
from pdf2md.llm.base_mixin import PostprocessMixin


class OllamaProvider(PostprocessMixin, LLMProvider):
    """Dostawca LLM korzystający z lokalnego serwera Ollama."""

    name = "Ollama (lokalny)"
    description = "Lokalny serwer Ollama — modele działają offline, bez klucza API."
    requires_api_key = False
    default_model = "qwen3:14b"

    def is_available(self) -> bool:
        """Zwraca True jeśli serwer Ollama odpowiada na /api/tags."""
        try:
            with urllib.request.urlopen(f"{self._base_url()}/api/tags", timeout=2) as resp:
                return bool(resp.status == 200)
        except Exception:
            return False

    def get_models(self) -> list[str]:
        """Zwraca listę dostępnych modeli z /api/tags."""
        try:
            with urllib.request.urlopen(f"{self._base_url()}/api/tags", timeout=2) as resp:
                data = json.loads(resp.read())
                return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []

    def _base_url(self) -> str:
        return (
            getattr(get_settings(), "ollama_url", "http://localhost:11434").rstrip("/")
            or "http://localhost:11434"
        )

    def _settings_model(self) -> str | None:
        return get_settings().ollama_model

    def _call_llm(self, text: str, instructions: str) -> str:
        model = self._resolve_model()
        prompt = (
            f"{POST_PROCESSING_PROMPT}\n\n{instructions}\n\n{text}"
            if instructions
            else f"{POST_PROCESSING_PROMPT}\n\n{text}"
        )
        payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()
        req = urllib.request.Request(
            f"{self._base_url()}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
            return str(result.get("response", text))

    def postprocess(
        self,
        markdown: str,
        mode: str = "whole_document",
        instructions: str = "",
    ) -> LLMResult:
        model = self._resolve_model()
        logger.info(f"Ollama post-processing: model={model}, mode={mode}")
        processed = self._postprocess_chunks(markdown, mode, instructions)
        return LLMResult(text=processed, provider_used=self.name)

    def correct(self, text: str, *, system_prompt: str, temperature: float = 0.0) -> str:
        """Korekta przez /api/chat: system+user dokładnie, bez dodatkowego promptu.

        ``think=False`` na poziomie głównym body wyłącza rozumowanie (qwen3 ma je domyślnie
        ON) — przy korekcie nie chcemy „ulepszania"/parafrazy. W options działać nie będzie.
        """
        model = self._resolve_model()
        payload = json.dumps(
            {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
                "stream": False,
                "think": False,
                "options": {"temperature": temperature},
            }
        ).encode()
        req = urllib.request.Request(
            f"{self._base_url()}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
            return str(result.get("message", {}).get("content", text))
