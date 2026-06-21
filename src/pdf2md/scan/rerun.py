"""Ponowny przebieg trudnych stron dokładniejszym silnikiem lub wyższym DPI.

Strony wytypowane przez scan/validation.py (np. z dużą liczbą znaków �) renderujemy ponownie
w wyższym DPI i puszczamy przez silnik fallbackowy. Realistyczny fallback w Fazie 2 to silnik
VLM (Etap 12) udostępniający metodę per-stronę ``_ocr_page(image_path)``.
"""

from __future__ import annotations

import os
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from loguru import logger

from pdf2md.scan.preprocessing import DPI_DIFFICULT


@runtime_checkable
class _PageOCREngine(Protocol):
    """Silnik zdolny do OCR pojedynczej strony-obrazu (jak VLMEngine)."""

    def load_model(self) -> None: ...
    def unload_model(self) -> None: ...
    def _ocr_page(self, image_path: str) -> str: ...


def _render_page(pdf_path: str, page_index: int, dpi: int, out_dir: str) -> str:
    """Renderuje pojedynczą stronę (0-based) PDF do PNG w out_dir i zwraca ścieżkę."""
    import pymupdf

    mat = pymupdf.Matrix(dpi / 72, dpi / 72)
    doc = pymupdf.open(pdf_path)
    try:
        pix = doc[page_index].get_pixmap(matrix=mat)
        path = str(Path(out_dir) / f"rerun_page_{page_index + 1:04d}.png")
        pix.save(path)
        return path
    finally:
        doc.close()


def rerun_difficult_pages(
    page_indices: list[int],
    pdf_path: str,
    fallback_engine: Any,
    higher_dpi: int = DPI_DIFFICULT,
) -> dict[int, str]:
    """Ponawia OCR wskazanych stron (0-based) silnikiem fallbackowym w wyższym DPI.

    Zwraca mapę {indeks_strony: poprawiony_markdown}. Silnik musi udostępniać interfejs
    per-strona (load_model / _ocr_page / unload_model) — typowo silnik VLM z Etapu 12.
    """
    if not page_indices:
        return {}
    if not isinstance(fallback_engine, _PageOCREngine):
        raise TypeError(
            "fallback_engine musi udostępniać _ocr_page/load_model/unload_model "
            "(silnik VLM z Etapu 12)."
        )

    results: dict[int, str] = {}
    work_dir = tempfile.mkdtemp(prefix="pdf2md_rerun_")
    logger.info(
        f"Ponowny przebieg {len(page_indices)} trudnych stron w DPI={higher_dpi} "
        f"silnikiem {getattr(fallback_engine, 'name', fallback_engine)}"
    )
    try:
        fallback_engine.load_model()
        for idx in page_indices:
            png = _render_page(pdf_path, idx, higher_dpi, work_dir)
            results[idx] = fallback_engine._ocr_page(png)
            with suppress(FileNotFoundError):
                os.remove(png)
    finally:
        fallback_engine.unload_model()
        with suppress(OSError):
            os.rmdir(work_dir)
    return results
