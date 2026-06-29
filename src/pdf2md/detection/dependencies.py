"""Zbiorczy raport środowiska dla `pdf2md doctor`.

Sondy narzędzi CLI mieszkają w `pdf2md.detection.tools`, a usług sieciowych
w `pdf2md.detection.services`; tu pozostaje agregator `check_all`.
Wszystkie funkcje są odporne na brak narzędzia — nie rzucają wyjątków.
"""

from __future__ import annotations

import platform
from typing import Any

from pdf2md.detection.hardware import check_gpu
from pdf2md.detection.services import check_ollama
from pdf2md.detection.tools import check_tools


def check_all() -> dict[str, Any]:
    """Zbiorczy raport stanu środowiska — używany przez `pdf2md doctor`."""
    return {
        "system": {
            "os": platform.system(),
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
        **check_tools(),
        "ollama": check_ollama(),
        "gpu": check_gpu(),
    }
