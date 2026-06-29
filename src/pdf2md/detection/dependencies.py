"""Wykrywanie dostępnych narzędzi systemowych i bibliotek.

Wszystkie funkcje są odporne na brak narzędzia — zwracają False/pusty dict,
nie rzucają wyjątków. Używane przez komendę `pdf2md doctor`.
"""

from __future__ import annotations

import platform
import shutil
import subprocess
from collections.abc import Callable
from functools import lru_cache
from typing import Any


def _default_version_parser(output: str) -> str:
    """Domyślny parser wersji: ostatni token pierwszej niepustej linii (np. ``tool 1.2.3``)."""
    for line in output.splitlines():
        if line.strip():
            return line.split()[-1]
    return ""


def probe_tool(
    name: str,
    version_args: list[str] | None = None,
    version_parser: Callable[[str], str] | None = None,
) -> dict[str, Any]:
    """Generyczna sonda narzędzia CLI dostępnego w PATH.

    Args:
        name: nazwa binarki szukanej przez ``shutil.which``.
        version_args: argumenty wywołania zwracającego wersję (np. ``["--version"]``).
            Gdy ``None`` — sprawdzamy tylko obecność w PATH, bez subprocessu.
        version_parser: opcjonalny parser wyjścia (stdout/stderr) na łańcuch wersji;
            domyślnie ostatni token pierwszej niepustej linii.

    Returns:
        Słownik ``{"available": bool, "version": str}``. Odporny na wyjątki — gdy binarka
        jest w PATH, lecz wywołanie wersji zawiedzie (timeout/OSError/parsowanie), zwraca
        ``available=False`` zamiast rzucać (jak reszta modułu).
    """
    result: dict[str, Any] = {"available": False, "version": ""}
    if shutil.which(name) is None:
        return result
    if not version_args:
        result["available"] = True
        return result
    parser = version_parser or _default_version_parser
    try:
        proc = subprocess.run(
            [name, *version_args],
            capture_output=True,
            text=True,
            timeout=5,
        )
        result["version"] = parser(proc.stdout or proc.stderr)
        result["available"] = True
    except Exception:
        pass
    return result


def check_tesseract() -> dict[str, Any]:
    """Sprawdza czy Tesseract OCR jest zainstalowany i zwraca jego wersję oraz języki.

    Returns:
        Słownik z kluczami: available (bool), version (str), languages (list[str]).
    """
    probe = probe_tool("tesseract", ["--version"])
    result: dict[str, Any] = {
        "available": probe["available"],
        "version": probe["version"],
        "languages": [],
    }
    if not probe["available"]:
        return result
    # --list-langs to rozszerzenie ponad generyczną sondę (sonda „bogatsza").
    try:
        lang_proc = subprocess.run(
            ["tesseract", "--list-langs"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        result["languages"] = [
            ln.strip()
            for ln in (lang_proc.stdout or lang_proc.stderr).splitlines()
            if ln.strip() and not ln.startswith("List")
        ]
    except Exception:
        pass
    return result


def check_poppler() -> bool:
    """Sprawdza czy pdftotext (część Poppler) jest dostępny w PATH."""
    return bool(probe_tool("pdftotext")["available"])


def check_pandoc() -> bool:
    """Sprawdza czy Pandoc jest dostępny w PATH."""
    return bool(probe_tool("pandoc")["available"])


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


@lru_cache(maxsize=1)
def cuda_usable() -> bool:
    """Sprawdza, czy CUDA jest nie tylko widoczna, ale wykonuje prosty kernel."""
    try:
        import torch
    except Exception:
        return False

    try:
        if not torch.cuda.is_available():
            return False
        tensor = torch.zeros(1).cuda()
        torch.cuda.synchronize()
        del tensor
    except Exception:
        return False
    return True


def check_gpu() -> dict[str, Any]:
    """Sprawdza dostępność GPU (CUDA przez PyTorch).

    Returns:
        Słownik z informacjami o PyTorch i CUDA.
    """
    result: dict[str, Any] = {
        "torch_available": False,
        "cuda_available": False,
        "cuda_usable": False,
        "device_name": "",
        "cuda_version": "",
    }
    try:
        import torch

        result["torch_available"] = True
        result["cuda_version"] = str(getattr(torch.version, "cuda", "") or "")
        if torch.cuda.is_available():
            result["cuda_available"] = True
            result["device_name"] = torch.cuda.get_device_name(0)
        result["cuda_usable"] = cuda_usable()
    except Exception:
        pass
    return result


def check_all() -> dict[str, Any]:
    """Zbiorczy raport stanu środowiska — używany przez `pdf2md doctor`."""
    return {
        "system": {
            "os": platform.system(),
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
        "tesseract": check_tesseract(),
        "poppler": check_poppler(),
        "pandoc": check_pandoc(),
        "ollama": check_ollama(),
        "gpu": check_gpu(),
    }
