"""Test integracyjny adaptera PyMuPDF4LLM."""

from __future__ import annotations

import importlib.metadata
from pathlib import Path

import pytest

from pdf2md.engines.pymupdf4llm_engine import PyMuPDF4LLMEngine


def _has_pymupdf4llm() -> bool:
    try:
        importlib.metadata.version("pymupdf4llm")
    except importlib.metadata.PackageNotFoundError:
        return False
    return True


@pytest.mark.integration
def test_pymupdf4llm_converts_text_pdf() -> None:
    """PyMuPDF4LLM konwertuje przykładowy PDF tekstowy."""
    if not _has_pymupdf4llm():
        pytest.skip("pymupdf4llm nie jest zainstalowany")

    fixture = Path("tests/fixtures/test_text.pdf")
    if not fixture.exists():
        pytest.skip("Brak tests/fixtures/test_text.pdf")

    result = PyMuPDF4LLMEngine().convert(str(fixture))

    assert result.markdown
    assert len(result.markdown) > 100
    assert result.pages > 0
