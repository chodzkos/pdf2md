# pdf2md Squeezer — Promty do Claude Code

> Użyj tych promptów kolejno, jeden etap na raz.
> Przed każdym promptem: sprawdź czy jesteś na właściwej gałęzi git.
> Po każdym etapie: uruchom testy, przejrzyj diff, zrób PR.

---

## Jak używać tego pliku

1. Otwórz terminal w VS Code (`Ctrl+` ` `)
2. Upewnij się że Claude Code jest uruchomiony (`claude`)
3. Skopiuj cały blok prompta poniżej
4. Wklej do Claude Code
5. Poczekaj na wykonanie — Claude Code może zadawać pytania
6. Po skończeniu sprawdź pliki w VS Code i uruchom testy

---

## PROMPT #0 — Inicjalizacja projektu

```
Zainicjuj projekt Python o nazwie "pdf2md" w bieżącym katalogu.
Zapoznaj się z plikiem docs/PROJEKT.md i docs/ROADMAP.md jeśli są dostępne.

Wykonaj następujące kroki:

1. STRUKTURA KATALOGÓW
Utwórz katalogi:
  src/pdf2md/engines/
  src/pdf2md/llm/
  src/pdf2md/core/
  src/pdf2md/detection/
  src/pdf2md/exporters/
  src/pdf2md/cli/
  src/pdf2md/gui/
  src/pdf2md/gui/widgets/
  src/pdf2md/utils/
  tests/unit/
  tests/integration/
  tests/fixtures/
  docs/
  scripts/
  .github/workflows/

2. PYPROJECT.TOML
Skonfiguruj dla narzędzia "uv" z:
- name = "pdf2md"
- python = ">=3.11"
- zależności: pydantic-settings, loguru, rich, click, PySide6
- dev zależności: pytest, pytest-cov, ruff, mypy, pre-commit
- opcjonalne grupy: engines-core (pymupdf4llm, marker-pdf, docling), engines-optional (mineru, pdf-craft), llm (anthropic, openai, google-generativeai)
- entry points:
    pdf2md = "pdf2md.cli.main:cli"
    pdf2md-gui = "pdf2md.gui.app:main"

3. PLIKI KONFIGURACYJNE
- .gitignore: Python standard + .env, dist/, build/, *.egg-info/, .mypy_cache/, .ruff_cache/, htmlcov/
- .env.example (override deweloperski) z polami: ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY,
  ANTHROPIC_MODEL, OPENAI_MODEL, GEMINI_MODEL, OLLAMA_MODEL (wszystkie puste, modele opcjonalne)
- LICENSE: MIT z rokiem 2025 i autorem "Marcin"
- .pre-commit-config.yaml z hookami: ruff (linter), ruff-format (formatter), mypy

4. GITHUB ACTIONS
Utwórz .github/workflows/ci.yml uruchamiający się na push i pull_request do main:
- zainstaluj uv
- uv sync
- uv run ruff check .
- uv run mypy src/
- uv run pytest --cov=pdf2md --cov-report=xml

5. PLACEHOLDERS
W każdym module utwórz __init__.py z docstringiem opisującym moduł.

6. README.md
Szkielet z:
- tytułem i opisem
- sekcją Features (placeholder)
- sekcją Installation (placeholder)
- sekcją Usage (placeholder)
- linkiem do docs/ROADMAP.md

7. TEST SANITY
Utwórz tests/unit/test_sanity.py:
- test importu pakietu pdf2md
- test że wersja jest zdefiniowana w __init__.py

Po zakończeniu pokaż mi:
- listę wszystkich utworzonych plików
- polecenia do uruchomienia: uv sync, uv run pytest
```

---

## PROMPT #1 — Rdzeń i abstrakcje

```
Jesteśmy na gałęzi etap-1-core. Zapoznaj się z docs/PROJEKT.md.

Zaimplementuj rdzeń aplikacji pdf2md:

1. src/pdf2md/engines/base.py
Utwórz:
- dataclass ConversionResult:
    markdown: str
    engine_used: str
    pages: int
    warnings: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    conversion_time: float = 0.0

- ABC ConversionEngine z atrybutami klasy:
    name: str
    description: str  
    supports_ocr: bool
    supports_llm: bool
    requires_gpu: bool = False
  i metodami abstrakcyjnymi:
    is_available(self) -> bool
    convert(self, pdf_path: str, **kwargs) -> ConversionResult
  i metodą is_installed(self) -> bool (alias dla is_available, dla czytelności)

  KRYTYCZNE — is_available() NIE importuje silnika. Sprawdza tylko obecność pakietu
  przez importlib.metadata.version("nazwa-pakietu") w try/except PackageNotFoundError.
  Fizyczny import (import marker itd.) wykonuj DOPIERO w convert(). Powód: registry
  odpytuje is_available() przy każdym starcie/--help/list-engines; import ciężkich
  bibliotek (torch) spowalniałby start o kilkanaście sekund.

2. src/pdf2md/llm/base.py
Utwórz:
- dataclass LLMResult:
    text: str
    provider_used: str
    tokens_used: int = 0

- ABC LLMProvider z atrybutami:
    name: str
    description: str
    requires_api_key: bool
    default_model: str   # bezpieczny fallback, NADPISYWANY przez config
  i metodami abstrakcyjnymi:
    is_available(self) -> bool
    postprocess(self, markdown: str, mode: str = "whole_document", instructions: str = "") -> LLMResult
  (mode to jeden z: none, whole_document, by_page, by_chunk, by_heading)

3. src/pdf2md/core/config.py
Użyj pydantic-settings, ale ŹRÓDŁEM PRAWDY jest plik config.toml (NIE .env).
- Lokalizacja: ~/.config/pdf2md/config.toml (utwórz z domyślnymi jeśli nie istnieje)
- .env służy WYŁĄCZNIE jako override deweloperski (nadpisuje wartości z toml gdy obecny)
Klasa Settings z polami:
- anthropic_api_key: str = ""
- openai_api_key: str = ""
- gemini_api_key: str = ""
- anthropic_model: str = ""   # puste = fallback z providera
- openai_model: str = ""
- gemini_model: str = ""
- ollama_model: str = "qwen2.5:14b"
- default_engine: str = "pymupdf4llm"
- default_output_dir: str = ""  (jeśli puste, zapisuj obok źródła)
- default_language: str = "pol+eng"
- llm_enabled: bool = False
- llm_provider: str = "none"
- llm_mode: str = "none"  # none|whole_document|by_page|by_chunk|by_heading
Kolejność ładowania: config.toml → nadpisanie przez .env (jeśli dev) → cache.
Funkcje: get_settings() (singleton), save_settings() (zapis do config.toml).
save_settings() musi być ATOMOWY: zapisz do pliku tymczasowego i os.replace() na docelowy
(eliminuje uszkodzenie pliku gdy CLI i GUI zapisują naraz — race condition).
WAŻNE: ten sam config czytają CLI i GUI — żadnego osobnego QSettings.

3b. src/pdf2md/detection/dependencies.py
Funkcje wykrywające stan środowiska (użyte później przez `pdf2md doctor`):
- check_tesseract() -> dict (wersja + lista języków)
- check_poppler() -> bool
- check_pandoc() -> bool
- check_ollama() -> dict (działa? + lista modeli)
- check_gpu() -> dict (CUDA dostępna? PyTorch CUDA?)
- check_all() -> dict (zbiorczy raport)
Wszystkie odporne na brak narzędzia (zwracają False/pusty, nie rzucają wyjątku).

3c. src/pdf2md/utils/chunking.py
Funkcje dzielenia tekstu na potrzeby LLM:
- by_chunk(text: str, max_tokens: int = 4000) -> list[str]
- by_heading(text: str) -> list[str]  (dzieli wg nagłówków Markdown)
- estimate_tokens(text: str) -> int  (przybliżenie)

4. src/pdf2md/core/registry.py
Utwórz:
- EngineRegistry:
    - __init__: lista wszystkich silników (na razie pusta lista)
    - register(engine: ConversionEngine)
    - get_all() -> list[ConversionEngine]
    - get_available() -> list[ConversionEngine]  (tylko te z is_available() == True)
    - get_by_name(name: str) -> ConversionEngine | None
    - describe() -> str  (tabela tekstowa dla CLI)

- LLMRegistry: analogicznie dla LLMProvider

- Globalne instancje: engine_registry = EngineRegistry(), llm_registry = LLMRegistry()

5. src/pdf2md/core/converter.py
Utwórz klasę Converter:
- convert(pdf_path: str, engine: ConversionEngine, llm: LLMProvider | None = None, output_path: str | None = None) -> ConversionResult
  Logika:
    - sprawdź czy plik istnieje
    - sprawdź czy engine.is_available()
    - zmierz czas: result = engine.convert(pdf_path)
    - jeśli llm nie None: result.markdown = llm.postprocess(result.markdown).text
    - jeśli output_path podany: zapisz plik .md
    - zwróć result
- convert_batch(pdf_paths: list[str], ...) -> list[ConversionResult]
  Dla każdego pliku wywołaj convert(), zbieraj wyniki.

6. src/pdf2md/utils/logging.py
Skonfiguruj loguru:
- format z timestampem, poziomem i modułem
- zapis do pliku logs/pdf2md.log (rotacja 10MB)
- eksportuj funkcję setup_logging()

7. TESTY
tests/unit/test_registry.py:
- Test dodania mock engine do registry
- Test get_available() zwraca tylko te z is_available() == True
- Test get_by_name() zwraca poprawny silnik

tests/unit/test_converter.py:
- Test convert() z mock engine (bez LLM)
- Test convert() z mock engine i mock LLM
- Test błędu gdy plik nie istnieje
- Test błędu gdy engine niedostępny
Użyj unittest.mock do mockowania.

Po zakończeniu uruchom: uv run pytest tests/unit/ -v
```

