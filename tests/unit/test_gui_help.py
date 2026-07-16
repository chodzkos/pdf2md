"""Test budowy okna pomocy z zakładkami Markdown (gui-kit 0.5.3) — wymaga Qt (CI)."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)

from PySide6.QtWidgets import QApplication

from pdf2md.gui.help_window import HELP_SECTIONS, build_help_window

pytestmark = pytest.mark.gui


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    try:
        return QApplication.instance() or QApplication([])
    except Exception as exc:  # pragma: no cover - środowisko bez Qt
        pytest.skip(f"Qt niedostępne: {exc}")


def test_build_help_window_has_markdown_sections(qapp: QApplication) -> None:
    window = build_help_window(None)
    try:
        assert window._tabs.count() == len(HELP_SECTIONS)
        titles = [window._tabs.tabText(i) for i in range(window._tabs.count())]
        assert titles == [title for title, _ in HELP_SECTIONS]
        # każda zakładka zarejestrowana jako Markdown → re-render na zmianę motywu
        assert all(is_markdown for _browser, _content, is_markdown in window._browsers)
    finally:
        window.deleteLater()
