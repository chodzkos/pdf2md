"""Testy detekcji GPU/CUDA oraz zbiorczego raportu środowiska."""

from __future__ import annotations

import builtins
import sys
from collections.abc import Generator
from types import SimpleNamespace
from typing import Any

import pytest

from pdf2md.detection import dependencies
from pdf2md.detection.dependencies import check_gpu, cuda_usable


class _FakeTensor:
    def __init__(self, kernel_raises: bool = False) -> None:
        self._kernel_raises = kernel_raises

    def cuda(self) -> _FakeTensor:
        if self._kernel_raises:
            raise RuntimeError("cudaErrorNoKernelImageForDevice")
        return self


class _FakeCuda:
    def __init__(self, available: bool = True, sync_raises: bool = False) -> None:
        self._available = available
        self._sync_raises = sync_raises
        self.synchronized = False

    def is_available(self) -> bool:
        return self._available

    def synchronize(self) -> None:
        if self._sync_raises:
            raise RuntimeError("CUDA synchronize failed")
        self.synchronized = True

    def get_device_name(self, _index: int) -> str:
        return "Fake CUDA"


class _FakeTorch:
    def __init__(
        self,
        available: bool = True,
        kernel_raises: bool = False,
        sync_raises: bool = False,
    ) -> None:
        self.cuda = _FakeCuda(available=available, sync_raises=sync_raises)
        self.version = SimpleNamespace(cuda="12.1")
        self._kernel_raises = kernel_raises
        self.zeros_calls = 0

    def zeros(self, _size: int) -> _FakeTensor:
        self.zeros_calls += 1
        return _FakeTensor(kernel_raises=self._kernel_raises)


@pytest.fixture(autouse=True)
def clear_cuda_usable_cache() -> Generator[None]:
    cuda_usable.cache_clear()
    yield
    cuda_usable.cache_clear()


def test_cuda_usable_false_when_torch_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Brak torch oznacza brak używalnej CUDA."""
    real_import = builtins.__import__

    def fake_import(name: str, *args: object, **kwargs: object) -> Any:
        if name == "torch":
            raise ImportError("torch missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.delitem(sys.modules, "torch", raising=False)
    monkeypatch.setattr(builtins, "__import__", fake_import)

    assert cuda_usable() is False


def test_cuda_usable_false_when_cuda_not_available(monkeypatch: pytest.MonkeyPatch) -> None:
    """Widoczność CUDA false nie uruchamia smoke testu."""
    fake_torch = _FakeTorch(available=False)
    monkeypatch.setitem(sys.modules, "torch", fake_torch)

    assert cuda_usable() is False
    assert fake_torch.zeros_calls == 0


def test_cuda_usable_runs_smoke_kernel(monkeypatch: pytest.MonkeyPatch) -> None:
    """CUDA jest używalna dopiero po udanym wykonaniu prostego kernela."""
    fake_torch = _FakeTorch(available=True)
    monkeypatch.setitem(sys.modules, "torch", fake_torch)

    assert cuda_usable() is True
    assert fake_torch.zeros_calls == 1
    assert fake_torch.cuda.synchronized is True


def test_cuda_usable_false_when_smoke_kernel_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stara karta z nieobsługiwanym kernelem zwraca false mimo is_available()."""
    fake_torch = _FakeTorch(available=True, kernel_raises=True)
    monkeypatch.setitem(sys.modules, "torch", fake_torch)

    assert cuda_usable() is False


def test_cuda_usable_result_is_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    """Smoke test nie powtarza się przy kolejnych wywołaniach."""
    fake_torch = _FakeTorch(available=True)
    monkeypatch.setitem(sys.modules, "torch", fake_torch)

    assert cuda_usable() is True
    assert cuda_usable() is True
    assert fake_torch.zeros_calls == 1


def test_check_gpu_reports_cuda_usable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Raport doctor zawiera wynik smoke testu CUDA."""
    fake_torch = _FakeTorch(available=True)
    monkeypatch.setitem(sys.modules, "torch", fake_torch)

    result = check_gpu()

    assert result["torch_available"] is True
    assert result["cuda_available"] is True
    assert result["cuda_usable"] is True
    assert result["device_name"] == "Fake CUDA"


def test_check_gpu_returns_defaults_when_torch_crashes(monkeypatch: pytest.MonkeyPatch) -> None:
    real_import = builtins.__import__

    def fake_import(name: str, *args: object, **kwargs: object) -> Any:
        if name == "torch":
            raise RuntimeError("broken torch")
        return real_import(name, *args, **kwargs)

    monkeypatch.delitem(sys.modules, "torch", raising=False)
    monkeypatch.setattr(builtins, "__import__", fake_import)

    result = dependencies.check_gpu()

    assert result["torch_available"] is False
    assert result["cuda_usable"] is False


def test_check_all_combines_reports(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dependencies.platform, "system", lambda: "Linux")
    monkeypatch.setattr(dependencies.platform, "platform", lambda: "Linux-test")
    monkeypatch.setattr(dependencies.platform, "python_version", lambda: "3.13")
    monkeypatch.setattr(
        dependencies,
        "check_tools",
        lambda: {"tesseract": {"available": False}, "poppler": True, "pandoc": False},
    )
    monkeypatch.setattr(dependencies, "check_ollama", lambda: {"available": True})
    monkeypatch.setattr(dependencies, "check_gpu", lambda: {"cuda_usable": False})

    assert dependencies.check_all() == {
        "system": {"os": "Linux", "platform": "Linux-test", "python": "3.13"},
        "tesseract": {"available": False},
        "poppler": True,
        "pandoc": False,
        "ollama": {"available": True},
        "gpu": {"cuda_usable": False},
    }
