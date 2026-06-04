# pdf2md Squeezer — Roadmap

> Każdy etap = jedna gałąź git (branch) = jeden Pull Request

---

## Szybki przegląd

```
FAZA 1 — v1.0 (orkiestrator gotowych silników)
Etap 0  Init projektu          ░░░░░  ~2h
Etap 1  Rdzeń i abstrakcje     ░░░░░  ~3h
Etap 2  PyMuPDF4LLM engine     ░░░░░  ~2h
Etap 3  Marker engine          ░░░░░  ~3h
Etap 4  Dostawcy LLM           ░░░░░  ~3h
Etap 5  CLI + doctor + dry-run ░░░░░  ~4h
Etap 6  GUI — szkielet         ░░░░░  ~4h
Etap 7  GUI — polish           ░░░░░  ~4h
Etap 8  Docling (core) + opc. MinerU, pdf-craft  ░░░░░  ~4h
Etap 9  Testy + dokumentacja   ░░░░░  ~3h
Etap 10 Packaging              ░░░░░  ~1-2 dni (trudny!)
────────────────────────────────────────────
Faza 1 łącznie                       ~35h + packaging

FAZA 2 — premium scan pipeline (lokalny VLM-OCR, wymaga GPU)
Etap 11 Preprocessing obrazu   ░░░░░  ~4h
Etap 12 Silniki VLM-OCR        ░░░░░  ~6h
Etap 13 Korekta LLM + walidacja ░░░░  ~6h
Etap 14 Składanie książki + EPUB ░░░░ ~5h
Etap 15 Profile skanowania     ░░░░░  ~3h
────────────────────────────────────────────
Faza 2 łącznie                       ~24h robocze
                          (w swoim tempie, nie naraz)
```

---

## Etap 0 — Inicjalizacja projektu
**Gałąź:** `main` (bezpośrednio)
**Czas:** ~2 godziny

### Cel
Działający szkielet projektu gotowy do development, z CI/CD od pierwszego commita.

### Zadania dla Claude Code
- [ ] Struktura katalogów `src/pdf2md/{engines,llm,core,cli,gui,utils}`
- [ ] `pyproject.toml` z uv — wszystkie zależności, entry points
- [ ] `.gitignore` (Python, VS Code, `.env`, `dist/`, `build/`, `__pycache__/`)
- [ ] `LICENSE` (MIT)
- [ ] `README.md` — szkielet z opisem projektu
- [ ] `.env.example` z placeholderami kluczy API
- [ ] `ruff` i `mypy` w `pyproject.toml`
- [ ] `.pre-commit-config.yaml` (ruff, mypy)
- [ ] `.github/workflows/ci.yml` — ruff + mypy + pytest na każdy push i PR
- [ ] Placeholder `__init__.py` w każdym module
- [ ] `tests/unit/test_sanity.py` — jeden test sprawdzający import pakietu

### Co robisz Ty
- [ ] Przeglądasz utworzone pliki w VS Code
- [ ] `uv sync` — instalacja zależności
- [ ] `uv run pytest` — sprawdzasz czy test przechodzi
- [ ] `git add -A && git commit -m "Etap 0: Inicjalizacja projektu"`
- [ ] `git push -u origin main`
- [ ] Sprawdzasz na GitHub czy CI (zielona fajka) przeszło

### Definicja ukończenia
✅ `uv run pytest` — zielone  
✅ `uv run ruff check .` — zero błędów  
✅ GitHub Actions — zielone  
✅ Struktura katalogów zgodna z docs/PROJEKT.md  

---

## Etap 1 — Rdzeń i abstrakcje
**Gałąź:** `etap-1-core`
**Czas:** ~3 godziny

### Cel
Wspólny interfejs dla wszystkich silników i dostawców LLM. To fundament — wszystko inne zależy od tego etapu.

### Zadania dla Claude Code
- [ ] `engines/base.py` — dataclass `ConversionResult`, ABC `ConversionEngine`
- [ ] `llm/base.py` — dataclass `LLMResult`, ABC `LLMProvider` (metoda `postprocess` przyjmuje `mode`)
- [ ] `core/config.py` — model konfiguracji oparty o **`config.toml` jako źródło prawdy** (`~/.config/pdf2md/config.toml`), z `.env` jako override deweloperskim. Pola: klucze API, nazwy modeli LLM (puste = fallback z kodu), domyślny silnik, llm_mode, ścieżka output, język. CLI i GUI czytają TEN SAM config. `save_settings()` ATOMOWY (zapis do temp + `os.replace()`, chroni przed race condition CLI/GUI).
- [ ] Konwencja w `engines/base.py`: `is_available()` sprawdza obecność pakietu przez `importlib.metadata.version()`, NIE importuje silnika (import dopiero w `convert()`) — inaczej start/`--help`/`list-engines` trwałyby kilkanaście sekund
- [ ] `detection/dependencies.py` — wykrywanie stanu systemu (Tesseract+języki, Poppler, Pandoc, Ollama+modele, GPU/CUDA, klucze API). Używane później przez `pdf2md doctor`.
- [ ] `utils/chunking.py` — funkcje dzielenia tekstu: `by_chunk(text, max_tokens)`, `by_heading(text)`, `by_page(pages)`. Gotowe na tryby LLM.
- [ ] `core/registry.py` — `EngineRegistry` i `LLMRegistry` z metodą `get_available()`
- [ ] `core/converter.py` — `Converter` orkiestrator: `convert(pdf_path, engine, llm=None, llm_mode="none") -> ConversionResult`
- [ ] `utils/logging.py` — konfiguracja loguru (plik + konsola)
- [ ] Testy jednostkowe: `test_registry.py`, `test_converter.py`, `test_config.py` (config.toml + override z .env), `test_chunking.py`

