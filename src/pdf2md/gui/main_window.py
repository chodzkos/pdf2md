"""Główne okno aplikacji pdf2md GUI."""

from __future__ import annotations

from pathlib import Path

from chodzkos_gui_kit.qt.dialogs import open_files
from chodzkos_gui_kit.qt.theme import ThemeManager, ThemeSetting
from chodzkos_gui_kit.qt.widgets import FileList, FileListTexts, PathEntry, PathEntryTexts
from loguru import logger
from PySide6.QtCore import QSize, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from pdf2md.core.config import get_settings
from pdf2md.detection.dependencies import check_pandoc
from pdf2md.exporters.pandoc_epub_exporter import PandocEpubExporter
from pdf2md.gui.settings_dialog import SettingsDialog
from pdf2md.gui.theming import attach_dark_titlebar, themed_message_box
from pdf2md.gui.widgets.engine_selector import EngineSelectorWidget
from pdf2md.gui.widgets.llm_selector import LLMSelectorWidget
from pdf2md.gui.widgets.log_panel import LogPanelWidget
from pdf2md.gui.widgets.profile_selector import ProfileSelectorWidget
from pdf2md.gui.workers import ConversionWorker
from pdf2md.utils.open_path import open_in_file_manager


def _separator() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFrameShadow(QFrame.Shadow.Sunken)
    return line


# Polskie etykiety toolbara kitowego FileList (pdf2md nie ma gettext).
_FILE_LIST_TEXTS = FileListTexts(
    files="Pliki",
    folder="Folder",
    remove="Usuń",
    clear="Wyczyść",
    tooltip_files="Dodaj pliki PDF przez okno wyboru",
    tooltip_folder="Dodaj pliki PDF z wybranego folderu",
    tooltip_remove="Usuń zaznaczone pozycje z listy",
    tooltip_clear="Usuń wszystkie pozycje z listy",
    list_tooltip="Lista plików — przeciągnij pliki PDF tutaj lub użyj przycisków powyżej",
    dialog_add_files="Dodaj pliki PDF",
    dialog_add_folder="Dodaj folder",
    filter_supported="PDF ({pattern})",
)


def _files_count_label(count: int) -> str:
    """Licznik plików z polskimi formami mnogimi (pdf2md nie ma gettext)."""
    if count == 1:
        form = "plik"
    elif 2 <= count % 10 <= 4 and not 12 <= count % 100 <= 14:
        form = "pliki"
    else:
        form = "plików"
    return f"{count} {form}"


