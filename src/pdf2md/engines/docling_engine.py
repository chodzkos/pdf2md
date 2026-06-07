"""Adapter silnika Docling."""

from __future__ import annotations

import importlib
import importlib.metadata
from pathlib import Path
from typing import Any, ClassVar

from loguru import logger

from pdf2md.detection.dependencies import cuda_usable
from pdf2md.engines.base import ConversionEngine, ConversionResult


class DoclingEngine(ConversionEngine):
    """Adapter konwertera Docling."""

    name = "Docling"
    description = "Enterprise-grade, precyzyjne tabele, integracje RAG (IBM Research)"
    supports_ocr = True
    supports_llm = False

    _CONVERT_KWARGS: ClassVar[set[str]] = {
        "headers",
        "raises_on_error",
        "max_num_pages",
        "max_file_size",
        "page_range",
    }

    _PIPELINE_OPTION_KEYS: ClassVar[set[str]] = {
        "do_ocr",
        "do_table_structure",
        "do_code_enrichment",
        "do_formula_enrichment",
        "force_backend_text",
        "generate_page_images",
        "generate_picture_images",
        "generate_table_images",
        "generate_parsed_pages",
        "ocr_batch_size",
        "layout_batch_size",
        "document_timeout",
        "images_scale",
    }

    def is_available(self) -> bool:
        """Sprawdza obecność pakietu bez importowania Docling."""
        try:
            importlib.metadata.version("docling")
        except importlib.metadata.PackageNotFoundError:
            return False
        return True

    def convert(self, pdf_path: str, device: object = "auto", **kwargs: object) -> ConversionResult:
        """Konwertuje PDF do Markdown przez Docling."""
        if not self.is_available():
            raise RuntimeError(
                "Silnik Docling nie jest zainstalowany. "
                "Zainstaluj go poleceniem: uv sync --extra engines-core"
            )

        path = Path(pdf_path)
        try:
            converter = self._build_converter(device=str(device), kwargs=kwargs)
            convert_kwargs = self._extract_convert_kwargs(kwargs)
            logger.info(f"Konwertuję {path} przez Docling")
            result = converter.convert(str(path), **convert_kwargs)
            markdown = result.document.export_to_markdown()
            pages = self._page_count(result, path)
        except Exception:
            logger.exception(f"Docling nie zdołał przekonwertować pliku: {path}")
            raise

        return ConversionResult(
            markdown=str(markdown),
            engine_used=self.name,
            pages=pages,
            metadata={"source": str(path)},
        )

    def _build_converter(self, device: str, kwargs: dict[str, object]) -> Any:
        docling_converter: Any = importlib.import_module("docling.document_converter")
        base_models: Any = importlib.import_module("docling.datamodel.base_models")
        pipeline_options_module: Any = importlib.import_module("docling.datamodel.pipeline_options")
        accelerator_module: Any = importlib.import_module("docling.datamodel.accelerator_options")

        resolved_device = self._resolve_device(str(kwargs.pop("docling_device", device)))
        threads = self._coerce_positive_int(
            kwargs.pop("docling_num_threads", 2),
            default=2,
        )

        pipeline_options = pipeline_options_module.PdfPipelineOptions()
        pipeline_options.accelerator_options = accelerator_module.AcceleratorOptions(
            device=resolved_device,
            num_threads=threads,
        )

        for option_key in self._PIPELINE_OPTION_KEYS:
            if option_key in kwargs:
                setattr(pipeline_options, option_key, kwargs.pop(option_key))

        return docling_converter.DocumentConverter(
            format_options={
                base_models.InputFormat.PDF: docling_converter.PdfFormatOption(
                    pipeline_options=pipeline_options
                )
            }
        )

    def _resolve_device(self, device: str) -> object:
        accelerator_module: Any = importlib.import_module("docling.datamodel.accelerator_options")
        normalized = device.lower().strip()
        if normalized not in {"auto", "cpu", "cuda"}:
            raise ValueError("Docling device musi mieć wartość: auto, cpu albo cuda")

        if normalized == "cpu":
            return accelerator_module.AcceleratorDevice.CPU

        if cuda_usable():
            return accelerator_module.AcceleratorDevice.CUDA

        if normalized == "cuda":
            logger.warning("CUDA niedostępna lub nieużywalna dla Docling — używam CPU.")
        return accelerator_module.AcceleratorDevice.CPU

    def _extract_convert_kwargs(self, kwargs: dict[str, object]) -> dict[str, object]:
        convert_kwargs: dict[str, object] = {}
        for key in list(kwargs):
            if key in self._CONVERT_KWARGS:
                convert_kwargs[key] = kwargs.pop(key)
        return convert_kwargs

    def _coerce_positive_int(self, value: object, default: int) -> int:
        try:
            parsed = int(str(value))
        except (TypeError, ValueError):
            return default
        return parsed if parsed > 0 else default

    def _page_count(self, result: object, path: Path) -> int:
        document = getattr(result, "document", None)
        pages = getattr(document, "pages", None)
        if pages is not None:
            try:
                return len(pages)
            except TypeError:
                pass

        pymupdf: Any = importlib.import_module("pymupdf")
        doc = pymupdf.open(str(path))
        try:
            return len(doc)
        finally:
            doc.close()
