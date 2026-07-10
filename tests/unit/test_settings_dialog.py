"""Testy dialogu ustawień GUI: dropdown modeli Ollamy i utrwalanie wyboru.

Uruchamiane na platformie Qt 'offscreen'. Jeśli Qt nie da się zainicjować (brak bibliotek
systemowych), testy są pomijane — nie wywalają CI.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)

from PySide6.QtWidgets import QApplication

from pdf2md.core import config
from pdf2md.gui import settings_dialog as sd
from pdf2md.gui.settings_dialog import SettingsDialog

pytestmark = pytest.mark.gui


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    try:
        app = QApplication.instance() or QApplication([])
    except Exception as exc:  # pragma: no cover - środowisko bez Qt
        pytest.skip(f"Qt niedostępne: {exc}")
    return app


@pytest.fixture()
def isolated_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    config_dir = tmp_path / "config"
    config_file = config_dir / "config.toml"
    monkeypatch.setattr(config, "_CONFIG_DIR", config_dir)
    monkeypatch.setattr(config, "_CONFIG_FILE", config_file)
    monkeypatch.setattr(config, "_settings_cache", None)
    return config_file


def _mock_ollama_tags(monkeypatch: pytest.MonkeyPatch, models: list[str]) -> None:
    body = json.dumps({"models": [{"name": m} for m in models]}).encode()

    class _Resp:
        def __enter__(self) -> _Resp:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return body

    monkeypatch.setattr(sd.urllib.request, "urlopen", lambda url, timeout=None: _Resp())


def test_construction_does_not_fetch_models_over_http(
    qapp: QApplication, isolated_config: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Konstrukcja dialogu NIE robi requestu HTTP — dropdown ma tylko bieżący model z configu."""

    def forbidden(url: object, timeout: object = None) -> object:
        raise AssertionError("brak requestu HTTP oczekiwany przy konstrukcji dialogu")

    monkeypatch.setattr(sd.urllib.request, "urlopen", forbidden)

    dialog = SettingsDialog()
    try:
        items = [dialog._ollama_model.itemText(i) for i in range(dialog._ollama_model.count())]
        # tylko model z configu (qwen3:14b) — bez listy pobieranej z serwera
        assert items == ["qwen3:14b"]
        assert dialog._ollama_model.currentText() == "qwen3:14b"
    finally:
        dialog.deleteLater()


def test_detect_populates_models_and_reselects_current(
    qapp: QApplication, isolated_config: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Slot po wątku „Wykryj modele" wypełnia listę i re-zaznacza model z configu; przycisk wraca."""
    _mock_ollama_tags(monkeypatch, ["modelA", "qwen3:14b", "modelB"])

    dialog = SettingsDialog()
    try:
        # Symulujemy zakończenie wątku pobierania — wynik _fetch_ollama_models trafia do slotu.
        dialog._on_models_fetched(sd._fetch_ollama_models(dialog._ollama_url.text()))

        items = [dialog._ollama_model.itemText(i) for i in range(dialog._ollama_model.count())]
        assert "modelA" in items
        assert "modelB" in items
        assert dialog._ollama_model.currentText() == "qwen3:14b"
        assert dialog._detect_button.isEnabled() is True
    finally:
        dialog.deleteLater()


def test_model_choice_saved_and_survives_reload(
    qapp: QApplication, isolated_config: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Wybór modelu zapisuje config.ollama_model i przetrwa przeładowanie configu z dysku."""
    _mock_ollama_tags(monkeypatch, ["qwen2.5:14b", "llama3:8b"])

    dialog = SettingsDialog()
    try:
        dialog._select_ollama_model("llama3:8b")
        dialog._on_ok()  # _settings_from_fields + save_settings
    finally:
        dialog.deleteLater()

    assert isolated_config.exists()
    # przeładuj config z dysku (wyczyść cache)
    monkeypatch.setattr(config, "_settings_cache", None)
    reloaded = config.get_settings()
    assert reloaded.ollama_model == "llama3:8b"