### Co robisz Ty
- [ ] `git checkout -b etap-1-core`
- [ ] Po skończeniu: `uv run pytest` → zielone
- [ ] `git add -A && git commit -m "Etap 1: Rdzeń i abstrakcje"`
- [ ] `git push origin etap-1-core`
- [ ] Na GitHub: utwórz Pull Request, przejrzyj diff, scal do main

### Definicja ukończenia
✅ ABC `ConversionEngine` i `LLMProvider` zdefiniowane  
✅ Konfiguracja z `config.toml` (jedno źródło prawdy), `.env` jako override  
✅ `utils/chunking.py` gotowe na tryby LLM  
✅ Registry prawidłowo wykrywa (mock) silniki  
✅ Converter wywołuje engine.convert() i opcjonalnie llm.postprocess()  
✅ Testy przechodzą  

---

## Etap 2 — Pierwszy silnik: PyMuPDF4LLM
**Gałąź:** `etap-2-pymupdf4llm`
**Czas:** ~2 godziny

### Cel
Pierwszy działający silnik konwersji — najłatwiejszy z pięciu. Po tym etapie masz działającą konwersję end-to-end.

### Zadania dla Claude Code
- [ ] `engines/pymupdf4llm_engine.py` — pełna implementacja:
  - `is_available()`: sprawdza `import pymupdf4llm`
  - `convert(pdf_path)`: wywołuje `pymupdf4llm.to_markdown(pdf_path)`
  - obsługa błędów, logowanie
- [ ] Aktualizacja `EngineRegistry` — rejestracja nowego silnika
- [ ] Test integracyjny `tests/integration/test_pymupdf4llm.py` używający `tests/fixtures/test_text.pdf`
- [ ] Prosty skrypt `scripts/test_convert.py` do ręcznego sprawdzenia

### Co robisz Ty
- [ ] `git checkout -b etap-2-pymupdf4llm`
- [ ] Wgrywasz `test_text.pdf` do `tests/fixtures/` (zwykły PDF z tekstem)
- [ ] Po skończeniu: uruchamiasz `uv run python scripts/test_convert.py tests/fixtures/test_text.pdf`
- [ ] Sprawdzasz plik `output.md` — czy wygląda rozsądnie
- [ ] `git add -A && git commit -m "Etap 2: PyMuPDF4LLM engine"`
- [ ] Pull Request → scal

### Definicja ukończenia
✅ Konwersja `test_text.pdf` → `output.md` działa  
✅ `is_available()` zwraca `True` gdy biblioteka zainstalowana, `False` gdy nie  
✅ Testy przechodzą  

---

## Etap 3 — Marker engine
**Gałąź:** `etap-3-marker`
**Czas:** ~3 godziny

### Cel
Drugi silnik — znacznie silniejszy, obsługuje OCR i ma wbudowany tryb LLM.

### Zadania dla Claude Code
- [ ] `engines/marker_engine.py`:
  - `is_available()`: sprawdza `import marker`
  - `convert(pdf_path, use_llm=False, llm_provider=None, lang="pl,en")`: wywołuje Marker API
  - obsługa parametru `use_llm` (przekazuje do Marker, jeśli `llm_provider` to Gemini/Ollama)
  - obsługa błędów, logowanie, raportowanie liczby stron
- [ ] Aktualizacja Registry
- [ ] Testy integracyjne z `test_scan.pdf` i `test_columns.pdf`
- [ ] Aktualizacja `scripts/test_convert.py` — flag `--engine marker`

### Co robisz Ty
- [ ] `git checkout -b etap-3-marker`
- [ ] `uv add marker-pdf` (możliwe że długa instalacja — Marker ma dużo zależności)
- [ ] Wgrywasz `test_scan.pdf` i `test_columns.pdf` do fixtures
- [ ] Testujesz oba pliki
- [ ] Porównujesz jakość wyników z PyMuPDF4LLM
- [ ] Pull Request → scal

### Definicja ukończenia
✅ Marker konwertuje PDF z OCR (skanowany plik)  
✅ Parametr `use_llm` działa bez błędu (nawet jeśli LLM nie skonfigurowany — graceful skip)  
✅ Testy przechodzą  

---

## Etap 4 — Dostawcy LLM
**Gałąź:** `etap-4-llm-providers`
**Czas:** ~3 godziny

### Cel
Warstwa post-processingu LLM — czyszczenie Markdownu po konwersji.

### Zadania dla Claude Code
- [ ] `llm/ollama_provider.py`:
  - `is_available()`: ping `http://localhost:11434/api/tags`
  - `get_available_models()`: lista zainstalowanych modeli
  - `postprocess(markdown, mode, instructions)`: wywołanie API Ollama
- [ ] `llm/anthropic_provider.py`:
  - `is_available()`: sprawdza `ANTHROPIC_API_KEY`
  - `postprocess(markdown, mode, instructions)`: Claude API