---

## PROMPT #2 — Silnik PyMuPDF4LLM

```
Jesteśmy na gałęzi etap-2-pymupdf4llm.

Zaimplementuj adapter dla silnika PyMuPDF4LLM:

1. src/pdf2md/engines/pymupdf4llm_engine.py
Klasa PyMuPDF4LLMEngine dziedzicząca po ConversionEngine:
- name = "PyMuPDF4LLM"
- description = "Szybki ekstraktor tekstu z natywnych PDF-ów. Nie obsługuje skanów."
- supports_ocr = False
- supports_llm = False

- is_available(): importlib.metadata.version("pymupdf4llm") w try/except PackageNotFoundError → True/False. NIE importuj pymupdf4llm tutaj.

- convert(pdf_path, **kwargs) -> ConversionResult:
  - sprawdź is_available(), jeśli nie to raise RuntimeError z instrukcją instalacji
  - import pymupdf4llm
  - md = pymupdf4llm.to_markdown(pdf_path)
  - policz strony: import pymupdf; doc = pymupdf.open(pdf_path); pages = len(doc)
  - zwróć ConversionResult(markdown=md, engine_used=self.name, pages=pages)
  - obsłuż wyjątki, loguj przez loguru

2. Rejestracja silnika
W src/pdf2md/engines/__init__.py:
- zaimportuj PyMuPDF4LLMEngine
- zarejestruj w globalnym engine_registry z core/registry.py:
  engine_registry.register(PyMuPDF4LLMEngine())

3. scripts/test_convert.py
Prosty skrypt CLI do testowania:
  python scripts/test_convert.py sciezka/do/pliku.pdf
  python scripts/test_convert.py sciezka/do/pliku.pdf --engine pymupdf4llm
Wypisze pierwsze 500 znaków Markdownu i czas konwersji.

4. Test integracyjny
tests/integration/test_pymupdf4llm.py:
- Sprawdź czy pymupdf4llm jest zainstalowany (jeśli nie, pytest.mark.skip)
- Konwertuj tests/fixtures/test_text.pdf (jeśli istnieje)
- Sprawdź że wynik nie jest pusty
- Sprawdź że wynik zawiera tekst (len > 100)
- Sprawdź że ConversionResult.pages > 0

Po zakończeniu pokaż polecenie do uruchomienia testu integracyjnego.
Pamiętaj że test_text.pdf musi być w tests/fixtures/ — poinformuj mnie jeśli go nie ma.
```

---

## PROMPT #3 — Silnik Marker

```
Jesteśmy na gałęzi etap-3-marker.

Zaimplementuj adapter dla silnika Marker:

1. src/pdf2md/engines/marker_engine.py
Klasa MarkerEngine dziedzicząca po ConversionEngine:
- name = "Marker"
- description = "Uniwersalny konwerter z OCR. Obsługuje skany, kolumny, tabele."
- supports_ocr = True
- supports_llm = True  (Marker ma wbudowany --use_llm)

- is_available(): importlib.metadata.version("marker-pdf") w try/except PackageNotFoundError → True/False. NIE importuj marker tutaj — import dopiero w convert()

- convert(pdf_path, use_llm=False, lang="pl,en", **kwargs) -> ConversionResult:
  Marker ma kilka API — użyj najnowszego (sprawdź aktualną dokumentację marker-pdf na PyPI).
  Preferowana ścieżka:
    from marker.converters.pdf import PdfConverter
    from marker.models import create_model_dict
    from marker.config.parser import ConfigParser
  Jeśli API różni się od powyższego, dostosuj.
  Wyciągnij tekst z wyniku konwersji Markera.
  Policz strony z pymupdf jeśli Marker nie podaje.

2. Obsługa use_llm
Jeśli use_llm=True i Marker wspiera to przez konfigurację — przekaż odpowiedni parametr.
Jeśli Marker nie obsługuje w tej wersji — loguj ostrzeżenie i kontynuuj bez LLM.

3. Rejestracja
W engines/__init__.py dodaj MarkerEngine do engine_registry.
Marker powinien być zarejestrowany PO PyMuPDF4LLM (wyżej w liście = wyżej priorytet).

4. Testy integracyjne
tests/integration/test_marker.py:
- skipif marker niezainstalowany
- konwertuj test_text.pdf — sprawdź wynik
- konwertuj test_scan.pdf (jeśli istnieje) — sprawdź wynik
- porównaj długość wyniku z PyMuPDF4LLM na tym samym pliku

Po zakończeniu:
1. Pokaż mi jak zainstalować Marker: uv add marker-pdf
2. Uruchom testy: uv run pytest tests/ -v
3. Pokaż output scripts/test_convert.py na test_text.pdf z --engine marker
```

---

## PROMPT #4 — Dostawcy LLM

