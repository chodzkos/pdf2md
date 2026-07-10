"""Widget wyboru silnika konwersji.

Combo buduje się natychmiast i optymistycznie (wszystkie pozycje aktywne), a kosztowne
`is_available()` wszystkich silników — pierwszy import torcha, ping HTTP serwerów VLM —
liczone jest w puli wątków POZA wątkiem UI. Po wyniku niedostępne pozycje są wyszarzane,
tooltipy poprawiane, a domyślny wybór dobierany do rzeczywistej dostępności.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QWidget

from pdf2md.core.engine_catalog import hint_for_engine
from pdf2md.core.registry import engine_registry

_CHECKING_HINT = "sprawdzam dostępność…"
_FALLBACK_HINT = "uv sync --extra engines-core"
_TOOLTIP_ROLE = 3  # Qt.ItemDataRole.ToolTipRole


class _AvailabilityBridge(QObject):
    """Most sygnałowy: przenosi wynik sondy z wątku puli do wątku UI."""

    ready = Signal(object)  # dict[str, bool]: nazwa_silnika -> is_available()


class _AvailabilityProbe(QRunnable):
    """Liczy is_available() wszystkich silników poza wątkiem UI."""

    def __init__(self, bridge: _AvailabilityBridge) -> None:
        super().__init__()
        self._bridge = bridge

    def run(self) -> None:
        result: dict[str, bool] = {}
        for engine in engine_registry.get_all():
            try:
                result[engine.name] = bool(engine.is_available())
            except Exception:
                result[engine.name] = False
        self._bridge.ready.emit(result)


class EngineSelectorWidget(QWidget):
    """ComboBox z silnikami — buduje się optymistycznie, dostępność liczy w tle."""

    engine_changed = Signal(str)  # nazwa wybranego silnika

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._descriptions: dict[str, str] = {}
        self._user_changed = False  # True dopiero gdy użytkownik RĘCZNIE zmieni wybór
        self._bridge: _AvailabilityBridge | None = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("Silnik:"))

        self._combo = QComboBox()
        self._populate_optimistic()
        self._combo.currentIndexChanged.connect(self._on_changed)
        # `activated` odpala się TYLKO przy wyborze użytkownika (nie przy setCurrentIndex).
        self._combo.activated.connect(self._on_user_activated)
        layout.addWidget(self._combo)
        layout.addStretch()

        self._start_availability_probe()

    def _populate_optimistic(self) -> None:
        """Buduje combo natychmiast: wszystkie pozycje aktywne, tooltip „sprawdzam…"."""
        engines = engine_registry.get_all()
        for engine in engines:
            self._combo.addItem(engine.name)
            idx = self._combo.count() - 1
            self._descriptions[engine.name] = engine.description
            self._combo.setItemData(idx, f"{engine.description}\n({_CHECKING_HINT})", _TOOLTIP_ROLE)

        if not engines:
            self._combo.addItem("(brak silników)")
            self._combo.setEnabled(False)

    def _start_availability_probe(self) -> None:
        """Odpala sondę is_available() w puli wątków (poza wątkiem UI)."""
        if not engine_registry.get_all():
            return
        bridge = _AvailabilityBridge()
        bridge.ready.connect(self._apply_availability)
        self._bridge = bridge  # referencja utrzymuje most przy życiu do czasu emisji
        QThreadPool.globalInstance().start(_AvailabilityProbe(bridge))

    def _apply_availability(self, availability: dict[str, bool]) -> None:
        """Po wyniku sondy: wyszarz niedostępne, popraw tooltipy, dobierz domyślny silnik."""
        model = self._combo.model()
        for idx in range(self._combo.count()):
            name = self._combo.itemText(idx)
            if name not in availability:
                continue
            description = self._descriptions.get(name, "")
            if availability[name]:
                tooltip = description
            else:
                # Hint per-silnik z katalogu (np. „uruchom serwer vLLM" dla PaddleOCR-VL),
                # zamiast sztywnego „uv sync", które dla silników-usług było mylące.
                hint = hint_for_engine(name) or _FALLBACK_HINT
                tooltip = f"Niedostępny. Instalacja/uruchomienie: {hint}\n{description}"
                if isinstance(model, QStandardItemModel):
                    item: QStandardItem | None = model.item(idx)
                    if item is not None:
                        item.setEnabled(False)
            self._combo.setItemData(idx, tooltip, _TOOLTIP_ROLE)

        # Domyślny wybór dopiero po wyniku — o ile użytkownik jeszcze nie wybrał ręcznie.
        if not self._user_changed:
            self._select_default_available(availability)

    def _select_default_available(self, availability: dict[str, bool]) -> None:
        """Zachowuje bieżący wybór, jeśli dostępny; inaczej pierwszy dostępny silnik."""
        if availability.get(self._combo.currentText()):
            return
        for idx in range(self._combo.count()):
            if availability.get(self._combo.itemText(idx)):
                self._combo.setCurrentIndex(idx)
                return

    def get_engine_name(self) -> str:
        """Zwraca nazwę aktualnie wybranego silnika."""
        return self._combo.currentText()

    def set_engine_name(self, name: str) -> None:
        """Ustawia aktywny silnik po nazwie (wybór z configu — nie liczony jako wybór użytkownika)."""
        for idx in range(self._combo.count()):
            if self._combo.itemText(idx).lower() == name.lower():
                self._combo.setCurrentIndex(idx)
                return

    def _on_user_activated(self, _index: int) -> None:
        self._user_changed = True

    def _on_changed(self, _index: int) -> None:
        self.engine_changed.emit(self._combo.currentText())
