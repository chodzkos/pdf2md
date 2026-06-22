"""Adapter silnika olmOCR (VLM 7B do skanów) — izolowany venv + subprocess.

olmOCR ma stos vLLM konfliktujący z projektem, więc żyje w osobnym venv (``~/.venvs/olmocr``,
zob. SILNIKI_INSTALACJA.md 2.7). pdf2md woła go przez subprocess (wzór jak MinerU): pipeline
renderuje strony, odpala wewnętrzny serwer vLLM i zapisuje Markdown (``--markdown``). Obecność
środowiska sprawdzamy po ścieżce do pythona venv — NIGDY nie importujemy olmocr w procesie pdf2md.

Komenda i domyślny model (``allenai/olmOCR-2-7B-1025-FP8``) zweryfikowane z
``python -m olmocr.pipeline --help`` zainstalowanej wersji.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from loguru import logger

from pdf2md.core.config import get_settings
from pdf2md.engines.base import ConversionResult
from pdf2md.engines.vlm_base import VLMEngine

#: Domyślna ścieżka izolowanego venv olmOCR (konwencja z SILNIKI_INSTALACJA.md 2.7).
_DEFAULT_VENV_PYTHON = Path.home() / ".venvs" / "olmocr" / "bin" / "python"


class OlmOCREngine(VLMEngine):
    """Adapter olmOCR — izolowany venv (subprocess), czysty Markdown ze skanów."""

    name = "olmOCR"
    description = "VLM 7B do skanów: czysty Markdown, równania, tabele, kolejność czytania"
    package_name = "olmocr"

    def __init__(self) -> None:
        super().__init__()
        self._process: subprocess.Popen[str] | None = None

    def _olmocr_python(self) -> str | None:
        """Ścieżka do pythona venv olmOCR: z configu, inaczej domyślny ~/.venvs/olmocr."""
        configured = get_settings().olmocr_python
        if configured and Path(configured).exists():
            return configured
        if _DEFAULT_VENV_PYTHON.exists():
            return str(_DEFAULT_VENV_PYTHON)
        return None

    def is_available(self) -> bool:
        """Obecność izolowanego środowiska olmOCR + GPU. Bez importu olmocr, nigdy nie rzuca."""
        if not self.has_gpu():
            return False
        return self._olmocr_python() is not None or shutil.which("olmocr") is not None

    def convert(self, pdf_path: str, **kwargs: object) -> ConversionResult:
        """Uruchamia pipeline olmOCR (venv izolowany) z ``--markdown`` na całym PDF."""
        if not self.is_available():
            raise RuntimeError(
                "Silnik olmOCR nie jest dostępny: wymaga izolowanego venv (~/.venvs/olmocr) "
                "oraz GPU. Zob. SILNIKI_INSTALACJA.md 2.7."
            )
        python = self._olmocr_python()
        if python is None:
            raise RuntimeError(
                "Nie znaleziono pythona venv olmOCR. Ustaw olmocr_python w config.toml "
                "albo zainstaluj wg SILNIKI_INSTALACJA.md 2.7."
            )

        settings = get_settings()
        model = settings.olmocr_model
        output_dir = kwargs.pop("output_dir", None)
        keep_output = output_dir is not None
        workspace = (
            Path(str(output_dir))
            if keep_output
            else Path(tempfile.mkdtemp(prefix="pdf2md_olmocr_"))
        )
        workspace.mkdir(parents=True, exist_ok=True)

        command = [
            python,
            "-m",
            "olmocr.pipeline",
            str(workspace),
            "--markdown",
            "--model",
            model,
            "--pdfs",
            str(pdf_path),
        ]
        # Bez tego flashinfer JIT-uje sampler przez nvcc i pada na nowym GPU (jak MinerU/vlm).
        env = {**os.environ, "VLLM_USE_FLASHINFER_SAMPLER": "0"}
        logger.info(f"olmOCR (venv izolowany): {' '.join(command)}")

        try:
            self._process = subprocess.Popen(
                command, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            stdout, stderr = self._process.communicate()
            returncode = self._process.returncode
            if returncode != 0:
                logger.error(
                    "olmOCR zakończył się błędem (kod %d).\nstdout: %s\nstderr: %s",
                    returncode,
                    (stdout or "")[:2000],
                    (stderr or "")[:2000],
                )
                tail = (stderr or "")[-500:]
                raise RuntimeError(f"olmOCR failed (code {returncode}): {tail}")
        finally:
            self.unload_model()

        markdown, pages = self._collect_markdown(workspace)
        return ConversionResult(
            markdown=markdown,
            engine_used=self.name,
            pages=pages,
            metadata={
                "source": str(pdf_path),
                "model": model,
                "work_dir": str(workspace) if keep_output else "",
            },
        )

    def unload_model(self) -> None:
        """Zamyka proces pipeline'u (terminate + wait); VRAM zwalnia OS przy wyjściu serwera vLLM."""
        proc = self._process
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
        self._process = None
        logger.debug("olmOCR: proces zamknięty (VRAM zwalnia OS)")

    def _collect_markdown(self, workspace: Path) -> tuple[str, int]:
        """Zbiera wygenerowane pliki .md z workspace olmOCR, posortowane po nazwie."""
        markdown_files = sorted(workspace.rglob("*.md"))
        if not markdown_files:
            raise RuntimeError(f"olmOCR nie wygenerował plików Markdown w {workspace}")
        parts = [path.read_text(encoding="utf-8") for path in markdown_files]
        return "\n\n---\n\n".join(parts), len(markdown_files)