```
Jesteśmy na gałęzi etap-4-llm-providers.

Zaimplementuj czterech dostawców LLM do post-processingu Markdownu:

PROMPT SYSTEMOWY (użyj wszędzie takiego samego):
Zapisz go jako stałą POST_PROCESSING_PROMPT w src/pdf2md/core/prompts.py:
"""
Jesteś asystentem do czyszczenia dokumentów. Otrzymasz tekst Markdown uzyskany 
z automatycznej konwersji pliku PDF. Tekst może zawierać błędy OCR, artefakty 
konwersji, nieprawidłowe tabele, powtarzające się elementy nawigacyjne.

Twoje zadanie:
1. Usuń artefakty OCR (błędnie rozpoznane znaki, losowe symbole)
2. Popraw uszkodzone tabele Markdown
3. Usuń nagłówki, stopki, numery stron jeśli są wyraźnie błędnie wstawione
4. Zachowaj oryginalną strukturę dokumentu (nagłówki, listy, akapity)
5. NIE dodawaj treści której nie ma w oryginale
6. NIE tłumacz tekstu

Zwróć TYLKO poprawiony Markdown, bez żadnych komentarzy, wyjaśnień ani wstępów.
"""

1. src/pdf2md/llm/ollama_provider.py
Klasa OllamaProvider:
- name = "Ollama (lokalny)"
- requires_api_key = False
- default_model = "qwen2.5:14b"
- is_available(): GET http://localhost:11434/api/tags timeout=2s, zwróć True jeśli 200
- get_models(): zwróć listę dostępnych modeli z /api/tags
- postprocess(markdown, mode="whole_document", instructions=""):
  model = settings.ollama_model or self.default_model
  POST http://localhost:11434/api/generate, stream=False
  Zastosuj chunkowanie wg `mode` (patrz punkt 5)

2. src/pdf2md/llm/anthropic_provider.py  
Klasa AnthropicProvider:
- name = "Claude (Anthropic)"
- requires_api_key = True
- default_model = "claude-sonnet-4-5"  # tylko FALLBACK, nadpisywany configiem
- is_available(): sprawdź ANTHROPIC_API_KEY w settings, try import anthropic
- postprocess(): model = settings.anthropic_model or self.default_model
  max_tokens=8192, system=POST_PROCESSING_PROMPT

3. src/pdf2md/llm/openai_provider.py
Klasa OpenAIProvider — analogicznie, default_model = "gpt-4o-mini" jako fallback

4. src/pdf2md/llm/gemini_provider.py
Klasa GeminiProvider — analogicznie, default_model jako fallback

WAŻNE — NAZWY MODELI NIE NA SZTYWNO:
Każdy provider bierze model z settings (anthropic_model/openai_model/gemini_model/ollama_model).
default_model w klasie to TYLKO bezpieczny fallback gdy config pusty.
Powód: nazwy modeli i dostępność API zmieniają się szybko — twardy hardcode powoduje,
że aplikacja przestaje działać po stronie dostawcy. Użytkownik nadpisuje model z CLI/GUI.

5. CHUNKOWANIE (użyj utils/chunking.py z Etapu 1)
W każdym postprocess() obsłuż parametr mode:
- whole_document: jeden call; ale najpierw estimate_tokens — jeśli przekracza bezpieczny
  limit modelu, zaloguj ostrzeżenie i automatycznie przełącz na by_chunk
- by_page: oczekuje listy stron (split po form feed / marker strony)
- by_chunk: chunking.by_chunk(text, max_tokens), korekta każdego, sklejenie
- by_heading: chunking.by_heading(text), korekta każdej sekcji, sklejenie

STRAŻNIK ROZMIARU (ważne dla surowego OCR): nagłówki z OCR bywają uszkodzone
(np. "# # Rozdzial 2", "H Rozdział 2" albo brak), więc by_heading może nie znaleźć
żadnego nagłówka i zwrócić jeden gigantyczny chunk → przekroczenie limitu tokenów.
Dlatego po podziale KAŻDY chunk (też z by_heading i by_page) przepuść przez kontrolę:
jeśli estimate_tokens(chunk) > bezpieczny limit (np. 8000), podziel ten konkretny
fragment dodatkowo przez by_chunk. Żaden chunk nie może trafić do LLM ponad limit.

6. src/pdf2md/llm/__init__.py
Zarejestruj wszystkich dostawców w llm_registry.
Kolejność rejestracji: Ollama, Claude, OpenAI, Gemini.

7. TESTY (bez prawdziwych API calls!)
tests/unit/test_llm_providers.py:
- Test OllamaProvider.is_available() gdy Ollama nie działa (mock requests → ConnectionError → False)
- Test AnthropicProvider.is_available() gdy brak klucza API (pusty string → False)
- Test że model jest brany z settings (ustaw settings.anthropic_model, sprawdź że użyto)
- Test że pusty config → użyto default_model (fallback)
- Test by_chunk dla długiego tekstu (mock LLM, sprawdź liczbę wywołań > 1)
- Test postprocess() z mock klientem — sprawdź że zwraca LLMResult
- Użyj unittest.mock.patch dla wszystkich zewnętrznych wywołań

Po zakończeniu:
uv run pytest tests/unit/test_llm_providers.py -v
```

---

## PROMPT #5 — CLI

