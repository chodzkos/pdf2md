"""Abstrakcja dostawcy LLM do post-processingu Markdown."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

# Dozwolone tryby przetwarzania przez LLM
LLM_MODES = frozenset({"none", "whole_document", "by_page", "by_chunk", "by_heading"})


@dataclass
class LLMResult:
    """Wynik przetwarzania przez model językowy."""

    text: str
    provider_used: str
    tokens_used: int = 0


class LLMProvider(ABC):
    """Abstrakcja dostawcy LLM — każdy adapter (Ollama, Claude, OpenAI…) musi ją implementować."""

    name: str
    description: str
    requires_api_key: bool
    default_model: str  # bezpieczny fallback, nadpisywany przez Settings

    @abstractmethod
    def is_available(self) -> bool:
        """Zwraca True jeśli dostawca jest osiągalny (API key / serwer Ollama)."""

    @abstractmethod
    def postprocess(
        self,
        markdown: str,
        mode: str = "whole_document",
        instructions: str = "",
    ) -> LLMResult:
        """Poprawia/czyści Markdown przy użyciu LLM.

        Args:
            markdown: Wejściowy tekst Markdown z silnika konwersji.
            mode: Sposób podziału tekstu — jeden z LLM_MODES.
            instructions: Dodatkowe instrukcje dla modelu.

        Returns:
            Wynik z poprawionym tekstem i statystykami.
        """

    @abstractmethod
    def correct(self, text: str, *, system_prompt: str, temperature: float = 0.0) -> str:
        """Korekta tekstu: wysyła do modelu DOKŁADNIE system=system_prompt, user=text.

        W przeciwieństwie do postprocess() NIE prependuje POST_PROCESSING_PROMPT ani żadnego
        innego promptu. Używane do konserwatywnej korekty OCR (scan/correction.py).

        Args:
            text: Tekst do skorygowania (jedna strona Markdown).
            system_prompt: Pełny prompt systemowy (np. SCAN_CORRECTION_PROMPT).
            temperature: Temperatura próbkowania — 0.0 dla korekty bez kreatywności.

        Returns:
            Skorygowany tekst (czysta odpowiedź modelu).
        """
