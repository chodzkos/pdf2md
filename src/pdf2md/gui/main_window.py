"""Główne okno aplikacji pdf2md GUI."""

from __future__ import annotations

from pathlib import Path

from loguru import logger
from PySide6.QtCore import QUrl
from PySide6.QtGui import QAction, QDesktopServices, QIcon, QKeySequence
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
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from pdf2md.core.config import get_settings
from pdf2md.detection.dependencies import check_pandoc
from pdf2md.exporters.pandoc_epub_exporter import PandocEpubExporter
from pdf2md.gui.settings_dialog import SettingsDialog
from pdf2md.gui.widgets.engine_selector import EngineSelectorWidget
from pdf2md.gui.widgets.file_list import FileListWidget
from pdf2md.gui.widgets.llm_selector import LLMSelectorWidget
from pdf2md.gui.widgets.log_panel import LogPanelWidget
from pdf2md.gui.workers import ConversionWorker
from pdf2md.utils.open_path import open_in_file_manager


def _separator() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFrameShadow(QFrame.Shadow.Sunken)
    return line


class MainWindow(QMainWindow):
    """Główne okno pdf2md."""

    def __init__(self, initial_files: list[str] | None = None) -> None:
        super().__init__()
        self.setWindowTitle("pdf2md")
        self.setMinimumSize(720, 640)
        self.setWindowIcon(QIcon(str(_icon_path())))

        self._worker: ConversionWorker | None = None
        self._last_output_dir: Path | None = None
        self._last_markdown_outputs: list[Path] = []
        self._initial_files = initial_files or []
        self._build_menu()
        self._build_ui()
        if self._initial_files:
            self._file_list.add_files(self._initial_files)

    # ------------------------------------------------------------------
    # Menu
    # ------------------------------------------------------------------

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("Plik")

        open_action = QAction("Otwórz pliki...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._on_add_files)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        settings_action = QAction("Ustawienia", self)
        settings_action.setShortcut(QKeySequence("Ctrl+,"))
        settings_action.triggered.connect(self._open_settings)
        file_menu.addAction(settings_action)

        file_menu.addSeparator()

        quit_action = QAction("Zakończ", self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        help_menu = self.menuBar().addMenu("Pomoc")

        about_action = QAction("O programie", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

        project_action = QAction("Strona projektu", self)
        project_action.triggered.connect(self._open_project_page)
        help_menu.addAction(project_action)

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
        self._engine_selector.set_engine_name(get_settings().default_engine)
        root.addWidget(self._engine_selector)

        # --- Wybór LLM ---
        self._llm_selector = LLMSelectorWidget()
        root.addWidget(self._llm_selector)

        # --- Folder wyjściowy ---
        out_row = QHBoxLayout()
        out_row.addWidget(QLabel("Folder wynikowy:"))
        self._output_edit = QLineEdit()
        self._output_edit.setPlaceholderText("(obok pliku źródłowego)")
        self._output_edit.setText(get_settings().default_output_dir)
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
        self._tabs = QTabWidget()
        self._log_panel = LogPanelWidget()
        self._log_panel.setMinimumHeight(120)
        self._preview = QTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        font = self._preview.font()
        font.setFamily("monospace")
        self._preview.setFont(font)
        self._tabs.addTab(self._log_panel, "Log")
        self._tabs.addTab(self._preview, "Podgląd")
        root.addWidget(self._tabs)

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

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self)
        if dialog.exec():
            settings = get_settings()
            if settings.default_output_dir:
                self._output_edit.setText(settings.default_output_dir)

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "O programie",
            "pdf2md\n\nKonwerter PDF do Markdown z wieloma silnikami i opcjonalnym LLM.",
        )

    def _open_project_page(self) -> None:
        QDesktopServices.openUrl(QUrl("https://github.com/chodzkos/pdf2md"))

    def _on_convert(self) -> None:
        files = self._file_list.get_files()
        if not files:
            QMessageBox.warning(self, "Brak plików", "Dodaj co najmniej jeden plik PDF.")
            return

        engine_name = self._engine_selector.get_engine_name()
        llm_name = self._llm_selector.get_llm_name()
        llm_model = self._llm_selector.get_model()
        output_dir = self._output_edit.text().strip()
        language = get_settings().default_language

        if not output_dir and files:
            output_dir = str(Path(files[0]).parent)

        self._btn_convert.setEnabled(False)
        self._progress.setValue(0)
        self._last_markdown_outputs = []
        self._last_output_dir = Path(output_dir) if output_dir else None
        self._preview.clear()
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
            language=language,
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
        output = Path(dst)
        if output.exists():
            self._last_markdown_outputs.append(output)
            self._preview.setPlainText(output.read_text(encoding="utf-8"))
            self._tabs.setCurrentWidget(self._preview)

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

        self._show_done_message(success, errors, total)

    def _show_done_message(self, success: int, errors: int, total: float) -> None:
        message = QMessageBox(self)
        message.setWindowTitle("Konwersja zakończona")
        message.setIcon(QMessageBox.Icon.Information)
        message.setText(
            f"Przetworzono: {success + errors} plik(ów)\n"
            f"✓ Sukces: {success}\n"
            f"✗ Błędy:  {errors}\n"
            f"Czas:     {total:.1f}s"
        )

        open_folder = None
        if success > 0:
            open_folder = message.addButton(
                "Otwórz folder wynikowy",
                QMessageBox.ButtonRole.ActionRole,
            )
        export_epub = None
        if check_pandoc() and self._last_markdown_outputs:
            export_epub = message.addButton("Eksportuj do EPUB", QMessageBox.ButtonRole.ActionRole)
        message.addButton("Zamknij", QMessageBox.ButtonRole.AcceptRole)
        message.exec()

        clicked = message.clickedButton()
        if open_folder is not None and clicked is open_folder:
            self._open_output_folder()
        elif export_epub is not None and clicked is export_epub:
            self._export_last_outputs_to_epub()

    def _open_output_folder(self) -> None:
        directory = self._last_output_dir
        if directory is None and self._last_markdown_outputs:
            directory = self._last_markdown_outputs[-1].parent
        if directory is None:
            return

        try:
            open_in_file_manager(directory)
        except Exception as exc:
            logger.warning(f"Nie udało się otworzyć folderu wynikowego: {exc}")

    def _export_last_outputs_to_epub(self) -> None:
        exporter = PandocEpubExporter()
        exported = 0
        for markdown_path in self._last_markdown_outputs:
            try:
                markdown = markdown_path.read_text(encoding="utf-8")
                exporter.export(markdown, markdown_path.with_suffix(".epub"))
                exported += 1
            except Exception as exc:
                QMessageBox.warning(self, "Eksport EPUB", f"Nie udało się eksportować EPUB:\n{exc}")
                return
        QMessageBox.information(self, "Eksport EPUB", f"Wyeksportowano {exported} plik(ów) EPUB.")


def _icon_path() -> Path:
    return Path(__file__).resolve().parent / "assets" / "icon.svg"
