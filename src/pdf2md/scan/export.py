"""Eksport złożonej książki: Markdown, EPUB (ebooklib → fallback Pandoc) i raport jakości.

Ciężki ``ebooklib`` importowany jest leniwie wewnątrz funkcji EPUB — import modułu działa
bez niego (wtedy EPUB idzie przez Pandoc).
"""

from __future__ import annotations

from html import escape
from pathlib import Path

from loguru import logger

from pdf2md.scan.assembly import Chapter, build_toc


def _chapters_to_markdown(chapters: list[Chapter], *, with_toc: bool = True) -> str:
    """Skleja rozdziały w jeden Markdown (opcjonalnie z TOC na początku)."""
    parts: list[str] = []
    if with_toc and chapters:
        parts.append(build_toc(chapters))
    for ch in chapters:
        heading = "#" * max(1, ch.level)
        parts.append(f"{heading} {ch.title}".rstrip())
        if ch.body.strip():
            parts.append(ch.body.strip())
    return "\n\n".join(parts).strip() + "\n"


def export_markdown(chapters: list[Chapter], output_path: str | Path) -> str:
    """Zapisuje książkę jako pojedynczy plik Markdown (book.md). Zwraca ścieżkę."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_chapters_to_markdown(chapters), encoding="utf-8")
    logger.info(f"Zapisano Markdown książki: {path} ({len(chapters)} rozdz.)")
    return str(path)


def _body_to_html(body: str) -> str:
    """Prosty Markdown→HTML: akapity rozdzielone pustą linią → <p>…</p> (z escapowaniem)."""
    paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
    return "\n".join(f"<p>{escape(p)}</p>" for p in paragraphs)


def export_epub(
    chapters: list[Chapter],
    metadata: dict[str, str],
    output_path: str | Path,
) -> str:
    """Buduje EPUB. Preferuje ebooklib (kontrola TOC/CSS/metadanych); Pandoc jako fallback."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        return _export_epub_ebooklib(chapters, metadata, path)
    except ImportError:
        logger.warning("ebooklib niedostępny — buduję EPUB przez Pandoc (fallback)")
        return _export_epub_pandoc(chapters, metadata, path)


def _export_epub_ebooklib(
    chapters: list[Chapter],
    metadata: dict[str, str],
    path: Path,
) -> str:
    from ebooklib import epub

    language = metadata.get("language", "pl")
    book = epub.EpubBook()
    book.set_identifier(metadata.get("identifier") or "pdf2md-book")
    book.set_title(metadata.get("title") or "Książka")
    book.set_language(language)
    if metadata.get("author"):
        book.add_author(metadata["author"])

    css = epub.EpubItem(
        uid="style",
        file_name="style/book.css",
        media_type="text/css",
        content=b"body { font-family: serif; line-height: 1.5; margin: 1em; }",
    )
    book.add_item(css)

    epub_chapters = []
    for i, ch in enumerate(chapters, 1):
        item = epub.EpubHtml(title=ch.title, file_name=f"chap_{i:03d}.xhtml", lang=language)
        item.content = f"<h1>{escape(ch.title)}</h1>\n{_body_to_html(ch.body)}"
        item.add_item(css)
        book.add_item(item)
        epub_chapters.append(item)

    book.toc = tuple(epub_chapters)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", *epub_chapters]

    epub.write_epub(str(path), book)
    logger.info(f"Zapisano EPUB (ebooklib): {path}")
    return str(path)


def _export_epub_pandoc(
    chapters: list[Chapter],
    metadata: dict[str, str],
    path: Path,
) -> str:
    from pdf2md.exporters.pandoc_epub_exporter import PandocEpubExporter

    title = metadata.get("title", "Książka")
    author = metadata.get("author", "")
    lang = metadata.get("language", "pl")
    yaml = f"---\ntitle: {title}\nauthor: {author}\nlang: {lang}\n---\n\n"
    markdown = yaml + _chapters_to_markdown(chapters)
    result = PandocEpubExporter().export(markdown, path)
    logger.info(f"Zapisano EPUB (pandoc): {result}")
    return str(result)


def export_quality_report(
    validation_results: list[dict[str, object]],
    output_path: str | Path,
) -> str:
    """Zapisuje raport jakości (report.html): tabela stron z metrykami i oznaczeniem rerun.

    Każdy wpis to dict z kluczami: ``page`` oraz metryki z page_quality_score
    (char_count, replacement_char_count, unreadable_markers, suspicious_patterns)
    i opcjonalnie ``rerun`` (bool).
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    rerun_count = sum(1 for r in validation_results if r.get("rerun"))
    rows: list[str] = []
    for r in validation_results:
        flagged = bool(r.get("rerun"))
        cls = ' class="rerun"' if flagged else ""
        rows.append(
            f"<tr{cls}><td>{escape(str(r.get('page', '')))}</td>"
            f"<td>{escape(str(r.get('char_count', '')))}</td>"
            f"<td>{escape(str(r.get('replacement_char_count', '')))}</td>"
            f"<td>{escape(str(r.get('unreadable_markers', '')))}</td>"
            f"<td>{escape(str(r.get('suspicious_patterns', '')))}</td>"
            f"<td>{'⚠️ tak' if flagged else 'nie'}</td></tr>"
        )

    html = f"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="utf-8">
<title>Raport jakości OCR</title>
<style>
body {{ font-family: sans-serif; margin: 2em; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ccc; padding: 6px 10px; text-align: right; }}
th {{ background: #f0f0f0; }}
tr.rerun {{ background: #ffecec; }}
.summary {{ margin-bottom: 1em; }}
</style>
</head>
<body>
<h1>Raport jakości OCR</h1>
<p class="summary">Stron: {len(validation_results)} · do ponownego przebiegu: {rerun_count}</p>
<table>
<thead><tr><th>Strona</th><th>Znaki</th><th>Znaki �</th><th>[nieczytelne]</th>
<th>Podejrzane wzorce</th><th>Rerun</th></tr></thead>
<tbody>
{chr(10).join(rows)}
</tbody>
</table>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")
    logger.info(f"Zapisano raport jakości: {path}")
    return str(path)
