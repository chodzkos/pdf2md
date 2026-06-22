"""Testy ScanPipelineEngine — sprzątanie work/ po EPUB i zachowanie przy --keep-work.

OCR jest zamockowany (fake engine zapisujący md_pages), korekta LLM pominięta — testujemy
orkiestrację i cykl życia katalogu roboczego bez GPU/modeli.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pdf2md.engines.base import ConversionEngine, ConversionResult
from pdf2md.engines.scan_pipeline_engine import ScanPipelineEngine


class _FakeOCREngine(ConversionEngine):
    """Udaje silnik VLM-OCR: zapisuje md_pages i zwraca ConversionResult."""

    name = "FakeOCR"
    description = "test"
    supports_ocr = True
    supports_llm = False
    requires_gpu = True

    def is_available(self) -> bool:
        return True

    def convert(self, pdf_path: str, **kwargs: object) -> ConversionResult:
        out = Path(str(kwargs["output_dir"]))
        md_pages = out / "md_pages"
        md_pages.mkdir(parents=True, exist_ok=True)
        (md_pages / "page_0001.md").write_text(
            "## Rozdział I\n\nTreść strony pierwszej.", encoding="utf-8"
        )
        (md_pages / "page_0002.md").write_text(
            "Dalszy ciąg treści strony drugiej.", encoding="utf-8"
        )
        return ConversionResult(markdown="x", engine_used=self.name, pages=2)


def _run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, keep_work: bool) -> ConversionResult:
    pytest.importorskip("ebooklib")
    engine = ScanPipelineEngine()
    # bez dostawcy LLM → korekta pominięta, surowy OCR
    monkeypatch.setattr(engine, "_resolve_llm_provider", lambda _p: None)
    out_base = tmp_path / "out"
    return engine.convert(
        str(tmp_path / "ksiazka.pdf"),
        output_dir=str(out_base),
        ocr_engine=_FakeOCREngine(),
        keep_work=keep_work,
    )


def _scanpipe_dirs(out_base: Path) -> list[Path]:
    return [p for p in out_base.glob("pdf2md_scanpipe_*") if p.is_dir()]


def test_pipeline_builds_outputs_and_cleans_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Po udanym EPUB: book.md/epub/report istnieją, a work/ jest sprzątany."""
    result = _run(tmp_path, monkeypatch, keep_work=False)
    out_base = tmp_path / "out"

    assert (out_base / "book.md").exists()
    assert (out_base / "book.epub").exists()
    assert (out_base / "report.html").exists()
    assert result.metadata["epub_path"]
    assert result.pages == 2
    # rozdział wykryty z nagłówka „## Rozdział I"
    assert int(result.metadata["chapters"]) >= 1  # type: ignore[arg-type]
    # katalog roboczy posprzątany
    assert _scanpipe_dirs(out_base) == []
    assert result.metadata["work_dir"] == ""


def test_pipeline_keeps_work_dir_with_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Z --keep-work katalog roboczy zostaje (debugowanie)."""
    result = _run(tmp_path, monkeypatch, keep_work=True)
    out_base = tmp_path / "out"

    kept = _scanpipe_dirs(out_base)
    assert len(kept) == 1
    assert result.metadata["work_dir"] == str(kept[0])
    # md_pages zachowane w katalogu roboczym
    assert (kept[0] / "md_pages" / "page_0001.md").exists()
