"""Konfiguracja logowania — loguru z zapisem do pliku i konsolą."""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger


def _is_windows_platform() -> bool:
    return sys.platform == "win32"


def _reconfigure_windows_stderr() -> None:
    """Force UTF-8 stderr on Windows before loguru attaches its console sink."""
    if not _is_windows_platform():
        return

    reconfigure = getattr(sys.stderr, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8", errors="replace")


_FILE_FORMAT = "{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {name}:{line} — {message}"


def _add_file_sink(path: Path, *, rotation: str, level: str) -> None:
    """Dodaje plikowy sink loguru best-effort — nie wywala startu przy niezapisywalnym katalogu.

    Ważne w trybie GUI (gui-script, brak konsoli): wyjątek z ``mkdir`` w niezapisywalnym
    CWD zabiłby aplikację po cichu (nie ma stderr, by pokazać traceback). Degradujemy więc
    do braku pliku i tylko ostrzegamy (jeśli jest gdzie).
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            path,
            level=level,
            format=_FILE_FORMAT,
            rotation=rotation,
            retention="30 days",
            encoding="utf-8",
        )
    except OSError as exc:
        logger.warning(f"Nie udało się utworzyć pliku logu {path}: {exc}")


def setup_logging(
    log_dir: Path | None = None,
    level: str = "INFO",
    verbose: bool = False,
    to_file: bool = False,
) -> None:
    """Konfiguruje loguru: konsola (jeśli jest) + rotowany plik logs/pdf2md.log.

    Args:
        log_dir: Katalog na pliki logów (domyślnie ./logs/).
        level: Minimalny poziom logowania dla konsoli.
        verbose: Jeśli True, ustawia poziom DEBUG na konsoli.
        to_file: Tryb GUI — dodaje stabilny log w katalogu użytkownika
            (``~/.config/pdf2md/logs/gui.log``), niezależny od CWD i konsoli.
    """
    logger.remove()  # usuń domyślny handler loguru
    _reconfigure_windows_stderr()

    console_level = "DEBUG" if verbose else level
    # W trybie GUI (gui-script / pythonw) sys.stderr bywa None — loguru rzuciłby przy add().
    if sys.stderr is not None:
        logger.add(
            sys.stderr,
            level=console_level,
            format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | "
            "<cyan>{name}</cyan> — {message}",
            colorize=True,
        )

    _add_file_sink((log_dir or Path("logs")) / "pdf2md.log", rotation="10 MB", level="DEBUG")

    if to_file:
        gui_log = Path.home() / ".config" / "pdf2md" / "logs" / "gui.log"
        _add_file_sink(gui_log, rotation="5 MB", level="INFO")
