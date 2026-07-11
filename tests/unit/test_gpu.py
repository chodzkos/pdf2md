"""Testy detekcji GPU/CUDA (cuda_usable smoke-kernel, check_gpu raport)."""

from __future__ import annotations

import builtins
import sys
from collections.abc import Generator
from types import SimpleNamespace
from typing import Any

import pytest

from pdf2md.detection.hardware import check_gpu, cuda_usable


class _FakeScalar:
    def __init__(self, value: float) -> None:
        self._value = value

    def item(self) -> float:
        return self._value


class _FakeTensor:
    def __init__(self, values: list[float], kernel_raises: bool = False) -> None:
        self._values = values
        self._kernel_raises = kernel_raises

    def __mul__(self, scalar: float) -> _FakeTensor:
        # Mnożenie elementwise = realny kernel SASS — na niewspieranej architekturze pada TU.
        if self._kernel_raises:
            raise RuntimeError("cudaErrorNoKernelImageForDevice")
        return _FakeTensor([v * scalar for v in self._values])

    def sum(self) -> _FakeScalar:
        return _FakeScalar(sum(self._values))


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
        wrong_result: bool = False,
    ) -> None:
        self.cuda = _FakeCuda(available=available, sync_raises=sync_raises)
        self.version = SimpleNamespace(cuda="12.1")
        self._kernel_raises = kernel_raises
        self._wrong_result = wrong_result
        self.ones_calls = 0

    def ones(self, size: int, device: str | None = None) -> _FakeTensor:
        self.ones_calls += 1
        # wrong_result: kernel „przechodzi", ale zwraca śmieci → weryfikacja wyniku ma dać False.
        base = 0.0 if self._wrong_result else 1.0
        return _FakeTensor([base] * size, kernel_raises=self._kernel_raises)


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
    assert fake_torch.ones_calls == 0


def test_cuda_usable_runs_smoke_kernel(monkeypatch: pytest.MonkeyPatch) -> None:
    """CUDA jest używalna dopiero po udanym wykonaniu prostego kernela."""
    fake_torch = _FakeTorch(available=True)
    monkeypatch.setitem(sys.modules, "torch", fake_torch)

    assert cuda_usable() is True
    assert fake_torch.ones_calls == 1
    assert fake_torch.cuda.synchronized is True


def test_cuda_usable_false_when_smoke_kernel_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stara karta z nieobsługiwanym kernelem: mnożenie rzuca (no kernel image) → False."""
    fake_torch = _FakeTorch(available=True, kernel_raises=True)
    monkeypatch.setitem(sys.modules, "torch", fake_torch)

    assert cuda_usable() is False


def test_cuda_usable_false_when_kernel_result_wrong(monkeypatch: pytest.MonkeyPatch) -> None:
    """Kernel „przechodzi", ale zwraca zły wynik (śmieci z GPU) → weryfikacja daje False.

    To sedno B19: sama alokacja/memcpy nie obnaża braku obrazu kernela; dopiero sprawdzenie
    wyniku realnej operacji (sum == 16.0) wyłapuje niewspieraną architekturę.
    """
    fake_torch = _FakeTorch(available=True, wrong_result=True)
    monkeypatch.setitem(sys.modules, "torch", fake_torch)

    assert cuda_usable() is False
    assert fake_torch.ones_calls == 1  # kernel odpalony, tylko wynik odrzucony


def test_cuda_usable_result_is_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    """Smoke test nie powtarza się przy kolejnych wywołaniach."""
    fake_torch = _FakeTorch(available=True)
    monkeypatch.setitem(sys.modules, "torch", fake_torch)

    assert cuda_usable() is True
    assert cuda_usable() is True
    assert fake_torch.ones_calls == 1


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

    result = check_gpu()

    assert result["torch_available"] is False
    assert result["cuda_usable"] is False