- [ ] `llm/openai_provider.py` — analogicznie
- [ ] `llm/gemini_provider.py` — analogicznie
- [ ] **Nazwy modeli NIE na sztywno.** Każdy provider bierze model z `settings` (`config.toml`/`.env`); jeśli puste, używa bezpiecznego fallbacku zdefiniowanego jako stała w pliku providera. Użytkownik nadpisuje z CLI/GUI. Powód: nazwy modeli i dostępność API zmieniają się szybko — hardcode powoduje, że aplikacja przestaje działać.
- [ ] **Tryby chunkowania** w `postprocess(markdown, mode)`: `whole_document`, `by_page`, `by_chunk`, `by_heading` (użyj `utils/chunking.py` z Etapu 1). Dla `whole_document` sprawdź czy tekst mieści się w kontekście — jeśli nie, ostrzeż i zaproponuj `by_chunk`.
- [ ] `LLMRegistry` z auto-detekcją dostępnych dostawców
- [ ] Prompt systemowy do post-processingu w `core/prompts.py` jako `POST_PROCESSING_PROMPT`:
  ```
  "Wyczyść i popraw poniższy Markdown uzyskany z konwersji PDF.
   Usuń artefakty OCR, popraw tabelki, zachowaj strukturę.
   Nie parafrazuj treści. Zwróć tylko poprawiony Markdown, bez komentarzy."
  ```
- [ ] Testy z mock'owanymi API (żeby nie płacić za testy), w tym test że model bierze się z configu i że chunkowanie dzieli długi tekst

### Co robisz Ty
- [ ] `git checkout -b etap-4-llm-providers`
- [ ] (Opcjonalne) Instalacja Ollama: https://ollama.com/download → `ollama pull qwen2.5:14b`
- [ ] Ustawiasz klucze API w `config.toml` lub `.env` (dev) dla dostawców do testów
- [ ] Testujesz post-processing na surowym Markdown z Etapu 2 (różne tryby chunkowania)
- [ ] Pull Request → scal

### Definicja ukończenia
✅ Każdy provider zwraca `is_available() = True/False` poprawnie  
✅ Model brany z configu (z fallbackiem), NIE hardcodowany  
✅ Tryby chunkowania działają (whole_document / by_page / by_chunk / by_heading)  
✅ `postprocess()` zwraca poprawiony Markdown  
✅ Testy z mockami przechodzą  
✅ Brak twardego błędu gdy klucz API nie jest ustawiony (graceful degradation)  

---

## Etap 5 — CLI
**Gałąź:** `etap-5-cli`
**Czas:** ~3 godziny

### Cel
Pełny interfejs linii komend — użytek dla zaawansowanych użytkowników i automatyzacji.

### Komendy do implementacji

```bash
# Podstawowa konwersja
pdf2md convert dokument.pdf

# Z wyborem silnika i wyjściem
pdf2md convert dokument.pdf -o wynik.md --engine marker

# Z post-processingiem LLM (z trybem chunkowania)
pdf2md convert dokument.pdf --engine marker --llm claude --llm-mode by_heading

# Podgląd planu bez konwersji (co, czym, gdzie)
pdf2md convert dokument.pdf --dry-run

# Batch processing
pdf2md convert *.pdf --output-dir wyniki/

# Sprawdź co jest dostępne
pdf2md list-engines
pdf2md list-llm

# Diagnostyka całego środowiska
pdf2md doctor

# Ustawienia (zapis do config.toml)
pdf2md config set default-engine marker
pdf2md config set anthropic-key sk-ant-...
pdf2md config show
```

### Zadania dla Claude Code
- [ ] `cli/main.py` z click:
  - komenda `convert` z flagami, w tym `--llm-mode [none|whole_document|by_page|by_chunk|by_heading]` i `--dry-run`
  - `--dry-run`: pokazuje typ PDF (z `detection/pdf_type.py`), wybrany silnik, czy silnik dostępny, czy Tesseract/Pandoc/Ollama dostępne, gdzie zapisze wynik — i kończy BEZ konwersji
  - komenda `list-engines` (tabela `rich`, z kolumną licencji)
  - komenda `list-llm` (tabela z dostępnymi dostawcami)
  - **komenda `doctor`** — pełna diagnostyka środowiska (użyj `detection/dependencies.py`):
    System/OS, Python, CUDA, PyTorch CUDA, Tesseract+języki (pol/eng), Poppler, Pandoc, Ollama+modele, status każdego silnika, status kluczy API. Kolorowo: ✅/⚠️/❌.
  - komenda `config` (get/set/show) operująca na `config.toml`
  - progress bar z `rich`, kolorowy output, raport końcowy
- [ ] Entry point w `pyproject.toml`: `pdf2md = "pdf2md.cli.main:cli"`
- [ ] Testy `tests/unit/test_cli.py` z `click.testing.CliRunner` (w tym `doctor` i `--dry-run`)

### Co robisz Ty
- [ ] `git checkout -b etap-5-cli`
- [ ] `uv pip install -e .` — instalacja z entry pointem
- [ ] `pdf2md doctor` — czy poprawnie wykrywa Twoje środowisko (WSL, GPU, Tesseract, Ollama)?
- [ ] `pdf2md list-engines` — czy pokazuje dostępne silniki?
- [ ] `pdf2md convert tests/fixtures/test_text.pdf --dry-run` — czy plan wygląda dobrze?
- [ ] `pdf2md convert tests/fixtures/test_text.pdf` — czy działa?
- [ ] Pull Request → scal

