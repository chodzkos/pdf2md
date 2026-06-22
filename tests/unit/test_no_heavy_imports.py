"""Regresja: moduły silników i helpery NIE importują ciężkich third-party na starcie.

Sprawdzane w izolowanym subprocess (świeży interpreter), bo w głównym procesie inne testy
mogły już zaimportować cv2/pymupdf/surya itd. To łapie ponowne dodanie top-level importu
ciężkiej zależności w przyszłości.
"""

from __future__ import annotations

import json
import subprocess
import sys

# Ciężkie third-party, które NIE mogą trafić do sys.modules przy zwykłym imporcie pakietu.
_FORBIDDEN = ["cv2", "pymupdf", "fitz", "surya", "marker", "docling"]


def _heavy_after_import(import_stmt: str) -> set[str]:
    """W świeżym subprocess wykonuje import_stmt i zwraca, które ciężkie moduły wczytał."""
    code = (
        f"{import_stmt}\n"
        "import sys, json\n"
        f"forbidden = {_FORBIDDEN!r}\n"
        "print(json.dumps([m for m in forbidden if m in sys.modules]))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
    )
    return set(json.loads(result.stdout.strip().splitlines()[-1]))


def test_importing_engines_pulls_no_heavy_libs() -> None:
    """`import pdf2md.engines` (cały rejestr silników) nie ciągnie cv2/pymupdf/surya/...."""
    assert _heavy_after_import("import pdf2md.engines") == set()


def test_importing_preprocessing_pulls_no_heavy_libs() -> None:
    """`import pdf2md.scan.preprocessing` działa bez wczytania cv2/pymupdf."""
    assert _heavy_after_import("import pdf2md.scan.preprocessing") == set()


def test_importing_vlm_base_pulls_no_heavy_libs() -> None:
    """Baza VLM importowalna bez torch/cv2/surya na starcie."""
    assert _heavy_after_import("import pdf2md.engines.vlm_base") == set()
