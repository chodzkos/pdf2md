# Changelog

## [Unreleased]

### Dodane

- Ekstrakcja obrazów z PDF (`--extract-images`, wymaga extra `[images]`) z referencjami w Markdown i filtrem rozmiaru.
- **Calibre jako opcjonalny backend eksportu EPUB** (`ebook-convert`), z detekcją w `doctor` i fallbackiem na Pandoc. Wybór backendu przez `[conversion].epub_backend` (`pandoc` domyślnie / `calibre`) lub flagę `convert --epub-backend`; gdy wybrano `calibre`, a `ebook-convert` jest poza PATH, eksport wraca do Pandoca.
- **`doctor`: gradacja sprzętowa** — rozróżnia stany GPU: karta zbyt stara na GPU (Pascal/Maxwell/Volta < sm_75 → tryb CPU, komunikat wprost, że aktualizacja sterownika nie pomoże — `compute_cap` ma pierwszeństwo przed wersją sterownika) vs za stary sterownik (CUDA < 13 → „zaktualizuj sterownik") vs brak PyTorch (zły venv → „zainstaluj zależności"; gdy przy braku torcha znana karta jest i tak za stara, doctor ostrzega, że instalacja torcha nic nie da); podpowiedź wykonalności per silnik pasuje do przyczyny (np. „karta za stara na GPU" zamiast mylącego „zaktualizuj sterownik"); nazwa i VRAM karty pokazywane z `nvidia-smi` także bez działającego CUDA (koniec pustego „Urządzenie: brak", gdy karta fizycznie jest). Wykonalność każdego silnika nadal względem wykrytego VRAM (✅ zmieści się / ⚠️ na granicy — do dostrojenia / ❌ za mało). Pomoc (zakładka „Instalacja silników") opisuje wymóg sterownika (jeden toolkit `+cu130`) i zależność „który silnik ruszy" od VRAM.
- **Faza 2 — premium scan pipeline** (Etapy 11–15): preprocessing skanów, silniki VLM-OCR, korekta LLM z walidacją, składanie książki i eksport EPUB/Markdown, profile skanowania.
- Silnik **Surya** (in-process, GPU) oraz **PaddleOCR-VL** (serwer OpenAI-compatible przez vLLM, izolowany venv) jako silniki VLM-OCR Fazy 2.
- Silnik **olmOCR-2-7B FP8** — adapter gotowy, **silnik zaparkowany**: serwuje na 24 GB z `--max_model_len 16384 --gpu_memory_utilization 0.90`, ale zajmuje ~całą kartę (nie współistnieje z modelem korekty LLM), start serwera 90–150 s na wywołanie i jest anglocentryczny. Dla dokumentów PL używać PaddleOCR-VL/Surya; jedyny sensowny tryb produkcyjny to external-server.
- **Wsparcie GPU (CUDA) na natywnym Windows** dla Surya/Marker: źródło torch `cu130` w `pyproject.toml` (`torch 2.12.1+cu130`) — liczenie na GPU także poza WSL.
- Motyw marki (jasny/ciemny/auto) i ciemny pasek tytułu przez `chodzkos-gui-kit` — pełny standard GUI (Fusion + QPalette + QSS akcentowy). Motyw stosowany przy starcie z `config.toml` (klucz `[ui].theme`, most `SettingsMapping`).
- Dyskretny przełącznik motywu (auto/jasny/ciemny) + „O programie" w lekkim górnym pasku okna głównego.
- Panel logów koloruje statusy (info/ostrzeżenie/błąd) rolami palety i przemalowuje istniejące wpisy po zmianie motywu — bez zaszytych hexów.
- Okno pomocy offline z zakładkami per funkcja (silniki konwersji, instalacja silników, post-processing LLM, profile skanowania, CLI, modele AI); dostęp z okna „O programie". Treść składana z palety (czytelna w obu motywach, re-render przy zmianie motywu), zmienny stan środowiska delegowany do `pdf2md doctor`.

### Zmienione

