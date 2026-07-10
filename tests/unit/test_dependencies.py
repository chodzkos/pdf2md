"""Testy zbiorczego raportu środowiska."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from pdf2md.detection import dependencies


class _FakeRegKey:
    """Minimalny odpowiednik uchwytu winreg (kontekst + dzieci + wartości)."""

    def __init__(
        self,
        children: dict[str, _FakeRegKey] | None = None,
        values: dict[str, str] | None = None,
    ) -> None:
        self.children = children or {}
        self.values = values or {}

    def __enter__(self) -> _FakeRegKey:
        return self

    def __exit__(self, *_exc: object) -> bool:
        return False


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
    monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/ebook-convert")

    assert dependencies.check_all() == {
        "system": {"os": "Linux", "platform": "Linux-test", "python": "3.13"},
        "tesseract": {"available": False},
        "poppler": True,
        "pandoc": False,
        "calibre": True,
        "ollama": {"available": True},
        "gpu": {"cuda_usable": False},
    }


def test_check_calibre_true_when_ebook_convert_in_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("shutil.which", lambda name: "/opt/calibre/ebook-convert")

    assert dependencies.check_calibre() is True


def test_check_calibre_false_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("shutil.which", lambda name: None)

    assert dependencies.check_calibre() is False


def test_calibre_path_returns_find_tool_result(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dependencies, "find_tool", lambda name, extra=(): "/x/ebook-convert")

    assert dependencies.calibre_path() == "/x/ebook-convert"
    assert dependencies.check_calibre() is True


def test_calibre_path_none_when_find_tool_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dependencies, "find_tool", lambda name, extra=(): None)

    assert dependencies.calibre_path() is None
    assert dependencies.check_calibre() is False


def test_calibre_path_passes_registry_and_known_dirs_to_find_tool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(dependencies, "_calibre_registry_paths", lambda: ["/reg/ebook-convert.exe"])
    monkeypatch.setattr(dependencies, "_calibre_known_dirs", lambda: ["/known/ebook-convert.exe"])
    seen: dict[str, object] = {}

    def fake_find(name: str, extra: object = ()) -> str | None:
        seen["name"] = name
        seen["extra"] = list(extra)  # type: ignore[arg-type]
        return None

    monkeypatch.setattr(dependencies, "find_tool", fake_find)

    dependencies.calibre_path()

    # Kolejność: rejestr przed znanymi katalogami (PATH obsługuje sam find_tool).
    assert seen["name"] == "ebook-convert"
    assert seen["extra"] == ["/reg/ebook-convert.exe", "/known/ebook-convert.exe"]


def test_calibre_registry_and_known_dirs_empty_off_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(dependencies.sys, "platform", "linux")

    assert dependencies._calibre_registry_paths() == []
    assert dependencies._calibre_known_dirs() == []


def test_calibre_registry_reads_install_location(monkeypatch: pytest.MonkeyPatch) -> None:
    calibre = _FakeRegKey(
        values={"DisplayName": "calibre 64bit", "InstallLocation": "/opt/Calibre2"}
    )
    other = _FakeRegKey(values={"DisplayName": "Notepad", "InstallLocation": "/opt/np"})
    uninstall = _FakeRegKey(children={"CalibreKey": calibre, "OtherKey": other})
    hklm = object()
    native = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"

    class _FakeWinreg:
        HKEY_LOCAL_MACHINE = hklm

        @staticmethod
        def OpenKey(root: object, sub: str) -> _FakeRegKey:  # noqa: N802 - API winreg (PascalCase)
            if root is hklm:
                if sub == native:
                    return uninstall
                raise OSError("brak klucza WOW6432Node")  # gałąź 32-bit nieobecna → pomijana
            assert isinstance(root, _FakeRegKey)
            if sub in root.children:
                return root.children[sub]
            raise OSError("brak wpisu")

        @staticmethod
        def QueryInfoKey(key: _FakeRegKey) -> tuple[int, int, int]:  # noqa: N802 - API winreg
            return (len(key.children), 0, 0)

        @staticmethod
        def EnumKey(key: _FakeRegKey, index: int) -> str:  # noqa: N802 - API winreg
            return list(key.children)[index]

        @staticmethod
        def QueryValueEx(key: _FakeRegKey, name: str) -> tuple[str, int]:  # noqa: N802 - API winreg
            if name in key.values:
                return (key.values[name], 1)
            raise OSError("brak wartości")

    monkeypatch.setattr(dependencies.sys, "platform", "win32")
    monkeypatch.setitem(sys.modules, "winreg", _FakeWinreg)

    # Tylko wpis „calibre*" z InstallLocation → ebook-convert.exe pod tą lokalizacją.
    assert dependencies._calibre_registry_paths() == [
        str(Path("/opt/Calibre2") / "ebook-convert.exe")
    ]


def test_calibre_known_dirs_on_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dependencies.sys, "platform", "win32")
    monkeypatch.setattr(dependencies.os, "environ", {"ProgramFiles": "/pf", "LOCALAPPDATA": "/lad"})

    dirs = dependencies._calibre_known_dirs()

    assert str(Path("/pf") / "Calibre2" / "ebook-convert.exe") in dirs
    # LOCALAPPDATA → podkatalog Programs\Calibre2.
    assert str(Path("/lad") / "Programs" / "Calibre2" / "ebook-convert.exe") in dirs