```
Jesteśmy na gałęzi etap-5-cli.

Zaimplementuj pełny interfejs linii komend dla pdf2md:

1. src/pdf2md/cli/main.py
Użyj biblioteki click. Utwórz grupę komend "cli" jako entry point.

KOMENDA: pdf2md convert
  Argumenty:
    files: argument (nargs=-1, required=True) — jeden lub wiele plików PDF lub glob *.pdf
  Opcje:
    --engine / -e: wybór silnika (choices z dostępnych nazw, default z settings)
    --output / -o: ścieżka wyjściowa (plik .md lub katalog jeśli wiele plików)
    --output-dir: katalog dla wyników batch
    --llm: dostawca LLM (choices: none, ollama, claude, openai, gemini, default: none)
    --llm-model: konkretny model LLM (nadpisuje config)
    --llm-mode: tryb chunkowania (choices: none, whole_document, by_page, by_chunk, by_heading)
    --lang: język OCR (default: "pol+eng")
    --dry-run: NIE konwertuj; pokaż plan i zakończ
    --verbose / -v: szczegółowy output
  Zachowanie:
    - Jeśli jeden plik i --output podany → zapisz pod tą nazwą
    - Jeśli wiele plików lub --output-dir → zapisz w katalogu, nazwy = oryginalne z .md
    - --dry-run: pokaż typ PDF (detection/pdf_type.py), wybrany silnik, czy dostępny,
      stan Tesseract/Pandoc/Ollama, ścieżkę wyjścia — i zakończ BEZ konwersji
    - Eksport przez warstwę exporters/ (markdown_exporter; epub przez pandoc_epub_exporter jeśli zażądano i Pandoc dostępny)
    - Progress bar z rich (per plik)
    - Raport końcowy: liczba plików, łączny czas, użyty silnik

KOMENDA: pdf2md list-engines
  Wyświetl tabelę rich z kolumnami:
    Nazwa | Status | Core/Opc. | OCR | LLM | Licencja | Opis
  Status: "✅ Dostępny" lub "❌ Niezainstalowany"
  Dla niedostępnych dodaj hint jak zainstalować (np. "uv add marker-pdf")

KOMENDA: pdf2md list-llm
  Analogiczna tabela dla dostawców LLM.
  Status: "✅ Gotowy" / "⚠️ Brak klucza API" / "❌ Niedostępny"

KOMENDA: pdf2md doctor
  Pełna diagnostyka środowiska (użyj detection/dependencies.check_all()).
  Wyświetl sekcje z kolorowym statusem ✅/⚠️/❌:
    System: OS (Windows/WSL/Linux/macOS), Python (wersja)
    GPU: CUDA wykryta/nie, PyTorch CUDA działa/nie
    Narzędzia: Tesseract (wersja + języki pol/eng), Poppler, Pandoc
    Ollama: działa/nie + lista modeli
    Silniki: status każdego (PyMuPDF4LLM, Marker, Docling, ...)
    Klucze API: OpenAI/Anthropic/Gemini ustawiony/brak (zamaskowany)
  To kluczowe narzędzie do debugowania na WSL/GPU — zrób je solidnie.

KOMENDA: pdf2md config
  Podkomendy (operują na config.toml, NIE na .env):
    show — wyświetl aktualną konfigurację (klucze maskowane)
    set KEY VALUE — zapisz wartość do ~/.config/pdf2md/config.toml
    edit — otwórz config.toml w domyślnym edytorze (os.environ.get("EDITOR", "nano"))

2. Inicjalizacja przy starcie CLI
Na początku każdej komendy:
- setup_logging()
- załaduj settings (config.toml + ewentualny override .env)
- zainicjuj registry (importując engines/__init__.py i llm/__init__.py)

3. Eksport — używaj warstwy exporters/ z rdzenia
NIE pisz osobnej funkcji pandoc tutaj — użyj exporters/markdown_exporter.py
i exporters/pandoc_epub_exporter.py (powstają jako część rdzenia).

4. TESTY
tests/unit/test_cli.py używając click.testing.CliRunner:
- Test "pdf2md list-engines" — sprawdź że zwraca kod 0
- Test "pdf2md list-llm" — sprawdź że zwraca kod 0
- Test "pdf2md doctor" — sprawdź że zwraca kod 0
- Test "pdf2md convert plik.pdf --dry-run" — sprawdź kod 0 i że NIE powstał plik .md
- Test "pdf2md config show" — sprawdź że zwraca kod 0
- Test "pdf2md convert nieistniejacy.pdf" — sprawdź błąd z kodem != 0
- Test "pdf2md convert plik.pdf --engine nieznany" — sprawdź błąd

5. Entry point
Upewnij się że w pyproject.toml jest:
[project.scripts]
pdf2md = "pdf2md.cli.main:cli"

Po zakończeniu:
uv pip install -e .
pdf2md --help
pdf2md list-engines
pdf2md convert tests/fixtures/test_text.pdf -v
```

---

## PROMPT #6 — GUI: szkielet

```
Jesteśmy na gałęzi etap-6-gui-skeleton.

Zaimplementuj szkielet GUI dla pdf2md używając PySide6.
WAŻNE: konwersja MUSI działać w osobnym wątku (QThread), inaczej UI się zawiesi.

1. src/pdf2md/gui/workers.py
Klasa ConversionWorker(QThread):
- Sygnały:
    progress = Signal(str, int)        # (nazwa_pliku, procent 0-100)
    file_done = Signal(str, str, float) # (plik_wejsciowy, plik_wyjsciowy, czas_s)
    file_error = Signal(str, str)       # (plik_wejsciowy, komunikat_błędu)
    all_done = Signal(int, int, float)  # (sukces, błędy, łączny_czas)
- __init__(files, engine_name, output_dir, llm_name="none")
- run(): iteruj po plikach, wywołuj Converter.convert(), emituj sygnały

2. src/pdf2md/gui/widgets/file_list.py
Klasa FileListWidget(QWidget):
- Lista plików (QListWidget)
- Obsługa drag & drop (acceptDrops=True, dragEnterEvent, dropEvent)
- Metody: add_files(paths), remove_selected(), clear(), get_files() -> list[str]
- Każdy element pokazuje: ikonę PDF, nazwę pliku, rozmiar

3. src/pdf2md/gui/widgets/engine_selector.py
Klasa EngineSelectorWidget(QWidget):
- QComboBox z dostępnymi silnikami (z engine_registry.get_all())
- Niedostępne silniki widoczne ale szare (setEnabled(False) dla tych pozycji)
- Tooltip dla każdej pozycji z opisem silnika
- Tooltip dla niedostępnych: "Niezainstalowany. Jak zainstalować: [instrukcja]"
- Sygnał: engine_changed = Signal(str)

4. src/pdf2md/gui/widgets/llm_selector.py
Klasa LLMSelectorWidget(QWidget):
- Checkbox "Włącz post-processing LLM"
- QComboBox z dostawcami (widoczny tylko gdy checkbox zaznaczony)
- Pole tekstowe na model (opcjonalne, z placeholder)
- Sygnał: llm_changed = Signal(str, str)  # (provider_name, model)

5. src/pdf2md/gui/widgets/log_panel.py
Klasa LogPanelWidget(QWidget):
- QTextEdit (read-only)
- Metody:
    log_info(msg: str)    — zielony tekst z timestampem
    log_error(msg: str)   — czerwony tekst
    log_warning(msg: str) — żółty tekst
    clear()

6. src/pdf2md/gui/main_window.py
Klasa MainWindow(QMainWindow):

Layout (QVBoxLayout):
  [Przyciski: Dodaj pliki | Wyczyść]
  [FileListWidget — z drag&drop]
  [Separator]
  [EngineSelectorWidget]
  [LLMSelectorWidget]
  [Folder wynikowy: QLineEdit + przycisk Przeglądaj]
  [Separator]
  [QProgressBar — per plik]
  [Przycisk KONWERTUJ (duży)]
  [Separator]
  [LogPanelWidget]

Logika:
- Kliknięcie "Konwertuj":
    1. Pobierz listę plików, silnik, opcje LLM
    2. Utwórz ConversionWorker
    3. Podłącz sygnały workera do slotów (on_progress, on_file_done, on_error, on_all_done)
    4. worker.start()
    5. Zablokuj przycisk "Konwertuj" podczas konwersji
- on_all_done(): odblokuj przycisk, pokaż QMessageBox ze statystykami

7. src/pdf2md/gui/app.py
Funkcja main():
- Utwórz QApplication
- setup_logging()
- Zainicjuj registry
- Utwórz MainWindow
- window.show()
- sys.exit(app.exec())

8. Entry point w pyproject.toml:
pdf2md-gui = "pdf2md.gui.app:main"

Po zakończeniu:
uv pip install -e .
uv run pdf2md-gui
```

---

## PROMPT #7 — GUI: dopracowanie

