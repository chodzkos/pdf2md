"""Testy historii konwersji SQLite."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from pdf2md.core import history


def test_history_records_and_lists_recent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / "history.db"
    monkeypatch.setenv("PDF2MD_HISTORY_DB", str(db_path))

    first_id = history.record(
        input_path="/tmp/a.pdf",
        engine="Marker",
        llm_provider="none",
        llm_mode="none",
        output_path="/tmp/a.md",
        status="ok",
        duration_s=1.25,
    )
    second_id = history.record(
        input_path="/tmp/b.pdf",
        engine="Docling",
        llm_provider="Ollama",
        llm_mode="whole_document",
        output_path="/tmp/b.md",
        status="error",
        duration_s=2.5,
        error_msg="boom",
    )

    entries = history.list_recent()

    assert [entry.id for entry in entries] == [second_id, first_id]
    assert entries[0].status == "error"
    assert entries[0].error_msg == "boom"
    assert entries[1].duration_s == 1.25


def test_history_filters_by_engine_case_insensitive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PDF2MD_HISTORY_DB", str(tmp_path / "history.db"))
    history.record(
        input_path="a.pdf",
        engine="Marker",
        output_path="a.md",
        status="ok",
        duration_s=1.0,
    )
    history.record(
        input_path="b.pdf",
        engine="Docling",
        output_path="b.md",
        status="ok",
        duration_s=1.0,
    )

    entries = history.list_recent(engine="marker")

    assert len(entries) == 1
    assert entries[0].engine == "Marker"


def test_history_export_csv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PDF2MD_HISTORY_DB", str(tmp_path / "history.db"))
    history.record(
        input_path="a.pdf",
        engine="Marker",
        output_path="a.md",
        status="ok",
        duration_s=1.0,
    )
    history.record(
        input_path="b.pdf",
        engine="Docling",
        output_path="b.md",
        status="ok",
        duration_s=1.0,
    )
    csv_path = tmp_path / "historia.csv"

    exported = history.export_csv(csv_path, engine="docling")

    assert exported == csv_path
    rows = list(csv.DictReader(csv_path.read_text(encoding="utf-8").splitlines()))
    assert len(rows) == 1
    assert rows[0]["engine"] == "Docling"
    assert rows[0]["input_path"] == "b.pdf"


def test_history_clear(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PDF2MD_HISTORY_DB", str(tmp_path / "history.db"))
    history.record(
        input_path="a.pdf",
        engine="Marker",
        output_path="a.md",
        status="ok",
        duration_s=1.0,
    )

    removed = history.clear()

    assert removed == 1
    assert history.list_recent() == []


def test_history_rejects_invalid_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PDF2MD_HISTORY_DB", str(tmp_path / "history.db"))

    with pytest.raises(ValueError, match="limit"):
        history.list_recent(limit=0)
