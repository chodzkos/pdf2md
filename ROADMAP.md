# pdf2md — Roadmap

> Każdy etap = jedna gałąź git (branch) = jeden Pull Request

---

## Szybki przegląd

```
Etap 0  Init projektu          ░░░░░  ~2h
Etap 1  Rdzeń i abstrakcje     ░░░░░  ~3h
Etap 2  PyMuPDF4LLM engine     ░░░░░  ~2h
Etap 3  Marker engine          ░░░░░  ~3h
Etap 4  Dostawcy LLM           ░░░░░  ~3h
Etap 5  CLI                    ░░░░░  ~3h
Etap 6  GUI — szkielet         ░░░░░  ~4h
Etap 7  GUI — polish           ░░░░░  ~4h
Etap 8  Silniki: MinerU, Docling, pdf-craft  ░░░░░  ~4h
Etap 9  Testy + dokumentacja   ░░░░░  ~3h
Etap 10 Packaging              ░░░░░  ~3h
────────────────────────────────────────────
Łącznie                              ~34h robocze
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
✅ Struktura katalogów zgodna z PROJEKT.md  

---

## Etap 1 — Rdzeń i abstrakcje
**Gałąź:** `etap-1-core`
**Czas:** ~3 godziny

### Cel
Wspólny interfejs dla wszystkich silników i dostawców LLM. To fundament — wszystko inne zależy od tego etapu.

### Zadania dla Claude Code
- [ ] `engines/base.py` — dataclass `ConversionResult`, ABC `ConversionEngine`
- [ ] `llm/base.py` — dataclass `LLMResult`, ABC `LLMProvider`
- [ ] `core/config.py` — `pydantic-settings` model konfiguracji (klucze API, domyślny silnik, domyślny LLM, ścieżka output)
- [ ] `core/registry.py` — `EngineRegistry` i `LLMRegistry` z metodą `get_available()`
- [ ] `core/converter.py` — `Converter` orkiestrator: `convert(pdf_path, engine, llm=None) -> ConversionResult`
- [ ] `utils/logging.py` — konfiguracja loguru (plik + konsola)
- [ ] Testy jednostkowe: `test_registry.py` (mock engines), `test_converter.py` (mock engine + mock llm)

### Co robisz Ty
- [ ] `git checkout -b etap-1-core`
- [ ] Po skończeniu: `uv run pytest` → zielone
- [ ] `git add -A && git commit -m "Etap 1: Rdzeń i abstrakcje"`
- [ ] `git push origin etap-1-core`
- [ ] Na GitHub: utwórz Pull Request, przejrzyj diff, scal do main

### Definicja ukończenia
✅ ABC `ConversionEngine` i `LLMProvider` zdefiniowane  
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
  - `postprocess(markdown, instructions)`: wywołanie API Ollama
- [ ] `llm/anthropic_provider.py`:
  - `is_available()`: sprawdza `ANTHROPIC_API_KEY` w env
  - `postprocess(markdown, instructions)`: Claude API (claude-sonnet-4-5)
- [ ] `llm/openai_provider.py` — analogicznie
- [ ] `llm/gemini_provider.py` — analogicznie
- [ ] `LLMRegistry` z auto-detekcją dostępnych dostawców
- [ ] Prompt systemowy do post-processingu w `core/prompts.py`:
  ```
  "Wyczyść i popraw poniższy Markdown uzyskany z konwersji PDF.
   Usuń artefakty OCR, popraw tabelki, zachowaj strukturę.
   Zwróć tylko poprawiony Markdown, bez komentarzy."
  ```
- [ ] Testy z mock'owanymi API (żeby nie płacić za testy)

### Co robisz Ty
- [ ] `git checkout -b etap-4-llm-providers`
- [ ] (Opcjonalne) Instalacja Ollama: https://ollama.com/download → `ollama pull llama3.2`
- [ ] Ustawiasz klucze API w `.env` dla tych dostawców których chcesz testować
- [ ] Testujesz post-processing na surowym Markdown z Etapu 2
- [ ] Pull Request → scal

### Definicja ukończenia
✅ Każdy provider zwraca `is_available() = True/False` poprawnie  
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

# Z post-processingiem LLM
pdf2md convert dokument.pdf --engine marker --llm claude

# Batch processing
pdf2md convert *.pdf --output-dir wyniki/

# Sprawdź co jest dostępne
pdf2md list-engines
pdf2md list-llm

# Ustawienia (zapis do config)
pdf2md config set default-engine marker
pdf2md config set anthropic-key sk-ant-...
pdf2md config show
```

