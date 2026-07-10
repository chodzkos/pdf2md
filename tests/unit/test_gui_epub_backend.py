"""Testy wyboru backendu EPUB w GUI i fallbacku eksportu."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)

from PySide6.QtWidgets import QApplication

from pdf2md.gui import main_window as mw
from pdf2md.gui.widgets import profile_selector as ps
from pdf2md.gui.widgets.profile_selector import ProfileEditDialog
from pdf2md.scan import profiles
from pdf2md.scan.profiles import load_profile

pytestmark = pytest.mark.gui


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    try:
        return QApplication.instance() or QApplication([])
    except Exception as exc:  # pragma: no cover - środowisko bez Qt
        pytest.skip(f"Qt niedostępne: {exc}")


class _MessageBoxStub:
    def exec(self) -> None:
        return None


def test_profile_editor_shows_only_available_epub_backends(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Combo backendu pokazuje tylko wykryte backendy i blokuje pojedynczy wybór."""
    monkeypatch.setattr(ps, "check_pandoc", lambda: True)
    monkeypatch.setattr(ps, "check_calibre", lambda: False)

    dialog = ProfileEditDialog("balanced")
    try:
        assert dialog._epub_backend.count() == 1
        assert dialog._epub_backend.itemData(0) == "pandoc"
        assert dialog._epub_backend.isEnabled() is False
    finally:
        dialog.deleteLater()


def test_profile_editor_saves_epub_backend_choice(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Wybór Calibre w edytorze profilu jest zapisywany w profilu użytkownika."""
    monkeypatch.setattr(profiles, "_USER_PROFILES_DIR", tmp_path / "profiles")
    monkeypatch.setattr(ps, "check_pandoc", lambda: True)
    monkeypatch.setattr(ps, "check_calibre", lambda: True)
    monkeypatch.setattr(ps, "themed_message_box", lambda *args, **kwargs: _MessageBoxStub())

    dialog = ProfileEditDialog("balanced")
    try:
        calibre_idx = dialog._epub_backend.findData("calibre")
        assert calibre_idx >= 0
        dialog._epub_backend.setCurrentIndex(calibre_idx)
        dialog._name.setText("balanced-calibre")

        dialog._on_save()
    finally:
        dialog.deleteLater()

    assert load_profile("balanced-calibre").output.epub_backend == "calibre"


def test_epub_backend_falls_back_from_missing_pandoc_to_calibre(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Preferowany Pandoc przełącza się na Calibre, gdy tylko Calibre jest dostępne."""
    monkeypatch.setattr(mw, "check_pandoc", lambda: False)
    monkeypatch.setattr(mw, "check_calibre", lambda: True)

    backend, warning = mw._resolve_epub_backend("pandoc")

    assert backend == "calibre"
    assert warning is not None
    assert "Pandoc" in warning
    assert "Calibre" in warning


def test_epub_backend_falls_back_from_missing_calibre_to_pandoc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Preferowane Calibre przełącza się na Pandoc, gdy tylko Pandoc jest dostępny."""
    monkeypatch.setattr(mw, "check_pandoc", lambda: True)
    monkeypatch.setattr(mw, "check_calibre", lambda: False)

    backend, warning = mw._resolve_epub_backend("calibre")

    assert backend == "pandoc"
    assert warning is not None
    assert "Calibre" in warning
    assert "Pandoc" in warning
