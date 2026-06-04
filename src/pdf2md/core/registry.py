"""Rejestry silników konwersji i dostawców LLM.

Moduły silników rejestrują się tu przy imporcie.
CLI i GUI odpytują registry zamiast importować silniki bezpośrednio.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pdf2md.engines.base import ConversionEngine
    from pdf2md.llm.base import LLMProvider


class EngineRegistry:
    """Rejestr silników konwersji PDF → Markdown."""

    def __init__(self) -> None:
        self._engines: list[ConversionEngine] = []

    def register(self, engine: ConversionEngine) -> None:
        """Rejestruje silnik konwersji."""
        self._engines.append(engine)

    def get_all(self) -> list[ConversionEngine]:
        """Zwraca wszystkie zarejestrowane silniki."""
        return list(self._engines)

    def get_available(self) -> list[ConversionEngine]:
        """Zwraca tylko silniki z is_available() == True."""
        return [e for e in self._engines if e.is_available()]

    def get_by_name(self, name: str) -> ConversionEngine | None:
        """Zwraca silnik o podanej nazwie lub None."""
        for engine in self._engines:
            if engine.name == name:
                return engine
        return None

    def describe(self) -> str:
        """Tabela tekstowa wszystkich silników — dla CLI."""
        if not self._engines:
            return "Brak zarejestrowanych silników."
        header = f"{'Silnik':<20} {'Dostępny':<10} {'OCR':<6} {'GPU':<6} Opis"
        sep = "-" * 70
        rows = [header, sep]
        for e in self._engines:
            available = "✓" if e.is_available() else "✗"
            ocr = "✓" if e.supports_ocr else "✗"
            gpu = "✓" if e.requires_gpu else "-"
            rows.append(f"{e.name:<20} {available:<10} {ocr:<6} {gpu:<6} {e.description}")
        return "\n".join(rows)


class LLMRegistry:
    """Rejestr dostawców LLM do post-processingu."""

    def __init__(self) -> None:
        self._providers: list[LLMProvider] = []

    def register(self, provider: LLMProvider) -> None:
        """Rejestruje dostawcę LLM."""
        self._providers.append(provider)

    def get_all(self) -> list[LLMProvider]:
        """Zwraca wszystkich zarejestrowanych dostawców."""
        return list(self._providers)

    def get_available(self) -> list[LLMProvider]:
        """Zwraca tylko dostawców z is_available() == True."""
        return [p for p in self._providers if p.is_available()]

    def get_by_name(self, name: str) -> LLMProvider | None:
        """Zwraca dostawcę o podanej nazwie lub None."""
        for provider in self._providers:
            if provider.name == name:
                return provider
        return None

    def describe(self) -> str:
        """Tabela tekstowa wszystkich dostawców — dla CLI."""
        if not self._providers:
            return "Brak zarejestrowanych dostawców LLM."
        header = f"{'Dostawca':<20} {'Dostępny':<10} {'API key':<10} Opis"
        sep = "-" * 65
        rows = [header, sep]
        for p in self._providers:
            available = "✓" if p.is_available() else "✗"
            api_key = "wymagany" if p.requires_api_key else "nie"
            rows.append(f"{p.name:<20} {available:<10} {api_key:<10} {p.description}")
        return "\n".join(rows)


# Globalne instancje — importowane przez CLI, GUI i silniki
engine_registry = EngineRegistry()
llm_registry = LLMRegistry()
