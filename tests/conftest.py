"""Globalne ustawienia testów ustawiane przed importem ciężkich silników."""

import os
from pathlib import Path

import pytest

os.environ.setdefault("PDFTEXT_WORKERS", "1")
os.environ.setdefault("TORCH_DEVICE", "cpu")


@pytest.fixture(autouse=True)
def isolate_history_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Każdy test dostaje własną bazę historii konwersji."""
    monkeypatch.setenv("PDF2MD_HISTORY_DB", str(tmp_path / "history.db"))
