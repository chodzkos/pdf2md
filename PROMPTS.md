# pdf2md — Promty do Claude Code

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
Zapoznaj się z plikiem PROJEKT.md i ROADMAP.md jeśli są dostępne.

Wykonaj następujące kroki:

1. STRUKTURA KATALOGÓW
Utwórz katalogi:
  src/pdf2md/engines/
  src/pdf2md/llm/
  src/pdf2md/core/
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
- opcjonalne grupy: engines (pymupdf4llm, marker-pdf, docling), llm (anthropic, openai, google-generativeai)
- entry points:
    pdf2md = "pdf2md.cli.main:cli"
    pdf2md-gui = "pdf2md.gui.app:main"

3. PLIKI KONFIGURACYJNE
- .gitignore: Python standard + .env, dist/, build/, *.egg-info/, .mypy_cache/, .ruff_cache/, htmlcov/
- .env.example z polami: ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY (puste wartości)
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
- linkiem do ROADMAP.md

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
Jesteśmy na gałęzi etap-1-core. Zapoznaj się z PROJEKT.md.

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
  i metodami abstrakcyjnymi:
    is_available(self) -> bool
    postprocess(self, markdown: str, instructions: str = "") -> LLMResult

3. src/pdf2md/core/config.py
Użyj pydantic-settings. Utwórz klasę Settings:
- anthropic_api_key: str = ""
- openai_api_key: str = ""
- gemini_api_key: str = ""
- default_engine: str = "pymupdf4llm"
- default_output_dir: str = ""  (jeśli puste, zapisuj obok źródła)
- default_language: str = "pol+eng"
- llm_enabled: bool = False
- llm_provider: str = "none"
- llm_model: str = ""
Odczyt z .env przez model_config = SettingsConfigDict(env_file=".env")
Singleton get_settings() zwracający cached instancję.

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

- is_available(): try: import pymupdf4llm; return True / except ImportError: return False

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

- is_available(): sprawdź czy można zaimportować marker

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
- is_available(): GET http://localhost:11434/api/tags timeout=2s, zwróć True jeśli 200
- get_models(): zwróć listę dostępnych modeli z /api/tags
- postprocess(markdown, instructions=""):
  POST http://localhost:11434/api/generate
  model = self.model (domyślnie "llama3.2")
  prompt = POST_PROCESSING_PROMPT + "\n\n" + markdown
  stream = False

2. src/pdf2md/llm/anthropic_provider.py  
Klasa AnthropicProvider:
- name = "Claude (Anthropic)"
- requires_api_key = True
- is_available(): sprawdź ANTHROPIC_API_KEY w settings, try import anthropic
- postprocess(): użyj anthropic SDK, model "claude-sonnet-4-5-20250929" lub najnowszy dostępny
  max_tokens=8192, system=POST_PROCESSING_PROMPT

3. src/pdf2md/llm/openai_provider.py
Klasa OpenAIProvider — analogicznie, model "gpt-4o-mini" (tańszy)

4. src/pdf2md/llm/gemini_provider.py
Klasa GeminiProvider — analogicznie z google-generativeai SDK, model "gemini-1.5-flash"

5. src/pdf2md/llm/__init__.py
Zarejestruj wszystkich dostawców w llm_registry.
Kolejność rejestracji: Ollama, Claude, OpenAI, Gemini.

6. TESTY (bez prawdziwych API calls!)
tests/unit/test_llm_providers.py:
- Test OllamaProvider.is_available() gdy Ollama nie działa (mock requests → ConnectionError → False)
- Test AnthropicProvider.is_available() gdy brak klucza API (pusty string → False)
- Test postprocess() z mock klientem anthropic — sprawdź że zwraca LLMResult
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
    --llm-model: konkretny model LLM
    --lang: język OCR (default: "pol+eng")
    --verbose / -v: szczegółowy output
  Zachowanie:
    - Jeśli jeden plik i --output podany → zapisz pod tą nazwą
    - Jeśli wiele plików lub --output-dir → zapisz w katalogu, nazwy = oryginalne z .md
    - Progress bar z rich (per plik)
    - Raport końcowy: liczba plików, łączny czas, użyty silnik

