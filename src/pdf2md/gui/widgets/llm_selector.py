"""Widget wyboru dostawcy LLM do post-processingu."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from pdf2md.core.registry import llm_registry


class LLMSelectorWidget(QWidget):
    """Checkbox + combo dostawcy + pole modelu."""

    llm_changed = Signal(str, str)  # (provider_name, model)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._checkbox = QCheckBox("Włącz post-processing LLM")
        layout.addWidget(self._checkbox)

        row = QHBoxLayout()
        row.setContentsMargins(20, 0, 0, 0)
        row.addWidget(QLabel("Dostawca:"))
        self._combo = QComboBox()
        self._populate_combo()
        row.addWidget(self._combo)

        row.addWidget(QLabel("Model:"))
        self._model_edit = QLineEdit()
        self._model_edit.setPlaceholderText("domyślny")
        self._model_edit.setMaximumWidth(180)
        row.addWidget(self._model_edit)
        row.addStretch()

        self._provider_row = QWidget()
        self._provider_row.setLayout(row)
        self._provider_row.setVisible(False)
        layout.addWidget(self._provider_row)

        self._checkbox.toggled.connect(self._provider_row.setVisible)
        self._checkbox.toggled.connect(self._emit)
        self._combo.currentIndexChanged.connect(self._emit)
        self._model_edit.textChanged.connect(self._emit)

    def _populate_combo(self) -> None:
        self._combo.addItem("none", "none")
        for provider in llm_registry.get_all():
            self._combo.addItem(provider.name, provider.name)

    def get_llm_name(self) -> str:
        """Zwraca nazwę wybranego dostawcy lub 'none'."""
        if not self._checkbox.isChecked():
            return "none"
        return str(self._combo.currentData() or "none")

    def get_model(self) -> str:
        """Zwraca wpisany model (pusty = użyj domyślnego z providera)."""
        return self._model_edit.text().strip()

    def _emit(self) -> None:
        self.llm_changed.emit(self.get_llm_name(), self.get_model())
