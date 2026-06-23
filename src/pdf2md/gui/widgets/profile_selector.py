"""Widget wyboru profilu skanowania + prosty edytor profilu (zapis jako profil użytkownika)."""

from __future__ import annotations

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

from pdf2md.gui.theming import follow_app_titlebar, themed_message_box


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
        layout.addRow("Eksport EPUB:", self._epub)

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

    def _on_save(self) -> None:
        from pdf2md.scan.profiles import load_profile, save_custom_profile

        name = self._name.text().strip() or f"{self._base}-custom"
        profile = load_profile(self._base)
        profile.name = name
        profile.dpi = self._dpi.value()
        profile.output.epub = self._epub.isChecked()
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
