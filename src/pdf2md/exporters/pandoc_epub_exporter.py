"""Eksporter EPUB oparty o Pandoc."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from chodzkos_detection import check_pandoc


class PandocEpubExporter:
    """Konwertuje Markdown do EPUB przez zewnętrzny Pandoc."""

    def export(
        self,
        markdown: str,
        output_path: str | Path,
        *,
        source_dir: Path | None = None,
    ) -> Path:
        if not check_pandoc():
            raise RuntimeError("Pandoc nie jest dostępny w PATH")

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Względne referencje ![](obraz.png) Pandoc rozwiązuje względem pliku wejściowego —
        # dlatego temp .md musi leżeć obok obrazów (source_dir), a nie w gołym /tmp.
        resource_dir = source_dir if source_dir is not None else path.parent
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", suffix=".md", dir=resource_dir, delete=False
        ) as tmp:
            tmp.write(markdown)
            tmp_path = Path(tmp.name)
        try:
            subprocess.run(
                # --resource-path jako druga linia obrony, gdyby temp trafił jednak indziej.
                ["pandoc", str(tmp_path), "-o", str(path), f"--resource-path={resource_dir}"],
                check=True,
                capture_output=True,
                text=True,
            )
        finally:
            tmp_path.unlink(missing_ok=True)
        return path
