"""Worker wątku konwersji — uruchamia Converter w osobnym QThread."""

from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from pdf2md.core import history as conversion_history
from pdf2md.core.config import get_settings
from pdf2md.core.converter import ConversionError, Converter
from pdf2md.core.image_extraction import (
    append_image_references,
    extract_pdf_images,
    image_output_dir,
)
from pdf2md.core.input_types import is_image_input
from pdf2md.core.registry import engine_registry, llm_registry
from pdf2md.engines.base import ConversionCancelled, ConversionEngine
from pdf2md.engines.vlm_base import VLMEngine
from pdf2md.llm.base import LLMProvider


def _model_field_for_provider(provider_name: str) -> str | None:
    """Mapuje nazwę dostawcy na pole modelu w Settings (dla override per-uruchomienie)."""
    name = provider_name.lower()
    if "ollama" in name:
        return "ollama_model"
    if "claude" in name or "anthropic" in name:
        return "anthropic_model"
    if "openai" in name or "gpt" in name:
        return "openai_model"
    if "gemini" in name or "google" in name:
        return "gemini_model"
    return None


def _has_in_place_images(engine_name: str) -> bool:
    return engine_name.strip().lower() in {"docling", "marker"}


class ConversionWorker(QThread):
    """Konwertuje pliki PDF w osobnym wątku, emitując sygnały postępu."""

    progress = Signal(str, int)  # (nazwa_pliku, procent 0-100)
    file_done = Signal(str, str, float)  # (plik_wejsciowy, plik_wyjsciowy, czas_s)
    file_error = Signal(str, str)  # (plik_wejsciowy, komunikat_błędu)
    all_done = Signal(int, int, float)  # (sukces, błędy, łączny_czas)
    cancelled = Signal(int, int, float)  # (sukces, błędy, łączny_czas) — po anulowaniu

    def __init__(
        self,
        files: list[str],
        engine_name: str,
        output_dir: str,
        llm_name: str = "none",
        llm_model: str = "",
        llm_mode: str = "whole_document",
        language: str = "pol+eng",
        docling_device: str | None = None,
        scan_profile: str = "",
        extract_images: bool = False,
    ) -> None:
        super().__init__()
        settings = get_settings()
        self._files = files
        self._engine_name = engine_name
        self._output_dir = output_dir
        self._llm_name = llm_name
        self._llm_model = llm_model
        self._llm_mode = llm_mode
        self._language = language
        self._scan_profile = scan_profile
        self._docling_device = docling_device or settings.docling_device
        self._extract_images = extract_images

    def cancel(self) -> None:
        """Prosi o kooperatywne przerwanie — sprawdzane między stronami i plikami."""
        self.requestInterruption()

    def run(self) -> None:
        """Iteruje po plikach, konwertuje każdy i emituje sygnały."""
        converter = Converter()
        engine = engine_registry.get_by_name(self._engine_name)
        llm = None
        if self._llm_name not in ("none", ""):
            llm = llm_registry.get_by_name(self._llm_name)

        if engine is None:
            for f in self._files:
                message = f"Silnik '{self._engine_name}' nie jest zarejestrowany."
                self._record_history(
                    pdf_path=f,
                    engine_name=self._engine_name,
                    llm=llm,
                    output_path=self._default_output_path(f),
                    status="error",
                    duration_s=0.0,
                    error_msg=message,
                )
                self.file_error.emit(f, message)
            self.all_done.emit(0, len(self._files), 0.0)
            return

        # Override modelu per-uruchomienie: ma pierwszeństwo nad config.<provider>_model,
        # ale NIE jest utrwalany (nie kasuje domyślnego ustawionego w GUI). Provider czyta
        # model leniwie z get_settings(), więc nadpisujemy singleton na czas przebiegu.
        settings = get_settings()
        override_field = (
            _model_field_for_provider(self._llm_name)
            if (llm is not None and self._llm_model)
            else None
        )
        original_model = getattr(settings, override_field) if override_field else None
        if override_field:
            setattr(settings, override_field, self._llm_model)

        try:
            self._convert_all(converter, engine, llm)
        finally:
            if override_field:
                setattr(settings, override_field, original_model)

    def _convert_all(
        self,
        converter: Converter,
        engine: ConversionEngine,
        llm: LLMProvider | None,
    ) -> None:
        total_start = time.monotonic()
        success = 0
        errors = 0
        was_cancelled = False

        # Silniki wspierające anulowanie per-strona dostają callback should_cancel.
        supports_page_cancel = (
            isinstance(engine, VLMEngine) or "scan pipeline" in engine.name.lower()
        )

        for i, pdf_path in enumerate(self._files):
            # Granica MIĘDZY PLIKAMI — nie zaczynaj kolejnego pliku po anulowaniu.
            if self.isInterruptionRequested():
                was_cancelled = True
                break

            filename = Path(pdf_path).name
            self.progress.emit(filename, 0)
            stem = Path(pdf_path).stem
            out_path = str(Path(self._output_dir) / f"{stem}.md") if self._output_dir else None
            file_start = time.monotonic()
            try:
                engine_kwargs: dict[str, object] = {}
                if engine.supports_ocr:
                    engine_kwargs["lang"] = self._language
                if supports_page_cancel:
                    engine_kwargs["should_cancel"] = self.isInterruptionRequested
                engine_options: dict[str, object] = {}
                if engine.name.lower() == "docling":
                    engine_options["device"] = self._docling_device
                if self._scan_profile and "scan pipeline" in engine.name.lower():
                    from pdf2md.scan.profiles import load_profile

                    engine_kwargs["profile"] = load_profile(self._scan_profile).model_dump()
                    # ScanPipeline pisze book.md/epub/report do output_dir samodzielnie;
                    # konwerter nie forwarduje output_dir, więc podajemy go w engine_kwargs.
                    engine_kwargs["output_dir"] = self._output_dir
                    out_path = None
                result = converter.convert(
                    pdf_path,
                    engine,
                    llm=llm,
                    output_path=out_path,
                    llm_mode=self._llm_mode,
                    engine_kwargs=engine_kwargs,
                    engine_options=engine_options,
                    record_history=False,
                )
                if self._should_extract_images(engine, pdf_path):
                    result.markdown = self._extract_images_for_output(
                        pdf_path,
                        result.markdown,
                        out_path,
                    )
                elapsed = time.monotonic() - file_start
                history_output = self._history_output_path(result, out_path)
                self._record_history(
                    pdf_path=pdf_path,
                    engine_name=engine.name,
                    llm=llm,
                    output_path=history_output,
                    status="ok",
                    duration_s=elapsed,
                )
                self.progress.emit(filename, 100)
                done_output = history_output if "scan pipeline" in engine.name.lower() else out_path
                if done_output and not Path(done_output).is_file():
                    done_output = None
                self.file_done.emit(pdf_path, done_output or "", elapsed)
                success += 1
                _ = result
            except ConversionCancelled:
                # Bieżący plik NIE jest kompletny — nie liczony jako sukces.
                self._record_history(
                    pdf_path=pdf_path,
                    engine_name=engine.name,
                    llm=llm,
                    output_path=out_path,
                    status="error",
                    duration_s=time.monotonic() - file_start,
                    error_msg="Konwersja anulowana",
                )
                was_cancelled = True
                break
            except (ConversionError, RuntimeError, OSError) as exc:
                self._record_history(
                    pdf_path=pdf_path,
                    engine_name=engine.name,
                    llm=llm,
                    output_path=out_path,
                    status="error",
                    duration_s=time.monotonic() - file_start,
                    error_msg=str(exc),
                )
                self.progress.emit(filename, 0)
                self.file_error.emit(pdf_path, str(exc))
                errors += 1

            # Emituj łączny postęp między plikami
            overall = int((i + 1) / len(self._files) * 100)
            self.progress.emit(filename, overall)

        total_elapsed = time.monotonic() - total_start
        if was_cancelled:
            self._release_after_cancel(engine, llm)
            self.cancelled.emit(success, errors, total_elapsed)
        else:
            self.all_done.emit(success, errors, total_elapsed)

    def _should_extract_images(self, engine: ConversionEngine, input_path: str) -> bool:
        return (
            self._extract_images
            and not _has_in_place_images(engine.name)
            and not is_image_input(input_path)
        )

    def _extract_images_for_output(
        self,
        pdf_path: str,
        markdown: str,
        out_path: str | None,
    ) -> str:
        output_path = (
            Path(out_path)
            if out_path
            else Path(self._output_dir or Path(pdf_path).parent) / f"{Path(pdf_path).stem}.md"
        )
        images = extract_pdf_images(
            pdf_path,
            image_output_dir(output_path),
            min_size=100,
        )
        updated_markdown = append_image_references(markdown, images, output_path)
        if out_path:
            output_file = Path(out_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(updated_markdown, encoding="utf-8")
        return updated_markdown

    def _default_output_path(self, pdf_path: str) -> str | None:
        if not self._output_dir:
            return None
        return str(Path(self._output_dir) / f"{Path(pdf_path).stem}.md")

    def _history_output_path(self, result: object, out_path: str | None) -> str | None:
        if out_path:
            return out_path
        metadata = getattr(result, "metadata", {})
        if isinstance(metadata, dict):
            book_md_path = metadata.get("book_md_path")
            if book_md_path:
                return str(book_md_path)
        return self._output_dir or None

    def _record_history(
        self,
        *,
        pdf_path: str,
        engine_name: str,
        llm: LLMProvider | None,
        output_path: str | None,
        status: conversion_history.HistoryStatus,
        duration_s: float,
        error_msg: str | None = None,
    ) -> None:
        conversion_history.record_safely(
            input_path=pdf_path,
            engine=engine_name,
            llm_provider=llm.name if llm is not None else "none",
            llm_mode=self._llm_mode,
            output_path=output_path,
            status=status,
            duration_s=duration_s,
            error_msg=error_msg,
        )

    def _release_after_cancel(self, engine: ConversionEngine, llm: LLMProvider | None) -> None:
        """Po anulowaniu zwalnia zasoby: VRAM silnika VLM + wyładowanie modelu Ollamy."""
        unload = getattr(engine, "unload_model", None)
        if callable(unload):
            try:
                unload()
            except Exception as exc:  # pragma: no cover - defensywnie
                _ = exc
        if llm is not None:
            from pdf2md.scan.correction import release_ollama_model

            release_ollama_model(llm)
