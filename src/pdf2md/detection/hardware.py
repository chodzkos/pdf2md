"""Wykrywanie sprzętu GPU i jego ograniczeń (gradacja dla `pdf2md doctor`).

Rozróżnia cztery stany, które prowadzą do różnych, *wykonalnych* komunikatów:

* ``ok`` — torch widzi działającą CUDA (mamy nazwę karty, VRAM, architekturę),
* ``driver_too_old`` — karta fizycznie jest, ale sterownik wspiera tylko CUDA < 13
  (torch jest skompilowany pod CUDA 13 → ``is_available()`` zwraca False mimo karty),
* ``no_gpu`` — brak karty NVIDIA (``nvidia-smi`` niedostępne) → tryb CPU,
* ``cuda_unavailable`` — ogólny fallback (karta jest, ale nie wpadła w powyższe).

ZERO nowych zależności: korzystamy z torcha (jeśli jest) i z ``nvidia-smi``
(subprocess), które doctor i tak woła do innych narzędzi. Funkcje są odporne na
brak narzędzi — nigdy nie rzucają.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass

# pdf2md instaluje torcha w wariancie +cu130 → do GPU potrzebny sterownik z CUDA 13.
REQUIRED_CUDA_MAJOR = 13


@dataclass(frozen=True)
class HardwareInfo:
    """Wynik wykrywania sprzętu GPU.

    Attributes:
        state: Jeden z ``ok`` / ``driver_too_old`` / ``no_gpu`` / ``cuda_unavailable``.
        name: Nazwa karty (pusta, gdy brak GPU).
        vram_gb: Pamięć karty w GiB (None, gdy nieznana / brak GPU).
        arch: Czytelna architektura, np. ``"Ampere (8.6)"`` (pusta dla stanów bez torcha).
        driver_cuda: Najwyższe CUDA wspierane przez sterownik, np. ``"12.2"`` (puste, gdy nieznane).
    """

    state: str
    name: str
    vram_gb: float | None
    arch: str
    driver_cuda: str


def _arch_label(capability: tuple[int, int]) -> str:
    """Mapuje compute capability na czytelną nazwę architektury."""
    major, minor = capability
    names = {
        (12, 0): "Blackwell",
        (9, 0): "Hopper",
        (8, 9): "Ada Lovelace",
        (8, 7): "Ampere",
        (8, 6): "Ampere",
        (8, 0): "Ampere",
        (7, 5): "Turing",
        (7, 2): "Volta",
        (7, 0): "Volta",
        (6, 1): "Pascal",
        (6, 0): "Pascal",
    }
    label = names.get((major, minor))
    if label is None and major <= 6:
        label = "Pascal lub starsza"
    return f"{label} ({major}.{minor})" if label else f"compute {major}.{minor}"


def _cuda_major(version: str) -> int | None:
    """Wyciąga główny numer wersji CUDA (np. ``"12.2"`` → 12)."""
    try:
        return int(version.split(".")[0])
    except (ValueError, IndexError, AttributeError):
        return None


def _probe_nvidia_smi() -> tuple[str, float | None, str] | None:
    """Pyta ``nvidia-smi`` o kartę. Zwraca (nazwa, vram_gb, cuda_sterownika) lub None.

    None oznacza brak fizycznej karty NVIDIA (``nvidia-smi`` niedostępne lub nie odpowiada) —
    traktujemy to jako tryb CPU, nie błąd krytyczny.
    """
    if not shutil.which("nvidia-smi"):
        return None
    name = ""
    vram_gb: float | None = None
    driver_cuda = ""
    try:
        query = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total,name", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return None
    lines = [ln for ln in (query.stdout or "").splitlines() if ln.strip()]
    if lines:
        parts = [p.strip() for p in lines[0].split(",")]
        if parts and parts[0]:
            try:
                vram_gb = round(float(parts[0]) / 1024, 1)  # MiB → GiB
            except ValueError:
                vram_gb = None
        if len(parts) > 1:
            name = parts[1]
    # Najwyższe CUDA sterownika czytamy z nagłówka gołego `nvidia-smi` (regex odporny na układ).
    try:
        plain = subprocess.run(["nvidia-smi"], capture_output=True, text=True, timeout=5)
        match = re.search(r"CUDA Version:\s*([0-9]+)\.([0-9]+)", plain.stdout or "")
        if match:
            driver_cuda = f"{match.group(1)}.{match.group(2)}"
    except Exception:
        pass
    return name, vram_gb, driver_cuda


def detect_hardware() -> HardwareInfo:
    """Wykrywa stan GPU z gradacją (CUDA OK / za stary sterownik / brak karty).

    Returns:
        :class:`HardwareInfo` — struktura opisująca wykryty sprzęt i jego ograniczenia.
    """
    try:
        import torch
    except Exception:
        torch = None

    # 1) Najpewniejsza ścieżka: torch ma działającą CUDA → pełne dane karty.
    if torch is not None:
        try:
            if torch.cuda.is_available():
                props = torch.cuda.get_device_properties(0)
                vram_gb = round(props.total_memory / 1024**3, 1)
                name = torch.cuda.get_device_name(0)
                arch = _arch_label(torch.cuda.get_device_capability(0))
                return HardwareInfo("ok", name, vram_gb, arch, "")
        except Exception:
            pass

    # 2) torch nie widzi CUDA — sprawdź, czy karta w ogóle istnieje (nvidia-smi).
    probe = _probe_nvidia_smi()
    if probe is None:
        return HardwareInfo("no_gpu", "", None, "", "")

    name, vram_gb, driver_cuda = probe
    torch_has_cuda = bool(getattr(getattr(torch, "version", None), "cuda", "")) if torch else False
    driver_major = _cuda_major(driver_cuda)

    # 3) Karta jest, torch ma CUDA, ale sterownik za stary → wykonalny komunikat o aktualizacji.
    if torch_has_cuda and driver_major is not None and driver_major < REQUIRED_CUDA_MAJOR:
        return HardwareInfo("driver_too_old", name, vram_gb, "", driver_cuda)

    # 4) Karta jest, ale nie wpadła w powyższe — ogólny fallback.
    return HardwareInfo("cuda_unavailable", name, vram_gb, "", driver_cuda)
