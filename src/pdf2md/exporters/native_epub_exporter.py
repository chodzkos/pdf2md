"""Native EPUB exporter using the portable ebooklib builder."""

from __future__ import annotations

from pathlib import Path

from pdf2md.exporters.epub import EpubMetadata, build_epub, from_markdown


class NativeEpubExporter:
    """Converts Markdown to EPUB without external Pandoc/Calibre processes."""

    def export(
        self,
        markdown: str,
        output_path: str | Path,
        *,
        source_dir: Path | None = None,
    ) -> Path:
        del source_dir
        path = Path(output_path)
        data = from_markdown(markdown, EpubMetadata())
        build_epub(data, path)
        return path
