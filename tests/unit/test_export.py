"""Testy eksportu książki (scan/export): Markdown, EPUB (ebooklib), raport jakości."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from pdf2md.scan.assembly import Chapter
from pdf2md.scan.export import export_epub, export_markdown, export_quality_report


def _chapters() -> list[Chapter]:
    return [
        Chapter(title="Rozdział I", body="Treść pierwszego rozdziału.\n\nDrugi akapit."),
        Chapter(title="Rozdział II", body="Treść drugiego rozdziału."),
    ]


def test_export_markdown_writes_toc_and_chapters(tmp_path: Path) -> None:
    """book.md zawiera TOC i nagłówki rozdziałów."""
    out = export_markdown(_chapters(), tmp_path / "book.md")
    text = Path(out).read_text(encoding="utf-8")

    assert "# Spis treści" in text
    assert "# Rozdział I" in text
    assert "# Rozdział II" in text
    assert "Treść pierwszego rozdziału." in text


def test_export_epub_builds_valid_zip_with_opf(tmp_path: Path) -> None:
    """EPUB to poprawny ZIP z content.opf zawierającym tytuł i rozdziały."""
    pytest.importorskip("ebooklib")
    metadata = {"title": "Rok Jednorożca", "author": "Andre Norton", "language": "pl"}

    out = export_epub(_chapters(), metadata, tmp_path / "book.epub")
    path = Path(out)
    assert path.exists()
    assert zipfile.is_zipfile(path)

    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        # mimetype + content.opf (ebooklib zapisuje opf w EPUB/)
        assert "mimetype" in names
        opf_name = next((n for n in names if n.endswith(".opf")), None)
        assert opf_name is not None, f"brak .opf w {names}"
        opf = zf.read(opf_name).decode("utf-8")
        assert "Rok Jednorożca" in opf
        assert "Andre Norton" in opf
        # dwa pliki rozdziałów w spisie zawartości
        chap_files = [n for n in names if n.endswith(".xhtml") and "chap_" in n]
        assert len(chap_files) == 2


def test_export_quality_report_html(tmp_path: Path) -> None:
    """report.html zawiera tabelę stron i oznacza strony do ponownego przebiegu."""
    results: list[dict[str, object]] = [
        {
            "page": 1,
            "char_count": 1200,
            "replacement_char_count": 0,
            "unreadable_markers": 0,
            "suspicious_patterns": 1,
            "rerun": False,
        },
        {
            "page": 2,
            "char_count": 40,
            "replacement_char_count": 8,
            "unreadable_markers": 2,
            "suspicious_patterns": 5,
            "rerun": True,
        },
    ]
    out = export_quality_report(results, tmp_path / "report.html")
    html = Path(out).read_text(encoding="utf-8")

    assert "<table" in html
    assert "Stron: 2" in html
    assert "do ponownego przebiegu: 1" in html
    assert 'class="rerun"' in html  # strona 2 oznaczona