### Definicja ukończenia
✅ `pdf2md convert plik.pdf` produkuje `.md` obok pliku źródłowego  
✅ `pdf2md doctor` pokazuje pełny stan środowiska  
✅ `--dry-run` pokazuje plan bez konwersji  
✅ `--output-dir` kieruje wyniki do folderu  
✅ `list-engines` pokazuje co jest zainstalowane  
✅ Batch `*.pdf` działa  
✅ Testy CLI przechodzą  

---

## Etap 6 — GUI: szkielet
**Gałąź:** `etap-6-gui-skeleton`
**Czas:** ~4 godziny

### Cel
Działające okno aplikacji z pełną funkcjonalnością konwersji (bez "polishu").

### Layout okna głównego
```
┌─────────────────────────────────────────────────────┐
│  pdf2md                                    [— □ ×]  │
├─────────────────────────────────────────────────────┤
│  [Dodaj pliki...]  [Wyczyść listę]                  │
│ ┌─────────────────────────────────────────────────┐ │
│ │ 📄 dokument1.pdf                    [ Usuń ]    │ │
│ │ 📄 raport_2024.pdf                  [ Usuń ]    │ │
│ │                                                 │ │
│ │        Przeciągnij pliki tutaj                  │ │
│ └─────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────┤
│  Silnik: [Marker                    ▼]              │
│          ⚪ PyMuPDF4LLM – Szybki, natywny tekst    │
│          🟢 Marker – Uniwersalny, OCR              │  
│          ⚫ MinerU – Niezainstalowany              │
│                                                     │
│  LLM: [ ] Włącz post-processing                    │
│       Dostawca: [Claude Sonnet      ▼]              │
│                                                     │
│  Output: [~/Desktop/wyniki/    ] [Przeglądaj...]   │
├─────────────────────────────────────────────────────┤
│  [████████████████░░░░░░░░]  dokument1.pdf  67%    │
│  [          Konwertuj          ]                    │
├─────────────────────────────────────────────────────┤
│  [16:42:01] ✅ dokument1.pdf → dokument1.md (2.1s) │
│  [16:42:03] ⏳ raport_2024.pdf – w trakcie...      │
└─────────────────────────────────────────────────────┘
```

### Zadania dla Claude Code
- [ ] `gui/app.py` — inicjalizacja QApplication
- [ ] `gui/main_window.py` — główne okno z layoutem
- [ ] `gui/widgets/file_list.py` — QListWidget z drag & drop
- [ ] `gui/widgets/engine_selector.py` — QComboBox z opisami i statusem (🟢/⚪/⚫)
- [ ] `gui/widgets/llm_selector.py` — toggle + wybór dostawcy
- [ ] `gui/workers.py` — `ConversionWorker(QThread)` z sygnałami: `progress`, `file_done`, `error`, `all_done`
- [ ] `gui/widgets/log_panel.py` — QTextEdit tylko do odczytu z kolorowym logiem
- [ ] Entry point: `pdf2md-gui = "pdf2md.gui.app:main"`

### Co robisz Ty
- [ ] `git checkout -b etap-6-gui-skeleton`
- [ ] `uv run pdf2md-gui` — sprawdzasz czy okno się otwiera
- [ ] Przeciągasz plik PDF na listę
- [ ] Klikasz Konwertuj — czy plik `.md` powstaje?
- [ ] Sprawdzasz czy UI się nie "zawiesza" podczas konwersji
- [ ] Pull Request → scal

### Definicja ukończenia
✅ Okno się otwiera  
✅ Drag & drop plików działa  
✅ Konwersja nie blokuje UI (progress bar się porusza)  
✅ Log pokazuje wyniki  

---

## Etap 7 — GUI: dopracowanie
**Gałąź:** `etap-7-gui-polish`
**Czas:** ~4 godziny

### Zadania dla Claude Code
- [ ] `gui/settings_dialog.py` — okno ustawień (Ctrl+,):
  - klucze API (edytowalne pola, maskowane, przycisk "Testuj klucz")
  - domyślny silnik
  - domyślny folder output
  - domyślny język OCR
  - zapis do `config.toml` przez `core/config` (to samo źródło co CLI — bez osobnego QSettings)
- [ ] Tooltip dla niedostępnych silników: "Jak zainstalować?" z linkiem do dokumentacji
- [ ] Przycisk "Otwórz folder wynikowy" po zakończeniu konwersji
- [ ] Podgląd wygenerowanego Markdown (osobna zakładka lub panel)
- [ ] Menu aplikacji: Plik → Otwórz, Ustawienia, O programie
- [ ] Ikona aplikacji (wygenerowana, SVG)
- [ ] Obsługa `--file` argumentu z CLI (otwieranie GUI z plikiem)
- [ ] (Jeśli Pandoc dostępny) przycisk "Eksportuj do EPUB"

### Co robisz Ty
- [ ] Testujesz ustawienia — czy klucze API się zapisują?
- [ ] Sprawdzasz podgląd Markdown
- [ ] Testujesz eksport do EPUB (jeśli masz Pandoc)
- [ ] Pull Request → scal

### Definicja ukończenia
✅ Ustawienia zapisują się między uruchomieniami  
✅ Podgląd Markdown działa  
✅ Tooltip dla niedostępnych silników  
✅ Eksport EPUB działa (jeśli Pandoc zainstalowany)  

---

