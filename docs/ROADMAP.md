# pdf2md Squeezer — Roadmap

> Każdy etap = jedna gałąź git (branch) = jeden Pull Request

---

## Szybki przegląd

```
STATUS (czerwiec 2026): Faza 1 (v1.0) i Faza 2 — UKOŃCZONE.
Działa: Marker (wszystkie strony, GPU), Surya (GPU), PaddleOCR-VL, pipeline skanów,
korekta LLM, anulowanie + zwalnianie VRAM, natywny Windows z CUDA (torch cu130).
olmOCR-2-7B FP8 — adapter gotowy, silnik ZAPARKOWANY (ekonomia VRAM 24 GB; szczegóły w Etapie 12).

FAZA 1 — v1.0 (orkiestrator gotowych silników)            [UKOŃCZONA]
Etap 0  Init projektu          █████  ~2h
Etap 1  Rdzeń i abstrakcje     █████  ~3h
Etap 2  PyMuPDF4LLM engine     █████  ~2h
Etap 3  Marker engine          █████  ~3h
Etap 4  Dostawcy LLM           █████  ~3h
Etap 5  CLI + doctor + dry-run █████  ~4h
Etap 6  GUI — szkielet         █████  ~4h
Etap 7  GUI — polish           █████  ~4h
Etap 8  Docling (core) + opc. MinerU       █████  ~4h
Etap 9  Testy + dokumentacja   █████  ~3h
Etap 10 Dystrybucja (pakiet pip/uv)  █████  ~3h
────────────────────────────────────────────
Faza 1 łącznie                       ~35h + packaging

FAZA 2 — premium scan pipeline (lokalny VLM-OCR, wymaga GPU)  [UKOŃCZONA]
Etap 11 Preprocessing obrazu   █████  ~4h
Etap 12 Silniki VLM-OCR        █████  ~6h   (Surya, PaddleOCR-VL; olmOCR zaparkowany)
Etap 13 Korekta LLM + walidacja █████  ~6h
Etap 14 Składanie książki + EPUB █████  ~5h
Etap 15 Profile skanowania     █████  ~3h
────────────────────────────────────────────
Faza 2 łącznie                       ~24h robocze
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
✅ Struktura katalogów zgodna z PROJEKT.md  

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

> **⚠️ Marker potrafi zawiesić WSL.** Domyślnie spawnuje workery = liczba rdzeni CPU, każdy ładuje modele → wyczerpanie RAM/VRAM → zawieszenie całej maszyny wirtualnej (i śmierć serwera VS Code). Na słabszym sprzęcie (≤16 GB RAM / ≤8 GB VRAM) to się dzieje natychmiast. Dlatego: dławienie równoległości od początku, jednostronicowy fixture, testy `heavy` wyłączone z domyślnego `pytest`, pre-download modeli. Wymaga też `.wslconfig` (zob. PROJEKT.md, KROK 6b).

### Zadania dla Claude Code
- [ ] `engines/marker_engine.py`:
  - `is_available()`: `importlib.metadata.version("marker-pdf")` (bez importu marker)
  - `convert(pdf_path, use_llm=False, llm_provider=None, lang="pl,en")`: wywołuje Marker API
  - **dławienie zasobów (konfigurowalne, domyślnie niskie)**: `disable_multiprocessing=True`, `pdftext_workers=1`, respektowanie `TORCH_DEVICE`; limity z `config.toml` (marker_workers, marker_device, marker_max_pages)
  - obsługa parametru `use_llm` (przekazuje do Marker, jeśli `llm_provider` to Gemini/Ollama)
  - obsługa błędów, logowanie, raportowanie liczby stron
- [ ] `tests/conftest.py`: ustaw `PDFTEXT_WORKERS=1` i `TORCH_DEVICE` PRZED importem marker
- [ ] Aktualizacja Registry
- [ ] Testy integracyjne oznaczone `@pytest.mark.heavy`, na **jednostronicowym** `test_text_1page.pdf` (NIE na wielostronicowych skanach)
- [ ] W `pyproject.toml`: marker `heavy` + `addopts = "-m 'not heavy'"`
- [ ] Aktualizacja `scripts/test_convert.py` — flaga `--engine marker`

### Co robisz Ty
- [ ] `git checkout -b etap-3-marker`
- [ ] Upewnij się, że masz `.wslconfig` z limitami RAM/swap/procesorów (KROK 6b w PROJEKT.md) i `wsl --shutdown`
- [ ] `uv add marker-pdf` (długa instalacja — Marker ma dużo zależności)
- [ ] `uv add "transformers>=4.48,<5"` — wymagane przez surya (Marker); zapobiega też cofnięciu transformers przez Docling do 4.47.x (objaw: `ImportError: cannot import name 'ALL_ATTENTION_FUNCTIONS'`). Zob. macierz zgodności w PROJEKT.md.
- [ ] Tworzysz jednostronicowy fixture: `test_text_1page.pdf`
- [ ] NAJPIERW pobierasz modele poza pytestem: `marker_single tests/fixtures/test_text_1page.pdf --output_dir /tmp/mk`
- [ ] `uv run pytest` (pomija heavy — powinno być szybkie i bezpieczne)
- [ ] Dopiero świadomie, z monitorowaniem w 2. terminalu (`watch -n1 free -h`, `nvidia-smi -l 1`): `uv run pytest -m heavy`
- [ ] Pull Request → scal

### Definicja ukończenia
✅ Marker konwertuje 1-stronicowy PDF bez zawieszania WSL  
✅ Multiprocessing wyłączony domyślnie, workery konfigurowalne  
✅ Testy `heavy` wyłączone z domyślnego `pytest`, uruchamiane świadomie  
✅ Parametr `use_llm` działa bez błędu (graceful skip gdy LLM nie skonfigurowany)  

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
- [ ] (Opcjonalne) Instalacja Ollama: https://ollama.com/download → `ollama pull qwen3:14b`
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
- [ ] Opcjonalnie instalujesz pozostałe:
  ```bash
  uv add docling          # ~300MB — silnik core (importowany w procesie)
  uv add pdf-craft        # opcjonalny (importowany w procesie)

  # MinerU NIE przez pip! Wymaga pillow>=11, a Marker przypina pillow<11 → konflikt.
  # Instaluj izolowanie (osobne środowisko, komenda CLI na PATH):
  uv tool install mineru --with mineru[all]
  mineru --help           # weryfikacja (CLI nazywa się "mineru", nie "magic-pdf")
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

