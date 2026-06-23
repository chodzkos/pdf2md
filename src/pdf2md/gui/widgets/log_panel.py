"""Panel logów GUI z kolorowym wyjściem (kolory z palety motywu)."""

from __future__ import annotations

from datetime import datetime

from chodzkos_gui_kit.qt.theme import current_palette
from PySide6.QtWidgets import QTextEdit, QVBoxLayout, QWidget

#: Poziomy logu i ich rola w palecie marki (czytana z bieżącego motywu).
#: info → accent, warning → amber, error → red (GUI_STANDARD §5/§6).
_Level = str


class LogPanelWidget(QWidget):
    """Read-only panel z kolorowanymi komunikatami logu.

    Kolory pochodzą z bieżącej palety motywu (``current_palette()``), nie z
    zaszytych hexów. Wpisy trzymamy jako ``(poziom, timestamp, treść)`` i
    przemalowujemy w :meth:`restyle` po zmianie motywu — wzorzec status-bara
    EpubForge: dane osobno, kolor z palety przy renderze.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        font = self._text.font()
        font.setFamily("monospace")
        self._text.setFont(font)

        # Surowe wpisy (poziom, timestamp, treść) — źródło prawdy do przemalowania.
        self._entries: list[tuple[_Level, str, str]] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._text)

    def log_info(self, msg: str) -> None:
        """Komunikat informacyjny (kolor accent)."""
        self._add("info", msg)

    def log_error(self, msg: str) -> None:
        """Komunikat błędu (kolor red)."""
        self._add("error", msg)

    def log_warning(self, msg: str) -> None:
        """Komunikat ostrzeżenia (kolor amber)."""
        self._add("warning", msg)

    def clear(self) -> None:
        """Czyści panel logów i bufor wpisów."""
        self._entries.clear()
        self._text.clear()

    def restyle(self) -> None:
        """Przemalowuje istniejące wpisy wg bieżącej palety (po zmianie motywu)."""
        self._text.clear()
        for level, ts, msg in self._entries:
            self._render(level, ts, msg)

    def _add(self, level: _Level, msg: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self._entries.append((level, ts, msg))
        self._render(level, ts, msg)

    def _render(self, level: _Level, ts: str, msg: str) -> None:
        color = self._color_for(level)
        html = f'<span style="color:{color}">[{ts}] {self._escape(msg)}</span>'
        self._text.append(html)

    @staticmethod
    def _color_for(level: _Level) -> str:
        palette = current_palette()
        if level == "error":
            return palette.red
        if level == "warning":
            return palette.amber
        return palette.accent

    @staticmethod
    def _escape(text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