```
Jesteśmy na gałęzi etap-7-gui-polish.

Dopracuj GUI pdf2md. Zakładam że szkielet z poprzedniego etapu działa.

1. src/pdf2md/gui/settings_dialog.py
Klasa SettingsDialog(QDialog) otwierana przez Ctrl+, lub menu Plik → Ustawienia:

Zakładki (QTabWidget):
  ZAKŁADKA "Klucze API":
    - Pole tekstowe "Anthropic API Key" (echo mode: password)
    - Przycisk "Testuj" obok każdego klucza
    - Analogicznie OpenAI i Gemini
  
  ZAKŁADKA "Domyślne ustawienia":
    - Combo "Domyślny silnik"
    - Pole "Domyślny folder wyjściowy"
    - Pole "Domyślny język OCR"
  
  ZAKŁADKA "Ollama":
    - Pole URL (domyślnie http://localhost:11434)
    - Przycisk "Wykryj modele"
    - Lista wykrytych modeli

Zapis do config.toml przez core/config.save_settings() — TEN SAM config co CLI.
NIE używaj QSettings (to rozjeżdża ustawienia GUI z CLI). Jedno źródło prawdy: config.toml.
Przyciski OK / Anuluj / Zastosuj.

2. Podgląd Markdown
W MainWindow dodaj QTabWidget (dolna część okna):
  Zakładka "Log" — istniejący LogPanel
  Zakładka "Podgląd" — QTextEdit z wynikiem ostatniej konwersji (markdown jako plain text)

3. Akcje po konwersji
W on_all_done():
  QMessageBox z przyciskami:
    "Otwórz folder wynikowy" → subprocess otwierający folder (os.startfile na Windows, xdg-open na Linux)
    "Zamknij"

4. Menu aplikacji (QMenuBar):
  Plik:
    Otwórz pliki...  (Ctrl+O)
    ────
    Ustawienia       (Ctrl+,)
    ────
    Zakończ          (Ctrl+Q)
  Pomoc:
    O programie
    Strona projektu (otwórz GitHub w przeglądarce)

5. Eksport do EPUB (opcjonalny)
Jeśli Pandoc dostępny (detection/dependencies.check_pandoc()):
  W on_all_done() dodaj do QMessageBox przycisk "Eksportuj do EPUB"
  → użyj exporters/pandoc_epub_exporter.py dla każdego wygenerowanego .md

6. Ikona aplikacji
Utwórz prostą ikonę SVG (symbol PDF ze strzałką → MD) w src/pdf2md/gui/assets/icon.svg
Ustaw jako ikonę okna: window.setWindowIcon(QIcon("..."))

7. Obsługa argumentów startowych
W app.py sprawdź sys.argv:
  pdf2md-gui plik.pdf → dodaj plik do listy i pokaż okno
  pdf2md-gui --help → pokaż help

Po zakończeniu przetestuj:
- Otwórz Ustawienia, wpisz klucz API, zamknij, otwórz ponownie — czy jest zapisany?
- Skonwertuj plik, sprawdź zakładkę Podgląd
- Sprawdź czy "Otwórz folder wynikowy" działa
```

---

## PROMPT #8 — Pozostałe silniki

```
Jesteśmy na gałęzi etap-8-engines.

Zaimplementuj adaptery dla trzech pozostałych silników.
WAŻNE: każdy silnik jest opcjonalny — is_available() musi zwracać False gdy nie zainstalowany,
bez żadnych wyjątków ani błędów.

1. src/pdf2md/engines/docling_engine.py
Klasa DoclingEngine:
- name = "Docling"
- description = "Enterprise-grade, precyzyjne tabele, integracje RAG (IBM Research)"
- supports_ocr = True
- supports_llm = False

- is_available(): importlib.metadata.version("docling") w try/except PackageNotFoundError → True/False. NIE importuj docling tutaj (ładuje torch) — import dopiero w convert()

- convert(pdf_path, **kwargs):
  from docling.document_converter import DocumentConverter
  converter = DocumentConverter()
  result = converter.convert(pdf_path)
  md = result.document.export_to_markdown()
  policz strony (pymupdf lub len(result.document.pages))

2. src/pdf2md/engines/mineru_engine.py
Klasa MinerUEngine:
- name = "MinerU"
- description = "Najlepszy dla dokumentów naukowych, wielokolumnowych i CJK"
- supports_ocr = True
- supports_llm = False
- requires_gpu = False  (działa na CPU, wolniej)

MinerU ma CLI. Użyj subprocess:
- is_available(): użyj shutil.which("magic-pdf") — zwraca ścieżkę lub None.
  WAŻNE: na Windows subprocess.run(["magic-pdf", ...]) bez .exe/.cmd rzuca FileNotFoundError;
  shutil.which() poprawnie lokalizuje binarkę z rozszerzeniem. Zwróć True jeśli which != None.
- convert(pdf_path, output_dir=None, **kwargs):
  Uruchom magic-pdf przez pełną ścieżkę z shutil.which (nie samą nazwę): magic-pdf -p pdf_path -o output_dir_temp
  MinerU tworzy pliki w output_dir_temp/
  Znajdź wygenerowany .md (glob)
  Wczytaj jako string, zwróć ConversionResult

3. src/pdf2md/engines/pdf_craft_engine.py
Klasa PdfCraftEngine:
- name = "pdf-craft"
- description = "Specjalista od skanowanych książek. Natywny output EPUB"
- supports_ocr = True
- supports_llm = False

Sprawdź aktualną dokumentację pdf-craft na PyPI.
Zaimplementuj is_available() przez importlib.metadata.version("pdf-craft") (bez importu modułu)
i convert() zgodnie z API biblioteki.
Jeśli pdf-craft generuje EPUB a nie MD, skonwertuj przez pandoc lub wyekstrahuj tekst.

4. Aktualizacja registry
W engines/__init__.py zarejestruj nowe silniki:
engine_registry.register(DoclingEngine())
engine_registry.register(MinerUEngine())
engine_registry.register(PdfCraftEngine())

5. Testy
tests/integration/test_additional_engines.py:
Dla każdego silnika:
@pytest.mark.skipif(not DoclingEngine().is_available(), reason="Docling niezainstalowany")
def test_docling_converts_pdf():
    ...

6. Dokumentacja
Utwórz docs/ENGINES.md z sekcją dla każdego silnika:
- Opis i mocne strony
- Kiedy używać
- Instrukcja instalacji
- Znane ograniczenia

Po zakończeniu pokaż mi:
pdf2md list-engines
(powinno pokazać wszystkie 5 silników, nawet te niezainstalowane)
```

---

## PROMPT #9 — Testy i dokumentacja

```
Jesteśmy na gałęzi etap-9-docs.

Uzupełnij testy i dokumentację projektu pdf2md.

1. POKRYCIE TESTAMI
Uruchom: uv run pytest --cov=pdf2md --cov-report=term-missing
Zidentyfikuj moduły z pokryciem <75%.
Uzupełnij testy dla tych modułów.
Cel: >75% ogólnego pokrycia.

Szczególnie upewnij się że przetestowane są:
- Każdy engine: is_available() True i False
- Converter: sukces, błąd pliku, błąd engine
- CLI: każda komenda z CliRunner
- Config: ładowanie z env, domyślne wartości
- LLM providers: is_available() z i bez klucza

2. README.md (główny)
Przepisz jako kompletny dokument:

# pdf2md

[odznaka CI] [odznaka licencji] [odznaka Python]

Krótki opis (2 zdania).

## ✨ Funkcje
- lista bulletów z najważniejszymi funkcjami

## 🔧 Silniki konwersji
Tabela: Silnik | Typ dokumentu | OCR | Instalacja

## 📦 Instalacja
### Wymagania wstępne (systemowe)
### Instalacja aplikacji
uv pip install pdf2md

### Instalacja silników (opcjonalnie)
uv pip install "pdf2md[marker]"
uv pip install "pdf2md[docling]"
...

## 🚀 Użycie
### GUI
[screenshot]
Uruchom: pdf2md-gui

### CLI
Przykłady komend z output

## ⚙️ Konfiguracja
Opis config.toml (źródło prawdy), .env jako override deweloperski, dostępnych zmiennych i modeli LLM

## 🤝 Współtworzenie
Link do docs/ROADMAP.md, zasady kontrybucji

3. docs/USAGE.md
Szczegółowy przewodnik:
- GUI krok po kroku z opisem każdego elementu
- CLI reference z wszystkimi flagami i przykładami
- Przewodnik "Który silnik wybrać?" z tabelką decyzyjną

4. CHANGELOG.md
Utwórz: v1.0.0 — Initial release (lista głównych funkcji)

5. Poprawki jeśli CI czerwone
Uruchom: uv run ruff check . && uv run mypy src/
Napraw wszystkie błędy.

Po zakończeniu:
uv run pytest --cov=pdf2md -v
(pokaż mi wynik i procent pokrycia)
```

