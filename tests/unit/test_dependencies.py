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

    assert dependencies.check_all() == {
        "system": {"os": "Linux", "platform": "Linux-test", "python": "3.13"},
        "tesseract": {"available": False},
        "poppler": True,
        "pandoc": False,
        "ollama": {"available": True},
        "gpu": {"cuda_usable": False},
    }
