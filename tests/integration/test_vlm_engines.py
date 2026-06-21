"""Testy integracyjne silników VLM-OCR (Faza 2).

Wszystkie wymagają GPU i zainstalowanego pakietu silnika. Pomijane (skip), gdy brak GPU
albo silnik niezainstalowany — nigdy nie wywalają zestawu testów na maszynie bez CUDA.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pdf2md.engines.olmocr_engine import OlmOCREngine
from pdf2md.engines.paddleocr_vl_engine import PaddleOCRVLEngine
from pdf2md.engines.surya_engine import SuryaEngine
from pdf2md.engines.vlm_base import VLMEngine

pytestmark = [pytest.mark.integration, pytest.mark.heavy]

SCAN_FIXTURE = Path(__file__).parent.parent / "fixtures" / "test_scan.pdf"

ENGINES = [
    pytest.param(SuryaEngine, id="surya"),
    pytest.param(OlmOCREngine, id="olmocr"),
    pytest.param(PaddleOCRVLEngine, id="paddleocr-vl"),
]


@pytest.mark.skipif(not VLMEngine.has_gpu(), reason="brak GPU/CUDA")
@pytest.mark.skipif(not SCAN_FIXTURE.exists(), reason="brak tests/fixtures/test_scan.pdf")
@pytest.mark.parametrize("engine_cls", ENGINES)
def test_vlm_engine_converts_single_page(engine_cls: type[VLMEngine], tmp_path: Path) -> None:
    """Konwersja jednej strony skanu daje niepusty Markdown."""
    engine = engine_cls()
    if not engine.is_available():
        pytest.skip(f"silnik {engine.name} niezainstalowany")

    result = engine.convert(str(SCAN_FIXTURE), output_dir=str(tmp_path), batch_size=1)

    assert result.engine_used == engine.name
    assert result.pages >= 1
    assert result.markdown.strip(), "wynik OCR jest pusty"
