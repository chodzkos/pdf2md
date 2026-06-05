"""Punkt wejścia aplikacji GUI pdf2md."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

import pdf2md.engines  # rejestruje silniki w engine_registry
import pdf2md.llm  # noqa: F401  # rejestruje dostawców LLM w llm_registry
from pdf2md.gui.main_window import MainWindow
from pdf2md.utils.logging import setup_logging


def main() -> None:
    """Uruchamia aplikację graficzną pdf2md."""
    setup_logging()
    app = QApplication(sys.argv)
    app.setApplicationName("pdf2md")
    app.setApplicationVersion("0.1.0-dev")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
