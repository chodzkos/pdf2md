"""Adapter silnika olmOCR (VLM 7B do skanów).

olmOCR działa jako własny pipeline operujący na całym PDF: renderuje strony, uruchamia
model przez serwer vLLM i zapisuje Markdown (flaga ``--markdown``). Pipeline sam zarządza
VRAM (uruchamia i zamyka serwer vLLM w obrębie subprocesu), więc zwolnienie VRAM następuje
przy zakończeniu procesu — stąd nadpisujemy convert() zamiast korzystać z paczkowej pętli
bazy. Import/obecność olmocr sprawdzamy tylko przez metadata, bez importu modelu.

Model: allenai/olmOCR-2-7B-1025-FP8 (zweryfikuj najnowszą wersję na PyPI/HuggingFace).
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from loguru import logger

from pdf2md.engines.base import ConversionResult
from pdf2md.engines.vlm_base import VLMEngine

DEFAULT_MODEL = "allenai/olmOCR-2-7B-1025-FP8"


class OlmOCREngine(VLMEngine):
    """Adapter olmOCR — czysty Markdown, równania, tabele, kolejność czytania."""

    name = "olmOCR"
    description = "VLM 7B do skanów: czysty Markdown, równania, tabele, kolejność czytania"
    package_name = "olmocr"

    def __init__(self, model: str = DEFAULT_MODEL) -> None:
        super().__init__()
        self.model = model

    def convert(self, pdf_path: str, **kwargs: object) -> ConversionResult:
        """Uruchamia pipeline olmOCR z flagą --markdown na całym PDF.

        Subprocess sam renderuje strony, odpala serwer vLLM i zwalnia VRAM przy wyjściu.
        """
        if not self.is_available():
            raise RuntimeError(
                "Silnik olmOCR nie jest dostępny: wymaga zainstalowanego pakietu 'olmocr' "
                "oraz działającego GPU (CUDA)."
            )

        output_dir = kwargs.pop("output_dir", None)
        keep_output = output_dir is not None
        workspace = (
            Path(str(output_dir))
            if keep_output
            else Path(tempfile.mkdtemp(prefix="pdf2md_olmocr_"))
        )
        workspace.mkdir(parents=True, exist_ok=True)

        command = [
            sys.executable,
            "-m",
            "olmocr.pipeline",
            str(workspace),
            "--markdown",
            "--model",
            self.model,
            "--pdfs",
            str(pdf_path),
        ]
        logger.info(f"olmOCR: {' '.join(command)}")
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            logger.error(
                "olmOCR zakończył się błędem (kod %d).\nstdout: %s\nstderr: %s",
                e.returncode,
                (e.stdout or "")[:2000],
                (e.stderr or "")[:2000],
            )
            tail = (e.stderr or "")[-500:]
            raise RuntimeError(f"olmOCR failed (code {e.returncode}): {tail}") from e
        finally:
            # serwer vLLM zamyka się wraz z subprocesem; dla pewności wymuś empty_cache
            self.unload_model()

        markdown, pages = self._collect_markdown(workspace)
        return ConversionResult(
            markdown=markdown,
            engine_used=self.name,
            pages=pages,
            metadata={
                "source": str(pdf_path),
                "model": self.model,
                "work_dir": str(workspace) if keep_output else "",
            },
        )

    def _collect_markdown(self, workspace: Path) -> tuple[str, int]:
        """Zbiera wygenerowane pliki .md z workspace olmOCR, posortowane po nazwie."""
        markdown_files = sorted(workspace.rglob("*.md"))
        if not markdown_files:
            raise RuntimeError(f"olmOCR nie wygenerował plików Markdown w {workspace}")
        parts = [path.read_text(encoding="utf-8") for path in markdown_files]
        return "\n\n---\n\n".join(parts), len(markdown_files)
