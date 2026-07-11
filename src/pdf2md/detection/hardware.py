"""Wykrywanie sprzętu GPU i jego ograniczeń (gradacja dla `pdf2md doctor`).

Rozróżnia sześć stanów, które prowadzą do różnych, *wykonalnych* komunikatów:

* ``ok`` — torch widzi działającą CUDA (mamy nazwę karty, VRAM, architekturę),
* ``arch_too_old`` — karta jest, ale architektura jest sprzed Turinga (compute < 7.5);
  build cu130 nie ma dla niej kerneli → tryb CPU, a aktualizacja sterownika NIE pomoże,
* ``driver_too_old`` — karta jest i jest dość nowa (compute ≥ 7.5), ale sterownik wspiera
  tylko CUDA < 13 (torch +cu130 → ``is_available()`` False mimo karty) → aktualizacja POMOŻE,
* ``no_torch`` — PyTorch nie jest importowalny w tym środowisku (zły venv / brak zależności);
  nazwę i VRAM karty nadal próbujemy odczytać z ``nvidia-smi``,
* ``no_gpu`` — brak karty NVIDIA (``nvidia-smi`` niedostępne) → tryb CPU,
* ``cuda_unavailable`` — ogólny fallback (karta jest, ale nie wpadła w powyższe).

KOLEJNOŚĆ jest krytyczna: ``compute_cap`` ma PIERWSZEŃSTWO przed wersją sterownika. Karta
sprzed Turinga (np. GTX 1070, compute 6.1) ze sterownikiem raportującym CUDA 12.7 to
``arch_too_old`` (karta za stara), NIE ``driver_too_old`` — aktualizacja sterownika nic nie da.

ZERO nowych zależności: korzystamy z torcha (jeśli jest) i z ``nvidia-smi`` (subprocess),
które doctor i tak woła. Funkcje są odporne na brak narzędzi — nigdy nie rzucają.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from pdf2md.utils.subprocess_flags import NO_WINDOW_FLAGS

# pdf2md instaluje torcha w wariancie +cu130 → do GPU potrzebny sterownik z CUDA 13.
REQUIRED_CUDA_MAJOR = 13
# Minimum architektury dla buildu +cu130 — Turing (sm_75). Niżej (Pascal/Volta) = brak kerneli.
MIN_COMPUTE_CAP = (7, 5)


@dataclass(frozen=True)
class HardwareInfo:
    """Wynik wykrywania sprzętu GPU.

    Attributes:
        state: ``ok`` / ``arch_too_old`` / ``driver_too_old`` / ``no_torch`` / ``no_gpu`` /
            ``cuda_unavailable``.
        name: Nazwa karty (pusta, gdy brak GPU).
        vram_gb: Pamięć karty w GiB (None, gdy nieznana / brak GPU).
        arch: Czytelna architektura, np. ``"Ampere (8.6)"`` (pusta dla stanów bez tej informacji).
        driver_cuda: Najwyższe CUDA wspierane przez sterownik, np. ``"12.2"`` (puste, gdy nieznane).
        compute_cap: Compute capability karty, np. ``"6.1"`` (puste, gdy nieznane).
    """

    state: str
    name: str
    vram_gb: float | None
    arch: str
    driver_cuda: str
    compute_cap: str = ""


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


def _parse_cap(value: str) -> tuple[int, int] | None:
    """Parsuje compute capability ``"X.Y"`` → ``(X, Y)``; None gdy nieznane/niepoprawne."""
    try:
        major, minor = value.split(".")
        return int(major), int(minor)
    except (ValueError, AttributeError):
        return None


def is_compute_cap_too_old(compute_cap: str) -> bool:
    """True, gdy ZNANA compute capability jest poniżej minimum buildu cu130 (Turing 7.5).

    Zwraca False, gdy compute_cap jest nieznane/niepoprawne — nie zgadujemy „za stara".
    """
    cap = _parse_cap(compute_cap)
    return cap is not None and cap < MIN_COMPUTE_CAP


def _min_supported_cap(arch_list: Any) -> tuple[int, int]:
    """Minimalna compute capability wspierana przez build torcha (z ``get_arch_list``).

    Lista wygląda jak ``["sm_75", "sm_80", "sm_120", ...]`` (ostatnia cyfra = minor).
    Fallback ``(7, 5)`` (Turing), gdy lista pusta/niedostępna.
    """
    caps: list[tuple[int, int]] = []
    try:
        for entry in arch_list or []:
            match = re.fullmatch(r"sm_(\d+)", str(entry))
            if match:
                digits = match.group(1)
                caps.append((int(digits[:-1]), int(digits[-1])))
    except Exception:
        return MIN_COMPUTE_CAP
    return min(caps) if caps else MIN_COMPUTE_CAP


def _smi_query(fields: list[str]) -> str | None:
    """Uruchamia ``nvidia-smi --query-gpu``; zwraca pierwszy niepusty wiersz stdout lub None.

    None, gdy nvidia-smi nie odpowiada albo zwraca błąd (np. nieobsługiwane pole na starszej
    wersji) — dzwoniący może wtedy spróbować węższego zapytania.
    """
    try:
        proc = subprocess.run(
            ["nvidia-smi", f"--query-gpu={','.join(fields)}", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=NO_WINDOW_FLAGS,
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    lines = [ln for ln in (proc.stdout or "").splitlines() if ln.strip()]
    return lines[0] if lines else None


def _read_driver_cuda() -> str:
    """Najwyższe CUDA sterownika z nagłówka gołego ``nvidia-smi`` (puste, gdy nieznane)."""
    try:
        plain = subprocess.run(
            ["nvidia-smi"],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=NO_WINDOW_FLAGS,
        )
        match = re.search(r"CUDA Version:\s*([0-9]+)\.([0-9]+)", plain.stdout or "")
        if match:
            return f"{match.group(1)}.{match.group(2)}"
    except Exception:
        pass
    return ""


def _probe_nvidia_smi() -> tuple[str, float | None, str, str] | None:
    """Pyta ``nvidia-smi`` o kartę. Zwraca (nazwa, vram_gb, compute_cap, cuda_sterownika) lub None.

    Najpierw JEDNO zapytanie o name+memory+compute_cap+driver_version; gdy starszy nvidia-smi nie
    zna ``compute_cap`` (błąd), spada do węższego zapytania (nazwa+VRAM) i compute_cap zostaje
    nieznane. None oznacza brak fizycznej karty (tryb CPU, nie błąd krytyczny).
    """
    if not shutil.which("nvidia-smi"):
        return None
    line = _smi_query(["name", "memory.total", "compute_cap", "driver_version"])
    has_cap = line is not None
    if line is None:
        line = _smi_query(["name", "memory.total"])  # starszy nvidia-smi bez compute_cap
    if line is None:
        return None
    parts = [p.strip() for p in line.split(",")]
    name = parts[0] if parts and parts[0] else ""
    vram_gb: float | None = None
    if len(parts) > 1:
        try:
            vram_gb = round(float(parts[1]) / 1024, 1)  # MiB → GiB
        except ValueError:
            vram_gb = None
    compute_cap = ""
    if has_cap and len(parts) > 2 and parts[2] and not parts[2].startswith("["):
        compute_cap = parts[2]  # "[Not Supported]"/"[N/A]" → traktujemy jako nieznane
    return name, vram_gb, compute_cap, _read_driver_cuda()


def _import_torch() -> Any:
    """Importuje torcha lub zwraca None (Any, by reszta funkcji była niezależna od stubów)."""
    try:
        import torch

        return torch
    except Exception:
        return None


def detect_hardware() -> HardwareInfo:
    """Wykrywa stan GPU z gradacją (compute_cap ma pierwszeństwo przed sterownikiem).

    Returns:
        :class:`HardwareInfo` — struktura opisująca wykryty sprzęt i jego ograniczenia.
    """
    torch = _import_torch()

    # 1) Najpewniejsza ścieżka: torch ma działającą CUDA → pełne dane karty.
    if torch is not None:
        try:
            if torch.cuda.is_available():
                props = torch.cuda.get_device_properties(0)
                vram_gb = round(props.total_memory / 1024**3, 1)
                name = torch.cuda.get_device_name(0)
                cap = torch.cuda.get_device_capability(0)
                compute_cap = f"{cap[0]}.{cap[1]}"
                arch = _arch_label(cap)
                # Rzadkie: karta poniżej minimum z arch_list buildu torcha.
                if tuple(cap) < _min_supported_cap(torch.cuda.get_arch_list()):
                    return HardwareInfo("arch_too_old", name, vram_gb, arch, "", compute_cap)
                return HardwareInfo("ok", name, vram_gb, arch, "", compute_cap)
        except Exception:
            pass

    # 2) Bez działającej CUDA — czy karta fizycznie istnieje (nvidia-smi)?
    probe = _probe_nvidia_smi()
    if probe is None:
        return HardwareInfo("no_gpu", "", None, "", "", "")
    name, vram_gb, compute_cap, driver_cuda = probe

    # 3) torch w ogóle nieobecny, a karta jest → no_torch (nazwa/VRAM z nvidia-smi).
    if torch is None:
        return HardwareInfo("no_torch", name, vram_gb, "", driver_cuda, compute_cap)

    # 4) Karta jest, torch jest, CUDA nie działa. compute_cap MA PIERWSZEŃSTWO przed sterownikiem.
    cap_tuple = _parse_cap(compute_cap)
    try:
        arch_list = torch.cuda.get_arch_list()
    except Exception:
        arch_list = []
    if cap_tuple is not None and cap_tuple < _min_supported_cap(arch_list):
        # 4a) Karta za stara — aktualizacja sterownika NIE pomoże.
        return HardwareInfo("arch_too_old", name, vram_gb, _arch_label(cap_tuple), "", compute_cap)

    # 4b) Karta dość nowa (lub compute_cap nieznane), ale sterownik < CUDA 13 → aktualizacja pomoże.
    torch_has_cuda = bool(getattr(getattr(torch, "version", None), "cuda", ""))
    driver_major = _cuda_major(driver_cuda)
    if torch_has_cuda and driver_major is not None and driver_major < REQUIRED_CUDA_MAJOR:
        return HardwareInfo("driver_too_old", name, vram_gb, "", driver_cuda, compute_cap)

    # 4c) Ogólny fallback.
    return HardwareInfo("cuda_unavailable", name, vram_gb, "", driver_cuda, compute_cap)


@lru_cache(maxsize=1)
def cuda_usable() -> bool:
    """Sprawdza, czy CUDA wykonuje REALNY kernel (nie tylko alokację), i zwraca poprawny wynik.

    Sama alokacja/`memcpy` (`torch.zeros(1).cuda()` + `synchronize`) NIE wymaga kernela SASS, więc
    na kartach nieobsługiwanych przez dany build (np. Pascal sm_61 + cu130) przechodziła, choć
    każdy realny kernel pada `AcceleratorError: no kernel image is available`. Dlatego odpalamy
    prawdziwą operację elementwise i weryfikujemy wynik — dopiero to obnaża brak obrazu kernela.
    """
    try:
        import torch
    except Exception:
        return False

    try:
        if not torch.cuda.is_available():
            return False
        tensor = torch.ones(8, device="cuda") * 2  # realny kernel elementwise (nie sama alokacja)
        ok = float(tensor.sum().item()) == 16.0  # .item() synchronizuje i ściąga wynik z GPU
        torch.cuda.synchronize()
        del tensor
        return ok
    except Exception:
        return False


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
