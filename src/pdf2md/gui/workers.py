"""Worker wątku konwersji — uruchamia Converter w osobnym QThread."""

from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from pdf2md.core.converter import ConversionError, Converter
from pdf2md.core.registry import engine_registry, llm_registry


class ConversionWorker(QThread):
    """Konwertuje pliki PDF w osobnym wątku, emitując sygnały postępu."""

    progress = Signal(str, int)  # (nazwa_pliku, procent 0-100)
    file_done = Signal(str, str, float)  # (plik_wejsciowy, plik_wyjsciowy, czas_s)
    file_error = Signal(str, str)  # (plik_wejsciowy, komunikat_błędu)
    all_done = Signal(int, int, float)  # (sukces, błędy, łączny_czas)

    def __init__(
        self,
        files: list[str],
        engine_name: str,
        output_dir: str,
        llm_name: str = "none",
        llm_model: str = "",
        llm_mode: str = "whole_document",
    ) -> None:
        super().__init__()
        self._files = files
        self._engine_name = engine_name
        self._output_dir = output_dir
        self._llm_name = llm_name
        self._llm_model = llm_model
        self._llm_mode = llm_mode

    def run(self) -> None:
        """Iteruje po plikach, konwertuje każdy i emituje sygnały."""
        converter = Converter()
        engine = engine_registry.get_by_name(self._engine_name)
        if engine is None:
            for f in self._files:
                self.file_error.emit(f, f"Silnik '{self._engine_name}' nie jest zarejestrowany.")
            self.all_done.emit(0, len(self._files), 0.0)
            return

        llm = None
        if self._llm_name not in ("none", ""):
            llm = llm_registry.get_by_name(self._llm_name)

        total_start = time.monotonic()
        success = 0
        errors = 0

        for i, pdf_path in enumerate(self._files):
            filename = Path(pdf_path).name
            self.progress.emit(filename, 0)
            try:
                stem = Path(pdf_path).stem
                out_path = str(Path(self._output_dir) / f"{stem}.md") if self._output_dir else None
                file_start = time.monotonic()
                result = converter.convert(
                    pdf_path,
                    engine,
                    llm=llm,
                    output_path=out_path,
                    llm_mode=self._llm_mode,
                )
                elapsed = time.monotonic() - file_start
                self.progress.emit(filename, 100)
                self.file_done.emit(pdf_path, out_path or "", elapsed)
                success += 1
                _ = result
            except (ConversionError, RuntimeError, OSError) as exc:
                self.progress.emit(filename, 0)
                self.file_error.emit(pdf_path, str(exc))
                errors += 1

            # Emituj łączny postęp między plikami
            overall = int((i + 1) / len(self._files) * 100)
            self.progress.emit(filename, overall)

        total_elapsed = time.monotonic() - total_start
        self.all_done.emit(success, errors, total_elapsed)