## Etap 10 — Dystrybucja jako pakiet (pip/uv)
**Gałąź:** `etap-10-packaging`
**Czas:** ~3 godziny

> **Decyzja dystrybucyjna.** Główny kanał wydania v1.0 to **pakiet Python (pip/uv)**, nie frozen binary. Powody:
> 1. **Licencja.** Publikujesz wyłącznie swój kod MIT. Silniki copyleft (PyMuPDF4LLM — AGPL, Marker — GPL, MinerU — AGPL) instaluje sam użytkownik u siebie — to nie jest dystrybucja tych pakietów przez Ciebie, więc Twój pakiet pozostaje czysto MIT.
> 2. **Elastyczność.** Użytkownik dokłada tylko te silniki, których chce: `uv pip install pymupdf4llm` itd. Orkiestrator importuje to, co jest zainstalowane.
> 3. **Frozen binary nie przyjmuje silników po fakcie.** Zamrożona binarka PyInstallera ma site-packages wbudowane na sztywno — nie da się do niej doinstalować silnika importowanego (PyMuPDF4LLM, Docling). Dlatego binarka ma sens dopiero, gdy bundluje **własny silnik MIT** (Faza 2, F02). Do tego czasu „goła" binarka byłaby prawie bezużyteczna.
>
> Frozen binary (PyInstaller) → przeniesiony do zadań **po Fazie 2** (sekcja niżej). Praca z `build.spec` z wcześniejszych prób nie idzie do kosza — zostaje na ten moment.

