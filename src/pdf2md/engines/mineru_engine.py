"""Adapter silnika MinerU."""

from __future__ import annotations

import importlib
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from loguru import logger

from pdf2md.core.config import get_settings
from pdf2md.engines.base import ConversionEngine, ConversionResult


class MinerUEngine(ConversionEngine):
    """Adapter CLI mineru instalowanego jako izolowane narzedzie uv."""

    name = "MinerU"
    description = "Najlepszy dla dokumentów naukowych, wielokolumnowych i CJK"
    supports_ocr = True
    supports_llm = False
    requires_gpu = False

    def is_available(self) -> bool:
        """Sprawdza obecność CLI przez shutil.which, bez importowania MinerU."""
        return shutil.which("mineru") is not None

    def convert(self, pdf_path: str, **kwargs: object) -> ConversionResult:
        """Konwertuje PDF do Markdown przez CLI mineru."""
        executable = shutil.which("mineru")
        if executable is None:
            raise RuntimeError(
                "Silnik MinerU nie jest zainstalowany lub mineru nie jest w PATH. "
                "Zainstaluj go poleceniem: uv tool install mineru --with mineru[all]"
            )

        path = Path(pdf_path)
        output_dir = kwargs.pop("output_dir", None)
        keep_output = output_dir is not None
        work_dir = Path(str(output_dir)) if output_dir is not None else Path(tempfile.mkdtemp())
        work_dir.mkdir(parents=True, exist_ok=True)

        backend = get_settings().mineru_backend
        command = [executable, "-p", str(path), "-o", str(work_dir), "-b", backend]
        env = (
            {**os.environ, "VLLM_USE_FLASHINFER_SAMPLER": "0"}
            if backend != "pipeline"
            else None
        )
        logger.info(f"Konwertuję {path} przez MinerU (backend={backend}): {' '.join(command)}")
        try:
            subprocess.run(command, check=True, capture_output=True, text=True, env=env)
            markdown_path = self._find_markdown(work_dir)
            markdown = markdown_path.read_text(encoding="utf-8")
            pages = self._page_count(path)
        except subprocess.CalledProcessError as e:
            logger.error(
                "MinerU zakończył się błędem (kod %d).\nstdout: %s\nstderr: %s",
                e.returncode,
                (e.stdout or "")[:2000],
                (e.stderr or "")[:2000],
            )
            tail = (e.stderr or "")[-500:]
            raise RuntimeError(
                f"MinerU failed (code {e.returncode}): {tail}"
            ) from e
        except Exception:
            logger.exception(f"MinerU nie zdołał przekonwertować pliku: {path}")
            raise
        finally:
            if not keep_output:
                shutil.rmtree(work_dir, ignore_errors=True)

        return ConversionResult(
            markdown=markdown,
            engine_used=self.name,
            pages=pages,
            metadata={
                "source": str(path),
                "mineru_output_dir": str(work_dir) if keep_output else "",
            },
        )

    def _find_markdown(self, output_dir: Path) -> Path:
        markdown_files = sorted(output_dir.rglob("*.md"), key=lambda item: item.stat().st_mtime)
        if not markdown_files:
            raise RuntimeError(f"MinerU nie wygenerował pliku Markdown w {output_dir}")
        return markdown_files[-1]

    def _page_count(self, path: Path) -> int:
        pymupdf: Any = importlib.import_module("pymupdf")
        doc = pymupdf.open(str(path))
        try:
            return len(doc)
        finally:
            doc.close()
