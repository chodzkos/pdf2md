"""Główne okno aplikacji pdf2md GUI."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from pdf2md.gui.widgets.engine_selector import EngineSelectorWidget
from pdf2md.gui.widgets.file_list import FileListWidget
from pdf2md.gui.widgets.llm_selector import LLMSelectorWidget
from pdf2md.gui.widgets.log_panel import LogPanelWidget
from pdf2md.gui.workers import ConversionWorker


def _separator() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFrameShadow(QFrame.Shadow.Sunken)
    return line


class MainWindow(QMainWindow):
    """Główne okno pdf2md."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("pdf2md")
        self.setMinimumSize(720, 640)

        self._worker: ConversionWorker | None = None
        self._build_ui()

    # ------------------------------------------------------------------
    # Budowa interfejsu
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(8)
        root.setContentsMargins(12, 12, 12, 12)

        # --- Przyciski górne ---
        btn_row = QHBoxLayout()
        self._btn_add = QPushButton("Dodaj pliki…")
        self._btn_add.clicked.connect(self._on_add_files)
        self._btn_clear = QPushButton("Wyczyść listę")
        self._btn_clear.clicked.connect(self._on_clear_list)
        btn_row.addWidget(self._btn_add)
        btn_row.addWidget(self._btn_clear)
        btn_row.addStretch()
        root.addLayout(btn_row)

        # --- Lista plików ---
        self._file_list = FileListWidget()
        self._file_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        root.addWidget(self._file_list)

        root.addWidget(_separator())

        # --- Wybór silnika ---
        self._engine_selector = EngineSelectorWidget()
        root.addWidget(self._engine_selector)

        # --- Wybór LLM ---
        self._llm_selector = LLMSelectorWidget()
        root.addWidget(self._llm_selector)

        # --- Folder wyjściowy ---
        out_row = QHBoxLayout()
        out_row.addWidget(QLabel("Folder wynikowy:"))
        self._output_edit = QLineEdit()
        self._output_edit.setPlaceholderText("(obok pliku źródłowego)")
        out_row.addWidget(self._output_edit)
        btn_browse = QPushButton("Przeglądaj…")
        btn_browse.clicked.connect(self._on_browse_output)
        out_row.addWidget(btn_browse)
        root.addLayout(out_row)

        root.addWidget(_separator())

        # --- Progress bar ---
        self._progress = QProgressBar()
        self._progress.setValue(0)
        self._progress.setTextVisible(True)
        root.addWidget(self._progress)

        # --- Przycisk KONWERTUJ ---
        self._btn_convert = QPushButton("KONWERTUJ")
        self._btn_convert.setFixedHeight(44)
        font = self._btn_convert.font()
        font.setPointSize(12)
        font.setBold(True)
        self._btn_convert.setFont(font)
        self._btn_convert.clicked.connect(self._on_convert)
        root.addWidget(self._btn_convert)

        root.addWidget(_separator())

        # --- Panel logów ---
        self._log_panel = LogPanelWidget()
        self._log_panel.setMinimumHeight(120)
        root.addWidget(self._log_panel)

    # ------------------------------------------------------------------
    # Sloty przycisków
    # ------------------------------------------------------------------

    def _on_add_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "Wybierz pliki PDF", "", "PDF (*.pdf)")
        if paths:
            self._file_list.add_files(paths)

    def _on_clear_list(self) -> None:
        self._file_list.clear()

    def _on_browse_output(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Wybierz folder wynikowy")
        if directory:
            self._output_edit.setText(directory)

    def _on_convert(self) -> None:
        files = self._file_list.get_files()
        if not files:
            QMessageBox.warning(self, "Brak plików", "Dodaj co najmniej jeden plik PDF.")
            return

        engine_name = self._engine_selector.get_engine_name()
        llm_name = self._llm_selector.get_llm_name()
        llm_model = self._llm_selector.get_model()
        output_dir = self._output_edit.text().strip()

        if not output_dir and files:
            output_dir = str(Path(files[0]).parent)

        self._btn_convert.setEnabled(False)
        self._progress.setValue(0)
        self._log_panel.log_info(
            f"Rozpoczynam konwersję {len(files)} plik(ów) | silnik: {engine_name}"
            + (f" | LLM: {llm_name}" if llm_name != "none" else "")
        )

        self._worker = ConversionWorker(
            files=files,
            engine_name=engine_name,
            output_dir=output_dir,
            llm_name=llm_name,
            llm_model=llm_model,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.file_done.connect(self._on_file_done)
        self._worker.file_error.connect(self._on_file_error)
        self._worker.all_done.connect(self._on_all_done)
        self._worker.start()

    # ------------------------------------------------------------------
    # Sloty workera
    # ------------------------------------------------------------------

    def _on_progress(self, filename: str, percent: int) -> None:
        self._progress.setValue(percent)
        self._progress.setFormat(f"{filename}  {percent}%")

    def _on_file_done(self, src: str, dst: str, elapsed: float) -> None:
        name = Path(src).name
        self._log_panel.log_info(f"✓ {name} → {dst}  ({elapsed:.1f}s)")

    def _on_file_error(self, src: str, message: str) -> None:
        name = Path(src).name
        self._log_panel.log_error(f"✗ {name}: {message}")

    def _on_all_done(self, success: int, errors: int, total: float) -> None:
        self._btn_convert.setEnabled(True)
        self._progress.setValue(100)

        if errors == 0:
            self._log_panel.log_info(f"Gotowe — {success} plik(ów) w {total:.1f}s")
        else:
            self._log_panel.log_warning(
                f"Gotowe — {success} sukces(ów), {errors} błąd(ów), łącznie {total:.1f}s"
            )

        QMessageBox.information(
            self,
            "Konwersja zakończona",
            f"Przetworzono: {success + errors} plik(ów)\n"
            f"✓ Sukces: {success}\n"
            f"✗ Błędy:  {errors}\n"
            f"Czas:     {total:.1f}s",
        )
