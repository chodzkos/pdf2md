"""Orkiestrator konwersji — łączy silnik konwersji z opcjonalnym LLM."""

from __future__ import annotations

import time
from pathlib import Path

from loguru import logger

from pdf2md.engines.base import ConversionEngine, ConversionResult
from pdf2md.llm.base import LLMProvider


class ConversionError(Exception):
    """Błąd podczas konwersji pliku PDF."""


class Converter:
    """Orkiestrator: silnik konwersji → opcjonalny LLM → zapis pliku."""

    def convert(
        self,
        pdf_path: str,
        engine: ConversionEngine,
        llm: LLMProvider | None = None,
        output_path: str | None = None,
        llm_mode: str = "none",
    ) -> ConversionResult:
        """Konwertuje jeden plik PDF do Markdown.

        Args:
            pdf_path: Ścieżka do pliku PDF.
            engine: Silnik konwersji do użycia.
            llm: Opcjonalny dostawca LLM do post-processingu.
            output_path: Ścieżka wyjściowa pliku .md (None = nie zapisuj).
            llm_mode: Tryb post-processingu LLM.

        Returns:
            Wynik konwersji z Markdown i metadanymi.

        Raises:
            ConversionError: Plik nie istnieje lub silnik niedostępny.
        """
        path = Path(pdf_path)
        if not path.exists():
            raise ConversionError(f"Plik nie istnieje: {pdf_path}")
        if not engine.is_available():
            raise ConversionError(f"Silnik '{engine.name}' nie jest dostępny")

        logger.info(f"Konwertuję: {path.name} (silnik: {engine.name})")
        start = time.monotonic()
        result = engine.convert(pdf_path)
        result.conversion_time = time.monotonic() - start

        if llm is not None:
            logger.info(f"Post-processing LLM: {llm.name}")
            llm_result = llm.postprocess(result.markdown, mode=llm_mode)
            result.markdown = llm_result.text

        if output_path is not None:
            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(result.markdown, encoding="utf-8")
            logger.info(f"Zapisano: {out}")

        logger.info(f"Gotowe: {path.name} — {result.pages} str., {result.conversion_time:.1f}s")
        return result

    def convert_batch(
        self,
        pdf_paths: list[str],
        engine: ConversionEngine,
        llm: LLMProvider | None = None,
        output_dir: str | None = None,
        llm_mode: str = "none",
    ) -> list[ConversionResult]:
        """Konwertuje wiele plików PDF.

        Args:
            pdf_paths: Lista ścieżek do plików PDF.
            engine: Silnik konwersji.
            llm: Opcjonalny dostawca LLM.
            output_dir: Katalog wyjściowy (None = obok źródła).
            llm_mode: Tryb post-processingu LLM.

        Returns:
            Lista wyników (w kolejności wejściowej).
        """
        results: list[ConversionResult] = []
        for pdf_path in pdf_paths:
            out: str | None = None
            if output_dir is not None:
                stem = Path(pdf_path).stem
                out = str(Path(output_dir) / f"{stem}.md")
            try:
                result = self.convert(pdf_path, engine, llm, output_path=out, llm_mode=llm_mode)
            except ConversionError as exc:
                logger.error(f"Błąd przy {pdf_path}: {exc}")
                result = ConversionResult(
                    markdown="",
                    engine_used=engine.name,
                    pages=0,
                    warnings=[str(exc)],
                )
            results.append(result)
        return results
