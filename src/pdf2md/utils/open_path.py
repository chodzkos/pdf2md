"""Bezpieczne otwieranie sciezek w systemowym menedzerze plikow."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path

from loguru import logger


def open_in_file_manager(path: str | Path) -> bool:
    """Otwiera sciezke w menedzerze plikow, bez rzucania wyjatkow na brak narzedzia."""
    target = str(Path(path))
    try:
        system = platform.system()
        if system == "Windows":
            startfile = getattr(os, "startfile", None)
            if not callable(startfile):
                logger.warning("Nie znaleziono narzedzia do otwarcia folderu: os.startfile")
                return False
            startfile(target)
            return True

        command = _open_command(system)
        if command is None:
            logger.warning(f"Nie znaleziono narzedzia do otwarcia folderu: {target}")
            return False

        subprocess.Popen([command, target])
        return True
    except Exception as exc:
        logger.warning(f"Nie udalo sie otworzyc folderu w menedzerze plikow: {exc}")
        return False


def _open_command(system: str) -> str | None:
    if system == "Darwin":
        return "open" if shutil.which("open") else None
    if system == "Linux" and _is_wsl():
        return "wslview" if shutil.which("wslview") else "explorer.exe"
    if system == "Linux":
        return "xdg-open" if shutil.which("xdg-open") else None
    return None


def _is_wsl() -> bool:
    return "microsoft" in platform.uname().release.lower()
