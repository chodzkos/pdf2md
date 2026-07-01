"""Testy zbiorczego raportu środowiska."""

from __future__ import annotations

import pytest

from pdf2md.detection import dependencies


def test_check_all_combines_reports(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dependencies.platform, "system", lambda: "Linux")
    monkeypatch.setattr(dependencies.platform, "platform", lambda: "Linux-test")
    monkeypatch.setattr(dependencies.platform, "python_version", lambda: "3.13")
    monkeypatch.setattr(
        dependencies,
        "check_tools",
        lambda: {"tesseract": {"available": False}, "poppler": True, "pandoc": False},
    )
    monkeypatch.setattr(dependencies, "check_ollama", lambda: {"available": True})
    monkeypatch.setattr(dependencies, "check_gpu", lambda: {"cuda_usable": False})
    monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/ebook-convert")

    assert dependencies.check_all() == {
        "system": {"os": "Linux", "platform": "Linux-test", "python": "3.13"},
        "tesseract": {"available": False},
        "poppler": True,
        "pandoc": False,
        "calibre": True,
        "ollama": {"available": True},
        "gpu": {"cuda_usable": False},
    }


def test_check_calibre_true_when_ebook_convert_in_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("shutil.which", lambda name: "/opt/calibre/ebook-convert")

    assert dependencies.check_calibre() is True


def test_check_calibre_false_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("shutil.which", lambda name: None)

    assert dependencies.check_calibre() is False
