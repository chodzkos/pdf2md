"""Bazowy adapter dla silników OCR opartych na modelach wizyjno-językowych (VLM).

Wszystkie silniki VLM wymagają GPU. `is_available()` MUSI zwracać False bez rzucania
wyjątku, gdy brakuje GPU albo pakietu silnika — dzięki temu CLI/GUI listują je jako
niedostępne zamiast wywalać się przy starcie.

Zarządzanie VRAM jest krytyczne na 24 GB: model VLM (np. olmOCR-2-7B ~7-8 GB) i model
korekty LLM (np. qwen3:14b ~9-10 GB) NIE zmieszczą się jednocześnie. Dlatego pipeline
ładuje VLM → przetwarza WSZYSTKIE strony → `unload_model()` (realne zwolnienie VRAM)
→ dopiero potem faza korekty LLM (Etap 13). Nigdy oba modele naraz.
"""

from __future__ import annotations

import gc
import importlib.metadata
import json
import os
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import Any, cast

from loguru import logger

from pdf2md.engines.base import ConversionEngine, ConversionResult
from pdf2md.scan.preprocessing import DPI_OLD_BOOKS, iter_page_batches


class VLMEngine(ConversionEngine):
    """Wspólna baza dla silników OCR opartych na VLM (olmOCR, PaddleOCR-VL, Surya)."""

    requires_gpu = True
    supports_ocr = True
    supports_llm = False

    #: Nazwa dystrybucji do importlib.metadata.version() — ustaw w podklasie.
    package_name: str = ""
    #: Domyślne DPI renderowania stron przed OCR.
    default_dpi: int = DPI_OLD_BOOKS

    def __init__(self) -> None:
        self._model: Any = None

    # ------------------------------------------------------------------
    # Dostępność
    # ------------------------------------------------------------------

    @staticmethod
    def has_gpu() -> bool:
        """Zwraca True tylko gdy torch widzi działającą CUDA. Nigdy nie rzuca."""
        try:
            import torch

            return bool(torch.cuda.is_available())
        except Exception:
            return False

    def is_available(self) -> bool:
        """Pakiet silnika zainstalowany ORAZ dostępne GPU. Bez importu modelu."""
        if not self.package_name:
            return False
        try:
            importlib.metadata.version(self.package_name)
        except importlib.metadata.PackageNotFoundError:
            return False
        except Exception:
            return False
        return self.has_gpu()

    # ------------------------------------------------------------------
    # Zarządzanie modelem / VRAM
    # ------------------------------------------------------------------

    def load_model(self) -> None:
        """Ładuje model VLM do pamięci GPU. Implementowane w podklasie."""
        raise NotImplementedError

    def unload_model(self) -> None:
        """Realnie zwalnia VRAM: usuwa referencje, gc.collect(), empty_cache().

        Podklasy z dodatkowymi referencjami (predyktory, serwery) powinny wyczyścić
        własne atrybuty, a potem wywołać super().unload_model().
        """
        self._model = None
        gc.collect()
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
        logger.debug(f"{self.name}: unload_model() — VRAM zwolniony")

    def _ocr_page(self, image_path: str) -> str:
        """Wykonuje OCR jednej strony (obrazu) i zwraca Markdown. Podklasa implementuje."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Konwersja
    # ------------------------------------------------------------------

    def convert(self, pdf_path: str, **kwargs: object) -> ConversionResult:
        """Konwersja paczkowa: render → OCR per strona → usuwanie PNG po paczce.

        Ładuje model raz, przetwarza wszystkie strony, na końcu (finally) zwalnia VRAM.
        Zapisuje surowe wyniki do ``work/ocr_json`` i Markdown stron do ``work/md_pages``.
        """
        if not self.is_available():
            raise RuntimeError(
                f"Silnik {self.name} nie jest dostępny: wymaga zainstalowanego pakietu "
                f"'{self.package_name}' oraz działającego GPU (CUDA)."
            )

        dpi = int(cast(Any, kwargs.pop("dpi", self.default_dpi)))
        batch_size = int(cast(Any, kwargs.pop("batch_size", 20)))
        output_dir = kwargs.pop("output_dir", None)
        keep_output = output_dir is not None
        work_dir = (
            Path(str(output_dir)) if keep_output else Path(tempfile.mkdtemp(prefix="pdf2md_vlm_"))
        )

        png_dir = work_dir / "png"
        ocr_json_dir = work_dir / "ocr_json"
        md_pages_dir = work_dir / "md_pages"
        for d in (png_dir, ocr_json_dir, md_pages_dir):
            d.mkdir(parents=True, exist_ok=True)

        page_markdowns: list[str] = []
        page_index = 0
        try:
            logger.info(f"{self.name}: ładuję model VLM…")
            self.load_model()
            for batch_paths in iter_page_batches(
                pdf_path, dpi=dpi, batch_size=batch_size, work_dir=str(png_dir)
            ):
                for png in batch_paths:
                    page_index += 1
                    markdown = self._ocr_page(png)
                    page_markdowns.append(markdown)
                    (md_pages_dir / f"page_{page_index:04d}.md").write_text(
                        markdown, encoding="utf-8"
                    )
                    (ocr_json_dir / f"page_{page_index:04d}.json").write_text(
                        json.dumps({"page": page_index, "markdown": markdown}, ensure_ascii=False),
                        encoding="utf-8",
                    )
                # zwolnij dysk: usuń PNG paczki przed renderem następnej
                for png in batch_paths:
                    with suppress(FileNotFoundError):
                        os.remove(png)
        finally:
            self.unload_model()

        markdown = "\n\n---\n\n".join(page_markdowns)
        return ConversionResult(
            markdown=markdown,
            engine_used=self.name,
            pages=page_index,
            metadata={
                "source": str(pdf_path),
                "dpi": dpi,
                "work_dir": str(work_dir) if keep_output else "",
            },
        )
