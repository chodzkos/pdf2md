"""Testy ekstrakcji obrazów z PDF do Markdown."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

pymupdf: Any = pytest.importorskip("pymupdf")
pil_image: Any = pytest.importorskip("PIL.Image")

from pdf2md.core.image_extraction import (
    append_image_references,
    extract_pdf_images,
    image_output_dir,
)


def _pdf_with_large_and_small_image(tmp_path: Path) -> Path:
    large = tmp_path / "large.png"
    small = tmp_path / "small.png"
    pil_image.new("RGB", (140, 120), color=(220, 30, 30)).save(large)
    pil_image.new("RGB", (20, 20), color=(30, 30, 220)).save(small)

    pdf = tmp_path / "images.pdf"
    doc = pymupdf.open()
    page = doc.new_page(width=320, height=320)
    page.insert_image(pymupdf.Rect(20, 20, 160, 140), filename=str(large))
    page.insert_image(pymupdf.Rect(180, 20, 200, 40), filename=str(small))
    doc.save(str(pdf))
    doc.close()
    return pdf


def test_extract_pdf_images_creates_png_refs_and_filters_small_images(tmp_path: Path) -> None:
    pdf = _pdf_with_large_and_small_image(tmp_path)
    output_path = tmp_path / "book.md"

    images = extract_pdf_images(pdf, image_output_dir(output_path), min_size=100)
    markdown = append_image_references("# Tytuł\n", images, output_path)

    assert len(images) == 1
    assert images[0].path == tmp_path / "book_images" / "page1_img1.png"
    assert images[0].path.is_file()
    assert images[0].width == 140
    assert images[0].height == 120
    assert "![](<book_images/page1_img1.png>)" in markdown
    assert "page1_img2" not in markdown
