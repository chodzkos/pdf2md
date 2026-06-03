"""Konfiguracja logowania — loguru z zapisem do pliku i konsolą."""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger


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
