"""Testy gradacji sprzętowej (wykrywanie GPU, pierwszeństwo compute_cap, stany)."""

from __future__ import annotations

import builtins
import subprocess
import sys
from types import SimpleNamespace
from typing import Any

import pytest

from pdf2md.detection import hardware
from pdf2md.detection.hardware import detect_hardware

# Domyślny build torcha +cu130 wspiera Turing wzwyż (min sm_75).
_DEFAULT_ARCH_LIST = ["sm_75", "sm_80", "sm_86", "sm_90", "sm_120"]


class _FakeProps:
    def __init__(self, total_memory: int) -> None:
        self.total_memory = total_memory


class _FakeCuda:
    def __init__(
        self,
        available: bool,
        total_memory: int = 0,
        capability: tuple[int, int] = (8, 6),
        name: str = "Fake GPU",
        arch_list: list[str] | None = None,
    ) -> None:
        self._available = available
        self._total_memory = total_memory
        self._capability = capability
        self._name = name
        self._arch_list = arch_list if arch_list is not None else _DEFAULT_ARCH_LIST

    def is_available(self) -> bool:
        return self._available

    def get_device_properties(self, _index: int) -> _FakeProps:
        return _FakeProps(self._total_memory)

    def get_device_name(self, _index: int) -> str:
        return self._name

    def get_device_capability(self, _index: int) -> tuple[int, int]:
        return self._capability

    def get_arch_list(self) -> list[str]:
        return self._arch_list


class _FakeTorch:
    def __init__(self, cuda: _FakeCuda, cuda_version: str = "13.0") -> None:
        self.cuda = cuda
        self.version = SimpleNamespace(cuda=cuda_version)


def _smi_runner(query_line: str, plain_stdout: str) -> Any:
    """Buduje atrapę subprocess.run dla obu wywołań nvidia-smi (query-gpu + goły nagłówek)."""

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if any(str(arg).startswith("--query-gpu") for arg in command):
            return subprocess.CompletedProcess(command, 0, stdout=query_line)
        return subprocess.CompletedProcess(command, 0, stdout=plain_stdout)

    return fake_run


def test_detect_hardware_ok_reads_vram_and_arch(monkeypatch: pytest.MonkeyPatch) -> None:
    """torch z działającą CUDA → stan ok + VRAM + architektura + compute_cap."""
    fake = _FakeTorch(_FakeCuda(available=True, total_memory=8 * 1024**3, capability=(8, 6)))
    monkeypatch.setitem(sys.modules, "torch", fake)

    info = detect_hardware()

    assert info.state == "ok"
    assert info.vram_gb == 8.0
    assert info.arch == "Ampere (8.6)"
    assert info.name == "Fake GPU"
    assert info.compute_cap == "8.6"


def test_detect_hardware_arch_too_old_when_cuda_available(monkeypatch: pytest.MonkeyPatch) -> None:
    """torch widzi CUDA, ale karta poniżej min(arch_list) → arch_too_old (wariant rzadki)."""
    fake = _FakeTorch(_FakeCuda(available=True, total_memory=8 * 1024**3, capability=(6, 1)))
    monkeypatch.setitem(sys.modules, "torch", fake)

    info = detect_hardware()

    assert info.state == "arch_too_old"
    assert info.compute_cap == "6.1"


def test_detect_hardware_arch_too_old_beats_old_driver(monkeypatch: pytest.MonkeyPatch) -> None:
    """KLUCZOWE: GTX 1070 (compute 6.1) + sterownik CUDA 12.7 → arch_too_old, NIE driver_too_old.

    compute_cap ma pierwszeństwo: aktualizacja sterownika nic nie da, bo architektura za stara.
    """
    fake = _FakeTorch(_FakeCuda(available=False), cuda_version="13.0")
    monkeypatch.setitem(sys.modules, "torch", fake)
    monkeypatch.setattr(hardware.shutil, "which", lambda _cmd: "/usr/bin/nvidia-smi")
    monkeypatch.setattr(
        hardware.subprocess,
        "run",
        _smi_runner(
            "NVIDIA GeForce GTX 1070, 8192, 6.1, 537.13\n",
            "Driver Version: 537.13   CUDA Version: 12.7 \n",
        ),
    )

    info = detect_hardware()

    assert info.state == "arch_too_old"  # NIE driver_too_old!
    assert info.name == "NVIDIA GeForce GTX 1070"
    assert info.vram_gb == 8.0
    assert info.compute_cap == "6.1"


def test_detect_hardware_driver_too_old(monkeypatch: pytest.MonkeyPatch) -> None:
    """Karta dość nowa (compute 8.6), torch ma CUDA, sterownik tylko 12.2 → driver_too_old."""
    fake = _FakeTorch(_FakeCuda(available=False), cuda_version="13.0")
    monkeypatch.setitem(sys.modules, "torch", fake)
    monkeypatch.setattr(hardware.shutil, "which", lambda _cmd: "/usr/bin/nvidia-smi")
    monkeypatch.setattr(
        hardware.subprocess,
        "run",
        _smi_runner(
            "NVIDIA GeForce RTX 3060, 12288, 8.6, 537.13\n",
            "Driver Version: 535.0   CUDA Version: 12.2 \n",
        ),
    )

    info = detect_hardware()

    assert info.state == "driver_too_old"
    assert info.driver_cuda == "12.2"
    assert info.name == "NVIDIA GeForce RTX 3060"
    assert info.vram_gb == 12.0


