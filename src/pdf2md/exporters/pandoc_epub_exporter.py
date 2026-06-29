"""Eksporter EPUB oparty o Pandoc."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from pdf2md.detection.tools import check_pandoc


class PandocEpubExporter:
    """Konwertuje Markdown do EPUB przez zewnętrzny Pandoc."""

    def export(self, markdown: str, output_path: str | Path) -> Path:
        if not check_pandoc():
            raise RuntimeError("Pandoc nie jest dostępny w PATH")

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".md", delete=False) as tmp:
            tmp.write(markdown)
            tmp_path = Path(tmp.name)
        try:
            subprocess.run(
                ["pandoc", str(tmp_path), "-o", str(path)],
                check=True,
                capture_output=True,
                text=True,
            )
        finally:
            tmp_path.unlink(missing_ok=True)
        return path
