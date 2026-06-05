"""Panel logów GUI z kolorowym wyjściem."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtWidgets import QTextEdit, QVBoxLayout, QWidget


class LogPanelWidget(QWidget):
    """Read-only panel z kolorowanymi komunikatami logu."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        font = self._text.font()
        font.setFamily("monospace")
        self._text.setFont(font)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._text)

    def log_info(self, msg: str) -> None:
        """Zielony tekst z timestampem."""
        self._append(msg, color="#2d9a4e")

    def log_error(self, msg: str) -> None:
        """Czerwony tekst z timestampem."""
        self._append(msg, color="#d9534f")

    def log_warning(self, msg: str) -> None:
        """Żółty tekst z timestampem."""
        self._append(msg, color="#e6a817")

    def clear(self) -> None:
        """Czyści panel logów."""
        self._text.clear()

    def _append(self, msg: str, color: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        html = f'<span style="color:{color}">[{ts}] {self._escape(msg)}</span>'
        self._text.append(html)

    @staticmethod
    def _escape(text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