## Etap 8 — Docling (core) + silniki opcjonalne
**Gałąź:** `etap-8-engines`
**Czas:** ~4 godziny

### Cel
Dodanie **Docling** jako trzeciego silnika rdzeniowego (stabilnego, do v1.0), oraz **MinerU i pdf-craft** jako silników opcjonalnych (best-effort, bardziej ryzykownych instalacyjnie). Kolejność celowa: najpierw domknij Docling (pewny, MIT, dobre Python API), dopiero potem dwa trudniejsze.

### Zadania dla Claude Code
- [ ] `engines/docling_engine.py` — wrapper przez Python API Docling (PRIORYTET — silnik core)
- [ ] `engines/mineru_engine.py` — wrapper przez subprocess CLI (opcjonalny)
- [ ] `engines/pdf_craft_engine.py` — wrapper pdf-craft (opcjonalny)
- [ ] Oznaczenie w Registry: które silniki są "core" a które "optional" (do pokazania w GUI/doctor)
- [ ] Aktualizacja Registry o nowe silniki
- [ ] Testy integracyjne (jeśli silniki zainstalowane, inaczej skip z `pytest.mark.skipif`)
- [ ] Dokumentacja "Jak zainstalować każdy silnik" w `docs/ENGINES.md`

### Co robisz Ty
- [ ] `git checkout -b etap-8-engines`
- [ ] Instalujesz Docling (core): `uv add docling`
- [ ] Opcjonalnie instalujesz pozostałe (każdy osobno, sprawdzasz czy działa):
  ```bash
  uv add docling          # ~300MB — silnik core
  uv add pdf-craft        # opcjonalny

  pip install mineru      # MinerU woli pip, sprawdź dokumentację
  ```
- [ ] Testujesz każdy silnik na `test_scan.pdf`
- [ ] Pull Request → scal

### Definicja ukończenia
✅ Każdy silnik ma `is_available()` działające poprawnie  
✅ Niedziałający silnik (niezainstalowany) jest gracefully pomijany  
✅ Testy z `skipif` przechodzą  

---

## Etap 9 — Testy i dokumentacja
**Gałąź:** `etap-9-docs`
**Czas:** ~3 godziny

### Zadania dla Claude Code
- [ ] Uzupełnienie testów do >75% coverage (`uv run pytest --cov`)
- [ ] `README.md` — pełny z:
  - screenshotami GUI
  - przykładami CLI
  - tabelką silników
  - instrukcją instalacji
- [ ] `docs/USAGE.md` — szczegóły CLI i GUI
- [ ] `docs/ENGINES.md` — instrukcje instalacji każdego silnika
- [ ] `docs/CONFIGURATION.md` — wszystkie opcje konfiguracji
- [ ] `CHANGELOG.md` — v1.0.0 release notes

### Co robisz Ty
- [ ] Robisz screenshot GUI i wgrywasz do `docs/screenshots/`
- [ ] Przeglądasz README — czy wszystko zrozumiałe?
- [ ] Testujesz instrukcje instalacji od zera (fresh install check)

### Definicja ukończenia
✅ Coverage ≥75%  
✅ README zawiera screenshot  
✅ Instrukcja instalacji działa  

---

## Etap 10 — Packaging
**Gałąź:** `etap-10-packaging`
**Czas:** ~1–2 dni (NIE 3 godziny — to jeden z najtrudniejszych etapów)

> **Realizm:** PyInstaller + PySide6 + OCR + zewnętrzne binarki (Tesseract, Poppler) + ewentualne modele to notorycznie kłopotliwa kombinacja. Nie zakładaj, że to "szybka końcówka". Strategia: **build portable bez ciężkich silników**, a silniki copyleft (Marker GPL, MinerU AGPL) i zewnętrzne binarki jako opcjonalne, instalowane osobno — to także rozwiązuje kwestię licencyjną (nie bundlujesz GPL/AGPL w jedno binary MIT).

### Zadania dla Claude Code
- [ ] `build.spec` dla PyInstaller — build **rdzeniowy**: CLI + GUI + lekkie silniki (PyMuPDF4LLM, Docling). Marker/MinerU/pdf-craft NIE wkompilowane — wykrywane jako opcjonalne, instalowane przez użytkownika.
- [ ] **`hiddenimports`** w build.spec: skoro silniki importujemy leniwie (dopiero w `convert()`), PyInstaller ich nie wykryje → `ModuleNotFoundError` przy użyciu. Dodaj jawnie pymupdf4llm, pymupdf, docling i ich podmoduły. Po buildzie przetestuj REALNĄ konwersję, nie tylko `--help`.
- [ ] **`multiprocessing.freeze_support()`** w punktach wejścia (`cli/main.py`, `gui/app.py`) pod `if __name__ == "__main__"` — biblioteki ML spawnują podprocesy, bez tego skompilowany `.exe` na Windows może wpaść w pętlę nieskończoną.
- [ ] `scripts/build_linux.sh` — buduje AppImage lub `.tar.gz`
- [ ] `scripts/build_windows.ps1` — buduje `.exe`. Tesseract/Poppler/Pandoc **nie bundlowane** — zamiast tego `pdf2md doctor` wykrywa ich brak i podaje instrukcję instalacji.
- [ ] `.github/workflows/release.yml`: tag `v*` → build Linux i Windows → GitHub Release
- [ ] Sekcja w README: "Instalacja Tesseract/Poppler/Pandoc na Windows" (zamiast koniecznego bundlowania)
- [ ] `docs/RELEASE.md` — checklist wydania

