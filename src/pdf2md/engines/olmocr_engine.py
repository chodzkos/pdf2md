"""Adapter silnika olmOCR (VLM 7B do skanów) — izolowany venv + subprocess.

olmOCR ma stos vLLM konfliktujący z projektem, więc żyje w osobnym venv (``~/.venvs/olmocr``,
zob. INSTALL.md 7.2). pdf2md woła go przez subprocess (wzór jak MinerU). Obecność
środowiska sprawdzamy po binie ``vllm`` w venv — NIGDY nie importujemy olmocr w procesie pdf2md.

olmOCR shelluje CLI ``vllm`` po gołej nazwie, więc env subprocesu musi mieć ``PATH`` z binem
izolowanego venv (inaczej ``FileNotFoundError: 'vllm'``). Na 24 GB konieczne są flagi vLLM
``--max_model_len`` i ``--gpu-memory-utilization`` (domyślny 128k KV-cache → OOM).

Komenda i flagi zweryfikowane z ``python -m olmocr.pipeline --help`` zainstalowanej wersji
(uwaga: ``--gpu-memory-utilization`` przez myślniki, ``--max_model_len`` przez podkreślnik).

> STATUS: ZAPARKOWANY w trybie spawn-per-plik (serwer-dziecko nie wstaje pod nightly-vLLM/
> transformers 5.x; ~całe 24 GB; 90-150 s/wywołanie; EN-centryczny). Tryb produkcyjny to
> external-server (``olmocr_server_url`` → ``--server``). Dla PL: PaddleOCR-VL/Surya.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from loguru import logger

from pdf2md.core.config import get_settings
from pdf2md.engines.base import ConversionResult
from pdf2md.engines.vlm_base import VLMEngine
from pdf2md.utils.subprocess_flags import NO_WINDOW_FLAGS

#: Domyślna ścieżka izolowanego venv olmOCR (konwencja z INSTALL.md 7.2).
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
        """Wykonalność olmOCR. Bez importu olmocr, nigdy nie rzuca.

        Venv olmOCR (python) jest wymagany zawsze — CLI odpalamy przez niego.
        Dalej rozgałęzia się wg trybu:

        * **external-server** (``olmocr_server_url`` ustawiony): inferencja żyje na serwerze,
          klient NIE wymaga lokalnego GPU ani bina ``vllm`` — wystarczy python venv. Dzięki
          temu tryb produkcyjny działa też spod Windows z serwerem w WSL2/Linux.
        * **spawn lokalny** (brak server_url): olmOCR sam wstaje jako serwer vLLM, więc
          wymaga GPU ORAZ bina ``vllm`` w venv (półzłożony venv bez vLLM/torch ma dawać ❌,
          nie fałszywe ✅).
        """
        python = self._olmocr_python()
        if python is None:
            return False
        if get_settings().olmocr_server_url:
            return True
        return self.has_gpu() and (Path(python).parent / "vllm").exists()

    def convert(self, pdf_path: str, **kwargs: object) -> ConversionResult:
        """Uruchamia pipeline olmOCR (venv izolowany) z ``--markdown`` na całym PDF."""
        if not self.is_available():
            raise RuntimeError(
                "Silnik olmOCR nie jest dostępny: wymaga kompletnego izolowanego venv "
                "(~/.venvs/olmocr z vLLM) oraz GPU. Zob. INSTALL.md 7.2."
            )
        python = self._olmocr_python()
        if python is None:
            raise RuntimeError(
                "Nie znaleziono pythona venv olmOCR. Ustaw olmocr_python w config.toml "
                "albo zainstaluj wg INSTALL.md 7.2."
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
            # Flagi vLLM (nazwy zweryfikowane z --help): bez nich vLLM bierze 128k KV-cache → OOM.
            "--max_model_len",
            str(settings.olmocr_max_model_len),
            "--gpu-memory-utilization",
            str(settings.olmocr_gpu_memory_utilization),
        ]
        if settings.olmocr_server_url:
            # Tryb produkcyjny: olmocr nie spawnuje lokalnego vLLM, gada z gotowym serwerem.
            command += ["--server", settings.olmocr_server_url]

        # olmocr shelluje CLI `vllm` po gołej nazwie → PATH musi zawierać bin izolowanego venv.
        venv_bin = Path(python).parent
        env = os.environ.copy()
        env["PATH"] = f"{venv_bin}{os.pathsep}" + env.get("PATH", "")
        env["VIRTUAL_ENV"] = str(venv_bin.parent)
        env["VLLM_USE_FLASHINFER_SAMPLER"] = "0"  # fix Blackwell (jak MinerU/vlm, Paddle)

        logger.info(f"olmOCR (venv izolowany): {' '.join(command)}")
        try:
            self._process = subprocess.Popen(
                command,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=NO_WINDOW_FLAGS,
            )
            stdout, stderr = self._process.communicate()
            returncode = self._process.returncode
            if returncode != 0:
                # loguru formatuje przez {}, NIE %-args — używamy f-stringa, żeby treść TRAFIŁA do logu.
                logger.error(
                    f"olmOCR zakończył się błędem (kod {returncode}).\n"
                    f"stdout: {(stdout or '')[:2000]}\n"
                    f"stderr: {(stderr or '')[:2000]}"
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
