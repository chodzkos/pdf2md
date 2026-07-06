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


def setup_logging(
    log_dir: Path | None = None,
    level: str = "INFO",
    verbose: bool = False,
) -> None:
    """Konfiguruje loguru: konsola + rotowany plik logs/pdf2md.log.

    Args:
        log_dir: Katalog na pliki logów (domyślnie ./logs/).
        level: Minimalny poziom logowania dla konsoli.
        verbose: Jeśli True, ustawia poziom DEBUG na konsoli.
    """
    logger.remove()  # usuń domyślny handler loguru
    _reconfigure_windows_stderr()

    console_level = "DEBUG" if verbose else level
    logger.add(
        sys.stderr,
        level=console_level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | "
        "<cyan>{name}</cyan> — {message}",
        colorize=True,
    )

    log_path = (log_dir or Path("logs")) / "pdf2md.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger.add(
        log_path,
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {name}:{line} — {message}",
        rotation="10 MB",
        retention="30 days",
        encoding="utf-8",
    )