def test_detect_hardware_no_torch_with_card(monkeypatch: pytest.MonkeyPatch) -> None:
    """Brak torcha, ale nvidia-smi widzi kartę → no_torch z nazwą i VRAM (nie pusto)."""
    real_import = builtins.__import__

    def fake_import(name: str, *args: object, **kwargs: object) -> Any:
        if name == "torch":
            raise ImportError("torch missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.delitem(sys.modules, "torch", raising=False)
    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.setattr(hardware.shutil, "which", lambda _cmd: "/usr/bin/nvidia-smi")
    monkeypatch.setattr(
        hardware.subprocess,
        "run",
        _smi_runner("NVIDIA GeForce RTX 4070, 12288, 8.9, 537.13\n", "CUDA Version: 13.0\n"),
    )

    info = detect_hardware()

    assert info.state == "no_torch"
    assert info.name == "NVIDIA GeForce RTX 4070"
    assert info.vram_gb == 12.0


def test_detect_hardware_no_gpu_when_smi_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Brak nvidia-smi (i brak działającej CUDA) → no_gpu (tryb CPU)."""
    fake = _FakeTorch(_FakeCuda(available=False), cuda_version="13.0")
    monkeypatch.setitem(sys.modules, "torch", fake)
    monkeypatch.setattr(hardware.shutil, "which", lambda _cmd: None)

    info = detect_hardware()

    assert info.state == "no_gpu"
    assert info.vram_gb is None
    assert info.name == ""


def test_detect_hardware_no_gpu_when_torch_and_smi_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Brak torcha + brak nvidia-smi → no_gpu (brak karty wygrywa nad brakiem torcha)."""
    real_import = builtins.__import__

    def fake_import(name: str, *args: object, **kwargs: object) -> Any:
        if name == "torch":
            raise ImportError("torch missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.delitem(sys.modules, "torch", raising=False)
    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.setattr(hardware.shutil, "which", lambda _cmd: None)

    info = detect_hardware()

    assert info.state == "no_gpu"


def test_detect_hardware_cuda_unavailable_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Karta dość nowa, torch bez CUDA (cpu-only build) → ogólny fallback cuda_unavailable."""
    fake = _FakeTorch(_FakeCuda(available=False), cuda_version="")  # torch +cpu
    monkeypatch.setitem(sys.modules, "torch", fake)
    monkeypatch.setattr(hardware.shutil, "which", lambda _cmd: "/usr/bin/nvidia-smi")
    monkeypatch.setattr(
        hardware.subprocess,
        "run",
        _smi_runner("NVIDIA RTX A4000, 16384, 8.6, 537.13\n", "CUDA Version: 13.0\n"),
    )

    info = detect_hardware()

    assert info.state == "cuda_unavailable"
    assert info.name == "NVIDIA RTX A4000"


def test_detect_hardware_old_smi_without_compute_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    """Starszy nvidia-smi bez pola compute_cap (query zwraca błąd) → fallback nazwa+VRAM."""
    fake = _FakeTorch(_FakeCuda(available=False), cuda_version="13.0")
    monkeypatch.setitem(sys.modules, "torch", fake)
    monkeypatch.setattr(hardware.shutil, "which", lambda _cmd: "/usr/bin/nvidia-smi")

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        joined = " ".join(str(arg) for arg in command)
        if "compute_cap" in joined:  # starszy nvidia-smi nie zna tego pola → błąd
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="invalid field")
        if "--query-gpu" in joined:
            return subprocess.CompletedProcess(command, 0, stdout="NVIDIA RTX A4000, 16384\n")
        return subprocess.CompletedProcess(command, 0, stdout="CUDA Version: 12.2\n")

    monkeypatch.setattr(hardware.subprocess, "run", fake_run)

    info = detect_hardware()

    # compute_cap nieznane → nie arch_too_old; sterownik 12.2 < 13 → driver_too_old.
    assert info.state == "driver_too_old"
    assert info.name == "NVIDIA RTX A4000"
    assert info.vram_gb == 16.0
    assert info.compute_cap == ""


def test_arch_label_known_and_unknown() -> None:
    """Mapowanie compute capability na nazwy architektur."""
    assert hardware._arch_label((12, 0)) == "Blackwell (12.0)"
    assert hardware._arch_label((8, 9)) == "Ada Lovelace (8.9)"
    assert hardware._arch_label((6, 1)) == "Pascal (6.1)"
    assert hardware._arch_label((5, 2)) == "Pascal lub starsza (5.2)"
    assert hardware._arch_label((10, 3)) == "compute 10.3"


def test_min_supported_cap_parses_arch_list() -> None:
    """min(arch_list) liczone poprawnie (sm_120 = 12.0, nie 1.20); fallback (7,5)."""
    assert hardware._min_supported_cap(["sm_80", "sm_75", "sm_120"]) == (7, 5)
    assert hardware._min_supported_cap(["sm_90", "sm_120"]) == (9, 0)
    assert hardware._min_supported_cap([]) == (7, 5)
    assert hardware._min_supported_cap(None) == (7, 5)
