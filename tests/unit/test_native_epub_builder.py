"""Tests for portable native EPUB builder."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

pytest.importorskip("ebooklib")
pytest.importorskip("markdown_it")

from pdf2md.exporters.epub import EpubChapter, EpubInput, EpubMetadata, build_epub, from_markdown


def test_build_epub_writes_metadata_toc_images_css_and_cover(tmp_path: Path) -> None:
    output = tmp_path / "book.epub"
    data = EpubInput(
        metadata=EpubMetadata(
            title="Native Book",
            authors=("Ada", "Bob"),
            language="pl",
            date="2026-07-16",
            identifier="book-id",
        ),
        chapters=(
            EpubChapter("Start", '<p>Hello</p><img src="images/pic.png" />'),
            EpubChapter("End", "<p>Bye</p>"),
        ),
        images={"images/pic.png": b"not-really-png"},
        css="body { color: black; }",
        cover=b"not-really-jpg",
    )

    build_epub(data, output)

    assert zipfile.is_zipfile(output)
    with zipfile.ZipFile(output) as zf:
        names = zf.namelist()
        opf_name = next(name for name in names if name.endswith(".opf"))
        opf = zf.read(opf_name).decode("utf-8")
        assert "Native Book" in opf
        assert "Ada" in opf
        assert "Bob" in opf
        assert "book-id" in opf
        assert any(name.endswith("nav.xhtml") for name in names)
        assert any(name.endswith("chap_001.xhtml") for name in names)
        assert any(name.endswith("chap_002.xhtml") for name in names)
        assert "EPUB/images/pic.png" in names
        assert any(name.endswith("cover.jpg") for name in names)
        assert zf.read("EPUB/style/book.css").decode("utf-8") == "body { color: black; }"


def test_from_markdown_splits_headings_and_rewrites_embedded_image_refs() -> None:
    data = from_markdown(
        "# One\n\nText ![](pic.png)\n\n## Two\n\nMore",
        {"title": "Fallback", "author": "Ada", "language": "en"},
        images={"pic.png": b"png"},
    )

    assert [chapter.title for chapter in data.chapters] == ["One", "Two"]
    assert 'src="images/pic.png"' in data.chapters[0].html_body
    assert data.images["pic.png"] == b"png"
    assert data.metadata.authors == ("Ada",)
    assert data.metadata.language == "en"
