"""Testy adaptera PyMuPDF4LLM bez importowania realnego silnika."""

from __future__ import annotations

import importlib.metadata
from pathlib import Path

import pytest

from pdf2md.engines import pymupdf4llm_engine
from pdf2md.engines.pymupdf4llm_engine import PyMuPDF4LLMEngine


def test_is_available_true_when_pymupdf4llm_installed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(importlib.metadata, "version", lambda package: "0.0.17")

    assert PyMuPDF4LLMEngine().is_available() is True


def test_is_available_false_when_pymupdf4llm_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_version(_package: str) -> str:
        raise importlib.metadata.PackageNotFoundError

    monkeypatch.setattr(importlib.metadata, "version", fake_version)

    assert PyMuPDF4LLMEngine().is_available() is False


def test_convert_raises_when_pymupdf4llm_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")
    engine = PyMuPDF4LLMEngine()
    monkeypatch.setattr(engine, "is_available", lambda: False)

    with pytest.raises(RuntimeError, match="engines-core"):
        engine.convert(str(pdf))


def test_convert_uses_pymupdf4llm_and_counts_pages(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")
    captured: dict[str, object] = {}

    class FakeDoc:
        def __len__(self) -> int:
            return 4

        def close(self) -> None:
            captured["closed"] = True

    class FakePymupdf:
        @staticmethod
        def open(path: str) -> FakeDoc:
            captured["opened"] = path
            return FakeDoc()

    class FakePymupdf4llm:
        @staticmethod
        def to_markdown(path: str, **kwargs: object) -> str:
            captured["to_markdown"] = (path, kwargs)
            return "# markdown"

    def fake_import_module(name: str) -> object:
        if name == "pymupdf":
            return FakePymupdf
        if name == "pymupdf4llm":
            return FakePymupdf4llm
        raise AssertionError(name)

    engine = PyMuPDF4LLMEngine()
    monkeypatch.setattr(engine, "is_available", lambda: True)
    monkeypatch.setattr(pymupdf4llm_engine.importlib, "import_module", fake_import_module)

    result = engine.convert(str(pdf), page_chunks=True)

    assert result.markdown == "# markdown"
    assert result.pages == 4
    assert result.engine_used == "PyMuPDF4LLM"
    assert captured["to_markdown"] == (str(pdf), {"page_chunks": True})
    assert captured["opened"] == str(pdf)
    assert captured["closed"] is True
