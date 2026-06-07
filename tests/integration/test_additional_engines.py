"""Testy integracyjne opcjonalnych silników konwersji."""

from __future__ import annotations

from pathlib import Path

import pytest

from pdf2md.engines.docling_engine import DoclingEngine
from pdf2md.engines.mineru_engine import MinerUEngine
from pdf2md.engines.pdf_craft_engine import PdfCraftEngine

FIXTURE = Path("tests/fixtures/test_text_1page.pdf")

pytestmark = pytest.mark.integration


def _fixture_path() -> str:
    if not FIXTURE.exists():
        pytest.skip("Brak tests/fixtures/test_text_1page.pdf")
    return str(FIXTURE)


@pytest.mark.skipif(not DoclingEngine().is_available(), reason="Docling niezainstalowany")
def test_docling_converts_pdf() -> None:
    """Docling konwertuje prosty PDF tekstowy do Markdown."""
    result = DoclingEngine().convert(
        _fixture_path(),
        do_ocr=False,
        force_backend_text=True,
        max_num_pages=1,
        page_range=(1, 1),
    )

    assert result.markdown
    assert result.pages >= 1
    assert result.engine_used == "Docling"


@pytest.mark.skipif(not MinerUEngine().is_available(), reason="MinerU niezainstalowany")
def test_mineru_converts_pdf(tmp_path: Path) -> None:
    """MinerU konwertuje prosty PDF tekstowy do Markdown przez CLI mineru."""
    result = MinerUEngine().convert(_fixture_path(), output_dir=str(tmp_path / "mineru"))

    assert result.markdown
    assert result.pages >= 1
    assert result.engine_used == "MinerU"


@pytest.mark.skipif(not PdfCraftEngine().is_available(), reason="pdf-craft niezainstalowany")
def test_pdf_craft_converts_pdf() -> None:
    """pdf-craft konwertuje prosty PDF do Markdown."""
    result = PdfCraftEngine().convert(_fixture_path(), ocr_size="tiny")

    assert result.markdown
    assert result.pages >= 1
    assert result.engine_used == "pdf-craft"
