"""Dialog ustawień GUI zapisujący do wspólnego config.toml."""

from __future__ import annotations

import importlib.metadata
import json
import urllib.request

from chodzkos_gui_kit.qt.dialogs import pick_dir
from pydantic import ValidationError
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from pdf2md.core.config import Settings, get_settings, save_settings
from pdf2md.core.registry import engine_registry
from pdf2md.detection.hardware import cuda_usable
from pdf2md.gui.theming import follow_app_titlebar, themed_message_box
from pdf2md.llm import sdk_package_for_provider


def _fetch_ollama_models(url: str) -> list[str]:
    """Pobiera listę modeli z {url}/api/tags. Po cichu zwraca [] przy błędzie.

    Funkcja modułowa (bez self) — bezpieczna do wywołania w wątku roboczym.
    """
    base = (url.strip() or "http://localhost:11434").rstrip("/")
    try:
        with urllib.request.urlopen(f"{base}/api/tags", timeout=3) as response:
            data = json.loads(response.read())
    except Exception:
        return []
    return [str(model.get("name", "")) for model in data.get("models", []) if model.get("name")]


class _OllamaModelsFetcher(QThread):
    """Pobiera modele Ollamy w osobnym wątku — sonda HTTP nie blokuje wątku UI."""

    fetched = Signal(list)  # list[str] nazw modeli

    def __init__(self, url: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._url = url

    def run(self) -> None:
        self.fetched.emit(_fetch_ollama_models(self._url))


class SettingsDialog(QDialog):
    """Okno ustawień aplikacji korzystające z core/config.py."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Ustawienia")
        self.setMinimumSize(560, 420)
        self._settings = get_settings()
        self._models_fetcher: _OllamaModelsFetcher | None = None
        self._build_ui()
        self._load_settings()
        self._titlebar = follow_app_titlebar(self)

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
        self._detect_button = QPushButton("Wykryj modele")
        self._detect_button.clicked.connect(self._detect_ollama_models)
        url_row.addWidget(self._ollama_url)
        url_row.addWidget(self._detect_button)
        layout.addLayout(url_row)

        model_row = QHBoxLayout()
        model_row.addWidget(QLabel("Domyślny model:"))
        self._ollama_model = QComboBox()
        self._ollama_model.setEditable(True)  # pozwól zachować model spoza listy /api/tags
        model_row.addWidget(self._ollama_model)
        layout.addLayout(model_row)
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
        # Bez requestu HTTP przy otwarciu dialogu — wstaw tylko bieżący model z configu.
        # Pełną listę użytkownik pobiera przyciskiem „Wykryj modele" (w wątku).
        self._select_ollama_model(self._settings.ollama_model)
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
                "ollama_model": self._ollama_model.currentText().strip()
                or self._settings.ollama_model,
            }
        )
        return Settings(**data)

    def _set_combo_value(self, combo: QComboBox, value: str) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _cuda_available(self) -> bool:
        return cuda_usable()

    def _commit_settings(self) -> bool:
        """Buduje i zapisuje Settings; przy ValidationError pokazuje komunikat i zwraca False.

        Pułapka na przyszłość: dziś combos ograniczają wejście, ale gdyby pojawiło się pole
        walidowane spoza dozwolonego zbioru, użytkownik dostanie czytelny komunikat zamiast
        niewyłapanego wyjątku (i okno nie zamknie się z niezapisanymi danymi).
        """
        try:
            self._settings = self._settings_from_fields()
        except ValidationError as exc:
            first = exc.errors()[0]
            loc = first.get("loc")
            field = str(loc[0]) if loc else "?"
            themed_message_box(
                self,
                QMessageBox.Icon.Warning,
                "Ustawienia",
                f"Nieprawidłowa wartość dla „{field}”: {first['msg']}",
            ).exec()
            return False
        save_settings(self._settings)
        return True

    def _apply(self) -> None:
        if self._commit_settings():
            themed_message_box(
                self, QMessageBox.Icon.Information, "Ustawienia", "Zapisano ustawienia."
            ).exec()

    def _on_ok(self) -> None:
        if self._commit_settings():
            self.accept()

    def _browse_default_output_dir(self) -> None:
        directory = pick_dir(
            parent=self,
            title="Wybierz domyślny folder wynikowy",
            start_dir=self._default_output_dir.text().strip(),
        )
        if directory:
            self._default_output_dir.setText(directory)

    def _test_api_key(self, provider: str, value: str) -> None:
        if not value:
            themed_message_box(
                self, QMessageBox.Icon.Warning, "Test klucza", "Klucz API nie jest wpisany."
            ).exec()
            return

        package = sdk_package_for_provider(provider)
        try:
            importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            themed_message_box(
                self,
                QMessageBox.Icon.Warning,
                "Test klucza",
                f"Klucz jest wpisany, ale pakiet {package} nie jest zainstalowany.",
            ).exec()
            return

        themed_message_box(
            self,
            QMessageBox.Icon.Information,
            "Test klucza",
            f"Klucz jest wpisany, a pakiet SDK ({package}) dostępny. "
            "Uwaga: nie wykonano zapytania do API.",
        ).exec()

    def _populate_ollama_models(self, models: list[str]) -> None:
        """Wypełnia dropdown modelami, zachowując bieżąco wybrany model."""
        current = self._ollama_model.currentText().strip()
        self._ollama_model.clear()
        self._ollama_model.addItems(models)
        if current:
            self._select_ollama_model(current)

    def _select_ollama_model(self, model: str) -> None:
        """Preselekcjonuje model; dodaje go do listy, jeśli go nie ma (combo jest editable)."""
        if not model:
            return
        index = self._ollama_model.findText(model)
        if index < 0:
            self._ollama_model.addItem(model)
            index = self._ollama_model.findText(model)
        self._ollama_model.setCurrentIndex(index)

    def _detect_ollama_models(self) -> None:
        """Pobiera modele w wątku (sonda HTTP poza wątkiem UI) z kursorem busy na przycisku."""
        if self._models_fetcher is not None and self._models_fetcher.isRunning():
            return
        url = self._ollama_url.text().strip() or "http://localhost:11434"
        self._detect_button.setEnabled(False)
        self._detect_button.setCursor(QCursor(Qt.CursorShape.BusyCursor))
        fetcher = _OllamaModelsFetcher(url, self)
        fetcher.fetched.connect(self._on_models_fetched)
        self._models_fetcher = fetcher
        fetcher.start()

    def _on_models_fetched(self, models: list[str]) -> None:
        """Slot w wątku UI: przywraca przycisk i wypełnia listę (albo ostrzega)."""
        self._detect_button.setEnabled(True)
        self._detect_button.unsetCursor()
        if not models:
            themed_message_box(
                self,
                QMessageBox.Icon.Warning,
                "Ollama",
                "Nie udało się pobrać modeli z Ollamy. Sprawdź URL i czy serwer działa.",
            ).exec()
            return
        # Po „Wykryj modele" zaznacz w combo model z configu, jeśli jest na liście.
        self._populate_ollama_models(models)
        self._select_ollama_model(self._settings.ollama_model)
