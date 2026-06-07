"""Testy detekcji typu PDF."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from pdf2md.detection import pdf_type


class _FakePage:
    def __init__(self, text: str) -> None:
        self._text = text

    def get_text(self, _mode: str) -> str:
        return self._text


class _FakeDoc:
    def __init__(self, texts: list[str]) -> None:
        self._pages = [_FakePage(text) for text in texts]
        self.closed = False

    def __iter__(self) -> iter:
        return iter(self._pages)

    def __len__(self) -> int:
        return len(self._pages)

    def close(self) -> None:
        self.closed = True


def _patch_pymupdf(
    monkeypatch: pytest.MonkeyPatch,
    texts: list[str],
) -> _FakeDoc:
    doc = _FakeDoc(texts)

    class FakePymupdf:
        @staticmethod
        def open(_path: str) -> _FakeDoc:
            return doc

    monkeypatch.setattr(pdf_type.importlib, "import_module", lambda name: FakePymupdf)
    return doc


def test_detect_pdf_type_missing_file() -> None:
    result = pdf_type.detect_pdf_type("/nie/ma/takiego.pdf")

    assert result["type"] == "unknown"
    assert result["reason"] == "plik nie istnieje"


@pytest.mark.parametrize(
    ("texts", "expected_type", "text_pages", "scan_pages"),
    [
        (["strona 1", "strona 2"], "native", 2, 0),
        (["", "   "], "scanned", 0, 2),
        (["tekst", ""], "mixed", 1, 1),
        ([], "unknown", 0, 0),
    ],
)
def test_detect_pdf_type_classifies_pages(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    texts: list[str],
    expected_type: str,
    text_pages: int,
    scan_pages: int,
) -> None:
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")
    doc = _patch_pymupdf(monkeypatch, texts)

    result = pdf_type.detect_pdf_type(str(pdf))

    assert result["type"] == expected_type
    assert result["pages"] == len(texts)
    assert result["text_pages"] == text_pages
    assert result["scan_pages"] == scan_pages
    assert doc.closed is True


def test_detect_pdf_type_returns_unknown_on_parser_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    pdf = tmp_path / "broken.pdf"
    pdf.write_bytes(b"broken")

    class BrokenPymupdf:
        @staticmethod
        def open(_path: str) -> Any:
            raise RuntimeError("cannot parse")

    monkeypatch.setattr(pdf_type.importlib, "import_module", lambda name: BrokenPymupdf)

    result = pdf_type.detect_pdf_type(str(pdf))

    assert result["type"] == "unknown"
    assert result["reason"] == "cannot parse"
