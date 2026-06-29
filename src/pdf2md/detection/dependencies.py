"""Wykrywanie GPU/CUDA oraz zbiorczy raport środowiska dla `pdf2md doctor`.

Sondy narzędzi CLI mieszkają w `pdf2md.detection.tools`, a usług sieciowych
w `pdf2md.detection.services`; tu pozostaje detekcja GPU oraz agregator `check_all`.
Wszystkie funkcje są odporne na brak narzędzia — nie rzucają wyjątków.
"""

from __future__ import annotations

import platform
from functools import lru_cache
from typing import Any

from pdf2md.detection.services import check_ollama
from pdf2md.detection.tools import check_tools


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
        **check_tools(),
        "ollama": check_ollama(),
        "gpu": check_gpu(),
    }
