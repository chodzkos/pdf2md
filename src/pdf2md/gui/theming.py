"""Pomocniki motywu dla okien GUI pdf2md (cienka warstwa nad gui-kit)."""

from __future__ import annotations

from chodzkos_gui_kit.qt.theme import current_palette, mode_of
from chodzkos_gui_kit.qt.titlebar import TitlebarSync
from PySide6.QtWidgets import QWidget


def follow_app_titlebar(window: QWidget) -> TitlebarSync:
    """Dołącza ciemny/jasny pasek tytułu okna do bieżącego motywu aplikacji.

    Dla krótkożyciowych modali (dialogi): ``TitlebarSync`` zostaje dzieckiem okna
    (żyje i ginie razem z nim — bez wycieku do ``ThemeManager``), a motyw czyta
    leniwie z :func:`current_palette`. Główne okno używa zamiast tego
    ``ThemeManager.attach_titlebar`` (re-sync przy każdym ``apply()``).
    """
    sync = TitlebarSync(window, lambda: mode_of(current_palette()))
    sync.refresh()
    return sync
