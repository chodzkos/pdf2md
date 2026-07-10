"""Testy EngineSelectorWidget (B12): budowa optymistyczna + zastosowanie wyniku sondy.

Logikę graying/domyślnego wyboru testujemy synchronicznie przez `_apply_availability`,
bez czekania na wątek puli (sonda realnie liczy is_available() poza wątkiem UI).
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)

from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import QApplication

import pdf2md.engines  # noqa: F401 - rejestruje silniki w engine_registry
from pdf2md.core.engine_catalog import hint_for_engine
from pdf2md.gui.widgets.engine_selector import EngineSelectorWidget

pytestmark = pytest.mark.gui


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    try:
        return QApplication.instance() or QApplication([])
    except Exception as exc:  # pragma: no cover - środowisko bez Qt
        pytest.skip(f"Qt niedostępne: {exc}")


def test_built_optimistically_all_enabled(qapp: QApplication) -> None:
    """Zaraz po budowie wszystkie pozycje są aktywne, a tooltip mówi „sprawdzam dostępność…"."""
    widget = EngineSelectorWidget()
    try:
        model = widget._combo.model()
        assert isinstance(model, QStandardItemModel)
        assert widget._combo.count() >= 2
        for idx in range(widget._combo.count()):
            assert model.item(idx).isEnabled() is True
            assert "sprawdzam dostępność" in widget._combo.itemData(idx, 3)
    finally:
        widget.deleteLater()


def test_apply_availability_greys_unavailable_and_selects_available(qapp: QApplication) -> None:
    """Po wyniku sondy: niedostępny wyszarzony, domyślny wybór skacze na pierwszy dostępny."""
    widget = EngineSelectorWidget()
    try:
        names = [widget._combo.itemText(i) for i in range(widget._combo.count())]
        assert len(names) >= 2
        availability = dict.fromkeys(names, False)
        availability[names[1]] = True
        widget._combo.setCurrentIndex(0)  # wybrany aktualnie niedostępny

        widget._apply_availability(availability)

        model = widget._combo.model()
        assert isinstance(model, QStandardItemModel)
        assert model.item(0).isEnabled() is False
        # Tooltip niedostępnego niesie hint PER-SILNIK z katalogu (nie sztywne „uv sync").
        expected_hint = hint_for_engine(names[0])
        assert expected_hint is not None
        assert expected_hint in widget._combo.itemData(0, 3)
        assert widget._combo.currentText() == names[1]  # domyślny → pierwszy dostępny
    finally:
        widget.deleteLater()


def test_apply_availability_respects_user_choice(qapp: QApplication) -> None:
    """Gdy użytkownik już wybrał ręcznie, wynik sondy NIE zmienia jego wyboru."""
    widget = EngineSelectorWidget()
    try:
        names = [widget._combo.itemText(i) for i in range(widget._combo.count())]
        assert len(names) >= 2
        widget._user_changed = True
        widget._combo.setCurrentIndex(0)
        availability = dict.fromkeys(names, False)
        availability[names[1]] = True

        widget._apply_availability(availability)

        assert widget._combo.currentIndex() == 0  # wybór użytkownika nietknięty
    finally:
        widget.deleteLater()