- **Okno pomocy to teraz wspólny `HelpWindow` z `chodzkos-gui-kit`** (pin `v0.5.0`); usunięty lokalny szkielet okna i własne helpery HTML. pdf2md był wzorcem ekstrakcji tego widgetu — teraz go konsumuje. **Treść 6 zakładek bez zmian** (Silniki / Instalacja / LLM / Profile / CLI / Model AI) — zostaje jako `help_tabs()` (dane pdf2md) składane kitowymi helperami (`section`/`paragraph`/`table`/`code`/`preformatted`); kolory przez `palette(...)`, delegacja zmiennego stanu do `pdf2md doctor`. Re-render przy zmianie motywu (re-`setHtml` na `PaletteChange`) i ciemną belkę DWM (`TitlebarSync`) liczy teraz kit — semantyka zachowana. `follow_app_titlebar` zostaje w pdf2md dla pozostałych okien (Ustawienia / O programie).
- **Domyślny model korekty Ollama: `qwen2.5:14b` → `qwen3:14b`** (spójność z dokumentacją i oknem pomocy). Zmiana dotyczy tylko wartości domyślnej dla nowych instalacji — istniejący `~/.config/pdf2md/config.toml` nie jest nadpisywany (świadomie, jak przy `marker_max_pages`).
- **Anulowanie konwersji w GUI**: kooperacyjne przerwanie między stronami i plikami oraz zwalnianie VRAM (unload modelu po anulowaniu).
- `marker_max_pages` domyślnie `0` (wszystkie strony); Surya wymuszona na GPU (CUDA) zamiast CPU.
- **Stos zależności domknięty**: `marker-pdf` przypięty `>=1.10,<2` (bez pinu resolver cofał do 0.3.10 → `ModuleNotFoundError: marker.config`), `transformers` ograniczone `>=4.56,<5` (wymóg surya 0.17.1), `pdf-craft` usunięty ze **wszystkich** extra.
- File-dialogi (wybór plików PDF, folder wyjściowy, domyślny folder w ustawieniach) przeniesione na helpery `chodzkos-gui-kit` (`open_files`/`pick_dir`) z regułą rozjazdu natywny/fallback: natywny Explorer gdy motyw zgodny z systemem, skonfigurowany ciemny fallback przy rozjeździe. Dodano test strażniczy przeciw bezpośredniemu `QFileDialog` w GUI.
- Pole „Folder wynikowy" (dawniej `QLineEdit` + „Przeglądaj") to teraz wspólny `PathEntry` z `chodzkos-gui-kit` (pin `v0.4.0`, `mode="dir"`): pole + przycisk „…" z `pick_dir` w jednym widgecie, etykiety po polsku przez `PathEntryTexts`. Zachowanie bez zmian (placeholder, wartość startowa z `default_output_dir`, odczyt przy konwersji).
- Lista plików to teraz wspólny `FileList` z `chodzkos-gui-kit` (pin `v0.4.1`); usunięty lokalny `FileListWidget`. **Nowości z widgetu**: własny toolbar (+Pliki / +Folder / Usuń / Wyczyść), licznik z polskimi formami mnogimi, **dodawanie całego folderu z rekursją podkatalogów** oraz sygnały `files_changed`/`selection_changed`. Duplikujące przyciski „Dodaj pliki…"/„Wyczyść listę" usunięte z okna głównego (menu Plik→Otwórz zostaje). Worker konwersji (cancel + zwalnianie VRAM) bez zmian — dostaje listę ścieżek jak dotąd.
- Panel logów to teraz wspólny `LogView` z `chodzkos-gui-kit` (pin `v0.4.3`); usunięty lokalny `LogPanelWidget`. Semantyka kolorów zachowana (`log_info` → zielony accent, `log_warning` → amber, `log_error` → red), timestampy `[HH:MM:SS]` jak dotąd. **Re-render historii przy zmianie motywu przejął kit** — usunięty własny `restyle()`/bufor; po przełączeniu motywu okno woła `set_theme(current_palette())`, a widget przemalowuje całą historię.
- **Usunięty menubar** (Plik/Pomoc) — meta-funkcje skonsolidowane na lekkim górnym pasku (GUI_STANDARD §6): przełącznik **Motyw**, **⚙ Ustawienia** (był w menu Plik) i **ⓘ O programie**. Menubar i lekki pasek się dublowały (§6 wprowadził pasek *zamiast* menubara). „Strona projektu" (dawniej menu Pomoc) przeniesiona do okna „O programie" jako przycisk — naturalny dom linków meta, z miejscem na przyszłą „Pomoc" offline. Przyciski listy plików (+Pliki/+Folder/Usuń/Wyczyść) to akcje `FileList` — bez zmian.

### Naprawione

- **`doctor` nie pokazuje mylącego hintu instalacji pod Windows** dla silników vLLM (MinerU / olmOCR / PaddleOCR-VL) — oznaczone jako wymagające Linux/WSL (status „❌ Niedostępny (wymaga Linux/WSL)" + uwaga, bez komendy instalacji, która i tak by nie zadziałała). Na Linux/WSL bez zmian (status „Niezainstalowany" + hint). Surya/Marker (GPU pod Windows) nietknięte.
- **Marker konwertował tylko 1. stronę** przy nieświeżym `~/.config/pdf2md/config.toml` (utrwalony `marker_max_pages=1` z czasów starego defaultu) — zmiana wartości domyślnej w kodzie nie nadpisuje istniejącego configu platformdirs.
- **torch na Windows wchodził jako `+cpu`** (Surya/Marker liczyły na CPU mimo karty) — wymuszone `+cu130` przez zadeklarowanie `torch`/`torchvision` jako jawnej zależności (inaczej `[tool.uv.sources]` ignoruje pakiet tranzytywny) + źródło indeksu cu130 + `uv lock --upgrade-package torch torchvision`.
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