---

## PROMPT #10 — Packaging

```
Jesteśmy na gałęzi etap-10-packaging.

UWAGA: to jeden z najtrudniejszych etapów (PyInstaller + PySide6 + OCR + binarki).
Nie traktuj go jak szybkiej końcówki. Strategia: build RDZENIOWY bez ciężkich i copyleft silników.

Przygotuj dystrybucję pdf2md jako standalone binary.

1. build.spec (PyInstaller)
Utwórz specfile budujący DWA binary:
- pdf2md (CLI) — bez GUI, mniejszy
- pdf2md-gui (GUI) — z PySide6

ZASADA LICENCYJNA I ROZMIAROWA:
- Wkompiluj TYLKO silniki lekkie i permisywne: PyMuPDF4LLM, Docling.
- NIE wkompilowuj Marker (GPL), MinerU (AGPL), pdf-craft, silników VLM — to copyleft i/lub ciężkie.
  Mają być wykrywane jako opcjonalne i instalowane osobno przez użytkownika (pip).
  Powód: bundlowanie GPL/AGPL w jedno binary zmusza do objęcia całości tą licencją (projekt jest MIT).

Upewnij się że dołączone są:
- Pliki danych: ikona SVG
- Qt plugins dla PySide6
- HIDDENIMPORTS (krytyczne): ponieważ silniki importujemy LENIWIE (dopiero w convert()),
  PyInstaller ich NIE wykryje automatycznie. Aplikacja skompiluje się, ale wybuchnie
  ModuleNotFoundError przy pierwszym użyciu nawet lekkiego silnika. Dodaj jawnie do
  hiddenimports w build.spec wszystkie wkompilowane moduły: pymupdf4llm, pymupdf, docling
  (i ich podmoduły, jeśli PyInstaller zgłasza braki). Po buildzie PRZETESTUJ realną konwersję,
  nie tylko --help.
- FREEZE_SUPPORT: w punkcie wejścia (cli/main.py i gui/app.py) dodaj na początku
  `import multiprocessing; multiprocessing.freeze_support()` pod `if __name__ == "__main__":`.
  Powód: biblioteki ML (torch/docling) wewnętrznie spawnują podprocesy (DataLoader itp.);
  bez freeze_support() skompilowany .exe na Windows może wejść w pętlę nieskończoną
  (rekurencyjne odpalanie samego siebie). To NIE wynika z QThread — QThread to wątki,
  nie multiprocessing — tylko z podprocesów bibliotek ML.

2. scripts/build_linux.sh
#!/bin/bash
set -e
uv run pip install pyinstaller
uv run pyinstaller build.spec --clean
echo "Binary dostępne w dist/"

3. scripts/build_windows.ps1
(dla cross-compilation lub uruchomienia na Windows)
Uwzględnij komentarz gdzie pobrać Tesseract i Poppler dla Windows.
PRZYPOMNIENIE: adaptery wołające zewnętrzne binarki (MinerU/magic-pdf) muszą używać
shutil.which() do lokalizacji pliku — na Windows samo "magic-pdf" bez .exe/.cmd zawiedzie.

4. .github/workflows/release.yml
Uruchamia się na: push tags v*

Jobs:
  build-linux:
    runs-on: ubuntu-latest
    kroki: checkout, install uv, uv sync, apt install poppler-utils tesseract-ocr, 
           install pyinstaller, pyinstaller build.spec, upload artifact

  build-windows:
    runs-on: windows-latest  
    kroki: analogicznie z choco install tesseract poppler

  create-release:
    needs: [build-linux, build-windows]
    kroki: download artifacts, gh release create z plikami

5. docs/RELEASE.md
Checklist przed wydaniem nowej wersji:
- [ ] Zaktualizuj CHANGELOG.md
- [ ] Zaktualizuj wersję w pyproject.toml
- [ ] Uruchom testy: uv run pytest
- [ ] Tag: git tag v1.0.0 && git push origin v1.0.0
- [ ] Obserwuj GitHub Actions

Po zakończeniu pokaż jak ręcznie przetestować build:
uv run pyinstaller build.spec --clean
./dist/pdf2md --help
./dist/pdf2md list-engines
```

---
---

# FAZA 2 — Promty (premium scan pipeline)

> Te etapy wymagają ukończonej Fazy 1 i GPU. Każdy etap = osobna gałąź = osobny PR, tak jak w Fazie 1.

---

## PROMPT #11 — Preprocessing obrazu

```
Jesteśmy na gałęzi etap-11-preprocessing. Zapoznaj się z docs/PROJEKT.md i sekcją FAZA 2 w docs/ROADMAP.md.

Utwórz nowy pakiet src/pdf2md/scan/ do pipeline'u skanowania książek.

1. src/pdf2md/scan/preprocessing.py
Funkcje (używaj OpenCV i pymupdf):
- pdf_to_images(pdf_path: str, dpi: int, output_dir: str) -> list[str]
  Rozbij PDF na obrazy PNG per strona. Nazwy: page_0001.png, page_0002.png...
  Użyj pymupdf (fitz) lub pdftoppm przez subprocess.
- deskew(image) — wyrównanie pochylenia (wykryj kąt, obróć)
- denoise(image) — redukcja szumu
- dewarp(image) — korekta wygięcia strony (opcjonalna, może być uproszczona)
- crop_margins(image) — przycięcie pustych marginesów
- normalize_contrast(image) — poprawa kontrastu (CLAHE)
- detect_double_page(image) -> bool i split_double_page(image) -> list[image]
- preprocess_page(image, operations: list[str]) -> image
  Konfigurowalny pipeline, operations np. ["deskew", "crop", "denoise"]

2. Profile DPI jako stałe:
DPI_STANDARD = 300, DPI_OLD_BOOKS = 400, DPI_DIFFICULT = 600

2b. PRZETWARZANIE STRUMIENIOWE (krytyczne dla dysku)
500 stron PNG przy 600 DPI to 15–25 GB plików tymczasowych — dysk padnie przy batchu książek.
Zaimplementuj generator/iterator paczkowy zamiast rozbijania całego PDF naraz:
- iter_page_batches(pdf_path, dpi, batch_size=20) -> yield list[ścieżek PNG paczki]
  Renderuje tylko bieżącą paczkę stron, oddaje ją do przetworzenia, a wywołujący
  USUWA pliki PNG paczki zanim pobierze następną.
- cleanup_work_dir(work_dir) — czyszczenie po udanym buildzie
To zużycie dysku ograniczy do ~jednej paczki naraz, nie całej książki.

3. CLI pomocniczy scripts/preprocess_test.py:
  python scripts/preprocess_test.py input.pdf --dpi 400 --deskew --crop --denoise
  Zapisuje obrazy przed i po do work/pages_png/ i work/preprocessed/

4. Testy tests/unit/test_preprocessing.py:
- Test pdf_to_images na tests/fixtures/test_scan.pdf (skipif brak pliku)
- Test iter_page_batches — sprawdź że oddaje strony paczkami i nie trzyma wszystkich naraz
- Test że deskew zwraca obraz tych samych wymiarów
- Test detect_double_page na syntetycznym szerokim obrazie

WAŻNE: ten etap NIE używa żadnego LLM ani modelu ML — to klasyczna obróbka obrazu.

Po zakończeniu pokaż wynik scripts/preprocess_test.py na skanie testowym.
```

