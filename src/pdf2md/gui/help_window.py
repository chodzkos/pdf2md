"""Okno pomocy offline pdf2md — szkielet (treść w kolejnym kroku).

Zakładki są **wstrzykiwane w pętli** z :meth:`HelpWindow._tabs` (lista
``(tytuł, html)``), nie sztywnymi metodami ``_make_X_tab`` — pod przyszłą
ekstrakcję wspólnego okna pomocy do gui-kit.

Kolory w HTML idą WYŁĄCZNIE przez funkcję ``palette(...)`` Qt (np.
``palette(mid)``) — Qt podstawia kolor z palety ``QTextBrowser``, więc działają
w obu motywach bez re-renderu. Zero zaszytych hexów.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QScrollArea,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from pdf2md.gui.theming import follow_app_titlebar


def _scroll(widget: QWidget) -> QScrollArea:
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setWidget(widget)
    return area


def _section(title: str, body: str) -> str:
    return f"<h3>{title}</h3>{body}"


def _p(text: str) -> str:
    return f"<p>{text}</p>"


def _ul(*items: str) -> str:
    rows = "".join(f"<li>{i}</li>" for i in items)
    return f"<ul>{rows}</ul>"


def _table(headers: list[str], rows: list[list[str]]) -> str:
    th = "".join(f"<th style='padding:4px 8px;text-align:left'>{h}</th>" for h in headers)
    trs = ""
    for row in rows:
        tds = "".join(f"<td style='padding:4px 8px'>{c}</td>" for c in row)
        trs += f"<tr>{tds}</tr>"
    return (
        "<table border='1' cellspacing='0' cellpadding='0' "
        "style='border-collapse:collapse;margin:4px 0'>"
        f"<tr style='background:palette(mid)'>{th}</tr>{trs}</table>"
    )


def _code(text: str) -> str:
    return f"<code style='background:palette(mid);padding:1px 4px;border-radius:2px'>{text}</code>"


def _pre(text: str) -> str:
    return (
        f"<pre style='background:palette(mid);padding:8px;border-radius:4px;"
        f"white-space:pre-wrap'>{text}</pre>"
    )


class HelpWindow(QDialog):
    """Okno pomocy z zakładkami (szkielet — jedna placeholder-zakładka)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Pomoc — pdf2md")
        # Tylko rozmiar startowy — geometrii NIE persystujemy (żadne okno pdf2md
        # tego nie robi; dodatkowe pole w typowanym Settings = narzut bez wartości).
        self.resize(720, 560)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        tabs = QTabWidget()
        for title, html in self._tabs():
            browser = QTextBrowser()
            browser.setHtml(html)
            tabs.addTab(_scroll(browser), title)
        layout.addWidget(tabs)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Ciemna belka tytułu podążająca za motywem aplikacji (jak settings_dialog).
        self._titlebar = follow_app_titlebar(self)

    def _tabs(self) -> list[tuple[str, str]]:
        """Zakładki pomocy jako ``(tytuł, html)``. Na razie placeholder."""
        return [("Placeholder", _section("Wkrótce", _p("Treść pomocy w toku.")))]
