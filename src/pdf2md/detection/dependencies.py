"""Wykrywanie dostępnych narzędzi systemowych i bibliotek.

Wszystkie funkcje są odporne na brak narzędzia — zwracają False/pusty dict,
nie rzucają wyjątków. Używane przez komendę `pdf2md doctor`.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import Any


def check_tesseract() -> dict[str, Any]:
    """Sprawdza czy Tesseract OCR jest zainstalowany i zwraca jego wersję oraz języki.

    Returns:
        Słownik z kluczami: available (bool), version (str), languages (list[str]).
    """
    result: dict[str, Any] = {"available": False, "version": "", "languages": []}
    if not shutil.which("tesseract"):
        return result
    try:
        proc = subprocess.run(
            ["tesseract", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        first_line = (proc.stdout or proc.stderr).splitlines()[0]
        result["version"] = first_line.split()[-1] if first_line else ""

        lang_proc = subprocess.run(
            ["tesseract", "--list-langs"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        langs = [
            ln.strip()
            for ln in (lang_proc.stdout or lang_proc.stderr).splitlines()
            if ln.strip() and not ln.startswith("List")
        ]
        result["languages"] = langs
        result["available"] = True
    except Exception:
        pass
    return result


def check_poppler() -> bool:
    """Sprawdza czy pdftotext (część Poppler) jest dostępny w PATH."""
    return shutil.which("pdftotext") is not None


def check_pandoc() -> bool:
    """Sprawdza czy Pandoc jest dostępny w PATH."""
    return shutil.which("pandoc") is not None


def check_ollama() -> dict[str, Any]:
    """Sprawdza czy serwer Ollama działa i zwraca listę dostępnych modeli.

    Returns:
        Słownik z kluczami: available (bool), models (list[str]).
    """
    result: dict[str, Any] = {"available": False, "models": []}
    try:
        import urllib.request

        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2) as resp:
            import json

            data = json.loads(resp.read())
            result["models"] = [m["name"] for m in data.get("models", [])]
            result["available"] = True
    except Exception:
        pass
    return result


def check_gpu() -> dict[str, Any]:
    """Sprawdza dostępność GPU (CUDA przez PyTorch).

    Returns:
        Słownik z kluczami: cuda_available (bool), device_name (str).
    """
    result: dict[str, Any] = {"cuda_available": False, "device_name": ""}
    try:
        import torch

        if torch.cuda.is_available():
            result["cuda_available"] = True
            result["device_name"] = torch.cuda.get_device_name(0)
    except Exception:
        pass
    return result


def check_all() -> dict[str, Any]:
    """Zbiorczy raport stanu środowiska — używany przez `pdf2md doctor`."""
    return {
        "tesseract": check_tesseract(),
        "poppler": check_poppler(),
        "pandoc": check_pandoc(),
        "ollama": check_ollama(),
        "gpu": check_gpu(),
    }
