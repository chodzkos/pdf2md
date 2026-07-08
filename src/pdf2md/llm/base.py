"""Abstrakcja dostawcy LLM do post-processingu Markdown."""

from __future__ import annotations

import copy
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Self

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

    #: Model wymuszony na czas jednego uruchomienia (override). Ustawiany WYŁĄCZNIE przez
    #: ``bind_model`` na płytkiej kopii — nigdy nie mutujemy współdzielonego singletona z
    #: rejestru ani globalnego ``Settings``. ``None`` → model bierzemy z konfiguracji/fallbacku.
    model_override: str | None = None

    def bind_model(self, model: str | None) -> Self:
        """Zwraca dostawcę z modelem wymuszonym per-uruchomienie.

        Bez ``model`` zwraca ``self``. Z modelem zwraca **płytką kopię** z ustawionym
        ``model_override`` — dzięki temu wołający (worker/CLI) przekazuje override jawnie,
        bez mutacji współdzielonej między wątkami (singleton w rejestrze / ``Settings``).
        """
        if not model:
            return self
        bound = copy.copy(self)
        bound.model_override = model
        return bound

    def _settings_model(self) -> str | None:
        """Model z konfiguracji dla tego dostawcy (nadpisywane per-provider).

        ``None``/pusty → ``_resolve_model`` spadnie na ``default_model``.
        """
        return None

    def _resolve_model(self) -> str:
        """Model do użycia w tej kolejności: override per-run → konfiguracja → wbudowany fallback."""
        return self.model_override or self._settings_model() or self.default_model

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
