"""Testy bezpiecznego otwierania sciezek w menedzerze plikow."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from pdf2md.utils import open_path


def _set_platform(
    monkeypatch: pytest.MonkeyPatch,
    system: str,
    release: str = "generic",
) -> None:
    monkeypatch.setattr(open_path.platform, "system", lambda: system)
    monkeypatch.setattr(open_path.platform, "uname", lambda: SimpleNamespace(release=release))


def test_open_in_file_manager_logs_when_linux_tool_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Brak xdg-open nie rzuca wyjatku i nie probuje uruchamiac procesu."""
    warnings: list[str] = []
    _set_platform(monkeypatch, "Linux")
    monkeypatch.setattr(open_path.shutil, "which", lambda _name: None)
    monkeypatch.setattr(open_path, "logger", SimpleNamespace(warning=warnings.append))

    def fail_popen(_command: list[str]) -> None:
        raise AssertionError("subprocess.Popen nie powinien zostac wywolany")

    monkeypatch.setattr(open_path.subprocess, "Popen", fail_popen)

    assert open_path.open_in_file_manager("/tmp/out") is False
    assert warnings


def test_open_in_file_manager_uses_explorer_on_wsl_without_wslview(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """WSL bez wslview uzywa explorer.exe i nie sprawdza jego kodu wyjscia."""
    calls: list[list[str]] = []
    _set_platform(monkeypatch, "Linux", release="5.15.90.1-microsoft-standard-WSL2")
    monkeypatch.setattr(open_path.shutil, "which", lambda _name: None)
    monkeypatch.setattr(open_path.subprocess, "Popen", lambda command: calls.append(command))

    assert open_path.open_in_file_manager("/tmp/out") is True
    assert calls == [["explorer.exe", "/tmp/out"]]


def test_open_in_file_manager_prefers_wslview_on_wsl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """WSL uzywa wslview, jesli jest dostepne."""
    calls: list[list[str]] = []
    _set_platform(monkeypatch, "Linux", release="5.15.90.1-microsoft-standard-WSL2")
    monkeypatch.setattr(
        open_path.shutil,
        "which",
        lambda name: "/usr/bin/wslview" if name == "wslview" else None,
    )
    monkeypatch.setattr(open_path.subprocess, "Popen", lambda command: calls.append(command))

    assert open_path.open_in_file_manager("/tmp/out") is True
    assert calls == [["wslview", "/tmp/out"]]


def test_open_in_file_manager_uses_xdg_open_on_linux(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Zwykly Linux uzywa xdg-open, jesli jest dostepne."""
    calls: list[list[str]] = []
    _set_platform(monkeypatch, "Linux", release="6.1.0-generic")
    monkeypatch.setattr(
        open_path.shutil,
        "which",
        lambda name: "/usr/bin/xdg-open" if name == "xdg-open" else None,
    )
    monkeypatch.setattr(open_path.subprocess, "Popen", lambda command: calls.append(command))

    assert open_path.open_in_file_manager("/tmp/out") is True
    assert calls == [["xdg-open", "/tmp/out"]]


def test_open_in_file_manager_uses_os_startfile_on_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Windows uzywa os.startfile."""
    calls: list[str] = []
    _set_platform(monkeypatch, "Windows")
    monkeypatch.setattr(open_path.os, "startfile", calls.append, raising=False)

    assert open_path.open_in_file_manager("C:/out") is True
    assert calls == ["C:/out"]


def test_open_in_file_manager_catches_process_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FileNotFoundError z procesu jest logowany i nie wychodzi poza helper."""
    warnings: list[str] = []
    _set_platform(monkeypatch, "Linux", release="6.1.0-generic")
    monkeypatch.setattr(open_path.shutil, "which", lambda _name: "/usr/bin/xdg-open")
    monkeypatch.setattr(open_path, "logger", SimpleNamespace(warning=warnings.append))

    def fail_popen(_command: list[str]) -> None:
        raise FileNotFoundError("xdg-open")

    monkeypatch.setattr(open_path.subprocess, "Popen", fail_popen)

    assert open_path.open_in_file_manager("/tmp/out") is False
    assert warnings
