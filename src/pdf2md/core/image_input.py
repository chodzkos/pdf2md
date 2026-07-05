"""Przygotowanie obrazów dokumentów do istniejących silników OCR."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from loguru import logger

from pdf2md.scan.preprocessing import DPI_STANDARD, preprocess_page

DEFAULT_IMAGE_PREPROCESSING = ("deskew", "denoise", "normalize")

_IMAGE_OCR_DEPS_HINT = "OCR obrazów wymaga zależności preprocessingu skanów: uv sync --extra scan"


def image_to_preprocessed_pdf(
    image_path: str | Path,
    output_dir: str | Path,
    *,
    operations: Sequence[str] = DEFAULT_IMAGE_PREPROCESSING,
    dpi: int = DPI_STANDARD,
) -> Path:
    """Zamienia JPG/PNG/TIFF na tymczasowy PDF po preprocessingu stron.

    Obrazy jedno-klatkowe są traktowane jako jedna strona. TIFF wielostronicowy jest rozwijany do
    kolejnych stron PDF w kolejności klatek.
    """
    from PIL import Image, ImageSequence

    source = Path(image_path)
    destination_dir = Path(output_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = destination_dir / f"{source.stem}_image_input.pdf"

    pages: list[Any] = []
    with Image.open(source) as image:
        for page_number, frame in enumerate(ImageSequence.Iterator(image), start=1):
            pages.append(_preprocess_frame(frame.copy(), operations))
            logger.debug(f"Przygotowano stronę obrazu {page_number}: {source}")

    if not pages:
        raise RuntimeError(f"Nie udało się odczytać obrazu: {source}")

    first, *rest = pages
    try:
        first.save(
            pdf_path,
            format="PDF",
            save_all=bool(rest),
            append_images=rest,
            resolution=float(dpi),
        )
    finally:
        for page in pages:
            close = getattr(page, "close", None)
            if callable(close):
                close()
    return pdf_path


def _preprocess_frame(frame: Any, operations: Sequence[str]) -> Any:
    try:
        import cv2
        import numpy as np
        from PIL import Image
    except ModuleNotFoundError as exc:
        raise RuntimeError(_IMAGE_OCR_DEPS_HINT) from exc

    rgb = frame.convert("RGB")
    bgr = cv2.cvtColor(np.array(rgb), cv2.COLOR_RGB2BGR)
    processed = preprocess_page(bgr, list(operations))
    if getattr(processed, "ndim", 0) == 3:
        processed = cv2.cvtColor(processed, cv2.COLOR_BGR2RGB)
    return Image.fromarray(processed).convert("RGB")
