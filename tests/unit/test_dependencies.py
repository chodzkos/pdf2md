"""Testy detekcji zależności środowiskowych."""

from __future__ import annotations

import builtins
import subprocess
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


def test_probe_tool_absent_when_not_in_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dependencies.shutil, "which", lambda _command: None)

    assert dependencies.probe_tool("widget", ["--version"]) == {
        "available": False,
        "version": "",
    }


def test_probe_tool_present_without_version_args(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dependencies.shutil, "which", lambda _command: "/usr/bin/widget")

    # Bez version_args sonda nie uruchamia subprocessu — sprawdza tylko obecność w PATH.
    def fail_run(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("subprocess nie powinien być wywołany")

    monkeypatch.setattr(dependencies.subprocess, "run", fail_run)

    assert dependencies.probe_tool("widget") == {"available": True, "version": ""}


def test_probe_tool_parses_version(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dependencies.shutil, "which", lambda _command: "/usr/bin/widget")

    def fake_run(
        command: list[str],
        *,
        capture_output: bool,
        text: bool,
        timeout: int,
    ) -> subprocess.CompletedProcess[str]:
        assert command == ["widget", "--version"]
        assert timeout == 5
        return subprocess.CompletedProcess(command, 0, stdout="widget 2.4.1\nfoo\n")

    monkeypatch.setattr(dependencies.subprocess, "run", fake_run)

    assert dependencies.probe_tool("widget", ["--version"]) == {
        "available": True,
        "version": "2.4.1",
    }


def test_probe_tool_custom_parser(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dependencies.shutil, "which", lambda _command: "/usr/bin/widget")
    monkeypatch.setattr(
        dependencies.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a[0], 0, stdout="ver=9.9\n"),
    )

    result = dependencies.probe_tool(
        "widget", ["--version"], version_parser=lambda out: out.split("=")[-1].strip()
    )

    assert result == {"available": True, "version": "9.9"}


def test_probe_tool_unavailable_when_version_call_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dependencies.shutil, "which", lambda _command: "/usr/bin/widget")

    def fake_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise OSError("boom")

    monkeypatch.setattr(dependencies.subprocess, "run", fake_run)

    assert dependencies.probe_tool("widget", ["--version"]) == {
        "available": False,
        "version": "",
    }


def test_check_tesseract_returns_version_and_languages(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tesseract raportuje wersje i dostepne jezyki."""
    monkeypatch.setattr(dependencies.shutil, "which", lambda command: "/usr/bin/tesseract")

    def fake_run(
        command: list[str],
        *,
        capture_output: bool,
        text: bool,
        timeout: int,
    ) -> subprocess.CompletedProcess[str]:
        assert capture_output is True
        assert text is True
        assert timeout == 5
        if command == ["tesseract", "--version"]:
            return subprocess.CompletedProcess(command, 0, stdout="tesseract 5.3.0\n")
        if command == ["tesseract", "--list-langs"]:
            return subprocess.CompletedProcess(
                command, 0, stdout="List of available languages\neng\npol\n"
            )
        raise AssertionError(command)

    monkeypatch.setattr(dependencies.subprocess, "run", fake_run)

    result = dependencies.check_tesseract()

    assert result == {"available": True, "version": "5.3.0", "languages": ["eng", "pol"]}


def test_check_tesseract_false_when_binary_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dependencies.shutil, "which", lambda _command: None)

    assert dependencies.check_tesseract() == {
        "available": False,
        "version": "",
        "languages": [],
    }


def test_check_tesseract_false_when_command_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dependencies.shutil, "which", lambda _command: "/usr/bin/tesseract")

    def fake_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise OSError("boom")

    monkeypatch.setattr(dependencies.subprocess, "run", fake_run)

    assert dependencies.check_tesseract()["available"] is False


def test_simple_binary_checks_use_shutil_which(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_which(command: str) -> str | None:
        return "/usr/bin/pdftotext" if command == "pdftotext" else None

    monkeypatch.setattr(dependencies.shutil, "which", fake_which)

    assert dependencies.check_poppler() is True
    assert dependencies.check_pandoc() is False


def test_check_ollama_returns_models(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResponse:
        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return b'{"models": [{"name": "qwen2.5:14b"}, {"name": "llama3"}]}'

    def fake_urlopen(url: str, *, timeout: int) -> FakeResponse:
        assert url == "http://localhost:11434/api/tags"
        assert timeout == 2
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    result = dependencies.check_ollama()

    assert result == {"available": True, "models": ["qwen2.5:14b", "llama3"]}


def test_check_ollama_false_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(*_args: object, **_kwargs: object) -> object:
        raise OSError("server down")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    assert dependencies.check_ollama() == {"available": False, "models": []}


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
    monkeypatch.setattr(dependencies, "check_tesseract", lambda: {"available": False})
    monkeypatch.setattr(dependencies, "check_poppler", lambda: True)
    monkeypatch.setattr(dependencies, "check_pandoc", lambda: False)
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