### Co robisz Ty
- [ ] `git tag v1.0.0 && git push origin v1.0.0`
- [ ] Obserwujesz GitHub Actions jak buduje release
- [ ] Pobierasz binary i testujesz na czystym systemie (Windows bez Pythona)
- [ ] Sprawdzasz że `pdf2md doctor` poprawnie podpowiada brakujące zależności

### Definicja ukończenia
✅ `pdf2md` i `pdf2md-gui` działają bez instalacji Pythona (rdzeniowe silniki)  
✅ Brakujące zależności/silniki są wykrywane z czytelną instrukcją instalacji  
✅ Build MIT nie zawiera wkompilowanych silników GPL/AGPL  
✅ GitHub Release zawiera pliki do pobrania  

---
---

# FAZA 2 — Premium Scan Pipeline (lokalny VLM-OCR)

> **Warunek wstępny:** ukończona Faza 1 (v1.0). Ta faza wymaga GPU (zoptymalizowana pod RTX 5090 Laptop 24 GB).
>
> **Cel fazy:** dedykowany tryb do skanowanych książek, który nie robi konwersji "jednym strzałem", tylko prowadzi dokument przez kontrolowany pipeline: PDF → obrazy → preprocessing → layout/OCR (VLM) → korekta LLM per-strona → walidacja jakości → składanie rozdziałów → Markdown/EPUB. Każdy etap pośredni jest zapisywany na dysk, co pozwala kontrolować błędy strona po stronie.
>
> **Architektura:** cały pipeline jest opakowany jako jeden silnik `ScanPipelineEngine` implementujący istniejący interfejs `ConversionEngine` z Fazy 1 — czyli pojawia się w GUI i CLI obok pozostałych silników, ale wewnątrz uruchamia wieloetapowy proces.

### Struktura robocza (work dir)
```
work/
├── pages_png/        # PDF rozbity na obrazy stron
├── preprocessed/     # po deskew/denoise/dewarp/crop
├── ocr_json/         # surowy wynik VLM-OCR (per strona)
├── md_pages/         # Markdown per strona
├── md_pages_clean/   # po korekcie LLM
├── md_chapters/      # złożone rozdziały
└── logs/             # raport jakości, lista trudnych stron
output/
├── book.md
├── book.epub
└── report.html
```

---

## Etap 11 — Preprocessing obrazu
**Gałąź:** `etap-11-preprocessing`
**Czas:** ~4 godziny

### Cel
Rozbicie PDF na obrazy stron i ich obróbka przed OCR. Tu nie ma żadnego LLM — to klasyczne przetwarzanie obrazu.

### Zadania dla Claude Code
- [ ] Nowy pakiet `src/pdf2md/scan/` z modułem `preprocessing.py`
- [ ] `pdf_to_images(pdf_path, dpi, output_dir)` — rozbicie PDF na PNG (pymupdf lub pdftoppm)
- [ ] **`iter_page_batches(pdf_path, dpi, batch_size=20)`** — przetwarzanie STRUMIENIOWE: renderuj strony paczkami, oddawaj do przetworzenia, usuwaj PNG paczki przed następną (500 stron @600 DPI to 15–25 GB — bez tego dysk pada)
- [ ] `cleanup_work_dir(work_dir)` — czyszczenie katalogu roboczego
- [ ] Profile DPI: 300 (standard), 400 (stare książki, mała czcionka), 600 (bardzo trudne skany)
- [ ] Operacje OpenCV: `deskew()`, `denoise()`, `dewarp()`, `crop_margins()`, `normalize_contrast()`
- [ ] `preprocess_page(image, operations: list) -> image` — konfigurowalny pipeline
- [ ] Detekcja "dwie strony na jednym skanie" i opcjonalny split
- [ ] Testy na `tests/fixtures/test_scan.pdf` (w tym test paczkowania)

### Co robisz Ty
- [ ] `git checkout -b etap-11-preprocessing`
- [ ] `sudo apt install poppler-utils imagemagick` (jeśli jeszcze nie masz)
- [ ] Wgrywasz skan książki do `tests/fixtures/` (np. `test_book_scan.pdf`, kilka stron)
- [ ] Sprawdzasz wizualnie wynik preprocessingu (obrazy w `work/preprocessed/`)
- [ ] Pull Request → scal

### Definicja ukończenia
✅ PDF rozbijany na obrazy w wybranym DPI  
✅ Przetwarzanie paczkowe nie trzyma wszystkich stron naraz (kontrola dysku)  
✅ deskew + crop + denoise dają wizualnie lepszy obraz  
✅ Testy przechodzą  

---

## Etap 12 — Silniki VLM-OCR
**Gałąź:** `etap-12-vlm-ocr`
**Czas:** ~6 godzin

### Cel
Trzy silniki OCR oparte na modelach wizyjno-językowych, jako adaptery `ConversionEngine`. To serce jakości w Fazie 2.