---

## PROMPT #12 — Silniki VLM-OCR

```
Jesteśmy na gałęzi etap-12-vlm-ocr.

Zaimplementuj trzy silniki OCR oparte na modelach wizyjno-językowych jako adaptery ConversionEngine.
WAŻNE: wszystkie wymagają GPU. is_available() musi zwracać False BEZ błędu gdy brak GPU lub modelu.

1. src/pdf2md/engines/vlm_base.py
Klasa bazowa VLMEngine(ConversionEngine):
- requires_gpu = True
- has_gpu() -> bool: try import torch; return torch.cuda.is_available() / except: False
  (import torch wewnątrz metody, nie na górze pliku)
- is_available() w podklasach: importlib.metadata.version(...) dla pakietu silnika ORAZ has_gpu().
  NIE importuj samego modelu/biblioteki wizyjnej w is_available().
- ZARZĄDZANIE VRAM (krytyczne na 24 GB): metody load_model() i unload_model().
  unload_model() musi REALNIE zwolnić VRAM: usuń referencje do modelu, gc.collect(),
  torch.cuda.empty_cache(); dla backendów serwerowych (vLLM) zamknij proces serwera.
  Powód: olmOCR-2-7B (~7-8 GB) i model korekty qwen2.5:14b (~9-10 GB) NIE zmieszczą się
  jednocześnie w 24 GB. Pipeline ładuje VLM → przetwarza WSZYSTKIE strony → unload_model()
  → dopiero potem faza korekty LLM (Etap 13). Nigdy oba modele naraz.
- wspólna logika: przetwarzanie paczkowe (scan/preprocessing.iter_page_batches),
  OCR per strona, zapis do work/ocr_json/ i work/md_pages/, usuwanie PNG po paczce

2. src/pdf2md/engines/olmocr_engine.py
Klasa OlmOCREngine(VLMEngine):
- name = "olmOCR"
- description = "VLM 7B do skanów: czysty Markdown, równania, tabele, kolejność czytania"
- supports_ocr = True
- model: allenai/olmOCR-2-7B-1025-FP8 (sprawdź najnowszą wersję na PyPI/GitHub)
- is_available(): importlib.metadata.version("olmocr") w try/except + has_gpu(). Bez importu olmocr.
- convert(): load_model() → uruchom olmOCR z flagą --markdown (API Pythona lub subprocess)
  → po wszystkich stronach unload_model(). Sprawdź aktualną dokumentację olmocr na PyPI.

3. src/pdf2md/engines/paddleocr_vl_engine.py
Klasa PaddleOCRVLEngine(VLMEngine):
- name = "PaddleOCR-VL"
- description = "Lekki parser dokumentów VLM, wielojęzyczny, wydajny"
- sprawdź aktualne API PaddleOCR-VL

4. src/pdf2md/engines/surya_engine.py
Klasa SuryaEngine(VLMEngine):
- name = "Surya"
- description = "Layout + OCR + reading order, dobry jako kontrola/fallback"
- użyj API surya (detekcja layoutu + OCR)

5. Rejestracja w engines/__init__.py (po silnikach Fazy 1).

6. Testy tests/integration/test_vlm_engines.py:
- skipif not has_gpu() lub silnik niezainstalowany
- konwersja jednej strony skanu, sprawdzenie że wynik niepusty

Po zakończeniu:
1. Pokaż jak zainstalować olmOCR (osobne środowisko, wymaga CUDA)
2. Pokaż jak sprawdzić GPU: python -c "import torch; print(torch.cuda.is_available())"
3. pdf2md list-engines (olmOCR/PaddleOCR-VL/Surya widoczne, oznaczone wymaganiem GPU)
```

---

## PROMPT #13 — Korekta LLM per-strona + walidacja

```
Jesteśmy na gałęzi etap-13-correction-validation.

Zaimplementuj korektę OCR i walidację jakości.

1. src/pdf2md/core/prompts.py — dodaj stałą SCAN_CORRECTION_PROMPT:
"""
Jesteś korektorem OCR. Popraw wyłącznie oczywiste błędy rozpoznawania tekstu.
Nie parafrazuj. Nie skracaj. Nie dopisuj informacji, których nie ma w tekście.
Zachowaj oryginalną składnię, interpunkcję, styl i akapity.
Połącz wyrazy przeniesione przez podział wiersza, jeśli jest to oczywiste.
Usuń numery stron, nagłówki i stopki tylko wtedy, gdy są ewidentnie metadanymi strony.
Fragmenty niepewne oznacz jako [nieczytelne].
Przypisy zachowaj i oznacz jako Markdown footnotes.
Nie modernizuj pisowni. Nie zamieniaj archaizmów. Nie tłumacz. Nie streszczaj.
Wynik zwróć jako czysty Markdown.
"""

2. src/pdf2md/scan/correction.py
- correct_page(md: str, provider: LLMProvider) -> str
  Używa SCAN_CORRECTION_PROMPT i dostawcy LLM z Fazy 1 (preferowany lokalny Ollama + Qwen 14B).
- correct_pages_batch(md_dir, provider, output_dir) — korekta wszystkich stron
  Tryb conservative: niska temperatura, brak kreatywności.

KOLEJNOŚĆ I VRAM (krytyczne): faza korekty uruchamia się DOPIERO po tym, jak silnik VLM
zwolnił VRAM (engine.unload_model() z Etapu 12). ScanPipelineEngine wymusza sekwencję:
cały OCR → unload VLM → korekta LLM. Dla Ollamy: po skończonej korekcie wyślij żądanie
z keep_alive=0, żeby Ollama wyładowała model korekty (domyślnie trzyma go 5 min w VRAM).
Dodaj guard: przed startem korekty zaloguj wolne VRAM (torch.cuda.mem_get_info) i ostrzeż,
jeśli model wizyjny nie został zwolniony.

3. src/pdf2md/scan/validation.py
- page_quality_score(md: str) -> dict z metrykami:
    char_count, replacement_char_count (znaki �), unreadable_markers (liczba [nieczytelne]),
    suspicious_patterns (rn/m, l/I, 0/O), is_empty, is_suspiciously_short
- detect_low_quality_pages(pages: list, thresholds) -> list[int]
- compare_ocr_outputs(md_a: str, md_b: str) -> float  (podobieństwo dwóch silników)
- should_rerun_page(score: dict, thresholds) -> bool

4. src/pdf2md/scan/rerun.py
- rerun_difficult_pages(page_indices, pdf_path, fallback_engine, higher_dpi)
  Ponowny przebieg trudnych stron dokładniejszym silnikiem lub wyższym DPI.

5. Testy:
- test_correction.py z MOCKowanym LLM (sprawdź że prompt zawiera "nie parafrazuj")
- test_validation.py: strona z � → wykryta jako niska jakość; pusta strona → wykryta;
  czysta strona → wysoki wynik

Po zakończeniu pokaż przykład: weź brudny OCR (z �, z błędami rn/m), uruchom walidację,
pokaż że strona jest oznaczona do ponownego przebiegu.
```

