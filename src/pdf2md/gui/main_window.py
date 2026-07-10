"""Główne okno aplikacji pdf2md GUI."""

from __future__ import annotations

from pathlib import Path

from chodzkos_detection import check_pandoc
from chodzkos_gui_kit.qt.theme import ThemeManager, ThemeSetting, current_palette
from chodzkos_gui_kit.qt.widgets import (
    FileList,
    FileListTexts,
    HelpWindow,
    LogView,
    PathEntry,
    PathEntryTexts,
)
from loguru import logger
from PySide6.QtCore import QObject, QRunnable, QSize, QThreadPool, QUrl, Signal
from PySide6.QtGui import QCloseEvent, QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QCheckBox,
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
from pdf2md.core.input_types import SUPPORTED_INPUT_EXTENSIONS
from pdf2md.detection.dependencies import check_calibre
from pdf2md.exporters import build_epub_exporter
from pdf2md.gui.help_window import HELP_TITLE, help_tabs
from pdf2md.gui.settings_dialog import SettingsDialog
from pdf2md.gui.theming import attach_dark_titlebar, themed_message_box
from pdf2md.gui.widgets.engine_selector import EngineSelectorWidget
from pdf2md.gui.widgets.llm_selector import LLMSelectorWidget
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
    tooltip_files="Dodaj pliki PDF lub obrazy przez okno wyboru",
    tooltip_folder="Dodaj pliki PDF lub obrazy z wybranego folderu",
    tooltip_remove="Usuń zaznaczone pozycje z listy",
    tooltip_clear="Usuń wszystkie pozycje z listy",
    list_tooltip="Lista plików — przeciągnij PDF/JPG/PNG/TIFF tutaj lub użyj przycisków powyżej",
    dialog_add_files="Dodaj pliki PDF lub obrazy",
    dialog_add_folder="Dodaj folder",
    filter_supported="PDF i obrazy ({pattern})",
)

_EXTRACT_IMAGES_TOOLTIP = (
    "Dla silników OCR (Surya, olmOCR, PaddleOCR). Marker i Docling osadzają obrazy automatycznie."
)
_EXTRACT_IMAGES_IN_PLACE_TOOLTIP = "Marker/Docling osadzają obrazy in-place — ekstrakcja zbędna."


def _files_count_label(count: int) -> str:
    """Licznik plików z polskimi formami mnogimi (pdf2md nie ma gettext)."""
    if count == 1:
        form = "plik"
    elif 2 <= count % 10 <= 4 and not 12 <= count % 100 <= 14:
        form = "pliki"
    else:
        form = "plików"
    return f"{count} {form}"


def _epub_backend_label(backend: str) -> str:
    if backend == "calibre":
        return "Calibre"
    if backend == "pandoc":
        return "Pandoc"
    return backend


def _resolve_epub_backend(preferred_backend: str) -> tuple[str | None, str | None]:
    """Wybiera dostępny backend EPUB i zwraca opcjonalny komunikat fallbacku."""
    preferred = preferred_backend.lower().strip()
    available: list[str] = []
    if check_pandoc():
        available.append("pandoc")
    if check_calibre():
        available.append("calibre")

    if preferred in available:
        return preferred, None
    if not available:
        return None, "Pandoc ani Calibre nie są dostępne. Nie można wyeksportować EPUB."

    fallback = "pandoc" if "pandoc" in available else available[0]
    message = (
        f"Backend EPUB z profilu ({_epub_backend_label(preferred)}) jest niedostępny.\n"
        f"Używam dostępnego backendu: {_epub_backend_label(fallback)}."
    )
    return fallback, message


def _has_in_place_images(engine_name: str) -> bool:
    return engine_name.strip().lower() in {"docling", "marker"}


class _EpubToolsBridge(QObject):
    """Most sygnałowy: przenosi wynik sondy narzędzi EPUB z wątku puli do wątku UI."""

    ready = Signal(bool, bool)  # (pandoc_dostępny, calibre_dostępny)