### Zadania dla Claude Code
- [ ] `pyproject.toml` gotowy do publikacji: metadane (autor, opis, URL, klasyfikatory, `license = MIT`), entry points (`pdf2md`, `pdf2md-gui`), opcjonalne extra: `engines-core` (z pinem `transformers>=4.48,<5` — wspólny mianownik Marker/Docling, zob. PROJEKT macierz zgodności), `engines-optional`, `llm`
- [ ] Weryfikacja, że pakiet buduje się czysto: `uv build` → wheel + sdist w `dist/`
- [ ] `docs/INSTALL.md` — instalacja: `uv tool install pdf2md` (sam orkiestrator), potem dokładanie silników (`uv pip install pymupdf4llm` / `docling` / `marker-pdf`) i LLM (`anthropic` / `openai` / `google-genai`), oraz silniki CLI (`uv tool install mineru --with mineru[all]`)
- [ ] `.github/workflows/release.yml`: na tag `v*` → `uv build` → GitHub Release z wheel + sdist (opcjonalnie publish na PyPI)
- [ ] README: sekcja instalacji + tabela „który silnik czym doinstalować"; `pdf2md doctor` jako narzędzie do wykrycia, czego brakuje
- [ ] `docs/RELEASE.md` — checklist wydania pakietu

### Co robisz Ty
- [ ] `git checkout -b etap-10-packaging`
- [ ] `uv build` — sprawdzasz, że powstają wheel + sdist
- [ ] Test w czystym środowisku: `uv tool install dist/pdf2md-*.whl` → `pdf2md doctor` (silniki jako „niedostępne, zainstaluj przez ...")
- [ ] Dokładasz jeden silnik: `uv pip install pymupdf4llm` → `pdf2md convert plik.pdf` działa
- [ ] `git tag v1.0.0 && git push origin v1.0.0` → obserwujesz release na GitHub
- [ ] Pull Request → scal

### Definicja ukończenia
✅ `uv build` produkuje wheel + sdist (czysto MIT, bez wbudowanych silników)  
✅ `uv tool install` daje działający orkiestrator; silniki dokładane przez pip/uv  
✅ `pdf2md doctor` podpowiada, czego brakuje i jak to zainstalować  
✅ GitHub Release zawiera pakiet do pobrania  

---

## Etap 10b — Frozen binary (PyInstaller) — PO FAZIE 2
**Gałąź:** `etap-10b-frozen-binary` (realizować dopiero po ukończeniu Fazy 2)
**Czas:** ~1–2 dni (trudny)

> **Warunek:** ukończony własny silnik z F02 (pdfplumber + pdfminer.six + Tesseract — wszystko permisywne: MIT/Apache/BSD). Dopiero wtedy frozen binary ma sens: bundluje **wyłącznie własny silnik MIT**, działa samodzielnie bez instalacji Pythona, a jego dystrybucja jest licencyjnie czysta. PyMuPDF4LLM/Docling/Marker/MinerU pozostają opcjonalne (pip/CLI), NIE wkompilowane.

### Zadania dla Claude Code (gdy nadejdzie czas)
- [ ] `build.spec` (PyInstaller): CLI + GUI + **tylko własny silnik MIT** i jego permisywne zależności. ŻADNYCH silników copyleft (PyMuPDF4LLM/Marker/MinerU) ani VLM w bundlu.
- [ ] **CPU-only torch** jeśli własny silnik użyje torcha (inaczej CArchive >4 GiB → `struct.error`); wymuś `torch+cpu`, odinstaluj `nvidia-*`/`triton` przed buildem; w skrypcie assert „brak nvidia-*"
- [ ] `hiddenimports` dla leniwie importowanych modułów; `copy_metadata()` dla pakietów, których `is_available()` używa `importlib.metadata`
- [ ] `multiprocessing.freeze_support()` w punktach wejścia (`cli/main.py`, `gui/app.py`)
- [ ] PySide6: NIE `collect_data_files/dynamic_libs` całości — tylko standardowe hooki dla importowanych `QtWidgets/QtGui/QtCore`
- [ ] `scripts/build_linux.sh`, `scripts/build_windows.ps1` (Windows: Tesseract/Poppler nie bundlowane, `pdf2md doctor` wskazuje instalację)
- [ ] **Realny test GUI** (nie tylko `--help`): `xvfb-run ./dist/pdf2md-gui` lub na maszynie z ekranem — weryfikacja pluginu platformy Qt
- [ ] `.github/workflows/release-binary.yml`: build Linux + Windows na tag

### Definicja ukończenia
✅ Binarka działa bez instalacji Pythona, używając własnego silnika MIT  
✅ Binarka NIE zawiera kodu copyleft (czysta dystrybucja MIT)  
✅ GUI realnie się uruchamia z frozen binary (przetestowane z sesją graficzną)  
✅ Brakujące zewnętrzne narzędzia/silniki wykrywane z instrukcją instalacji  


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
Cztery silniki OCR oparte na modelach wizyjno-językowych, jako adaptery `ConversionEngine`. To serce jakości w Fazie 2. **Dwie kategorie** (wynik debugowania zależności w praktyce): Surya działa **in-process** w głównym venv (torch, transformers≥4.48, zgodny z Markerem), a olmOCR i PaddleOCR-VL są **izolowane** (osobne środowiska, wołane przez subprocess/HTTP) — bo ich stosy (vLLM / PaddlePaddle) konfliktują z projektem.

### Zadania dla Claude Code
- [ ] `engines/vlm_base.py` — baza z `has_gpu()`; rozdziel na `InProcessVLMEngine` i `ExternalVLMEngine` (subprocess/usługa), bo logika is_available()/load/unload się różni
- [ ] `engines/surya_engine.py` — **in-process** (główny venv); zrób jako pierwszy, domyka „≥1 silnik VLM działa"
- [ ] `engines/olmocr_engine.py` — **izolowany subprocess**: osobny venv (`~/.venvs/olmocr`), ścieżka do jego pythona w configu, uruchomienie przez `python -m olmocr.pipeline` z env `VLLM_USE_FLASHINFER_SAMPLER=0`
- [ ] `engines/paddleocr_vl_engine.py` — **izolowana usługa HTTP**: model chodzi jako `paddleocr genai_server --backend vllm`, adapter rozmawia po HTTP (API OpenAI, jak Ollama) lub przez `paddleocr doc_parser`; config: `paddleocr_vl_url`
- [ ] **Zarządzanie VRAM**: `load_model()`/`unload_model()`. In-process (Surya) → `gc.collect()`+`torch.cuda.empty_cache()`. Izolowane (olmOCR/PaddleOCR-VL) → **unload = zamknięcie procesu/serwera** (VRAM zwalnia OS; prościej i pewniej). olmOCR (~7-8 GB) i qwen3:14b (~9-10 GB) NIE zmieszczą się naraz w 24 GB
- [ ] Każdy silnik: `requires_gpu = True`; `is_available()` bez importu modelu (in-process → `importlib.metadata.version()`+`has_gpu()`; izolowany → obecność venv/usługi+`has_gpu()`)
- [ ] Output per strona do `work/ocr_json/` i `work/md_pages/`, przetwarzanie paczkowe (iter_page_batches)
- [ ] Aktualizacja Registry
- [ ] Testy z `skipif` gdy brak GPU lub silnika/środowiska

### Co robisz Ty
- [ ] `git checkout -b etap-12-vlm-ocr`
- [ ] **Instalacja zewnętrznych silników wg `INSTALL.md`** (Surya w głównym venv; olmOCR i PaddleOCR-VL w osobnych środowiskach; PaddleOCR-VL na Blackwellu → vLLM nightly cu129 + prekompilowany flash-attn)
- [ ] Sprawdzasz że GPU jest wykrywane (`nvidia-smi`, `torch.cuda.is_available()`)
- [ ] Testujesz każdy silnik na 2-3 stronach skanu — porównujesz z Markerem z Fazy 1
- [ ] Po teście sprawdzasz `nvidia-smi` — czy `unload_model()` (kill procesu) faktycznie zwolnił VRAM
- [ ] Pull Request → scal

### Definicja ukończenia — ✅ DOMKNIĘTE (czerwiec 2026)
✅ Co najmniej jeden silnik VLM-OCR działa end-to-end: **MinerU/vlm** (zarejestrowany, zielony w `doctor`) + **PaddleOCR-VL** (potwierdzony na RTX 5090 — serwer + OCR dobrej jakości na realnym skanie)  
✅ `is_available()` zwraca False bez błędu, gdy silnik/serwer niedostępny — dla PaddleOCR-VL **pinguje serwer** pod `paddleocr_vl_url` (PROMPT D9), nie importuje `paddle`  
✅ VRAM dla izolowanych silników zwalnia się przez zatrzymanie procesu/serwera (`pkill -f "vllm serve"`, widoczne w `nvidia-smi`)  
✅ **Surya — DZIAŁA in-process.** marker-pdf 1.10.x pinuje `surya-ocr 0.17.x` (predyktory: `DetectionPredictor`/`FoundationPredictor`/`RecognitionPredictor`), więc adapter `surya_engine.py` w głównym venv działa — **potwierdzone konwersją realnego skanu** (czerwiec 2026). NIE jest redundantna z Markerem (różne ścieżki: Surya = detekcja + OCR per-strona; Marker = layout + OCR + struktura).  

> **KOREKTA (czerwiec 2026): Surya NIE jest odłożona — działa.** Wcześniejszy wniosek „Surya
> zablokowana na 0.6.x i redundantna z Markerem" był **błędny** — wynikał z **cichego downgrade'u
> marker-pdf do 0.3.10** (resolver cofał nieprzypiętego markera; 0.3.10 to stare API + pin
> `surya-ocr 0.6.x`). Po przypięciu `marker-pdf>=1.10,<2` instaluje się `surya-ocr 0.17.x`
> (predyktorowe API — dokładnie to, pod które pisany był adapter) i Surya konwertuje. **Wniosek
> operacyjny:** marker-pdf MUSI być przypięty do 1.x — bez pinu resolver wybiera 0.3.10 (objaw:
> `ModuleNotFoundError: No module named 'marker.config'`). Etap 12 domknięty na MinerU/vlm +
> PaddleOCR-VL + **Surya**. PaddleOCR-VL: przepis pod Blackwella w PROJEKT.md; `is_available()`
> pinguje serwer (PROMPT D9). Następny etap: **13 — korekta LLM per-strona + sekwencja VRAM**
> (kill serwera VLM → załaduj qwen3 → koryguj).

---

## Etap 13 — Korekta LLM per-strona + walidacja jakości
**Gałąź:** `etap-13-correction-validation`
**Czas:** ~6 godzin

### Cel
Korekta wyniku OCR lokalnym LLM (konserwatywnie, bez parafrazy) oraz automatyczna detekcja stron o niskiej jakości i ich ponowny przebieg.

### Zadania dla Claude Code
- [ ] `scan/correction.py` — korekta per-strona przez `LLMProvider` z Fazy 1 (preferowany Ollama + Qwen3 14B Q4/Q5)
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
- [ ] (Jeśli używasz lokalnego LLM) `ollama pull qwen3:14b` lub odpowiednik
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
- **fast** — DPI 300, deskew, PaddleOCR/Tesseract, korekta Qwen3 14B, bez dewarp. Do beletrystyki i dobrych skanów.
- **balanced** (domyślny) — DPI 400, deskew+denoise+dewarp auto, Surya/PaddleOCR-VL, korekta Qwen3 14B, walidacja. Do książek popularnonaukowych, przypisów, tabel.
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
- [ ] GitHub Release zawiera pakiet (wheel + sdist) do pobrania; `uv tool install` działa
