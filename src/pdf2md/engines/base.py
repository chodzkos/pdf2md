"""Abstrakcja silnika konwersji PDF → Markdown."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ConversionResult:
    """Wynik konwersji pojedynczego pliku PDF."""

    markdown: str
    engine_used: str
    pages: int
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)
    conversion_time: float = 0.0


class ConversionEngine(ABC):
    """Abstrakcja silnika konwersji — każdy adapter musi ją implementować."""

    name: str
    description: str
    supports_ocr: bool
    supports_llm: bool
    requires_gpu: bool = False

    @abstractmethod
    def is_available(self) -> bool:
        """Zwraca True jeśli silnik jest zainstalowany i gotowy do użycia."""

    @abstractmethod
    def convert(self, pdf_path: str, **kwargs: object) -> ConversionResult:
        """Konwertuje plik PDF do Markdown.

        Args:
            pdf_path: Ścieżka do pliku PDF.
            **kwargs: Opcje specyficzne dla silnika.

        Returns:
            Wynik konwersji.
        """

    def is_installed(self) -> bool:
        """Alias dla is_available() — dla czytelności kodu."""
        return self.is_available()
