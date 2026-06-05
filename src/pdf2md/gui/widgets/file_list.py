"""Widget listy plików PDF z obsługą drag & drop."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QVBoxLayout, QWidget


class FileListWidget(QWidget):
    """Lista plików PDF z obsługą przeciągania i upuszczania."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)

        self._list = QListWidget()
        self._list.setAlternatingRowColors(True)
        self._list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._list)

    # ------------------------------------------------------------------
    # Publiczne API
    # ------------------------------------------------------------------

    def add_files(self, paths: list[str]) -> None:
        """Dodaje pliki PDF do listy (pomija duplikaty)."""
        existing = self.get_files()
        for path in paths:
            if path not in existing and path.lower().endswith(".pdf"):
                item = self._make_item(path)
                self._list.addItem(item)

    def remove_selected(self) -> None:
        """Usuwa zaznaczone pozycje z listy."""
        for item in self._list.selectedItems():
            self._list.takeItem(self._list.row(item))

    def clear(self) -> None:
        """Czyści całą listę."""
        self._list.clear()

    def get_files(self) -> list[str]:
        """Zwraca ścieżki wszystkich plików na liście."""
        return [
            self._list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self._list.count())
        ]

    # ------------------------------------------------------------------
    # Drag & drop
    # ------------------------------------------------------------------

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            urls: list[QUrl] = event.mimeData().urls()
            if any(u.toLocalFile().lower().endswith(".pdf") for u in urls):
                event.acceptProposedAction()
                return
        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        paths = [
            u.toLocalFile()
            for u in event.mimeData().urls()
            if u.toLocalFile().lower().endswith(".pdf")
        ]
        self.add_files(paths)
        event.acceptProposedAction()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_item(self, path: str) -> QListWidgetItem:
        p = Path(path)
        size_kb = p.stat().st_size // 1024 if p.exists() else 0
        label = f"{p.name}  ({size_kb} KB)"
        item = QListWidgetItem(label)
        item.setData(Qt.ItemDataRole.UserRole, path)
        item.setToolTip(path)
        return item
