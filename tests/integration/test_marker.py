"""Testy integracyjne adaptera Marker."""

from __future__ import annotations

import importlib.metadata
import os
from pathlib import Path

import pytest

from pdf2md.engines.marker_engine import MarkerEngine
from pdf2md.engines.pymupdf4llm_engine import PyMuPDF4LLMEngine


def _has_package(package_name: str) -> bool:
    try:
        importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return False
    return True


RUN_REAL_MARKER = os.getenv("PDF2MD_RUN_MARKER_INTEGRATION") == "1"

pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
    pytest.mark.skipif(
        not RUN_REAL_MARKER,
        reason=(
            "Pełny Marker ładuje ciężkie modele i potrafi ubić WSL/VS Code. "
            "Uruchom świadomie: PDF2MD_RUN_MARKER_INTEGRATION=1 pytest tests/integration/test_marker.py -v"
        ),
    ),
]


@pytest.mark.skipif(not _has_package("marker-pdf"), reason="marker-pdf nie jest zainstalowany")
def test_marker_converts_text_pdf() -> None:
    """Marker konwertuje przykładowy PDF tekstowy."""
    fixture = Path("tests/fixtures/test_text.pdf")
    if not fixture.exists():
        pytest.skip("Brak tests/fixtures/test_text.pdf")

    result = MarkerEngine().convert(str(fixture), torch_device="cpu", page_range="0")

    assert result.markdown
    assert len(result.markdown) > 100
    assert result.pages > 0


@pytest.mark.skipif(not _has_package("marker-pdf"), reason="marker-pdf nie jest zainstalowany")
def test_marker_converts_scan_pdf_if_fixture_exists() -> None:
    """Marker konwertuje fixture skanu, jeśli jest dostępny lokalnie."""
    fixture = Path("tests/fixtures/test_scan.pdf")
    if not fixture.exists():
        pytest.skip("Brak tests/fixtures/test_scan.pdf")

    result = MarkerEngine().convert(str(fixture), torch_device="cpu", page_range="0")

    assert result.markdown
    assert len(result.markdown) > 20
    assert result.pages > 0


@pytest.mark.skipif(not _has_package("marker-pdf"), reason="marker-pdf nie jest zainstalowany")
@pytest.mark.skipif(not _has_package("pymupdf4llm"), reason="pymupdf4llm nie jest zainstalowany")
def test_marker_output_length_compared_to_pymupdf4llm() -> None:
    """Marker i PyMuPDF4LLM zwracają niepuste wyniki dla tego samego PDF-a."""
    fixture = Path("tests/fixtures/test_text.pdf")
    if not fixture.exists():
        pytest.skip("Brak tests/fixtures/test_text.pdf")

    marker_result = MarkerEngine().convert(str(fixture), torch_device="cpu", page_range="0")
    pymupdf_result = PyMuPDF4LLMEngine().convert(str(fixture))

    assert len(marker_result.markdown) > 100
    assert len(pymupdf_result.markdown) > 100
    assert marker_result.pages == pymupdf_result.pages
