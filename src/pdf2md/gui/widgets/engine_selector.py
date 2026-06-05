"""Widget wyboru silnika konwersji."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QWidget

from pdf2md.core.registry import engine_registry


class EngineSelectorWidget(QWidget):
    """ComboBox z silnikami — niedostępne silniki są wyszarzone."""

    engine_changed = Signal(str)  # nazwa wybranego silnika

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("Silnik:"))

        self._combo = QComboBox()
        self._populate()
        self._combo.currentIndexChanged.connect(self._on_changed)
        layout.addWidget(self._combo)
        layout.addStretch()

    def _populate(self) -> None:
        engines = engine_registry.get_all()
        for engine in engines:
            self._combo.addItem(engine.name)
            idx = self._combo.count() - 1
            model = self._combo.model()

            if engine.is_available():
                tooltip = engine.description
            else:
                tooltip = (
                    f"Niezainstalowany. Jak zainstalować: uv sync --extra engines-core\n"
                    f"{engine.description}"
                )
                # Wyszarz niedostępną pozycję
                if isinstance(model, QStandardItemModel):
                    item: QStandardItem | None = model.item(idx)
                    if item is not None:
                        item.setEnabled(False)

            self._combo.setItemData(idx, tooltip, 3)  # Qt.ItemDataRole.ToolTipRole = 3

        if not engines:
            self._combo.addItem("(brak silników)")
            self._combo.setEnabled(False)

        # Ustaw domyślnie pierwszy dostępny silnik
        for i, engine in enumerate(engines):
            if engine.is_available():
                self._combo.setCurrentIndex(i)
                break

    def get_engine_name(self) -> str:
        """Zwraca nazwę aktualnie wybranego silnika."""
        return self._combo.currentText()

    def set_engine_name(self, name: str) -> None:
        """Ustawia aktywny silnik po nazwie, jeśli jest na liście."""
        for idx in range(self._combo.count()):
            if self._combo.itemText(idx).lower() == name.lower():
                self._combo.setCurrentIndex(idx)
                return

    def _on_changed(self, _index: int) -> None:
        self.engine_changed.emit(self._combo.currentText())
