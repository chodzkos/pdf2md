"""Adapter silnika pdf-craft."""

from __future__ import annotations

import importlib
import importlib.metadata
import tempfile
from pathlib import Path
from typing import Any, ClassVar

from loguru import logger

from pdf2md.engines.base import ConversionEngine, ConversionResult


class PdfCraftEngine(ConversionEngine):
    """Adapter biblioteki pdf-craft."""

    name = "pdf-craft"
    description = "Specjalista od skanowanych książek. Natywny output EPUB"
    supports_ocr = True
    supports_llm = False

    _OPTION_KEYS: ClassVar[set[str]] = {
        "analysing_path",
        "ocr_size",
        "models_cache_path",
        "dpi",
        "max_page_image_file_size",
        "includes_cover",
        "includes_footnotes",
        "ignore_pdf_errors",
        "ignore_ocr_errors",
        "generate_plot",
        "toc_llm",
        "toc_assumed",
        "local_only",
        "pdf_handler",
    }

    def is_available(self) -> bool:
        """Sprawdza obecność pakietu bez importowania pdf-craft."""
        try:
            importlib.metadata.version("pdf-craft")
        except importlib.metadata.PackageNotFoundError:
            return False
        return True

    def convert(self, pdf_path: str, **kwargs: object) -> ConversionResult:
        """Konwertuje PDF do Markdown przez pdf-craft."""
        if not self.is_available():
            raise RuntimeError(
                "Silnik pdf-craft nie jest zainstalowany. "
                "Zainstaluj go poleceniem: uv sync --extra engines-optional"
            )

        path = Path(pdf_path)
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            markdown_path = tmp_path / f"{path.stem}.md"
            assets_path = tmp_path / "assets"
            analysing_path = tmp_path / "analysis"
            options = {
                key: value
                for key, value in kwargs.items()
                if key in self._OPTION_KEYS and value is not None
            }
            options.setdefault("analysing_path", str(analysing_path))

            try:
                pdf_craft: Any = importlib.import_module("pdf_craft")
                transform_markdown = pdf_craft.transform_markdown
                logger.info(f"Konwertuję {path} przez pdf-craft")
                transform_markdown(
                    pdf_path=str(path),
                    markdown_path=str(markdown_path),
                    markdown_assets_path=str(assets_path),
                    **options,
                )
                markdown = markdown_path.read_text(encoding="utf-8")
                pages = self._page_count(path)
            except Exception:
                logger.exception(f"pdf-craft nie zdołał przekonwertować pliku: {path}")
                raise

        return ConversionResult(
            markdown=markdown,
            engine_used=self.name,
            pages=pages,
            metadata={"source": str(path)},
        )

    def _page_count(self, path: Path) -> int:
        pymupdf: Any = importlib.import_module("pymupdf")
        doc = pymupdf.open(str(path))
        try:
            return len(doc)
        finally:
            doc.close()
