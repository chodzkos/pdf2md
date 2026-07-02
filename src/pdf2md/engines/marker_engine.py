"""Adapter silnika Marker."""

from __future__ import annotations

import importlib
import importlib.metadata
import os
from pathlib import Path
from typing import Any

from loguru import logger

from pdf2md.core.config import get_settings
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
        settings = get_settings()
        use_llm = bool(kwargs.pop("use_llm", False))
        lang = str(kwargs.pop("lang", "pl,en"))
        marker_device = kwargs.pop("marker_device", settings.marker_device)
        torch_device = kwargs.pop("torch_device", marker_device)
        marker_workers_value = kwargs.pop("marker_workers", None)
        if marker_workers_value is None:
            marker_workers_value = kwargs.pop("pdftext_workers", settings.marker_workers)
        else:
            kwargs.pop("pdftext_workers", None)
        marker_workers = self._coerce_positive_int(
            marker_workers_value,
            default=1,
        )
        output_path = kwargs.pop("output_path", None)
        marker_max_pages = self._coerce_optional_positive_int(
            kwargs.pop("marker_max_pages", settings.marker_max_pages)
        )
        try:
            self._configure_worker_env(marker_workers)
            self._configure_gpu_batches(settings)
            self._configure_torch_device(torch_device)
            (
                config_parser_cls,
                pdf_converter_cls,
                create_model_dict,
                text_from_rendered,
                convert_if_not_rgb,
            ) = self._load_marker_api()
            pymupdf: Any = importlib.import_module("pymupdf")

            config_parser, llm_service = self._prepare_config_parser(
                config_parser_cls=config_parser_cls,
                use_llm=use_llm,
                lang=lang,
                kwargs=kwargs,
                workers=marker_workers,
                max_pages=marker_max_pages,
            )
            converter = pdf_converter_cls(
                config=config_parser.generate_config_dict(),
                artifact_dict=create_model_dict(),
                processor_list=config_parser.get_processors(),
                renderer=config_parser.get_renderer(),
                llm_service=llm_service,
            )

            logger.info(f"Konwertuję {path} przez Marker")
            rendered = converter(str(path))
            markdown, _, images = text_from_rendered(rendered)
            marker_output_path = Path(str(output_path)) if output_path else path.with_suffix(".md")
            self._save_inline_images(images, marker_output_path, convert_if_not_rgb)
            pages = self._converted_page_count(converter, path, pymupdf)
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
        self,
        use_llm: bool,
        lang: str,
        kwargs: dict[str, object],
        workers: int,
        max_pages: int | None,
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
        limited_page_range = self._limited_page_range(config.get("page_range"), max_pages)
        if limited_page_range is not None:
            config["page_range"] = limited_page_range
        config["disable_multiprocessing"] = True
        config["pdftext_workers"] = workers
        return config

    def _prepare_config_parser(
        self,
        config_parser_cls: Any,
        use_llm: bool,
        lang: str,
        kwargs: dict[str, object],
        workers: int,
        max_pages: int | None,
    ) -> tuple[Any, Any]:
        """Buduje ConfigParser Markera i rozwiązuje usługę LLM.

        Jeśli use_llm=True, ale ta wersja/konfiguracja Markera nie udostępnia usługi LLM,
        loguje ostrzeżenie i kontynuuje konwersję bez post-processingu LLM (graceful skip).
        """
        config = self._build_config(
            use_llm=use_llm,
            lang=lang,
            kwargs=kwargs,
            workers=workers,
            max_pages=max_pages,
        )
        config_parser = config_parser_cls(config)
        if not use_llm:
            return config_parser, None
        try:
            return config_parser, config_parser.get_llm_service()
        except Exception as exc:
            logger.warning(
                f"Marker nie udostępnia usługi LLM w tej wersji/konfiguracji ({exc}). "
                "Kontynuuję konwersję bez post-processingu LLM."
            )
            fallback_config = self._build_config(
                use_llm=False,
                lang=lang,
                kwargs=kwargs,
                workers=workers,
                max_pages=max_pages,
            )
            return config_parser_cls(fallback_config), None

    def _load_marker_api(self) -> tuple[Any, Any, Any, Any, Any]:
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
            output_module.convert_if_not_rgb,
        )

    def _extract_metadata(self, rendered: object) -> dict[str, object]:
        """Wyciąga metadane z obiektu renderowanego, jeśli Marker je zwraca."""
        metadata = getattr(rendered, "metadata", {})
        return metadata if isinstance(metadata, dict) else {}

    def _save_inline_images(
        self,
        images: object,
        output_path: Path,
        convert_if_not_rgb: Any,
    ) -> None:
        """Zapisuje obrazy Markera pod ścieżkami użytymi już w Markdown."""
        if not isinstance(images, dict) or not images:
            return

        saved = 0
        for img_name, img in images.items():
            if not isinstance(img_name, str):
                continue
            image_path = self._inline_image_path(output_path, img_name)
            image_path.parent.mkdir(parents=True, exist_ok=True)
            converted = convert_if_not_rgb(img)
            converted.save(image_path, format="PNG")
            saved += 1
        if saved:
            logger.info(f"Zapisano obrazy Markera: {saved} plik(ów)")

    def _inline_image_path(self, output_path: Path, img_name: str) -> Path:
        image_path = Path(img_name)
        if image_path.is_absolute():
            return image_path
        return output_path.parent / image_path

    def _converted_page_count(self, converter: object, path: Path, pymupdf: Any) -> int:
        """Zwraca liczbę stron faktycznie przetworzonych przez Marker, jeśli jest dostępna."""
        page_count = getattr(converter, "page_count", None)
        if isinstance(page_count, int) and page_count > 0:
            return page_count

        doc = pymupdf.open(str(path))
        try:
            return len(doc)
        finally:
            doc.close()

    def _configure_gpu_batches(self, settings: Any) -> None:
        """Ustawia env surya dla rozmiarów batchy GPU przed importem modeli Markera.

        Wartości dobiera się empirycznie patrząc na `nvidia-smi -l 1`; podnoś aż
        VRAM/util sensownie rośnie, ale przed OOM. Na 24 GB jest duży zapas
        (~50-280 MB VRAM na element batcha, zależnie od modelu). Batche działają
        niezależnie od disable_multiprocessing (który jest CPU-side i nie dotyczy GPU).
        Env varów nie nadpisujemy jeśli użytkownik ustawił je już z zewnątrz.
        """
        if settings.marker_torch_device:
            os.environ.setdefault("TORCH_DEVICE", settings.marker_torch_device)
        for env_key, value in (
            ("RECOGNITION_BATCH_SIZE", settings.marker_recognition_batch_size),
            ("DETECTOR_BATCH_SIZE", settings.marker_detector_batch_size),
            ("LAYOUT_BATCH_SIZE", settings.marker_layout_batch_size),
            ("TABLE_REC_BATCH_SIZE", settings.marker_table_rec_batch_size),
        ):
            if value:
                os.environ.setdefault(env_key, str(value))

    def _configure_worker_env(self, workers: int) -> None:
        """Ustawia limity workerów przed importem Markera."""
        worker_count = str(workers)
        os.environ["PDFTEXT_WORKERS"] = worker_count
        os.environ["NUM_WORKERS"] = worker_count

    def _configure_torch_device(self, torch_device: object) -> None:
        """Ustawia urządzenie Markera przed importem jego modułów."""
        if os.environ.get("TORCH_DEVICE"):
            return

        if torch_device not in (None, ""):
            os.environ["TORCH_DEVICE"] = str(torch_device)
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

    def _limited_page_range(self, page_range: object, max_pages: int | None) -> object:
        """Ogranicza zakres stron do konserwatywnego maksimum."""
        if max_pages is None:
            return page_range
        if page_range in (None, ""):
            return "0" if max_pages == 1 else f"0-{max_pages - 1}"

        pages = self._parse_page_range(page_range)
        if pages is None:
            return page_range
        return ",".join(str(page) for page in pages[:max_pages])

    def _parse_page_range(self, page_range: object) -> list[int] | None:
        if isinstance(page_range, str):
            pages: list[int] = []
            for item in page_range.split(","):
                if not item:
                    continue
                if "-" in item:
                    start, end = item.split("-", maxsplit=1)
                    pages.extend(range(int(start), int(end) + 1))
                else:
                    pages.append(int(item))
            return sorted(set(pages))
        if isinstance(page_range, range):
            return list(page_range)
        if isinstance(page_range, (list, tuple, set)):
            return sorted({int(page) for page in page_range})
        return None

    def _coerce_positive_int(self, value: object, default: int) -> int:
        if not isinstance(value, (int, str, float)):
            return default
        try:
            number = int(value)
        except (TypeError, ValueError):
            return default
        return max(1, number)

    def _coerce_optional_positive_int(self, value: object) -> int | None:
        if value in (None, "", 0, "0"):
            return None
        if not isinstance(value, (int, str, float)):
            return None
        try:
            number = int(value)
        except (TypeError, ValueError):
            return None
        return number if number > 0 else None