---

## PROMPT #14 — Składanie książki + EPUB

```
Jesteśmy na gałęzi etap-14-book-assembly.

Zaimplementuj składanie poprawionych stron w książkę i eksport.

1. src/pdf2md/scan/assembly.py
- remove_repeated_headers_footers(pages: list[str]) -> list[str]
  Wykryj linie powtarzające się na wielu stronach (nagłówki/stopki) i usuń.
- merge_paragraphs_across_pages(pages: list[str]) -> str
  Połącz akapity przerwane na granicy strony.
- fix_hyphenation(text: str) -> str
  Napraw wyrazy podzielone myślnikiem na końcu wiersza.
- detect_chapters(text: str) -> list[Chapter]
  Wykryj rozdziały (nagłówki, "Rozdział X", duże odstępy).
- normalize_punctuation(text: str) -> str
  Normalizuj cudzysłowy („") i myślniki (—).
- build_toc(chapters: list[Chapter]) -> str

2. src/pdf2md/scan/export.py
- export_markdown(chapters, output_path) -> str  (book.md)
- export_epub(chapters, metadata, output_path)
  Preferuj ebooklib (kontrola nad TOC, CSS, metadanymi). Pandoc jako fallback.
- export_quality_report(validation_results, output_path)
  report.html z listą stron, wynikami jakości i oznaczeniem trudnych stron.

3. Integracja w ScanPipelineEngine
Utwórz src/pdf2md/engines/scan_pipeline_engine.py:
- name = "Scan Pipeline (premium)"
- Opakowuje cały przepływ: preprocessing → VLM-OCR → (unload VLM) → korekta → walidacja → składanie → eksport
- WYMUSZA sekwencję VRAM: cały OCR z załadowanym modelem wizyjnym → engine.unload_model()
  → dopiero korekta LLM (oba modele nigdy naraz w pamięci — patrz Etap 12/13)
- Przetwarzanie paczkowe stron (iter_page_batches) z usuwaniem PNG po paczce
- Po UDANYM zbudowaniu EPUB: automatyczne czyszczenie work/ (cleanup_work_dir),
  z opcją --keep-work do debugowania
- Implementuje interfejs ConversionEngine (pojawia się w GUI/CLI jak inne silniki)
- convert() przyjmuje profile (z Etapu 15) i zwraca ConversionResult z dodatkową ścieżką EPUB

4. Testy:
- test_assembly.py: dzielenie wyrazów, łączenie akapitów, usuwanie nagłówków
- test_export.py: zbuduj EPUB z mock rozdziałów, rozpakuj, sprawdź content.opf
- test że work/ jest czyszczony po udanym buildzie (i zachowany przy --keep-work)

Po zakończeniu uruchom pełny pipeline na skanie testowym (kilka stron) i pokaż:
- czy book.md ma poprawne rozdziały
- czy book.epub otwiera się (sprawdź strukturę zip)
```

---

## PROMPT #15 — Profile skanowania

```
Jesteśmy na gałęzi etap-15-scan-profiles.

Zaimplementuj system profili dla pipeline'u skanowania.

1. Pliki profili w profiles/ (YAML):

profiles/fast.yaml:
  name: fast
  dpi: 300
  preprocess: {deskew: true, denoise: false, dewarp: false}
  ocr: {engine: paddleocr, gpu: true}
  llm_cleanup: {enabled: true, provider: ollama, model: qwen2.5:14b, chunk: page}
  output: {markdown: true, epub: true}

profiles/balanced.yaml:
  name: balanced
  dpi: 400
  preprocess: {deskew: true, denoise: true, dewarp: auto, crop: auto}
  layout: {engine: surya}
  ocr: {engine: paddleocr-vl, gpu: true}
  llm_cleanup: {enabled: true, provider: ollama, model: qwen2.5:14b, chunk: page}
  postprocess: {remove_headers_footers: true, merge_paragraphs: true, fix_hyphenation: true}
  output: {markdown: true, epub: true, quality_report: true}

profiles/premium.yaml:
  name: premium
  dpi: 400
  preprocess: {deskew: true, denoise: true, dewarp: true, crop: true}
  layout: {engine: olmocr}
  ocr: {primary: olmocr, secondary: surya, compare_outputs: true}
  llm_cleanup: {enabled: true, provider: ollama, model: qwen2.5:14b, mode: conservative, chunk: page_then_chapter}
  postprocess: {remove_headers_footers: true, merge_paragraphs: true, fix_hyphenation: true, footnotes: true, toc_detection: true}
  validation: {detect_low_confidence_pages: true, rerun_bad_pages: true}
  output: {markdown: true, epub: true, html_report: true}

2. src/pdf2md/scan/profiles.py
- Model Profile (pydantic) walidujący strukturę YAML
- load_profile(name_or_path: str) -> Profile
- list_profiles() -> list[str]  (wbudowane + użytkownika z ~/.config/pdf2md/profiles/)
- save_custom_profile(profile, name)

3. Integracja CLI w cli/main.py:
- Nowa komenda: pdf2md scan <pdf> --profile [fast|balanced|premium] -o output/
- pdf2md list-profiles

4. Integracja GUI:
- W trybie skanowania dropdown wyboru profilu
- Przycisk "Edytuj profil" otwierający edytor ustawień profilu

5. docs/SCAN_PROFILES.md — opis każdego profilu, kiedy używać, jak stworzyć własny.

6. Testy test_profiles.py: ładowanie każdego wbudowanego profilu, walidacja błędnego YAML.

Po zakończeniu:
pdf2md list-profiles
pdf2md scan tests/fixtures/test_book_scan.pdf --profile balanced -o output/
(pokaż wynik i czas dla różnych profili)
```

---

## Wskazówki ogólne

### Dwie zasady do DOPISANIA na końcu każdego prompta etapowego
Te dwie reguły warto dokleić do każdego prompta (#1 i dalej) — utwardzają pracę agenta:

```
1. Nie zmieniaj publicznych interfejsów z poprzednich etapów bez potrzeby.
   Jeśli zmiana interfejsu jest konieczna — najpierw opisz powód i poczekaj na moją zgodę.

2. Przed implementacją adaptera sprawdź FAKTYCZNE, zainstalowane API biblioteki
   w środowisku (wersja + sygnatury), zamiast zakładać że przykładowe importy są aktualne.
   Dotyczy to zwłaszcza Marker, Docling, pdf-craft, olmOCR — ich API bywa zmienne.
```

### Gdy Claude Code coś nie rozumie
Doprecyzuj: "Zanim cokolwiek zrobisz, przeczytaj plik docs/PROJEKT.md i potwierdź że rozumiesz architekturę"

### Gdy coś nie działa po implementacji
"Test X failuje z błędem: [wklej błąd]. Napraw to nie zmieniając interfejsu publicznego."

### Gdy chcesz zrozumieć decyzję
"Wytłumacz dlaczego wybrałeś to rozwiązanie zamiast [alternatywa]."

### Gdy coś jest niezgodne z planem
"To rozwiązanie odbiega od architektury z docs/PROJEKT.md w zakresie [X]. Dostosuj je do planu."

### Szybki reset jeśli coś się popsuło
git stash         # schowaj zmiany
git stash drop    # usuń
# zacznij etap od nowa z promptem
```
