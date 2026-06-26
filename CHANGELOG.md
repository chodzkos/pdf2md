# Changelog

## [Unreleased]

### Dodane

- Motyw marki (jasny/ciemny/auto) i ciemny pasek tytułu przez `chodzkos-gui-kit` — pełny standard GUI (Fusion + QPalette + QSS akcentowy). Motyw stosowany przy starcie z `config.toml` (klucz `[ui].theme`, most `SettingsMapping`).
- Dyskretny przełącznik motywu (auto/jasny/ciemny) + „O programie" w lekkim górnym pasku okna głównego.
- Panel logów koloruje statusy (info/ostrzeżenie/błąd) rolami palety i przemalowuje istniejące wpisy po zmianie motywu — bez zaszytych hexów.

### Zmienione

- File-dialogi (wybór plików PDF, folder wyjściowy, domyślny folder w ustawieniach) przeniesione na helpery `chodzkos-gui-kit` (`open_files`/`pick_dir`) z regułą rozjazdu natywny/fallback: natywny Explorer gdy motyw zgodny z systemem, skonfigurowany ciemny fallback przy rozjeździe. Dodano test strażniczy przeciw bezpośredniemu `QFileDialog` w GUI.
- Pole „Folder wynikowy" (dawniej `QLineEdit` + „Przeglądaj") to teraz wspólny `PathEntry` z `chodzkos-gui-kit` (pin `v0.4.0`, `mode="dir"`): pole + przycisk „…" z `pick_dir` w jednym widgecie, etykiety po polsku przez `PathEntryTexts`. Zachowanie bez zmian (placeholder, wartość startowa z `default_output_dir`, odczyt przy konwersji).
- Lista plików to teraz wspólny `FileList` z `chodzkos-gui-kit` (pin `v0.4.1`); usunięty lokalny `FileListWidget`. **Nowości z widgetu**: własny toolbar (+Pliki / +Folder / Usuń / Wyczyść), licznik z polskimi formami mnogimi, **dodawanie całego folderu z rekursją podkatalogów** oraz sygnały `files_changed`/`selection_changed`. Duplikujące przyciski „Dodaj pliki…"/„Wyczyść listę" usunięte z okna głównego (menu Plik→Otwórz zostaje). Worker konwersji (cancel + zwalnianie VRAM) bez zmian — dostaje listę ścieżek jak dotąd.
- Panel logów to teraz wspólny `LogView` z `chodzkos-gui-kit` (pin `v0.4.3`); usunięty lokalny `LogPanelWidget`. Semantyka kolorów zachowana (`log_info` → zielony accent, `log_warning` → amber, `log_error` → red), timestampy `[HH:MM:SS]` jak dotąd. **Re-render historii przy zmianie motywu przejął kit** — usunięty własny `restyle()`/bufor; po przełączeniu motywu okno woła `set_theme(current_palette())`, a widget przemalowuje całą historię.

### Naprawione

- Polskie etykiety standardowych elementów Qt: przyciski `OK/Anuluj/Zastosuj` w oknie ustawień oraz opisy/przyciski/tooltips nienatywnego `QFileDialog` (fallback przy rozjeździe motywu) — przez załadowanie tłumaczeń Qt (`QTranslator`: `qtbase_pl`, `qt_pl`) przy starcie GUI. Brak `.qm` w danej dystrybucji loguje ostrzeżenie zamiast cichego pominięcia.
- Wszystkie okna komunikatów (`QMessageBox`: O programie, zapis ustawień, test klucza, brak plików, eksport EPUB, podsumowanie konwersji, zapis profilu) mają belkę tytułu podążającą za motywem **aplikacji** zamiast systemu — helper `themed_message_box`/`attach_dark_titlebar` (natywny uchwyt + `follow_app_titlebar` przed pokazaniem). Koniec jasnych belek przy stałym ciemnym motywie aplikacji na jasnym systemie.

## v1.0.0

### Dodane

- CLI `pdf2md` z komendami `convert`, `list-engines`, `list-llm`, `doctor` i `config`.
- GUI `pdf2md-gui` (PySide6) z kolejką plików, wyborem silnika, opcjonalnym LLM, logiem, podglądem Markdown i eksportem EPUB przez Pandoc.
- Silniki konwersji: PyMuPDF4LLM, Marker, Docling, MinerU.
- OCR dla skanów oraz obsługa dokumentów mieszanych, wielokolumnowych, tabel i materiałów naukowych.
- Wspólny `~/.config/pdf2md/config.toml` dla CLI i GUI; `.env` jako override deweloperski.
- Dostawcy LLM: Ollama, Anthropic Claude, OpenAI, Google Gemini.
- Tryby post-processingu LLM: `whole_document`, `by_page`, `by_chunk`, `by_heading`.
- `pdf2md doctor` — diagnostyka zależności systemowych, silników, LLM, Tesseracta, Pandoca, Ollamy i realnej używalności CUDA.
- Eksport Markdown i EPUB (przez Pandoc).
- Preprocessing skanów (`scan/preprocessing.py`): wyrównanie, deskewing, denoising, kontrast — fundament dla Fazy 2 VLM-OCR.
- Konfigurowalne rozmiary batchy GPU dla Markera/surya (`marker_recognition_batch_size`, `marker_detector_batch_size`, `marker_layout_batch_size`, `marker_table_rec_batch_size`).
- Konfigurowalne backendy MinerU (`mineru_backend`: `pipeline` lub `vlm`); backend `vlm` automatycznie ustawia `VLLM_USE_FLASHINFER_SAMPLER=0` dla kompatybilności z nowymi GPU (Blackwell sm_120).
- Testy jednostkowe: konfiguracja, CLI, converter, silniki, dostawcy LLM, detekcja zależności, eksportery, preprocessing.

### Ograniczenia v1.0

- Wymagany Python 3.11–3.12 (ekosystem ML nie obsługuje 3.13+).
- pdf-craft wykluczony z powodu nieusuwalnego konfliktu `transformers` z Markerem i Doclingiem.
- Faza 2 (VLM-OCR, skanowane książki wysokiej jakości) — po v1.0, wymaga GPU ≥24 GB VRAM.