class MainWindow(QMainWindow):
    """Główne okno pdf2md."""

    def __init__(self, theme_manager: ThemeManager, initial_files: list[str] | None = None) -> None:
        super().__init__()
        self.setWindowTitle("pdf2md")
        self.setMinimumSize(720, 640)
        self.setWindowIcon(QIcon(str(_icon_path())))

        self._theme_manager = theme_manager
        self._worker: ConversionWorker | None = None
        self._last_output_dir: Path | None = None
        self._last_markdown_outputs: list[Path] = []
        self._initial_files = initial_files or []
        self._build_menu()
        self._build_ui()

        # Ciemny pasek tytułu (DWM = motyw app); re-render logu po zmianie motywu.
        self._theme_manager.attach_titlebar(self)
        self._theme_manager.theme_changed.connect(self._on_theme_changed)

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

        # --- Górny pasek (lekki): logo+nazwa | przełącznik motywu + O programie ---
        root.addLayout(self._build_topbar())

        # --- Lista plików (kitowy FileList: własny toolbar +Pliki/+Folder/Usuń/Wyczyść,
        #     licznik, D&D z rekursją folderów) ---
        self._file_list = FileList(
            extensions={".pdf"},
            texts=_FILE_LIST_TEXTS,
            count_label=_files_count_label,
        )
        self._file_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        root.addWidget(self._file_list)

        root.addWidget(_separator())

        # --- Wybór silnika ---
        self._engine_selector = EngineSelectorWidget()
        self._engine_selector.set_engine_name(get_settings().default_engine)
        root.addWidget(self._engine_selector)

        # --- Profil skanowania (widoczny tylko dla silnika Scan Pipeline) ---
        self._profile_selector = ProfileSelectorWidget()
        self._profile_selector.setVisible(
            self._is_scan_engine(self._engine_selector.get_engine_name())
        )
        self._engine_selector.engine_changed.connect(self._on_engine_changed)
        root.addWidget(self._profile_selector)

        # --- Wybór LLM ---
        self._llm_selector = LLMSelectorWidget()
        root.addWidget(self._llm_selector)

        # --- Folder wyjściowy (kitowy PathEntry: pole + „…" z pick_dir) ---
        out_row = QHBoxLayout()
        out_row.addWidget(QLabel("Folder wynikowy:"))
        self._output_entry = PathEntry(
            mode="dir",
            placeholder="(obok pliku źródłowego)",
            texts=PathEntryTexts(
                tooltip_dir="Wybierz folder wynikowy",
                title_dir="Wybierz folder wynikowy",
            ),
        )
        self._output_entry.set(get_settings().default_output_dir)
        out_row.addWidget(self._output_entry, stretch=1)
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

        # --- Przycisk ANULUJ (aktywny tylko w trakcie konwersji) ---
        self._btn_cancel = QPushButton("Anuluj")
        self._btn_cancel.setEnabled(False)
        self._btn_cancel.clicked.connect(self._on_cancel)
        root.addWidget(self._btn_cancel)

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

    def _build_topbar(self) -> QHBoxLayout:
        """Lekki górny pasek (GUI_STANDARD §6): logo+nazwa | motyw + O programie.

        Przełącznik motywu i „O programie" to meta-funkcje — siedzą dyskretnie
        w pasku, nie w zakładkach roboczych.
        """
        bar = QHBoxLayout()

        logo = QLabel()
        logo.setPixmap(QIcon(str(_icon_path())).pixmap(QSize(20, 20)))
        bar.addWidget(logo)
        name = QLabel("pdf2md")
        name_font = name.font()
        name_font.setBold(True)
        name.setFont(name_font)
        bar.addWidget(name)

        bar.addStretch()

        bar.addWidget(QLabel("Motyw:"))
        self._theme_combo = QComboBox()
        for label, value in (("Auto", "auto"), ("Jasny", "light"), ("Ciemny", "dark")):
            self._theme_combo.addItem(label, value)
        current = self._theme_combo.findData(self._theme_manager.setting)
        if current >= 0:
            self._theme_combo.setCurrentIndex(current)
        # `activated` reaguje tylko na wybór użytkownika — programowe ustawienie
        # indeksu powyżej nie wywoła apply() podczas budowy UI.
        self._theme_combo.activated.connect(self._on_theme_selected)
        bar.addWidget(self._theme_combo)

        about_btn = QToolButton()
        about_btn.setText("ⓘ")
        about_btn.setToolTip("O programie")
        about_btn.clicked.connect(self._show_about)
        bar.addWidget(about_btn)

        return bar

    def _on_theme_selected(self, index: int) -> None:
        """Użytkownik zmienił motyw — apply() zapisze go w config.toml przez most."""
        setting: ThemeSetting = self._theme_combo.itemData(index)
        self._theme_manager.apply(setting)

    def _on_theme_changed(self, _palette: object) -> None:
        """Po zmianie motywu przemaluj kolory logu wg nowej palety."""
        self._log_panel.restyle()

    # ------------------------------------------------------------------
    # Sloty przycisków
    # ------------------------------------------------------------------

    def _on_add_files(self) -> None:
        # Wejście z menu Plik→Otwórz (Ctrl+O); toolbar widgetu ma własne „+Pliki".
        paths = open_files(parent=self, title="Wybierz pliki PDF", name_filter="PDF (*.pdf)")
        if paths:
            self._file_list.add_files(paths)

    def _is_scan_engine(self, engine_name: str) -> bool:
        return "scan pipeline" in engine_name.lower()

    def _on_engine_changed(self, engine_name: str) -> None:
        self._profile_selector.setVisible(self._is_scan_engine(engine_name))

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self)
        if dialog.exec():
            settings = get_settings()
            if settings.default_output_dir:
                self._output_entry.set(settings.default_output_dir)

    def _show_about(self) -> None:
        # Zwykły tekst — themed_message_box wystarcza (belka za motywem aplikacji).
        themed_message_box(
            self,
            QMessageBox.Icon.Information,
            "O programie",
            "pdf2md\n\nKonwerter PDF do Markdown z wieloma silnikami i opcjonalnym LLM.",
        ).exec()

    def _open_project_page(self) -> None:
        QDesktopServices.openUrl(QUrl("https://github.com/chodzkos/pdf2md"))

    def _on_convert(self) -> None:
        # kit FileList.files() zwraca list[Path]; worker oczekuje str.
        files = [str(path) for path in self._file_list.files()]
        if not files:
            themed_message_box(
                self, QMessageBox.Icon.Warning, "Brak plików", "Dodaj co najmniej jeden plik PDF."
            ).exec()
            return

        engine_name = self._engine_selector.get_engine_name()
        llm_name = self._llm_selector.get_llm_name()
        llm_model = self._llm_selector.get_model()
        output_dir = self._output_entry.get()
        language = get_settings().default_language

        # Scan Pipeline sam steruje korektą LLM przez profil — wyłącz generyczny post-processing
        scan_profile = ""
        if self._is_scan_engine(engine_name):
            scan_profile = self._profile_selector.get_profile_name()
            llm_name, llm_model = "none", ""

        if not output_dir and files:
            output_dir = str(Path(files[0]).parent)

        self._btn_convert.setEnabled(False)
        self._btn_cancel.setEnabled(True)
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
            scan_profile=scan_profile,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.file_done.connect(self._on_file_done)
        self._worker.file_error.connect(self._on_file_error)
        self._worker.all_done.connect(self._on_all_done)
        self._worker.cancelled.connect(self._on_cancelled)
        self._worker.start()

    def _on_cancel(self) -> None:
        """Prosi worker o przerwanie i blokuje przycisk (zatrzyma się na granicy)."""
        if self._worker is not None and self._worker.isRunning():
            self._btn_cancel.setEnabled(False)
            self._log_panel.log_warning(
                "Anulowanie… zatrzymam na najbliższej granicy strony/pliku."
            )
            self._worker.cancel()

    def _on_cancelled(self, success: int, errors: int, total: float) -> None:
        """Konwersja anulowana — UI wraca do spoczynku, ukończone pliki zostają."""
        self._btn_convert.setEnabled(True)
        self._btn_cancel.setEnabled(False)
        self._progress.setValue(0)
        self._log_panel.log_warning(
            f"Anulowano — ukończono {success} plik(ów), {errors} błąd(ów) w {total:.1f}s. "
            "VRAM zwolniony."
        )

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
        self._btn_cancel.setEnabled(False)
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
        # Własne przyciski (EPUB/Zamknij) → instancja zostaje; dokładamy belkę.
        attach_dark_titlebar(message)
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
                themed_message_box(
                    self,
                    QMessageBox.Icon.Warning,
                    "Eksport EPUB",
                    f"Nie udało się eksportować EPUB:\n{exc}",
                ).exec()
                return
        themed_message_box(
            self,
            QMessageBox.Icon.Information,
            "Eksport EPUB",
            f"Wyeksportowano {exported} plik(ów) EPUB.",
        ).exec()


def _icon_path() -> Path:
    return Path(__file__).resolve().parent / "assets" / "icon.svg"
