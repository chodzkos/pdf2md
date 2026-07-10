"""Zbiorczy raport środowiska dla `pdf2md doctor`.

Sondy narzędzi CLI i usług sieciowych pochodzą z pakietu `chodzkos_detection`
(stdlib-only), a detekcja sprzętu z lokalnego `pdf2md.detection.hardware`;
tu pozostaje agregator `check_all` oraz wykrywanie Calibre poza PATH.
Funkcje są odporne na brak narzędzia.
"""

from __future__ import annotations

import os
import platform
import sys
from pathlib import Path
from typing import Any

from chodzkos_detection import check_ollama, check_tools, find_tool

from pdf2md.detection.hardware import check_gpu  # LOKALNY (sprzęt) — celowo nie z pakietu

_CALIBRE_EXE = "ebook-convert"


def _calibre_registry_paths() -> list[str]:
    """Kandydackie ścieżki `ebook-convert.exe` z rejestru Windows.

    Calibre trzyma `InstallLocation` pod kluczami uninstall (natywny + WOW6432Node).
    Realna instalacja bywa poza PATH i poza `%ProgramFiles%` (np. `C:\\Calibre2`), więc
    rejestr jest pewniejszy niż sztywna lista katalogów. Odczyt owinięty w try/except —
    zwraca [] przy każdym problemie; poza Windows (brak `winreg`) też []. `winreg`
    importujemy warunkowo pod `sys.platform == "win32"`.
    """
    paths: list[str] = []
    # Blok pod `sys.platform == "win32"` (nie early-return) — tak mypy traktuje go jako
    # kod platformowy (bez ostrzeżeń „unreachable" na Linuksie) i sprawdza `winreg` pod win32.
    if sys.platform == "win32":
        import winreg

        subkeys = (
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
        )
        for subkey in subkeys:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, subkey) as key:
                    count = winreg.QueryInfoKey(key)[0]
                    for index in range(count):
                        try:
                            entry_name = winreg.EnumKey(key, index)
                            with winreg.OpenKey(key, entry_name) as entry:
                                display = str(winreg.QueryValueEx(entry, "DisplayName")[0])
                                if not display.lower().startswith("calibre"):
                                    continue
                                location = str(winreg.QueryValueEx(entry, "InstallLocation")[0])
                                if location:
                                    paths.append(str(Path(location) / "ebook-convert.exe"))
                        except OSError:
                            continue  # wpis bez DisplayName/InstallLocation — pomiń
            except OSError:
                continue  # brak danego klucza uninstall — pomiń
    return paths


def _calibre_known_dirs() -> list[str]:
    """Sztywne fallbacki instalacji Calibre na Windows (trzeci priorytet, po PATH i rejestrze)."""
    candidates: list[str] = []
    if sys.platform == "win32":
        for env_var in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
            base = os.environ.get(env_var)
            if not base:
                continue
            sub = Path("Programs", "Calibre2") if env_var == "LOCALAPPDATA" else Path("Calibre2")
            candidates.append(str(Path(base) / sub / "ebook-convert.exe"))
    return candidates


def calibre_path() -> str | None:
    """Pełna ścieżka do `ebook-convert` (Calibre) albo None.

    Kolejność wykrywania: PATH (`shutil.which`) → rejestr Windows (`InstallLocation`) →
    znane katalogi. Poza Windows sprowadza się do PATH (lista dodatkowa jest pusta).
    """
    extra = [*_calibre_registry_paths(), *_calibre_known_dirs()]
    return find_tool(_CALIBRE_EXE, extra)


def check_calibre() -> bool:
    """True, gdy `ebook-convert` (CLI Calibre) jest wykrywalny (PATH/rejestr/znane katalogi).

    Calibre to opcjonalny backend eksportu EPUB obok Pandoca. Zwraca bool (jak dotąd, bez
    łamania API); pełną ścieżkę do binarki zwraca `calibre_path()`.
    """
    return calibre_path() is not None


def check_all() -> dict[str, Any]:
    """Zbiorczy raport stanu środowiska — używany przez `pdf2md doctor`."""
    return {
        "system": {
            "os": platform.system(),
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
        **check_tools(),
        "calibre": check_calibre(),
        "ollama": check_ollama(),
        "gpu": check_gpu(),
    }
