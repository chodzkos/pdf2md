"""Portable EPUB builder.

This module is intentionally isolated: it depends only on stdlib, ebooklib and
Markdown parsing. It accepts structured chapter HTML and writes an EPUB file.
"""

from __future__ import annotations

import mimetypes
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from html import escape
from pathlib import Path
from typing import cast
from uuid import uuid4

from ebooklib import epub
from markdown_it import MarkdownIt

_DEFAULT_CSS = (
    "body { font-family: serif; line-height: 1.5; margin: 1em; }\nimg { max-width: 100%; }"
)
_IMAGE_REF_RE = re.compile(r'(<img\s+[^>]*src=["\'])([^"\']+)(["\'][^>]*>)', re.IGNORECASE)
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_SLUG_RE = re.compile(r"[^A-Za-z0-9_.-]+")


@dataclass(frozen=True)
class EpubMetadata:
    """Metadata required by the portable EPUB builder."""

    title: str = "Książka"
    authors: tuple[str, ...] = ()
    language: str = "pl"
    date: str | None = None
    identifier: str | None = None


@dataclass(frozen=True)
class EpubChapter:
    """Single EPUB chapter with an HTML/XHTML body fragment."""

    title: str
    html_body: str


@dataclass(frozen=True)
class EpubInput:
    """Structured input for native EPUB generation."""

    metadata: EpubMetadata = field(default_factory=EpubMetadata)
    chapters: tuple[EpubChapter, ...] = ()
    images: Mapping[str, bytes] = field(default_factory=dict)
    css: str | None = None
    cover: bytes | None = None


def build_epub(data: EpubInput, output_path: str | Path) -> None:
    """Build an EPUB from structured chapter HTML."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    metadata = data.metadata
    book = epub.EpubBook()
    book.set_identifier(metadata.identifier or f"urn:uuid:{uuid4()}")
    book.set_title(metadata.title)
    book.set_language(metadata.language)
    for author in metadata.authors:
        book.add_author(author)
    if metadata.date:
        book.add_metadata("DC", "date", metadata.date)

    css_item = epub.EpubItem(
        uid="style",
        file_name="style/book.css",
        media_type="text/css",
        content=(data.css or _DEFAULT_CSS).encode("utf-8"),
    )
    book.add_item(css_item)

    for name, payload in data.images.items():
        book.add_item(
            epub.EpubItem(
                uid=_safe_uid(name),
                file_name=name,
                media_type=_media_type(name),
                content=payload,
            )
        )

    if data.cover is not None:
        book.set_cover("cover.jpg", data.cover)

    epub_chapters: list[epub.EpubHtml] = []
    chapters = data.chapters or (EpubChapter(metadata.title, ""),)
    for index, chapter in enumerate(chapters, 1):
        item = epub.EpubHtml(
            title=chapter.title,
            file_name=f"chap_{index:03d}.xhtml",
            lang=metadata.language,
        )
        item.content = f"<h1>{escape(chapter.title)}</h1>\n{chapter.html_body}"
        item.add_item(css_item)
        book.add_item(item)
        epub_chapters.append(item)

    book.toc = tuple(epub_chapters)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", *epub_chapters]
    epub.write_epub(str(path), book)


def from_markdown(
    md_text: str,
    metadata: EpubMetadata | Mapping[str, object] | None = None,
    images: Mapping[str, bytes] | None = None,
    css: str | None = None,
    cover: bytes | None = None,
) -> EpubInput:
    """Parse Markdown into chapter HTML and return portable EPUB input."""

    normalized_metadata = _metadata_from_mapping(metadata)
    html_chapters = [
        EpubChapter(
            title=title, html_body=_rewrite_image_refs(_markdown_to_html(body), images or {})
        )
        for title, body in _split_markdown_chapters(md_text, normalized_metadata.title)
    ]
    return EpubInput(
        metadata=normalized_metadata,
        chapters=tuple(html_chapters),
        images=dict(images or {}),
        css=css,
        cover=cover,
    )


def _split_markdown_chapters(md_text: str, fallback_title: str) -> list[tuple[str, str]]:
    chapters: list[tuple[str, list[str]]] = []
    current_title = fallback_title
    current_lines: list[str] = []
    for line in md_text.splitlines():
        match = _HEADING_RE.match(line)
        if match:
            if current_lines or chapters:
                chapters.append((current_title, current_lines))
            current_title = _strip_inline_markup(match.group(2))
            current_lines = []
        else:
            current_lines.append(line)
    chapters.append((current_title, current_lines))
    return [(title, "\n".join(lines).strip()) for title, lines in chapters if title or lines]


def _markdown_to_html(md_text: str) -> str:
    if not md_text.strip():
        return ""
    return cast(str, MarkdownIt("commonmark", {"html": True}).render(md_text))


def _rewrite_image_refs(html: str, images: Mapping[str, bytes]) -> str:
    if not images:
        return html

    def replace(match: re.Match[str]) -> str:
        src = match.group(2)
        image_name = Path(src).name
        if src.startswith("images/") or image_name not in images:
            return match.group(0)
        return f"{match.group(1)}images/{image_name}{match.group(3)}"

    return _IMAGE_REF_RE.sub(replace, html)


def _metadata_from_mapping(metadata: EpubMetadata | Mapping[str, object] | None) -> EpubMetadata:
    if isinstance(metadata, EpubMetadata):
        return metadata
    if metadata is None:
        return EpubMetadata(date=date.today().isoformat())
    authors_value = metadata.get("authors", metadata.get("author", ()))
    if isinstance(authors_value, str):
        authors = tuple(a.strip() for a in authors_value.split(",") if a.strip())
    elif isinstance(authors_value, (list, tuple, set)):
        authors = tuple(str(a).strip() for a in authors_value if str(a).strip())
    else:
        authors = (str(authors_value).strip(),) if str(authors_value).strip() else ()
    return EpubMetadata(
        title=str(metadata.get("title") or "Książka"),
        authors=authors,
        language=str(metadata.get("language") or metadata.get("lang") or "pl"),
        date=str(metadata["date"]) if metadata.get("date") else None,
        identifier=str(metadata["identifier"]) if metadata.get("identifier") else None,
    )


def _strip_inline_markup(text: str) -> str:
    return re.sub(r"[*_`]+", "", text).strip()


def _safe_uid(name: str) -> str:
    return _SLUG_RE.sub("_", name).strip("_") or "item"


def _media_type(name: str) -> str:
    guessed, _ = mimetypes.guess_type(name)
    return guessed or "application/octet-stream"
