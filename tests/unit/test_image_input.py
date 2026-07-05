"""Testy wejść obrazowych JPG/PNG/TIFF."""

from __future__ import annotations

from pathlib import Path

import pytest

from pdf2md.core.converter import ConversionError, Converter
from pdf2md.engines.base import ConversionEngine, ConversionResult


class _FakeImageOCREngine(ConversionEngine):
    name = "Fake OCR"
    description = "test"
    supports_ocr = True
    supports_llm = False

    def __init__(self) -> None:
        self.seen_path = ""

    def is_available(self) -> bool:
        return True

    def convert(self, pdf_path: str, **kwargs: object) -> ConversionResult:
        pymupdf = pytest.importorskip("pymupdf")
        self.seen_path = pdf_path
        doc = pymupdf.open(pdf_path)
        try:
            pages = len(doc)
        finally:
            doc.close()
        markdown = "\n\n---\n\n".join(f"tekst strony {index}" for index in range(1, pages + 1))
        return ConversionResult(markdown=markdown, engine_used=self.name, pages=pages)


class _FakeTextEngine(_FakeImageOCREngine):
    name = "Fake Text"
    supports_ocr = False


@pytest.mark.parametrize(
    ("suffix", "image_format"),
    [
        (".png", "PNG"),
        (".jpg", "JPEG"),
    ],
)
def test_converter_accepts_single_image_inputs(
    tmp_path: Path, suffix: str, image_format: str
) -> None:
    image = _write_image(tmp_path / f"scan{suffix}", image_format=image_format)
    engine = _FakeImageOCREngine()

    result = Converter().convert(str(image), engine)

    assert result.pages == 1
    assert "tekst strony 1" in result.markdown
    assert Path(engine.seen_path).suffix == ".pdf"
    assert result.metadata["source"] == str(image)
    assert result.metadata["input_type"] == "image"


def test_converter_accepts_multipage_tiff(tmp_path: Path) -> None:
    pil_image = pytest.importorskip("PIL.Image")
    first = pil_image.new("RGB", (600, 240), "white")
    second = pil_image.new("RGB", (600, 240), "white")
    tiff = tmp_path / "scan.tiff"
    first.save(tiff, format="TIFF", save_all=True, append_images=[second])
    engine = _FakeImageOCREngine()

    result = Converter().convert(str(tiff), engine)

    assert result.pages == 2
    assert "tekst strony 1" in result.markdown
    assert "tekst strony 2" in result.markdown


def test_converter_rejects_image_for_non_ocr_engine(tmp_path: Path) -> None:
    image = _write_image(tmp_path / "scan.png")

    with pytest.raises(ConversionError, match="wymaga silnika OCR"):
        Converter().convert(str(image), _FakeTextEngine())


def _write_image(path: Path, *, image_format: str = "PNG") -> Path:
    pil_image = pytest.importorskip("PIL.Image")
    image = pil_image.new("RGB", (600, 240), "white")
    image.save(path, format=image_format)
    return path
