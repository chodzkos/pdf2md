"""Eksporter EPUB oparty o Calibre (`ebook-convert`)."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from pdf2md.detection.dependencies import check_calibre


class CalibreEpubExporter:
    """Konwertuje Markdown do EPUB przez zewnętrzny `ebook-convert` z Calibre."""

    def export(self, markdown: str, output_path: str | Path) -> Path:
        if not check_calibre():
            raise RuntimeError("Calibre (ebook-convert) nie jest dostępny w PATH")

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Calibre rozpoznaje format wejściowy po rozszerzeniu — temp z .md włącza wtyczkę Markdown.
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".md", delete=False) as tmp:
            tmp.write(markdown)
            tmp_path = Path(tmp.name)
        try:
            subprocess.run(
                ["ebook-convert", str(tmp_path), str(path)],
                check=True,
                capture_output=True,
                text=True,
            )
        finally:
            tmp_path.unlink(missing_ok=True)
        return path
