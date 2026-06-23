"""Pomocniki motywu dla okien GUI pdf2md (cienka warstwa nad gui-kit)."""

from __future__ import annotations

from chodzkos_gui_kit.qt.theme import current_palette, mode_of
from chodzkos_gui_kit.qt.titlebar import TitlebarSync
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox, QWidget


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


def attach_dark_titlebar(window: QWidget) -> TitlebarSync:
    """Wymusza belkę okna na motyw aplikacji JESZCZE przed pokazaniem.

    ``WA_NativeWindow`` tworzy natywny uchwyt od razu, więc ``winId`` jest
    wiarygodny i DWM pociemni belkę przed ``exec()`` (wzorzec kitowego
    ``_dark_dialog``). Bez tego pierwsze pokazanie modala mignęłoby belką
    systemu (jasną przy rozjeździe motyw-aplikacji vs motyw-systemu).

    Zwrócony ``TitlebarSync`` jest dzieckiem ``window`` (żyje i ginie z oknem),
    więc nie trzeba trzymać referencji po stronie wołającego.
    """
    window.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, True)
    return follow_app_titlebar(window)


def themed_message_box(
    parent: QWidget | None,
    icon: QMessageBox.Icon,
    title: str,
    text: str,
) -> QMessageBox:
    """``QMessageBox`` z belką podążającą za motywem APLIKACJI (nie systemu).

    Buduje instancję zamiast statycznych ``about``/``information``/``warning``,
    bo tylko instancja może dostać :func:`attach_dark_titlebar` przed pokazaniem.
    Użytkownik wołający robi ``themed_message_box(...).exec()``.
    """
    box = QMessageBox(parent)
    box.setIcon(icon)
    box.setWindowTitle(title)
    box.setText(text)
    attach_dark_titlebar(box)
    return box
