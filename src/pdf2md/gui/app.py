"""Punkt wejścia aplikacji GUI pdf2md."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

import pdf2md.engines  # rejestruje silniki w engine_registry
import pdf2md.llm  # noqa: F401  # rejestruje dostawców LLM w llm_registry
from pdf2md.gui.main_window import MainWindow
from pdf2md.utils.logging import setup_logging


def main() -> None:
    """Uruchamia aplikację graficzną pdf2md."""
    args = sys.argv[1:]
    if "--help" in args or "-h" in args:
        print("Usage: pdf2md-gui [PDF ...]")
        print()
        print("Uruchamia graficzny konwerter PDF do Markdown.")
        print("Podane pliki PDF zostaną dodane do listy konwersji.")
        return

    initial_files = [arg for arg in args if arg.lower().endswith(".pdf")]

    setup_logging()
    app = QApplication(sys.argv)
    app.setApplicationName("pdf2md")
    app.setApplicationVersion("0.1.0-dev")
    icon_path = Path(__file__).resolve().parent / "assets" / "icon.svg"
    app.setWindowIcon(QIcon(str(icon_path)))
    window = MainWindow(initial_files=initial_files)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    import multiprocessing

    multiprocessing.freeze_support()
    main()
