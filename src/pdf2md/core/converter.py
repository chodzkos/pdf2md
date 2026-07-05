"""Orkiestrator konwersji — łączy silnik konwersji z opcjonalnym LLM."""

from __future__ import annotations

import tempfile
import time
from contextlib import ExitStack
from pathlib import Path

from loguru import logger

from pdf2md.core import history as conversion_history
from pdf2md.core.image_input import image_to_preprocessed_pdf
from pdf2md.core.input_types import is_image_input, is_supported_input
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
        engine_kwargs: dict[str, object] | None = None,
        engine_options: dict[str, object] | None = None,
        record_history: bool = True,
    ) -> ConversionResult:
        """Konwertuje jeden plik PDF do Markdown.

        Args:
            pdf_path: Ścieżka do pliku PDF.
            engine: Silnik konwersji do użycia.
            llm: Opcjonalny dostawca LLM do post-processingu.
            output_path: Ścieżka wyjściowa pliku .md (None = nie zapisuj).
            llm_mode: Tryb post-processingu LLM.
            engine_kwargs: Opcje specyficzne dla silnika konwersji.
            engine_options: Opcje przekazywane bezpośrednio do silnika konwersji.
            record_history: Czy zapisać wpis historii w tej warstwie.

        Returns:
            Wynik konwersji z Markdown i metadanymi.

        Raises:
            ConversionError: Plik nie istnieje lub silnik niedostępny.
        """
        start = time.monotonic()
        try:
            path = Path(pdf_path)
            if not path.exists():
                raise ConversionError(f"Plik nie istnieje: {pdf_path}")
            if not is_supported_input(path):
                raise ConversionError(
                    "Nieobsługiwany format wejściowy. Obsługiwane: PDF, JPG, PNG, TIFF."
                )
            input_is_image = is_image_input(path)
            if input_is_image and not engine.supports_ocr:
                raise ConversionError(
                    f"Wejście obrazowe wymaga silnika OCR, a '{engine.name}' go nie obsługuje."
                )
            if not engine.is_available():
                raise ConversionError(f"Silnik '{engine.name}' nie jest dostępny")

            logger.info(f"Konwertuję: {path.name} (silnik: {engine.name})")
            with ExitStack() as stack:
                effective_path = str(path)
                if input_is_image:
                    tmp_dir = stack.enter_context(tempfile.TemporaryDirectory(prefix="pdf2md_img_"))
                    effective_path = str(image_to_preprocessed_pdf(path, tmp_dir))
                    logger.info(
                        f"Obraz wejściowy przygotowany jako tymczasowy PDF: {effective_path}"
                    )

                options = {**(engine_kwargs or {}), **(engine_options or {})}
                if output_path is not None and engine.name.lower() in {"docling", "marker"}:
                    options.setdefault("output_path", output_path)
                result = engine.convert(effective_path, **options)
            result.conversion_time = time.monotonic() - start
            if input_is_image:
                result.metadata.setdefault("source", str(path))
                result.metadata["input_type"] = "image"

            if llm is not None:
                logger.info(f"Post-processing LLM: {llm.name}")
                llm_result = llm.postprocess(result.markdown, mode=llm_mode)
                result.markdown = llm_result.text

            if output_path is not None:
                out = Path(output_path)
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(result.markdown, encoding="utf-8")
                logger.info(f"Zapisano: {out}")

            duration = time.monotonic() - start
            if record_history:
                self._record_history(
                    pdf_path=pdf_path,
                    engine=engine,
                    llm=llm,
                    llm_mode=llm_mode,
                    output_path=output_path,
                    status="ok",
                    duration_s=duration,
                )
            logger.info(f"Gotowe: {path.name} — {result.pages} str., {result.conversion_time:.1f}s")
            return result
        except Exception as exc:
            if record_history:
                self._record_history(
                    pdf_path=pdf_path,
                    engine=engine,
                    llm=llm,
                    llm_mode=llm_mode,
                    output_path=output_path,
                    status="error",
                    duration_s=time.monotonic() - start,
                    error_msg=str(exc),
                )
            raise

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
            output_dir: Katalog wyjściowy dla plików .md (None = nie zapisuj, zwróć wynik tylko w pamięci).
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

    def _record_history(
        self,
        *,
        pdf_path: str,
        engine: ConversionEngine,
        llm: LLMProvider | None,
        llm_mode: str,
        output_path: str | None,
        status: conversion_history.HistoryStatus,
        duration_s: float,
        error_msg: str | None = None,
    ) -> None:
        conversion_history.record_safely(
            input_path=pdf_path,
            engine=engine.name,
            llm_provider=llm.name if llm is not None else "none",
            llm_mode=llm_mode,
            output_path=output_path,
            status=status,
            duration_s=duration_s,
            error_msg=error_msg,
        )
