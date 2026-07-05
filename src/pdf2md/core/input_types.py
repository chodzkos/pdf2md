"""Wspólne typy wejścia obsługiwane przez CLI i GUI."""

from __future__ import annotations

from pathlib import Path

PDF_INPUT_EXTENSIONS = frozenset({".pdf"})
IMAGE_INPUT_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".tif", ".tiff"})
SUPPORTED_INPUT_EXTENSIONS = PDF_INPUT_EXTENSIONS | IMAGE_INPUT_EXTENSIONS


def is_pdf_input(path: str | Path) -> bool:
    """Czy ścieżka wygląda jak wejściowy PDF."""
    return Path(path).suffix.lower() in PDF_INPUT_EXTENSIONS


def is_image_input(path: str | Path) -> bool:
    """Czy ścieżka wygląda jak obsługiwany obraz dokumentu."""
    return Path(path).suffix.lower() in IMAGE_INPUT_EXTENSIONS


def is_supported_input(path: str | Path) -> bool:
    """Czy ścieżka ma obsługiwane rozszerzenie wejściowe."""
    return Path(path).suffix.lower() in SUPPORTED_INPUT_EXTENSIONS


def supported_input_pattern() -> str:
    """Zwraca wzorzec glob do dialogów plików."""
    preferred = [".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif"]
    return " ".join(f"*{suffix}" for suffix in preferred)
