"""Punkt wejścia aplikacji GUI pdf2md."""

from __future__ import annotations

import sys
from pathlib import Path

from chodzkos_gui_kit.qt.theme import ThemeManager
from loguru import logger
from PySide6.QtCore import QLibraryInfo, QTranslator
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

import pdf2md.engines  # rejestruje silniki w engine_registry
import pdf2md.llm  # noqa: F401  # rejestruje dostawców LLM w llm_registry
from pdf2md.gui.main_window import MainWindow
from pdf2md.gui.theme_bridge import SettingsMapping
from pdf2md.utils.logging import setup_logging


def _install_qt_translations(app: QApplication) -> None:
    """Ładuje polskie tłumaczenia Qt dla standardowych stringów.

    pdf2md jest po polsku, ale standardowe etykiety Qt (przyciski
    ``QDialogButtonBox`` OK/Cancel/Apply, opisy i tooltips nienatywnego
    ``QFileDialog``) zostają w domyślnym angielskim, dopóki nie zainstalujemy
    ``QTranslator``. Translatory parentujemy do ``app`` (utrzymanie referencji).

    ``qtbase_pl`` to główny katalog (przyciski, dialogi plików); ``qt_pl`` to
    zbiorczy meta-katalog (jeśli istnieje w danej dystrybucji PySide6). Gdy
    ``qtbase_pl.qm`` nie istnieje (na części dystrybucji to osobny pakiet),
    logujemy ostrzeżenie zamiast cicho pomijać — i NIE wywalamy aplikacji.
    """
    translations = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)

    qtbase = QTranslator(app)
    if qtbase.load("qtbase_pl", translations):
        app.installTranslator(qtbase)
    else:
        logger.warning(
            f"Brak qtbase_pl.qm w {translations} — standardowe przyciski/dialogi Qt "
            "pozostaną po angielsku. Doinstaluj tłumaczenia Qt dla tej dystrybucji."
        )

    # Zbiorczy katalog (best-effort, bez ostrzeżenia — bywa nieobecny).
    qt_all = QTranslator(app)
    if qt_all.load("qt_pl", translations):
        app.installTranslator(qt_all)


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
    app.setApplicationVersion("1.0.0")
    icon_path = Path(__file__).resolve().parent / "assets" / "icon.svg"
    app.setWindowIcon(QIcon(str(icon_path)))

    # Tłumaczenia Qt (PL) — PRZED budową okien, by standardowe etykiety Qt
    # (przyciski dialogów, nienatywny QFileDialog) były po polsku.
    _install_qt_translations(app)

    # Motyw marki: ThemeManager czyta/pisze config.toml przez SettingsMapping.
    # .setting to wczytany z configu tryb (auto/light/dark); apply() ustawia
    # Fusion + paletę + QSS — NIE wołamy setStyle ręcznie.
    theme_manager = ThemeManager(app, SettingsMapping())
    theme_manager.apply(theme_manager.setting)

    window = MainWindow(theme_manager, initial_files=initial_files)
    window.show()
    sys.exit(app.exec())