class _EpubToolsProbe(QRunnable):
    """Liczy check_pandoc()/check_calibre() poza wątkiem UI (na Windows: rejestr/FS/PATH).

    Uruchamiane na starcie konwersji — wynik trafia do cache MainWindow i jest gotowy,
    zanim pojawi się dialog końcowy (żaden blokujący `which`/rejestr na wątku UI).
    """

    def __init__(self, bridge: _EpubToolsBridge) -> None:
        super().__init__()
        self._bridge = bridge

    def run(self) -> None:
        try:
            pandoc = bool(check_pandoc())
            calibre = bool(check_calibre())
        except Exception:
            pandoc, calibre = False, False
        self._bridge.ready.emit(pandoc, calibre)


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
        self._batch_total = 0  # liczba plików w bieżącym batchu (do etykiety paska)
        # Cache dostępności narzędzi EPUB liczony w tle na starcie konwersji (None = jeszcze nieznany).
        self._epub_tools: tuple[bool, bool] | None = None
        self._epub_tools_bridge: _EpubToolsBridge | None = None
        self._initial_files = initial_files or []
        self._build_ui()

        # Ciemny pasek tytułu (DWM = motyw app); re-render logu po zmianie motywu.
        self._theme_manager.attach_titlebar(self)
        self._theme_manager.theme_changed.connect(self._on_theme_changed)

        if self._initial_files:
            self._file_list.add_files(self._initial_files)

    # ------------------------------------------------------------------
    # Budowa interfejsu
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(8)
        root.setContentsMargins(12, 12, 12, 12)

        # --- Górny pasek (lekki §6): logo+nazwa | motyw + ⚙ Ustawienia + ⓘ O programie ---
        root.addLayout(self._build_topbar())

        # --- Lista plików (kitowy FileList: własny toolbar +Pliki/+Folder/Usuń/Wyczyść,
        #     licznik, D&D z rekursją folderów) ---
        self._file_list = FileList(
            extensions=set(SUPPORTED_INPUT_EXTENSIONS),
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

        # --- Opcje konwersji per-sesja ---
        self._extract_images = QCheckBox("Ekstrahuj obrazy z PDF")
        self._extract_images.setChecked(False)
        self._extract_images.setToolTip(_EXTRACT_IMAGES_TOOLTIP)
        self._sync_extract_images_enabled(self._engine_selector.get_engine_name())
        root.addWidget(self._extract_images)

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
        # kitowy LogView: log_info→"ok" (zielony accent), warning→amber, error→red;
        # re-render historii i timestampy [HH:MM:SS] robi sam widget.
        self._log_panel = LogView(timestamps=True)
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
        """Lekki górny pasek (GUI_STANDARD §6): logo+nazwa | motyw + ⚙ Ustawienia + ⓘ.

        Meta-funkcje (motyw, ustawienia, o programie) siedzą dyskretnie w pasku —
        zastępują dawny menubar, nie w zakładkach roboczych.
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

        settings_btn = QToolButton()
        settings_btn.setText("⚙")
        settings_btn.setToolTip("Ustawienia")
        settings_btn.clicked.connect(self._open_settings)
        bar.addWidget(settings_btn)

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
        """Po zmianie motywu przemaluj log wg nowej palety (re-render robi kit LogView)."""
        self._log_panel.set_theme(current_palette())

    def closeEvent(self, event: QCloseEvent) -> None:
        """Zamyka okno dopiero po kooperatywnym zatrzymaniu workera."""
        worker = self._worker
        if worker is None or not worker.isRunning():
            event.accept()
            return

        self._log_panel.log_warning("Zamykanie — przerywam konwersję…")
        worker.cancel()
        if worker.wait(15000):
            self._worker = None
            event.accept()
            return

        event.ignore()
        themed_message_box(
            self,
            QMessageBox.Icon.Warning,
            "Konwersja w toku",
            "Nie udało się przerwać konwersji w 15 sekund. Spróbuj ponownie za chwilę.",
        ).exec()

    # ------------------------------------------------------------------
    # Sloty przycisków
    # ------------------------------------------------------------------

    def _is_scan_engine(self, engine_name: str) -> bool:
        return "scan pipeline" in engine_name.lower()

    def _on_engine_changed(self, engine_name: str) -> None:
        self._profile_selector.setVisible(self._is_scan_engine(engine_name))
        self._sync_extract_images_enabled(engine_name)

    def _sync_extract_images_enabled(self, engine_name: str) -> None:
        in_place = _has_in_place_images(engine_name)
        self._extract_images.setEnabled(not in_place)
        self._extract_images.setToolTip(
            _EXTRACT_IMAGES_IN_PLACE_TOOLTIP if in_place else _EXTRACT_IMAGES_TOOLTIP
        )

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self)
        if dialog.exec():
            settings = get_settings()
            if settings.default_output_dir:
                self._output_entry.set(settings.default_output_dir)

    def _show_about(self) -> None:
        # themed_message_box → ciemna belka za motywem aplikacji. Meta-akcje (Pomoc,
        # Strona projektu) grupujemy tutaj, nie jako osobne ikony na pasku.
        box = themed_message_box(
            self,
            QMessageBox.Icon.Information,
            "O programie",
            "pdf2md\n\nKonwerter PDF do Markdown z wieloma silnikami i opcjonalnym LLM.",
        )
        help_btn = box.addButton("Pomoc", QMessageBox.ButtonRole.ActionRole)
        project_btn = box.addButton("Strona projektu", QMessageBox.ButtonRole.ActionRole)
        box.addButton("Zamknij", QMessageBox.ButtonRole.AcceptRole)
        box.exec()
        clicked = box.clickedButton()
        if clicked is help_btn:
            HelpWindow(self, title=HELP_TITLE, tabs=help_tabs()).exec()
        elif clicked is project_btn:
            self._open_project_page()

    def _open_project_page(self) -> None:
        QDesktopServices.openUrl(QUrl("https://github.com/chodzkos/pdf2md"))

    def _on_convert(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            self._log_panel.log_warning("Konwersja już trwa — poczekaj na zakończenie.")
            return
        self._worker = None

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
        self._batch_total = len(files)
        self._last_markdown_outputs = []
        self._last_output_dir = Path(output_dir) if output_dir else None
        self._start_epub_tools_probe()
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
            extract_images=self._extract_images.isChecked(),
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
        self._finish_worker()
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

    def _on_progress(self, filename: str, index: int, percent: int) -> None:
        total = self._batch_total or 1
        self._progress.setValue(percent)
        self._progress.setFormat(f"[{index}/{total}] {filename}  {percent}%")

    def _on_file_done(self, src: str, dst: str, elapsed: float) -> None:
        name = Path(src).name
        self._log_panel.log_info(f"✓ {name} → {dst}  ({elapsed:.1f}s)")
        if not dst:
            return
        output = Path(dst)
        if output.is_file():
            self._last_markdown_outputs.append(output)
            self._preview.setPlainText(output.read_text(encoding="utf-8"))
            self._tabs.setCurrentWidget(self._preview)

    def _on_file_error(self, src: str, message: str) -> None:
        name = Path(src).name
        self._log_panel.log_error(f"✗ {name}: {message}")

    def _on_all_done(self, success: int, errors: int, total: float) -> None:
        self._finish_worker()
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

    def _finish_worker(self) -> None:
        self._worker = None

    def _start_epub_tools_probe(self) -> None:
        """Liczy dostępność Pandoc/Calibre w tle (QThreadPool) na starcie konwersji.

        Dzięki temu dialog końcowy nie odpala blokującego `which`/rejestru na wątku UI.
        """
        self._epub_tools = None
        bridge = _EpubToolsBridge()
        bridge.ready.connect(self._on_epub_tools_ready)
        self._epub_tools_bridge = bridge  # referencja utrzymuje most przy życiu
        QThreadPool.globalInstance().start(_EpubToolsProbe(bridge))

    def _on_epub_tools_ready(self, pandoc: bool, calibre: bool) -> None:
        self._epub_tools = (pandoc, calibre)

    def _epub_tools_available(self) -> tuple[bool, bool]:
        """Zwraca (pandoc, calibre) z cache; awaryjnie liczy synchronicznie, gdy sonda nie zdążyła."""
        if self._epub_tools is not None:
            return self._epub_tools
        return check_pandoc(), check_calibre()

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
        pandoc_ok, calibre_ok = self._epub_tools_available()
        if self._last_markdown_outputs and (pandoc_ok or calibre_ok):
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

    def _selected_profile_epub_backend(self) -> str:
        from pdf2md.scan.profiles import load_profile

        profile = load_profile(self._profile_selector.get_profile_name())
        return profile.output.epub_backend

    def _export_last_outputs_to_epub(self) -> None:
        try:
            preferred_backend = self._selected_profile_epub_backend()
        except Exception as exc:
            themed_message_box(
                self,
                QMessageBox.Icon.Warning,
                "Eksport EPUB",
                f"Nie udało się odczytać backendu EPUB z profilu:\n{exc}",
            ).exec()
            return

        backend, warning = _resolve_epub_backend(preferred_backend)
        if warning:
            logger.warning(warning)
            themed_message_box(self, QMessageBox.Icon.Warning, "Eksport EPUB", warning).exec()
        if backend is None:
            return

        exporter = build_epub_exporter(backend)
        exported = 0
        for markdown_path in self._last_markdown_outputs:
            try:
                markdown = markdown_path.read_text(encoding="utf-8")
                # Obrazy inline leżą obok pliku .md — bez source_dir Pandoc/Calibre
                # tworzą temp w /tmp i gubią względne referencje (EPUB bez obrazów).
                exporter.export(
                    markdown,
                    markdown_path.with_suffix(".epub"),
                    source_dir=markdown_path.parent,
                )
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