KOMENDA: pdf2md list-engines
  Wyświetl tabelę rich z kolumnami:
    Nazwa | Status | OCR | LLM | Opis
  Status: "✅ Dostępny" lub "❌ Niezainstalowany"
  Dla niedostępnych dodaj hint jak zainstalować (np. "uv add marker-pdf")

KOMENDA: pdf2md list-llm
  Analogiczna tabela dla dostawców LLM.
  Status: "✅ Gotowy" / "⚠️ Brak klucza API" / "❌ Niedostępny"

KOMENDA: pdf2md config
  Podkomendy:
    show — wyświetl aktualną konfigurację (bez sekretnych wartości, klucze maskowane)
    set KEY VALUE — zapisz wartość do .env w katalogu roboczym
    edit — otwórz .env w domyślnym edytorze (os.environ.get("EDITOR", "nano"))

2. Inicjalizacja przy starcie CLI
Na początku każdej komendy:
- setup_logging()
- załaduj settings
- zainicjuj registry (importując engines/__init__.py i llm/__init__.py)

3. src/pdf2md/utils/pandoc.py
Funkcja:
- is_pandoc_available() -> bool: sprawdź czy pandoc jest w PATH
- convert_to_epub(md_path: str, output_path: str) -> bool: wywołaj subprocess pandoc

4. TESTY
tests/unit/test_cli.py używając click.testing.CliRunner:
- Test "pdf2md list-engines" — sprawdź że zwraca kod 0
- Test "pdf2md list-llm" — sprawdź że zwraca kod 0
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

Zapis do QSettings (persystentny między sesjami, nie do .env).
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
Jeśli pandoc dostępny (utils/pandoc.is_pandoc_available()):
  W on_all_done() dodaj do QMessageBox przycisk "Eksportuj do EPUB"
  → wywołaj pandoc.convert_to_epub() dla każdego wygenerowanego .md

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

- is_available(): try: from docling.document_converter import DocumentConverter; return True

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
- is_available(): subprocess.run(["magic-pdf", "--version"], capture_output=True) — kod 0 = dostępny
- convert(pdf_path, output_dir=None, **kwargs):
  Uruchom: magic-pdf -p pdf_path -o output_dir_temp
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
Zaimplementuj is_available() i convert() zgodnie z API biblioteki.
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
Opis .env i dostępnych zmiennych

## 🤝 Współtworzenie
Link do ROADMAP.md, zasady kontrybucji

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

Przygotuj dystrybucję pdf2md jako standalone binary.

1. build.spec (PyInstaller)
Utwórz specfile dla PyInstaller budujący DWA binary:
- pdf2md (CLI) — bez GUI, mniejszy
- pdf2md-gui (GUI) — z PySide6

Upewnij się że dołączone są:
- Pliki danych: ikona SVG
- Ukryte importy dla silników (marker, docling itd. nie są wykrywane automagicznie)
- Qt plugins dla PySide6

2. scripts/build_linux.sh
#!/bin/bash
set -e
uv run pip install pyinstaller
uv run pyinstaller build.spec --clean
echo "Binary dostępne w dist/"

3. scripts/build_windows.ps1
(dla cross-compilation lub uruchomienia na Windows)
Uwzględnij komentarz gdzie pobrać Tesseract i Poppler dla Windows.

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

## Wskazówki ogólne

### Gdy Claude Code coś nie rozumie
Doprecyzuj: "Zanim cokolwiek zrobisz, przeczytaj plik PROJEKT.md i potwierdź że rozumiesz architekturę"

### Gdy coś nie działa po implementacji
"Test X failuje z błędem: [wklej błąd]. Napraw to nie zmieniając interfejsu publicznego."

### Gdy chcesz zrozumieć decyzję
"Wytłumacz dlaczego wybrałeś to rozwiązanie zamiast [alternatywa]."

### Gdy coś jest niezgodne z planem
"To rozwiązanie odbiega od architektury z PROJEKT.md w zakresie [X]. Dostosuj je do planu."

### Szybki reset jeśli coś się popsuło
git stash         # schowaj zmiany
git stash drop    # usuń
# zacznij etap od nowa z promptem
```