### Zadania dla Claude Code
- [ ] `engines/olmocr_engine.py` — adapter olmOCR (model olmOCR-2-7B-FP8, flaga `--markdown`, uruchomienie przez vLLM lub serwer lokalny)
- [ ] `engines/paddleocr_vl_engine.py` — adapter PaddleOCR-VL
- [ ] `engines/surya_engine.py` — adapter Surya (layout + OCR + reading order)
- [ ] Wspólna baza `engines/vlm_base.py` z detekcją GPU (`torch.cuda.is_available()`) i ostrzeżeniem gdy brak GPU
- [ ] **Zarządzanie VRAM**: metody `load_model()` / `unload_model()`. `unload_model()` realnie zwalnia pamięć (usuń referencje, `gc.collect()`, `torch.cuda.empty_cache()`; vLLM → zamknij proces). Konieczne, bo olmOCR (~7-8 GB) i model korekty qwen2.5:14b (~9-10 GB) NIE zmieszczą się naraz w 24 GB.
- [ ] Każdy silnik: `is_available()` przez `importlib.metadata.version()` + `has_gpu()` (BEZ importu modelu), `requires_gpu = True`
- [ ] Output per strona do `work/ocr_json/` i `work/md_pages/`, przetwarzanie paczkowe (iter_page_batches)
- [ ] Aktualizacja Registry
- [ ] Testy z `skipif` gdy brak GPU lub silnika

### Co robisz Ty
- [ ] `git checkout -b etap-12-vlm-ocr`
- [ ] Instalacja w czystym środowisku (olmOCR wymaga osobnego env — sprawdź dokumentację):
  ```bash
  # olmOCR — najlepiej osobne środowisko conda/uv, wymaga CUDA
  # Pobiera model 7B przy pierwszym uruchomieniu
  ```
- [ ] Sprawdzasz że GPU jest wykrywane (`nvidia-smi`, `torch.cuda.is_available()`)
- [ ] Testujesz olmOCR na 2-3 stronach skanu — porównujesz z Markerem z Fazy 1
- [ ] Po teście sprawdzasz `nvidia-smi` — czy `unload_model()` faktycznie zwolnił VRAM
- [ ] Pull Request → scal

### Definicja ukończenia
✅ olmOCR konwertuje skan strony do Markdown na GPU  
✅ `unload_model()` realnie zwalnia VRAM (widoczne w nvidia-smi)  
✅ `is_available()` zwraca False (bez błędu) gdy brak GPU lub modelu  
✅ Co najmniej jeden silnik VLM działa end-to-end  

---

## Etap 13 — Korekta LLM per-strona + walidacja jakości
**Gałąź:** `etap-13-correction-validation`
**Czas:** ~6 godzin

### Cel
Korekta wyniku OCR lokalnym LLM (konserwatywnie, bez parafrazy) oraz automatyczna detekcja stron o niskiej jakości i ich ponowny przebieg.

### Zadania dla Claude Code
- [ ] `scan/correction.py` — korekta per-strona przez `LLMProvider` z Fazy 1 (preferowany Ollama + Qwen 14B Q4/Q5)
- [ ] **Sekwencja VRAM**: korekta startuje DOPIERO po `unload_model()` silnika VLM (Etap 12) — oba modele nigdy naraz w pamięci. Dla Ollamy po korekcie wyślij `keep_alive=0` (wyładowanie modelu, domyślnie trzymany 5 min). Guard: zaloguj wolne VRAM przed startem korekty.
- [ ] Konserwatywny prompt korekcyjny w `core/prompts.py` jako `SCAN_CORRECTION_PROMPT`:
  ```
  Jesteś korektorem OCR. Popraw wyłącznie oczywiste błędy rozpoznawania tekstu.
  Nie parafrazuj. Nie skracaj. Nie dopisuj informacji, których nie ma.
  Zachowaj oryginalną składnię, interpunkcję, styl i akapity.
  Połącz wyrazy przeniesione przez podział wiersza, jeśli to oczywiste.
  Usuń numery stron, nagłówki i stopki tylko gdy są ewidentnie metadanymi strony.
  Fragmenty niepewne oznacz jako [nieczytelne].
  Przypisy oznacz jako Markdown footnotes.
  Nie modernizuj pisowni, nie zamieniaj archaizmów, nie tłumacz, nie streszczaj.
  Zwróć wynik jako czysty Markdown.
  ```
- [ ] `scan/validation.py` — heurystyki jakości:
  - liczba znaków na stronie, wykrycie pustych stron, nagłe spadki liczby znaków
  - liczba znaków � i `[nieczytelne]`
  - podejrzane ciągi (rn↔m, l↔I, 0↔O)
  - porównanie dwóch silników OCR (jeśli włączone)
- [ ] `should_rerun_page(quality_score, threshold) -> bool`
- [ ] Logika ponownego przebiegu trudnych stron dokładniejszym silnikiem/DPI
- [ ] Testy z mockowanym LLM + przykładowe "brudne" strony

### Co robisz Ty
- [ ] `git checkout -b etap-13-correction-validation`
- [ ] (Jeśli używasz lokalnego LLM) `ollama pull qwen2.5:14b` lub odpowiednik
- [ ] Testujesz korektę na surowym OCR z Etapu 12 — sprawdzasz że LLM NIE parafrazuje
- [ ] Sprawdzasz raport walidacji (które strony oznaczone jako trudne)
- [ ] Pull Request → scal

### Definicja ukończenia
✅ Korekta LLM poprawia OCR bez zmiany treści  
✅ Walidacja wykrywa strony o niskiej jakości  
✅ Trudne strony są ponawiane automatycznie  

---

## Etap 14 — Składanie książki + eksport EPUB
**Gałąź:** `etap-14-book-assembly`
**Czas:** ~5 godzin

