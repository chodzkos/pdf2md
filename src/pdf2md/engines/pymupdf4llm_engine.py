"""Adapter silnika PyMuPDF4LLM."""

from __future__ import annotations

import importlib.metadata
from pathlib import Path
from typing import Any

from loguru import logger

from pdf2md.engines.base import ConversionEngine, ConversionResult


class PyMuPDF4LLMEngine(ConversionEngine):
    """Adapter szybkiego ekstraktora tekstu dla natywnych PDF-ów."""

    name = "PyMuPDF4LLM"
    description = "Szybki ekstraktor tekstu z natywnych PDF-ów. Nie obsługuje skanów."
    supports_ocr = False
    supports_llm = False

    def is_available(self) -> bool:
        """Sprawdza obecność pakietu bez importowania ciężkiego silnika."""
        try:
            importlib.metadata.version("pymupdf4llm")
        except importlib.metadata.PackageNotFoundError:
            return False
        return True

    def convert(self, pdf_path: str, **kwargs: object) -> ConversionResult:
        """Konwertuje natywny PDF do Markdown przez PyMuPDF4LLM."""
        if not self.is_available():
            raise RuntimeError(
                "Silnik PyMuPDF4LLM nie jest zainstalowany. "
                'Zainstaluj go poleceniem: uv sync --extra engines-core albo pip install "pdf2md[engines-core]".'
            )

        path = Path(pdf_path)
        try:
            pymupdf: Any = importlib.import_module("pymupdf")
            pymupdf4llm: Any = importlib.import_module("pymupdf4llm")

            logger.info(f"Konwertuję {path} przez PyMuPDF4LLM")
            markdown = pymupdf4llm.to_markdown(str(path), **kwargs)
            doc = pymupdf.open(str(path))
            try:
                pages = len(doc)
            finally:
                doc.close()
        except Exception:
            logger.exception(f"PyMuPDF4LLM nie zdołał przekonwertować pliku: {path}")
            raise

        return ConversionResult(markdown=markdown, engine_used=self.name, pages=pages)
