"""Treść okna pomocy offline pdf2md — zakładki Markdown z plików pakietu.

Od gui-kit 0.5.3 ``HelpWindow`` renderuje Markdown natywnie
(:meth:`chodzkos_gui_kit.qt.widgets.HelpWindow.add_markdown_section`,
``QTextBrowser.setMarkdown`` + re-render na ``PaletteChange`` objęty przez kit).
Zasada „jeden plik prawdy": treść zakładek leży w plikach ``src/pdf2md/help_docs/*.md``
(dane pakietu), a nie w stringach HTML w kodzie.

Pliki czytane są w runtime przez :func:`importlib.resources.files` — działa zarówno
z drzewa źródeł, jak i z zainstalowanego wheela (żadnej żonglerki ``Path(__file__)``).

Wołający::

    from pdf2md.gui.help_window import build_help_window
    build_help_window(parent).exec()
"""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from chodzkos_gui_kit.qt.widgets import HelpWindow
    from PySide6.QtWidgets import QWidget

HELP_TITLE = "Pomoc — pdf2md"

#: Zakładki pomocy: (tytuł, plik w ``help_docs/``). Kolejność = kolejność zakładek.
HELP_SECTIONS: list[tuple[str, str]] = [
    ("Silniki konwersji", "engines.md"),
    ("Instalacja silników", "install.md"),
    ("Post-processing LLM", "llm.md"),
    ("Profile skanowania", "profiles.md"),
    ("CLI", "cli.md"),
    ("Model AI / Ollama", "models.md"),
]


def help_doc_path(filename: str) -> Path:
    """Ścieżka do pliku pomocy w pakiecie ``pdf2md/help_docs/`` (wheel i drzewo źródeł)."""
    return cast(Path, files("pdf2md").joinpath("help_docs", filename))


def build_help_window(parent: QWidget | None) -> HelpWindow:
    """Buduje okno pomocy z zakładkami Markdown (kolejność wg :data:`HELP_SECTIONS`)."""
    from chodzkos_gui_kit.qt.widgets import HelpWindow

    window = HelpWindow(parent, title=HELP_TITLE)
    for title, filename in HELP_SECTIONS:
        window.add_markdown_section(title, help_doc_path(filename))
    return window