### Cel
Złożenie poprawionych stron w spójną książkę i eksport do Markdown + EPUB z raportem jakości.

### Zadania dla Claude Code
- [ ] `scan/assembly.py`:
  - usuwanie powtarzalnych nagłówków/stopek
  - łączenie akapitów między stronami
  - naprawa dzielenia wyrazów (hyphenation)
  - detekcja rozdziałów → struktura `md_chapters/`
  - normalizacja cudzysłowów i myślników
  - zachowanie kursywy/pogrubień jeśli OCR je wykrył
  - budowa spisu treści (TOC)
- [ ] `scan/export.py`:
  - `book.md` (scalony)
  - EPUB przez `ebooklib` (lepsza kontrola) lub Pandoc jako fallback
  - `report.html` — raport jakości z miniaturami trudnych stron
- [ ] LLM może działać rozdziałami (nie całą książką naraz)
- [ ] `engines/scan_pipeline_engine.py` — `ScanPipelineEngine` wymuszający sekwencję: preprocessing → OCR (VLM) → unload VLM → korekta → walidacja → składanie → eksport. Po UDANYM buildzie EPUB automatyczne czyszczenie `work/` (flaga `--keep-work` do debugowania).
- [ ] Testy końcowe: skan kilkustronicowy → poprawny EPUB (walidacja struktury); test czyszczenia work/

### Co robisz Ty
- [ ] `git checkout -b etap-14-book-assembly`
- [ ] Uruchamiasz pełny pipeline na skanie testowym (kilka–kilkanaście stron)
- [ ] Otwierasz wynikowy EPUB w czytniku (Calibre, Foliate)
- [ ] Sprawdzasz `report.html` — czy trudne strony są oznaczone
- [ ] Pull Request → scal

### Definicja ukończenia
✅ Strony łączą się w spójny `book.md` z rozdziałami  
✅ EPUB otwiera się poprawnie w czytniku  
✅ Raport HTML pokazuje jakość konwersji  

---

## Etap 15 — Profile skanowania (fast / balanced / premium)
**Gałąź:** `etap-15-scan-profiles`
**Czas:** ~3 godziny

### Cel
Trzy gotowe profile konfiguracji całego pipeline'u, dostępne z CLI i GUI.

### Profile (pliki YAML w `profiles/`)
- **fast** — DPI 300, deskew, PaddleOCR/Tesseract, korekta Qwen 14B, bez dewarp. Do beletrystyki i dobrych skanów.
- **balanced** (domyślny) — DPI 400, deskew+denoise+dewarp auto, Surya/PaddleOCR-VL, korekta Qwen 14B, walidacja. Do książek popularnonaukowych, przypisów, tabel.
- **premium** — DPI 400, pełny preprocessing, olmOCR + Surya jako kontrola, porównanie wyników, korekta konserwatywna page→chapter, rerun trudnych stron, raport HTML. Do trudnych i starych skanów.

### Zadania dla Claude Code
- [ ] `profiles/fast.yaml`, `balanced.yaml`, `premium.yaml` (struktura jak w notatkach źródłowych)
- [ ] `scan/profiles.py` — ładowanie i walidacja profilu (pydantic)
- [ ] CLI: `pdf2md scan plik.pdf --profile premium`
- [ ] GUI: dropdown wyboru profilu w trybie skanowania
- [ ] Możliwość zapisania własnego profilu przez użytkownika
- [ ] Dokumentacja `docs/SCAN_PROFILES.md`

### Co robisz Ty
- [ ] `git checkout -b etap-15-scan-profiles`
- [ ] Testujesz każdy profil na tym samym skanie — porównujesz jakość i czas
- [ ] Dostrajasz domyślny profil do swoich typowych dokumentów
- [ ] Pull Request → scal

### Definicja ukończenia
✅ `pdf2md scan plik.pdf --profile premium` działa end-to-end  
✅ Trzy profile dają różny kompromis jakość/szybkość  
✅ GUI pozwala wybrać profil  

---

## Definicja "Done" dla Fazy 2

- [ ] Pełny pipeline skan → EPUB działa z profilem premium
- [ ] olmOCR (lub inny VLM) działa lokalnie na GPU
- [ ] Korekta LLM nie zmienia treści (tylko poprawia OCR)
- [ ] Walidacja wykrywa i ponawia trudne strony
- [ ] Trzy profile dostępne z CLI i GUI
- [ ] Raport jakości HTML generowany dla każdej konwersji

---

## Workflow Git dla każdego etapu

```bash
# Przed etapem
git checkout main
git pull
git checkout -b etap-N-nazwa

# Praca z Claude Code...

# Po etapie
uv run pytest          # musi być zielone
uv run ruff check .    # zero błędów
git add -A
git commit -m "Etap N: Krótki opis"
git push origin etap-N-nazwa

# Na GitHub: New Pull Request → przejrzyj diff → Merge
git checkout main
git pull
```

---

## Definicja "Done" dla v1.0

- [ ] `pdf2md convert plik.pdf` działa z przynajmniej 2 silnikami
- [ ] GUI otwiera się, konwertuje plik, zapisuje wynik
- [ ] LLM post-processing działa z przynajmniej 1 dostawcą
- [ ] Testy: ≥75% coverage, wszystkie zielone
- [ ] README jest kompletne z przykładami
- [ ] GitHub Release zawiera binary do pobrania
