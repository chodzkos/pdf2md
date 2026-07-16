"""Widget wyboru profilu skanowania + prosty edytor profilu (zapis jako profil użytkownika)."""

from __future__ import annotations

from chodzkos_detection import check_pandoc
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QWidget,
)

from pdf2md.detection.dependencies import check_calibre
from pdf2md.gui.theming import follow_app_titlebar, themed_message_box

_EPUB_BACKEND_LABELS = {
    "pandoc": "Pandoc",
    "native": "Native (ebooklib)",
    "calibre": "Calibre",
}


def available_epub_backend_options() -> list[tuple[str, str]]:
    """Zwraca wykryte backendy EPUB jako pary (wartość, etykieta)."""
    options: list[tuple[str, str]] = []
    if check_pandoc():
        options.append(("pandoc", _EPUB_BACKEND_LABELS["pandoc"]))
    options.append(("native", _EPUB_BACKEND_LABELS["native"]))
    if check_calibre():
        options.append(("calibre", _EPUB_BACKEND_LABELS["calibre"]))
    return options


class ProfileSelectorWidget(QWidget):
    """Dropdown profilu skanowania + przycisk „Edytuj profil"."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(20, 0, 0, 0)
        row.addWidget(QLabel("Profil skanowania:"))
        self._combo = QComboBox()
        row.addWidget(self._combo)
        self._edit_btn = QPushButton("Edytuj profil")
        self._edit_btn.clicked.connect(self._open_editor)
        row.addWidget(self._edit_btn)
        row.addStretch()
        self.reload_profiles(select="balanced")

    def reload_profiles(self, select: str | None = None) -> None:
        from pdf2md.scan.profiles import list_profiles

        current = select or self.get_profile_name()
        self._combo.clear()
        self._combo.addItems(list_profiles())
        if current:
            idx = self._combo.findText(current)
            if idx >= 0:
                self._combo.setCurrentIndex(idx)

    def get_profile_name(self) -> str:
        return self._combo.currentText().strip()

    def _open_editor(self) -> None:
        dialog = ProfileEditDialog(self.get_profile_name(), self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.saved_name:
            self.reload_profiles(select=dialog.saved_name)


class ProfileEditDialog(QDialog):
    """Minimalny edytor profilu: DPI + przełączniki wyjścia, zapis jako profil użytkownika."""

    def __init__(self, base_profile: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Edytuj profil: {base_profile}")
        self.saved_name = ""
        self._base = base_profile

        from pdf2md.scan.profiles import load_profile

        profile = load_profile(base_profile)

        layout = QFormLayout(self)
        self._dpi = QSpinBox()
        self._dpi.setRange(72, 1200)
        self._dpi.setValue(profile.dpi)
        layout.addRow("DPI:", self._dpi)

        self._epub = QCheckBox()
        self._epub.setChecked(profile.output.epub)

        self._epub_backend = QComboBox()
        self._populate_epub_backend(profile.output.epub_backend)
        self._epub.toggled.connect(self._sync_epub_backend_enabled)
        epub_row = QHBoxLayout()
        epub_row.addWidget(self._epub)
        epub_row.addWidget(self._epub_backend)
        epub_row.addStretch()
        layout.addRow("Eksport EPUB:", epub_row)

        self._report = QCheckBox()
        self._report.setChecked(profile.output.quality_report or profile.output.html_report)
        layout.addRow("Raport jakości:", self._report)

        self._name = QLineEdit()
        self._name.setPlaceholderText(f"{base_profile}-custom")
        layout.addRow("Zapisz jako:", self._name)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        self._titlebar = follow_app_titlebar(self)

    def _populate_epub_backend(self, selected_backend: str) -> None:
        self._epub_backend.clear()
        for value, label in available_epub_backend_options():
            self._epub_backend.addItem(label, value)

        selected_idx = self._epub_backend.findData(selected_backend)
        if selected_idx >= 0:
            self._epub_backend.setCurrentIndex(selected_idx)
        elif self._epub_backend.count() == 0:
            self._epub_backend.addItem("Brak dostępnych backendów", None)

        self._sync_epub_backend_enabled()

    def _sync_epub_backend_enabled(self) -> None:
        self._epub_backend.setEnabled(self._epub.isChecked() and self._epub_backend.count() > 1)

    def _on_save(self) -> None:
        from pdf2md.scan.profiles import load_profile, save_custom_profile

        name = self._name.text().strip() or f"{self._base}-custom"
        profile = load_profile(self._base)
        profile.name = name
        profile.dpi = self._dpi.value()
        profile.output.epub = self._epub.isChecked()
        backend = self._epub_backend.currentData()
        if backend in {"pandoc", "native", "calibre"}:
            profile.output.epub_backend = str(backend)
        profile.output.quality_report = self._report.isChecked()
        try:
            path = save_custom_profile(profile, name)
        except Exception as exc:  # pragma: no cover - błąd zapisu pokazujemy użytkownikowi
            themed_message_box(
                self, QMessageBox.Icon.Warning, "Profil", f"Nie udało się zapisać profilu:\n{exc}"
            ).exec()
            return
        self.saved_name = name
        themed_message_box(
            self, QMessageBox.Icon.Information, "Profil", f"Zapisano profil „{name}”:\n{path}"
        ).exec()
        self.accept()
