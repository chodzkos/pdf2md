"""Eksportery wynikowego Markdown i EPUB."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Protocol

from pdf2md.detection.dependencies import check_calibre
from pdf2md.exporters.calibre_epub_exporter import CalibreEpubExporter
from pdf2md.exporters.markdown_exporter import MarkdownExporter
from pdf2md.exporters.pandoc_epub_exporter import PandocEpubExporter

logger = logging.getLogger(__name__)


class EpubExporter(Protocol):
    def export(
        self, markdown: str, output_path: str | Path, *, source_dir: Path | None = None
    ) -> Path: ...


EPUB_BACKENDS = ("pandoc", "native", "calibre")


def build_epub_exporter(backend: str = "pandoc") -> EpubExporter:
    """Zwraca eksporter EPUB dla wybranego backendu, z fallbackiem na Pandoc.

    Gdy ``backend == "calibre"``, ale `ebook-convert` jest niedostępny, wraca do
    Pandoca (z ostrzeżeniem). Nieznana wartość również skutkuje Pandokiem.
    """
    if backend == "native":
        from pdf2md.exporters.native_epub_exporter import NativeEpubExporter

        return NativeEpubExporter()
    if backend == "calibre":
        if check_calibre():
            return CalibreEpubExporter()
        logger.warning("Calibre (ebook-convert) niedostępne — eksportuję EPUB przez Pandoc")
    return PandocEpubExporter()


__all__ = [
    "EPUB_BACKENDS",
    "CalibreEpubExporter",
    "EpubExporter",
    "MarkdownExporter",
    "PandocEpubExporter",
    "build_epub_exporter",
]
