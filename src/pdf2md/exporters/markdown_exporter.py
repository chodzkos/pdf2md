"""Eksporter Markdown do pliku."""

from __future__ import annotations

from pathlib import Path


class MarkdownExporter:
    """Zapisuje wynik konwersji jako plik Markdown."""

    def export(self, markdown: str, output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(markdown, encoding="utf-8")
        return path