### Zadania dla Claude Code
- [ ] `cli/main.py` z click:
  - komenda `convert` z wszystkimi flagami
  - komenda `list-engines` (tabela ASCII z `rich`)
  - komenda `list-llm` (tabela z dostępnymi dostawcami)
  - komenda `config` (get/set/show)
  - progress bar z `rich` podczas konwersji
  - kolorowy output (zielone success, czerwone błędy)
  - raport końcowy: czas konwersji, silnik, liczba stron
- [ ] Entry point w `pyproject.toml`: `pdf2md = "pdf2md.cli.main:cli"`
- [ ] Testy `tests/unit/test_cli.py` z `click.testing.CliRunner`

### Co robisz Ty
- [ ] `git checkout -b etap-5-cli`
- [ ] `uv pip install -e .` — instalacja z entry pointem
- [ ] Testujesz komendy ręcznie
- [ ] `pdf2md list-engines` — czy pokazuje dostępne silniki?
- [ ] `pdf2md convert tests/fixtures/test_text.pdf` — czy działa?
- [ ] Pull Request → scal

### Definicja ukończenia
✅ `pdf2md convert plik.pdf` produkuje `.md` obok pliku źródłowego  
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
  - zapis do `QSettings` (trwały między sesjami)
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

## Etap 8 — Pozostałe silniki
**Gałąź:** `etap-8-engines`
**Czas:** ~4 godziny

### Cel
Dodanie MinerU, Docling i pdf-craft jako dodatkowych opcji.

### Zadania dla Claude Code
- [ ] `engines/mineru_engine.py` — wrapper przez subprocess CLI (MinerU ma CLI)
- [ ] `engines/docling_engine.py` — wrapper przez Python API Docling
- [ ] `engines/pdf_craft_engine.py` — wrapper pdf-craft
- [ ] Aktualizacja Registry o nowe silniki
- [ ] Testy integracyjne (jeśli silniki zainstalowane, inaczej skip z `pytest.mark.skipif`)
- [ ] Dokumentacja "Jak zainstalować każdy silnik" w `docs/ENGINES.md`

### Co robisz Ty
- [ ] `git checkout -b etap-8-engines`
- [ ] Instalujesz wybrane silniki (każdy osobno, sprawdzasz czy działa):
  ```bash
  uv add docling          # ~300MB
  uv add pdf-craft        # mniejszy
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
**Czas:** ~3 godziny

### Zadania dla Claude Code
- [ ] `build.spec` dla PyInstaller (GUI + CLI jako dwa binary)
- [ ] `scripts/build_linux.sh` — buduje AppImage lub `.tar.gz`
- [ ] `scripts/build_windows.ps1` — buduje `.exe` (uwaga: Tesseract i Poppler muszą być dołączone)
- [ ] `.github/workflows/release.yml`:
  - uruchamia się na tag `v*` (np. `v1.0.0`)
  - buduje binary dla Linux i Windows
  - tworzy GitHub Release z artefaktami
- [ ] Instrukcja "Release checklist" w `docs/RELEASE.md`

### Co robisz Ty
- [ ] `git tag v1.0.0 && git push origin v1.0.0`
- [ ] Obserwujesz GitHub Actions jak buduje release
- [ ] Pobierasz binary ze strony Release i testujesz na czystym systemie

### Definicja ukończenia
✅ `pdf2md` binary działa bez instalacji Python  
✅ `pdf2md-gui` otwiera się na Windows bez instalacji  
✅ GitHub Release zawiera pliki do pobrania  

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
