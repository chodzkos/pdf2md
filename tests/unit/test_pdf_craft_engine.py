"""Testy adaptera pdf-craft bez uruchamiania realnego OCR."""

from __future__ import annotations

import importlib.metadata
from pathlib import Path

import pytest

from pdf2md.engines import pdf_craft_engine
from pdf2md.engines.pdf_craft_engine import PdfCraftEngine


def test_is_available_true_when_pdf_craft_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(importlib.metadata, "version", lambda package: "1.0.13")

    assert PdfCraftEngine().is_available() is True


def test_is_available_false_when_pdf_craft_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_version(_package: str) -> str:
        raise importlib.metadata.PackageNotFoundError

    monkeypatch.setattr(importlib.metadata, "version", fake_version)

    assert PdfCraftEngine().is_available() is False


def test_convert_raises_when_pdf_craft_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")
    engine = PdfCraftEngine()
    monkeypatch.setattr(engine, "is_available", lambda: False)

    with pytest.raises(RuntimeError, match="pdf-craft"):
        engine.convert(str(pdf))


def test_convert_uses_pdf_craft_api_and_filters_options(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")
    captured: dict[str, object] = {}

    class FakePdfCraft:
        @staticmethod
        def transform_markdown(
            *,
            pdf_path: str,
            markdown_path: str,
            markdown_assets_path: str,
            **options: object,
        ) -> None:
            captured["pdf_path"] = pdf_path
            captured["markdown_assets_path"] = markdown_assets_path
            captured["options"] = options
            Path(markdown_path).write_text("# pdf-craft\n", encoding="utf-8")

    def fake_import_module(name: str) -> object:
        if name == "pdf_craft":
            return FakePdfCraft
        raise AssertionError(name)

    engine = PdfCraftEngine()
    monkeypatch.setattr(engine, "is_available", lambda: True)
    monkeypatch.setattr(engine, "_page_count", lambda path: 3)
    monkeypatch.setattr(pdf_craft_engine.importlib, "import_module", fake_import_module)

    result = engine.convert(
        str(pdf),
        ocr_size="tiny",
        ignore_pdf_errors=True,
        unsupported_option="ignored",
    )

    assert result.markdown == "# pdf-craft\n"
    assert result.engine_used == "pdf-craft"
    assert result.pages == 3
    assert result.metadata == {"source": str(pdf)}
    assert captured["pdf_path"] == str(pdf)
    assert captured["options"] == {
        "analysing_path": str(Path(captured["markdown_assets_path"]).parent / "analysis"),
        "ocr_size": "tiny",
        "ignore_pdf_errors": True,
    }


def test_page_count_closes_document(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")
    captured: dict[str, object] = {}

    class FakeDoc:
        def __len__(self) -> int:
            return 5

        def close(self) -> None:
            captured["closed"] = True

    class FakePymupdf:
        @staticmethod
        def open(path: str) -> FakeDoc:
            captured["opened"] = path
            return FakeDoc()

    monkeypatch.setattr(pdf_craft_engine.importlib, "import_module", lambda name: FakePymupdf)

    assert PdfCraftEngine()._page_count(pdf) == 5
    assert captured["opened"] == str(pdf)
    assert captured["closed"] is True
