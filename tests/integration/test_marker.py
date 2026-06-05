"""Testy integracyjne adaptera Marker."""

from __future__ import annotations

import importlib.metadata
import os
from pathlib import Path

import pytest

from pdf2md.engines.marker_engine import MarkerEngine


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
    pytest.mark.heavy,
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
    """Marker konwertuje jednostronicowy PDF tekstowy w trybie oszczędnym."""
    fixture = Path("tests/fixtures/test_text_1page.pdf")
    if not fixture.exists():
        pytest.skip("Brak tests/fixtures/test_text_1page.pdf")

    result = MarkerEngine().convert(
        str(fixture),
        marker_device="cpu",
        marker_workers=1,
        marker_max_pages=1,
        disable_multiprocessing=True,
        page_range="0",
    )

    assert result.markdown
    assert len(result.markdown) > 20
    assert result.pages == 1
