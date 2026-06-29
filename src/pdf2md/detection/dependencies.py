"""Zbiorczy raport środowiska dla `pdf2md doctor`.

Sondy narzędzi CLI i usług sieciowych pochodzą z pakietu `chodzkos_detection`
(stdlib-only), a detekcja sprzętu z lokalnego `pdf2md.detection.hardware`;
tu pozostaje agregator `check_all`. Funkcje są odporne na brak narzędzia.
"""

from __future__ import annotations

import platform
from typing import Any

from chodzkos_detection import check_ollama, check_tools

from pdf2md.detection.hardware import check_gpu  # LOKALNY (sprzęt) — celowo nie z pakietu


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
