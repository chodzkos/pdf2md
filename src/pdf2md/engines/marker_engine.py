"""Adapter silnika Marker."""

from __future__ import annotations

import importlib
import importlib.metadata
import os
from pathlib import Path
from typing import Any

from loguru import logger

from pdf2md.engines.base import ConversionEngine, ConversionResult


class MarkerEngine(ConversionEngine):
    """Adapter uniwersalnego konwertera Marker."""

    name = "Marker"
    description = "Uniwersalny konwerter z OCR. Obsługuje skany, kolumny, tabele."
    supports_ocr = True
    supports_llm = True

    def is_available(self) -> bool:
        """Sprawdza obecność pakietu bez importowania Markera."""
        try:
            importlib.metadata.version("marker-pdf")
        except importlib.metadata.PackageNotFoundError:
            return False
        return True

    def convert(self, pdf_path: str, **kwargs: object) -> ConversionResult:
        """Konwertuje PDF do Markdown przez Marker."""
        if not self.is_available():
            raise RuntimeError(
                "Silnik Marker nie jest zainstalowany. "
                "Zainstaluj go poleceniem: uv sync --extra engines-core"
            )

        path = Path(pdf_path)
        use_llm = bool(kwargs.pop("use_llm", False))
        lang = str(kwargs.pop("lang", "pl,en"))
        torch_device = kwargs.pop("torch_device", None)
        try:
            self._configure_torch_device(torch_device)
            config_parser_cls, pdf_converter_cls, create_model_dict, text_from_rendered = (
                self._load_marker_api()
            )
            pymupdf: Any = importlib.import_module("pymupdf")

            config = self._build_config(use_llm=use_llm, lang=lang, kwargs=kwargs)
            config_parser = config_parser_cls(config)
            converter = pdf_converter_cls(
                config=config_parser.generate_config_dict(),
                artifact_dict=create_model_dict(),
                processor_list=config_parser.get_processors(),
                renderer=config_parser.get_renderer(),
                llm_service=config_parser.get_llm_service(),
            )

            logger.info(f"Konwertuję {path} przez Marker")
            rendered = converter(str(path))
            markdown, _, _ = text_from_rendered(rendered)

            doc = pymupdf.open(str(path))
            try:
                pages = len(doc)
            finally:
                doc.close()
        except Exception:
            logger.exception(f"Marker nie zdołał przekonwertować pliku: {path}")
            raise

        return ConversionResult(
            markdown=str(markdown),
            engine_used=self.name,
            pages=pages,
            metadata=self._extract_metadata(rendered),
        )

    def _build_config(
        self, use_llm: bool, lang: str, kwargs: dict[str, object]
    ) -> dict[str, object]:
        """Buduje konfigurację Markera zgodną z ConfigParser."""
        config: dict[str, object] = {
            "output_format": "markdown",
            "use_llm": use_llm,
        }
        if lang:
            config["languages"] = lang
        if use_llm:
            logger.info("Marker uruchomiony z use_llm=True")
        config.update(kwargs)
        return config

    def _load_marker_api(self) -> tuple[Any, Any, Any, Any]:
        """Importuje Marker dopiero w momencie konwersji."""
        config_module = importlib.import_module("marker.config.parser")
        converter_module = importlib.import_module("marker.converters.pdf")
        models_module = importlib.import_module("marker.models")
        output_module = importlib.import_module("marker.output")
        return (
            config_module.ConfigParser,
            converter_module.PdfConverter,
            models_module.create_model_dict,
            output_module.text_from_rendered,
        )

    def _extract_metadata(self, rendered: object) -> dict[str, object]:
        """Wyciąga metadane z obiektu renderowanego, jeśli Marker je zwraca."""
        metadata = getattr(rendered, "metadata", {})
        return metadata if isinstance(metadata, dict) else {}

    def _configure_torch_device(self, torch_device: object) -> None:
        """Ustawia urządzenie Markera przed importem jego modułów."""
        if torch_device is not None:
            os.environ["TORCH_DEVICE"] = str(torch_device)
            return

        if os.environ.get("TORCH_DEVICE"):
            return

        try:
            torch: Any = importlib.import_module("torch")
            if not torch.cuda.is_available():
                return
            major, minor = torch.cuda.get_device_capability(0)
            device_arch = f"sm_{major}{minor}"
            supported_arches = set(torch.cuda.get_arch_list())
        except Exception as exc:
            os.environ["TORCH_DEVICE"] = "cpu"
            logger.warning(f"Nie udało się zweryfikować CUDA dla Markera, wymuszam CPU: {exc}")
            return

        if supported_arches and device_arch not in supported_arches:
            os.environ["TORCH_DEVICE"] = "cpu"
            logger.warning(
                "CUDA widoczna, ale nieobsługiwana przez zainstalowany PyTorch "
                f"({device_arch}; obsługiwane: {', '.join(sorted(supported_arches))}). "
                "Marker zostanie uruchomiony na CPU."
            )
