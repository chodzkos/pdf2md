"""Testy gradacji sprzętowej (wykrywanie GPU i ograniczeń sterownika)."""

from __future__ import annotations

import builtins
import subprocess
import sys
from types import SimpleNamespace
from typing import Any

import pytest

from pdf2md.detection import hardware
from pdf2md.detection.hardware import detect_hardware


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
    ) -> None:
        self._available = available
        self._total_memory = total_memory
        self._capability = capability
        self._name = name

    def is_available(self) -> bool:
        return self._available

    def get_device_properties(self, _index: int) -> _FakeProps:
        return _FakeProps(self._total_memory)

    def get_device_name(self, _index: int) -> str:
        return self._name

    def get_device_capability(self, _index: int) -> tuple[int, int]:
        return self._capability


class _FakeTorch:
    def __init__(self, cuda: _FakeCuda, cuda_version: str = "13.0") -> None:
        self.cuda = cuda
        self.version = SimpleNamespace(cuda=cuda_version)


def _smi_runner(memory_name_line: str, plain_stdout: str) -> Any:
    """Buduje atrapę subprocess.run dla obu wywołań nvidia-smi."""

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if "--query-gpu=memory.total,name" in command:
            return subprocess.CompletedProcess(command, 0, stdout=memory_name_line)
        return subprocess.CompletedProcess(command, 0, stdout=plain_stdout)

    return fake_run


def test_detect_hardware_ok_reads_vram_and_arch(monkeypatch: pytest.MonkeyPatch) -> None:
    """torch z działającą CUDA → stan ok + VRAM + architektura."""
    fake = _FakeTorch(_FakeCuda(available=True, total_memory=8 * 1024**3, capability=(8, 6)))
    monkeypatch.setitem(sys.modules, "torch", fake)

    info = detect_hardware()

    assert info.state == "ok"
    assert info.vram_gb == 8.0
    assert info.arch == "Ampere (8.6)"
    assert info.name == "Fake GPU"


def test_detect_hardware_driver_too_old(monkeypatch: pytest.MonkeyPatch) -> None:
    """Karta jest, torch ma CUDA, sterownik wspiera tylko 12.2 → driver_too_old."""
    fake = _FakeTorch(_FakeCuda(available=False), cuda_version="13.0")
    monkeypatch.setitem(sys.modules, "torch", fake)
    monkeypatch.setattr(hardware.shutil, "which", lambda _cmd: "/usr/bin/nvidia-smi")
    monkeypatch.setattr(
        hardware.subprocess,
        "run",
        _smi_runner(
            "24576, NVIDIA GeForce RTX 3090\n",
            "Driver Version: 535.0   CUDA Version: 12.2 \n",
        ),
    )

    info = detect_hardware()

    assert info.state == "driver_too_old"
    assert info.driver_cuda == "12.2"
    assert info.name == "NVIDIA GeForce RTX 3090"
    assert info.vram_gb == 24.0


def test_detect_hardware_no_gpu_when_smi_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Brak nvidia-smi (i brak działającej CUDA) → no_gpu (tryb CPU)."""
    fake = _FakeTorch(_FakeCuda(available=False), cuda_version="13.0")
    monkeypatch.setitem(sys.modules, "torch", fake)
    monkeypatch.setattr(hardware.shutil, "which", lambda _cmd: None)

    info = detect_hardware()

    assert info.state == "no_gpu"
    assert info.vram_gb is None
    assert info.name == ""


def test_detect_hardware_no_gpu_when_torch_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Brak torcha + brak nvidia-smi → no_gpu, bez wyjątku."""
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
    """Karta jest, ale torch bez CUDA (cpu-only build) → ogólny fallback cuda_unavailable."""
    fake = _FakeTorch(_FakeCuda(available=False), cuda_version="")  # torch +cpu
    monkeypatch.setitem(sys.modules, "torch", fake)
    monkeypatch.setattr(hardware.shutil, "which", lambda _cmd: "/usr/bin/nvidia-smi")
    monkeypatch.setattr(
        hardware.subprocess,
        "run",
        _smi_runner("16384, NVIDIA RTX A4000\n", "CUDA Version: 13.0\n"),
    )

    info = detect_hardware()

    assert info.state == "cuda_unavailable"
    assert info.name == "NVIDIA RTX A4000"


def test_arch_label_known_and_unknown() -> None:
    """Mapowanie compute capability na nazwy architektur."""
    assert hardware._arch_label((12, 0)) == "Blackwell (12.0)"
    assert hardware._arch_label((8, 9)) == "Ada Lovelace (8.9)"
    assert hardware._arch_label((6, 1)) == "Pascal (6.1)"
    assert hardware._arch_label((5, 2)) == "Pascal lub starsza (5.2)"
    assert hardware._arch_label((10, 3)) == "compute 10.3"
