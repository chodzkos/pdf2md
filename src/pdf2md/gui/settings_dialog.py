"""Dialog ustawień GUI zapisujący do wspólnego config.toml."""

from __future__ import annotations

import importlib.metadata
import json
import urllib.request

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from pdf2md.core.config import Settings, get_settings, save_settings
from pdf2md.core.registry import engine_registry
from pdf2md.detection.dependencies import cuda_usable


class SettingsDialog(QDialog):
    """Okno ustawień aplikacji korzystające z core/config.py."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Ustawienia")
        self.setMinimumSize(560, 420)
        self._settings = get_settings()
        self._build_ui()
        self._load_settings()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_api_keys_tab(), "Klucze API")
        self._tabs.addTab(self._build_defaults_tab(), "Domyślne ustawienia")
        self._tabs.addTab(self._build_ollama_tab(), "Ollama")
        root.addWidget(self._tabs)

        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Apply
        )
        self._buttons.accepted.connect(self._on_ok)
        self._buttons.rejected.connect(self.reject)
        apply_button = self._buttons.button(QDialogButtonBox.StandardButton.Apply)
        if apply_button is not None:
            apply_button.clicked.connect(self._apply)
        root.addWidget(self._buttons)

    def _build_api_keys_tab(self) -> QWidget:
        tab = QWidget()
        layout = QFormLayout(tab)

        self._anthropic_key = self._password_edit()
        layout.addRow(
            "Anthropic API Key:", self._with_test_button(self._anthropic_key, "anthropic")
        )

        self._openai_key = self._password_edit()
        layout.addRow("OpenAI API Key:", self._with_test_button(self._openai_key, "openai"))

        self._gemini_key = self._password_edit()
        layout.addRow("Gemini API Key:", self._with_test_button(self._gemini_key, "gemini"))
        return tab

    def _build_defaults_tab(self) -> QWidget:
        tab = QWidget()
        layout = QFormLayout(tab)

        self._default_engine = QComboBox()
        for engine in engine_registry.get_all():
            self._default_engine.addItem(engine.name, engine.name)
        if self._default_engine.count() == 0:
            self._default_engine.addItem("pymupdf4llm", "pymupdf4llm")
        layout.addRow("Domyślny silnik:", self._default_engine)

        output_row = QHBoxLayout()
        self._default_output_dir = QLineEdit()
        self._default_output_dir.setPlaceholderText("(obok pliku źródłowego)")
        browse = QPushButton("Przeglądaj…")
        browse.clicked.connect(self._browse_default_output_dir)
        output_row.addWidget(self._default_output_dir)
        output_row.addWidget(browse)
        layout.addRow("Domyślny folder wyjściowy:", output_row)

        self._default_language = QLineEdit()
        layout.addRow("Domyślny język OCR:", self._default_language)

        self._docling_device = QComboBox()
        for value in ("auto", "cpu", "cuda"):
            self._docling_device.addItem(value, value)
        if not self._cuda_available():
            cuda_index = self._docling_device.findData("cuda")
            if cuda_index >= 0:
                self._docling_device.setItemData(
                    cuda_index,
                    "GPU niewykryte — zostanie użyte CPU",
                    role=Qt.ItemDataRole.ToolTipRole,
                )
        layout.addRow("Docling device:", self._docling_device)
        return tab

    def _build_ollama_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        url_row = QHBoxLayout()
        url_row.addWidget(QLabel("URL:"))
        self._ollama_url = QLineEdit()
        self._ollama_url.setPlaceholderText("http://localhost:11434")
        detect = QPushButton("Wykryj modele")
        detect.clicked.connect(self._detect_ollama_models)
        url_row.addWidget(self._ollama_url)
        url_row.addWidget(detect)
        layout.addLayout(url_row)

        self._ollama_models = QListWidget()
        layout.addWidget(self._ollama_models)
        return tab

    def _password_edit(self) -> QLineEdit:
        edit = QLineEdit()
        edit.setEchoMode(QLineEdit.EchoMode.Password)
        return edit

    def _with_test_button(self, edit: QLineEdit, provider: str) -> QWidget:
        wrapper = QWidget()
        row = QHBoxLayout(wrapper)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(edit)
        button = QPushButton("Testuj")
        button.clicked.connect(lambda: self._test_api_key(provider, edit.text().strip()))
        row.addWidget(button)
        return wrapper

    def _load_settings(self) -> None:
        self._anthropic_key.setText(self._settings.anthropic_api_key)
        self._openai_key.setText(self._settings.openai_api_key)
        self._gemini_key.setText(self._settings.gemini_api_key)
        self._default_output_dir.setText(self._settings.default_output_dir)
        self._default_language.setText(self._settings.default_language)
        self._ollama_url.setText(self._settings.ollama_url)
        self._set_combo_value(self._docling_device, self._settings.docling_device)

        target = self._settings.default_engine.lower()
        for idx in range(self._default_engine.count()):
            value = str(self._default_engine.itemData(idx) or self._default_engine.itemText(idx))
            if value.lower() == target:
                self._default_engine.setCurrentIndex(idx)
                break

    def _settings_from_fields(self) -> Settings:
        data = self._settings.model_dump()
        data.update(
            {
                "anthropic_api_key": self._anthropic_key.text().strip(),
                "openai_api_key": self._openai_key.text().strip(),
                "gemini_api_key": self._gemini_key.text().strip(),
                "default_engine": str(self._default_engine.currentData()),
                "default_output_dir": self._default_output_dir.text().strip(),
                "default_language": self._default_language.text().strip() or "pol+eng",
                "docling_device": str(self._docling_device.currentData()),
                "ollama_url": self._ollama_url.text().strip() or "http://localhost:11434",
            }
        )
        return Settings(**data)

    def _set_combo_value(self, combo: QComboBox, value: str) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _cuda_available(self) -> bool:
        return cuda_usable()

    def _apply(self) -> None:
        self._settings = self._settings_from_fields()
        save_settings(self._settings)
        QMessageBox.information(self, "Ustawienia", "Zapisano ustawienia.")

    def _on_ok(self) -> None:
        self._settings = self._settings_from_fields()
        save_settings(self._settings)
        self.accept()

    def _browse_default_output_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Wybierz domyślny folder wynikowy")
        if directory:
            self._default_output_dir.setText(directory)

    def _test_api_key(self, provider: str, value: str) -> None:
        if not value:
            QMessageBox.warning(self, "Test klucza", "Klucz API nie jest wpisany.")
            return

        package = {
            "anthropic": "anthropic",
            "openai": "openai",
            "gemini": "google-generativeai",
        }[provider]
        try:
            importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            QMessageBox.warning(
                self,
                "Test klucza",
                f"Klucz jest wpisany, ale pakiet {package} nie jest zainstalowany.",
            )
            return

        QMessageBox.information(self, "Test klucza", "Klucz jest wpisany, a pakiet SDK dostępny.")

    def _detect_ollama_models(self) -> None:
        url = (self._ollama_url.text().strip() or "http://localhost:11434").rstrip("/")
        self._ollama_models.clear()
        try:
            with urllib.request.urlopen(f"{url}/api/tags", timeout=3) as response:
                data = json.loads(response.read())
        except Exception as exc:
            QMessageBox.warning(self, "Ollama", f"Nie udało się połączyć z Ollamą:\n{exc}")
            return

        models = [
            str(model.get("name", "")) for model in data.get("models", []) if model.get("name")
        ]
        if not models:
            self._ollama_models.addItem("(brak modeli)")
            return
        self._ollama_models.addItems(models)
