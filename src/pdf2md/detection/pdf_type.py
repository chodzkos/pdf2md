"""Prosta detekcja typu PDF na potrzeby dry-run CLI."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any


def detect_pdf_type(pdf_path: str) -> dict[str, Any]:
    """Rozpoznaje, czy PDF ma warstwę tekstową, czy wygląda jak skan.

    Funkcja jest celowo defensywna: gdy PyMuPDF nie jest dostępny albo plik jest
    uszkodzony, zwraca typ ``unknown`` zamiast przerywać dry-run.
    """
    path = Path(pdf_path)
    result: dict[str, Any] = {
        "type": "unknown",
        "pages": 0,
        "text_pages": 0,
        "scan_pages": 0,
        "reason": "",
    }
    if not path.exists():
        result["reason"] = "plik nie istnieje"
        return result

    try:
        pymupdf = importlib.import_module("pymupdf")
        doc = pymupdf.open(str(path))
        try:
            result["pages"] = len(doc)
            for page in doc:
                text = page.get_text("text").strip()
                if text:
                    result["text_pages"] += 1
                else:
                    result["scan_pages"] += 1
        finally:
            doc.close()
    except Exception as exc:
        result["reason"] = str(exc)
        return result

    pages = int(result["pages"])
    text_pages = int(result["text_pages"])
    scan_pages = int(result["scan_pages"])
    if pages == 0:
        result["type"] = "unknown"
    elif text_pages == pages:
        result["type"] = "native"
    elif scan_pages == pages:
        result["type"] = "scanned"
    else:
        result["type"] = "mixed"
    return result
