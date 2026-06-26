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
Zapoznaj się z plikiem PROJEKT.md i ROADMAP.md jeśli są dostępne.

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
- opcjonalne grupy: engines-core (pymupdf4llm, marker-pdf, docling), engines-optional (pdf-craft), llm (anthropic, openai, google-genai)
  UWAGA: użyj google-genai (nowe SDK), NIE google-generativeai (stare, EOL od sierpnia 2025)
  UWAGA: NIE umieszczaj mineru w zależnościach pip. MinerU wymaga pillow>=11, a marker-pdf
  (engines-core) przypina pillow<11 — konflikt nie do rozwiązania w jednym środowisku.
  MinerU jest wołany przez CLI (subprocess), więc instaluje się go IZOLOWANIE:
  uv tool install mineru --with mineru[all]  (poza projektem, nie jako dependency)
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
- ollama_model: str = "qwen3:14b"   # domyślna sugestia; użytkownik nadpisuje w config.toml (na 24 GB można 27-32B)
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

  KRYTYCZNE — DŁAWIENIE ZASOBÓW (inaczej Marker zawiesza WSL na słabszym sprzęcie):
  Marker przez pdftext/Surya domyślnie spawnuje workery = liczba rdzeni CPU, każdy ładuje
  modele → wyczerpanie RAM/VRAM → zawieszenie całego WSL. Domyślnie konwertuj zachowawczo:
  - wyłącz multiprocessing (nowsze API: disable_multiprocessing=True; starsze: NUM_WORKERS=1)
  - ogranicz pdftext_workers=1
  - respektuj zmienną TORCH_DEVICE (pozwól wymusić cpu)
  - czytaj limity z konfiguracji (config.toml): marker_workers, marker_device, marker_max_pages
  Te wartości MUSZĄ być konfigurowalne, z bezpiecznymi (niskimi) domyślnymi.

2. Obsługa use_llm
Jeśli use_llm=True i Marker wspiera to przez konfigurację — przekaż odpowiedni parametr.
Jeśli Marker nie obsługuje w tej wersji — loguj ostrzeżenie i kontynuuj bez LLM.

3. Rejestracja
W engines/__init__.py dodaj MarkerEngine do engine_registry.
Marker powinien być zarejestrowany PO PyMuPDF4LLM (wyżej w liście = wyżej priorytet).

4. Testy integracyjne — OPT-IN i jednostronicowe (NIE mogą wieszać WSL)
tests/conftest.py: ustaw zmienne PRZED importem marker (sesyjnie):
  os.environ.setdefault("PDFTEXT_WORKERS", "1")
  os.environ.setdefault("TORCH_DEVICE", os.environ.get("TORCH_DEVICE", "cpu"))

tests/integration/test_marker.py:
- oznacz CAŁY moduł @pytest.mark.heavy (ciężkie testy ML, wyłączone z domyślnego pytest)
- skipif marker niezainstalowany
- używaj JEDNOSTRONICOWEGO fixture (tests/fixtures/test_text_1page.pdf), nigdy dużych skanów
- w konwersji przekaż disable_multiprocessing=True i ogranicz strony do 1
- konwertuj 1 stronę — sprawdź że wynik niepusty
- NIE rób w teście porównania na wielostronicowym skanie (to dla ręcznego uruchomienia)

W pyproject.toml dodaj:
  [tool.pytest.ini_options]
  markers = ["heavy: ciezkie testy ML (Marker/VLM), uruchamiane recznie"]
  addopts = "-m 'not heavy'"
Wtedy "uv run pytest" pomija ciężkie; "uv run pytest -m heavy" uruchamia świadomie.

Po zakończeniu:
1. Pokaż jak zainstalować Marker: uv add marker-pdf
2. NAJPIERW pobierz modele poza pytestem na 1-stronicowym PDF: marker_single tests/fixtures/test_text_1page.pdf --output_dir /tmp/mk
3. Uruchom lekkie testy: uv run pytest (pomija heavy)
4. Dopiero świadomie i z monitorowaniem (free -h, nvidia-smi): uv run pytest -m heavy
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
- default_model = "qwen3:14b"
- is_available(): GET http://localhost:11434/api/tags timeout=2s, zwróć True jeśli 200
- get_models(): zwróć listę dostępnych modeli z /api/tags
- postprocess(markdown, mode="whole_document", instructions=""):
  model = settings.ollama_model or self.default_model
  POST http://localhost:11434/api/generate, stream=False
  Zastosuj chunkowanie wg `mode` (patrz punkt 5)
  WYŁĄCZ thinking: w ciele żądania ustaw pole "think": False na NAJWYŻSZYM poziomie
    (obok "model", "prompt", "stream") — NIE w "options", bo tam Ollama je ignoruje.
    Powód: modele Qwen3/3.5 mają thinking włączony domyślnie, a do czyszczenia Markdown
    (zadanie dosłowne, nie rozumowe) chain-of-thought tylko spowalnia i miesza wynik.
    Opcjonalnie wystaw to jako pole configu ollama_think: bool = False, gdyby ktoś chciał
    thinking do trudniejszych zadań — ale domyślnie False.

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
Klasa GeminiProvider — użyj NOWEGO SDK google-genai (stare google-generativeai jest EOL):
- is_available(): importlib.metadata.version("google-genai") + klucz w settings
- default_model jako bezpieczny fallback (np. "gemini-2.5-flash"), nadpisywany z configu
- postprocess(markdown, mode="whole_document", instructions=""):
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=settings.gemini_api_key)
    model = settings.gemini_model or self.default_model
    resp = client.models.generate_content(
        model=model,
        contents=POST_PROCESSING_PROMPT + "\n\n" + markdown,
        config=types.GenerateContentConfig(temperature=0.1),
    )
    return LLMResult(text=resp.text, provider_used=self.name)
- import google.genai tylko wewnątrz metody, nie na górze pliku
- obsłuż chunkowanie wg mode (jak pozostali providerzy)

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

MinerU jest instalowany IZOLOWANIE (uv tool install mineru --with mineru[all]), NIE jako pip
dependency — bo wymaga pillow>=11, a Marker przypina pillow<11. Adapter woła jego CLI przez subprocess.
W MinerU 2.x+ komenda nazywa się "mineru" (stare "magic-pdf" to wersje 1.x — nieaktualne).
- is_available(): użyj shutil.which("mineru") — zwraca ścieżkę lub None.
  WAŻNE: na Windows subprocess.run(["mineru", ...]) bez .exe/.cmd rzuca FileNotFoundError;
  shutil.which() poprawnie lokalizuje binarkę z rozszerzeniem. Zwróć True jeśli which != None.
- convert(pdf_path, output_dir=None, **kwargs):
  Uruchom mineru przez pełną ścieżkę z shutil.which (nie samą nazwę): mineru -p pdf_path -o output_dir_temp
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

## PROMPT #10 — Dystrybucja jako pakiet (pip/uv)

```
Jesteśmy na gałęzi etap-10-packaging.

Główny kanał wydania v1.0 to PAKIET Python (pip/uv), NIE frozen binary.
Powód: publikujemy tylko kod MIT; silniki copyleft (PyMuPDF4LLM-AGPL, Marker-GPL, MinerU-AGPL)
instaluje sam użytkownik u siebie. Frozen binary i tak nie przyjmuje silników importowanych po
fakcie (zamrożone site-packages), więc ma sens dopiero z własnym silnikiem z Fazy 2.

1. pyproject.toml — przygotuj do publikacji:
   - metadane: name, version, description, authors, readme, license = "MIT", urls (repo),
     classifiers, requires-python
   - [project.scripts]: pdf2md = "pdf2md.cli.main:cli"; pdf2md-gui = "pdf2md.gui.app:main"
   - [project.optional-dependencies]:
       engines-core = [pymupdf4llm, marker-pdf, docling]
       engines-optional = [pdf-craft]
       llm = [anthropic, openai, google-genai]
   - MinerU NIE w extra (instalowany przez uv tool — patrz Etap 8)

2. Build pakietu:
   uv build        # → dist/pdf2md-<ver>.whl + dist/pdf2md-<ver>.tar.gz

3. docs/INSTALL.md — instrukcja:
   - sam orkiestrator:  uv tool install pdf2md
   - dokładanie silników:  uv pip install pymupdf4llm   (albo docling / marker-pdf)
   - LLM:  uv pip install anthropic   (albo openai / google-genai)
   - silnik CLI:  uv tool install mineru --with mineru[all]
   - pierwsza diagnostyka:  pdf2md doctor  (pokaże, czego brakuje)

4. README — sekcja instalacji + tabela "który silnik czym doinstalować".

5. .github/workflows/release.yml — na tag v*:
   - uv build
   - utwórz GitHub Release i dołącz wheel + sdist (opcjonalnie publish na PyPI przez trusted publishing)

6. docs/RELEASE.md — checklist:
   - [ ] CHANGELOG.md zaktualizowany
   - [ ] wersja w pyproject.toml podbita
   - [ ] uv run pytest zielone
   - [ ] git tag vX.Y.Z && git push origin vX.Y.Z
   - [ ] sprawdź Release na GitHub

Po zakończeniu pokaż jak przetestować w czystym środowisku:
uv build
uv tool install dist/pdf2md-*.whl
pdf2md doctor
uv pip install pymupdf4llm
pdf2md convert tests/fixtures/test_text_1page.pdf
```

> **Frozen binary (PyInstaller) — odłożony do Etapu 10b, PO Fazie 2.** Zamrożona binarka nie
> przyjmie silników importowanych po fakcie, więc ma sens dopiero gdy bundluje własny silnik MIT
> (F02). Wcześniejsza praca z `build.spec` (CPU-only torch, hiddenimports, copy_metadata,
> freeze_support, odchudzony PySide6) zostaje zachowana i przyda się wtedy. Zob. ROADMAP, Etap 10b.

---
---

# FAZA 2 — Promty (premium scan pipeline)

> Te etapy wymagają ukończonej Fazy 1 i GPU. Każdy etap = osobna gałąź = osobny PR, tak jak w Fazie 1.

---

## PROMPT #11 — Preprocessing obrazu

```
Jesteśmy na gałęzi etap-11-preprocessing. Zapoznaj się z PROJEKT.md i sekcją FAZA 2 w ROADMAP.md.

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

> ⚠️ **PROMPT HISTORYCZNY / CZĘŚCIOWO ZASTĄPIONY (czerwiec 2026).** Etap 12 zrealizowano wg
> pierwotnej wersji tego promptu i **domknięto** na MinerU/vlm + PaddleOCR-VL (zob. ROADMAP →
> Etap 12). **NIE uruchamiaj tej wersji ponownie na działającym kodzie** — przepisałaby
> sprawne adaptery. Nieaktualne fragmenty:
> 1. **Surya** — odłożona: marker pinuje `surya-ocr>=0.6.13,<0.7.0` (stare, funkcyjne API; brak
>    `DetectionPredictor`), więc w głównym venv Surya jest redundantna z Markerem. Surya 2.0
>    (serwowany VLM) → FEATURES **F19**. Sekcja „Surya" poniżej jest nieaktualna.
> 2. **PaddleOCR-VL** — NIE startuj serwera z adaptera (`load_model = start genai_server`).
>    Serwer jest **user-managed** (`vllm serve` ręcznie), adapter tylko **pinguje** go w
>    `is_available()` i gada po HTTP → **użyj PROMPTU D9** (zastępuje sekcję PaddleOCR-VL poniżej).
> 3. **Split `InProcessVLMEngine`/`ExternalVLMEngine`** — odłożony: po odłożeniu Suryi nie ma
>    silnika in-process, więc ta podklasa nie miałaby użytkownika (przedwczesna abstrakcja).
>    Obecny pojedynczy `VLMEngine` obsługuje izolowane (olmOCR + PaddleOCR-VL).
> 4. **olmOCR** — do zrobienia później osobnym, celowanym **PROMPTEM D10** (poniżej, w sekcji
>    retrofit). Sekcja „olmOCR" tutaj zostaje jako referencja.
>
> Poniższa treść pozostaje jako **referencja architektury dwóch kategorii silników** — nie do
> ponownego wykonania w całości.

```
Jesteśmy na gałęzi etap-12-vlm-ocr.

Zaimplementuj cztery silniki OCR oparte na modelach wizyjno-językowych jako adaptery ConversionEngine.
WAŻNE: wszystkie wymagają GPU. is_available() musi zwracać False BEZ błędu gdy brak GPU lub silnika.

ARCHITEKTURA — dwie kategorie silników VLM (to wynik realnego debugowania zależności):
- IN-PROCESS: Surya — torch + transformers w GŁÓWNYM środowisku projektu (zgodny z Markerem,
  transformers>=4.48). Importowany normalnie, unload przez gc/empty_cache.
- IZOLOWANE (subprocess/usługa): olmOCR i PaddleOCR-VL — ciężkie stosy (vLLM / PaddlePaddle),
  konfliktują z głównym środowiskiem, więc żyją w OSOBNYCH środowiskach i są wołane przez
  subprocess lub HTTP. NIE importuj ich do procesu projektu. unload = zamknięcie procesu/serwera
  (VRAM zwalnia się sam przy wyjściu procesu — prościej i pewniej niż empty_cache).

1. src/pdf2md/engines/vlm_base.py
Klasa bazowa VLMEngine(ConversionEngine):
- requires_gpu = True
- has_gpu() -> bool: try import torch; return torch.cuda.is_available() / except: False
  (import torch wewnątrz metody, nie na górze pliku)
- is_available() w podklasach: dla in-process — importlib.metadata.version(...) + has_gpu();
  dla izolowanych — sprawdzenie obecności środowiska/komendy (np. ścieżka do venv/CLI,
  shutil.which) + has_gpu(), BEZ importu modelu.
- ZARZĄDZANIE VRAM (krytyczne na 24 GB): load_model() i unload_model().
  * in-process (Surya): unload_model() usuwa referencje, gc.collect(), torch.cuda.empty_cache().
  * izolowane (olmOCR/PaddleOCR-VL): load = start procesu/serwera, unload = zamknięcie procesu
    (terminate + wait; VRAM zwalnia OS przy wyjściu). To prostsze i pewniejsze.
  Powód: olmOCR-2-7B (~7-8 GB) i model korekty qwen3:14b (~9-10 GB) NIE zmieszczą się
  jednocześnie w 24 GB. Pipeline ładuje VLM → przetwarza WSZYSTKIE strony → unload_model()
  → dopiero potem faza korekty LLM (Etap 13). Nigdy oba modele naraz.
- Rozważ dwie podklasy bazowe: InProcessVLMEngine i ExternalVLMEngine (subprocess/HTTP),
  żeby logika is_available()/load/unload nie mieszała się między kategoriami.
- wspólna logika: przetwarzanie paczkowe (scan/preprocessing.iter_page_batches),
  OCR per strona, zapis do work/ocr_json/ i work/md_pages/, usuwanie PNG po paczce

2. src/pdf2md/engines/surya_engine.py  [IN-PROCESS — zrób jako pierwszy, najłatwiejszy]
Klasa SuryaEngine(InProcessVLMEngine):
- name = "Surya"
- description = "Layout + OCR + reading order, dobry jako kontrola/fallback"
- używa API surya w głównym venv (ten sam surya co Marker; transformers>=4.48). Import leniwy.
- is_available(): importlib.metadata.version("surya-ocr") w try/except + has_gpu().
- To domyka „co najmniej jeden silnik VLM działa end-to-end" bez ruszania izolowanych stosów.

3. src/pdf2md/engines/olmocr_engine.py  [IZOLOWANY — subprocess]
Klasa OlmOCREngine(ExternalVLMEngine):
- name = "olmOCR"
- description = "VLM 7B do skanów: czysty Markdown, równania, tabele, kolejność czytania"
- supports_ocr = True
- model: allenai/olmOCR-2-7B-1025-FP8 (sprawdź najnowszą wersję; FP8 OK na Blackwellu sm_120)
- środowisko: osobny venv (np. ~/.venvs/olmocr), ścieżka do jego python w config.toml
  (pole olmocr_python: str | None). is_available(): venv istnieje + has_gpu(). Bez importu olmocr.
- convert(): subprocess do `python -m olmocr.pipeline ...` (sprawdź aktualną komendę w docs),
  z env VLLM_USE_FLASHINFER_SAMPLER=0 (bez tego flashinfer JIT-uje sampler przez nvcc i pada
  na nowym GPU). unload = zamknięcie procesu.

4. src/pdf2md/engines/paddleocr_vl_engine.py  [IZOLOWANY — usługa HTTP]
Klasa PaddleOCRVLEngine(ExternalVLMEngine):
- name = "PaddleOCR-VL"
- description = "Lekki (0.9B) parser dokumentów VLM, wielojęzyczny, SOTA, wydajny"
- MODEL DZIAŁA JAKO USŁUGA: `paddleocr genai_server --model_name PaddleOCR-VL-1.6-0.9B
  --backend vllm --port <port>` w osobnym środowisku. Adapter rozmawia z nim po HTTP
  (API zgodne z OpenAI, jak Ollama) albo woła CLI `paddleocr doc_parser --vl_rec_backend
  vllm-server --vl_rec_server_url http://127.0.0.1:<port>/v1`.
- config.toml: paddleocr_vl_url: str | None (jeśli usługa już chodzi) ORAZ opcjonalnie
  paddleocr_env: str | None (ścieżka do venv, gdy adapter ma sam wystartować serwer).
- is_available(): jeśli podany URL — ping serwera; w przeciwnym razie obecność środowiska
  + has_gpu(). Bez importu paddle.
- load_model() = start genai_server (subprocess) jeśli nie podano gotowego URL; unload = zamknięcie.
- UWAGA Blackwell (sm_120): wymaga vLLM z nightly (cu129) + prekompilowany flash-attn — patrz
  „PaddleOCR-VL NVIDIA Blackwell GPUs Usage Tutorial". To należy do INSTALACJI środowiska, nie kodu.

5. Rejestracja w engines/__init__.py (po silnikach Fazy 1).

6. Testy tests/integration/test_vlm_engines.py:
- skipif not has_gpu() lub silnik/środowisko niezainstalowane
- Surya: konwersja jednej strony skanu, wynik niepusty
- olmOCR/PaddleOCR-VL: jeśli środowisko/usługa dostępne — smoke test; inaczej skip

Po zakończeniu:
1. Pokaż jak zainstalować każdy silnik (Surya w głównym venv; olmOCR i PaddleOCR-VL w osobnych
   środowiskach — odeślij do SILNIKI_INSTALACJA.md)
2. Pokaż jak sprawdzić GPU: python -c "import torch; print(torch.cuda.is_available())"
3. pdf2md list-engines (Surya/olmOCR/PaddleOCR-VL widoczne, oznaczone wymaganiem GPU i kategorią)
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
  Używa SCAN_CORRECTION_PROMPT i dostawcy LLM z Fazy 1 (preferowany lokalny Ollama + Qwen3 14B).
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
  llm_cleanup: {enabled: true, provider: ollama, model: qwen3:14b, chunk: page}
  output: {markdown: true, epub: true}

profiles/balanced.yaml:
  name: balanced
  dpi: 400
  preprocess: {deskew: true, denoise: true, dewarp: auto, crop: auto}
  layout: {engine: surya}
  ocr: {engine: paddleocr-vl, gpu: true}
  llm_cleanup: {enabled: true, provider: ollama, model: qwen3:14b, chunk: page}
  postprocess: {remove_headers_footers: true, merge_paragraphs: true, fix_hyphenation: true}
  output: {markdown: true, epub: true, quality_report: true}

profiles/premium.yaml:
  name: premium
  dpi: 400
  preprocess: {deskew: true, denoise: true, dewarp: true, crop: true}
  layout: {engine: olmocr}
  ocr: {primary: olmocr, secondary: surya, compare_outputs: true}
  llm_cleanup: {enabled: true, provider: ollama, model: qwen3:14b, mode: conservative, chunk: page_then_chapter}
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
---

# Promty dodatkowe (retrofit do istniejącego projektu)

> Te prompty nie należą do liniowej roadmapy — to ulepszenia dodawane do już działających
> etapów. Każdy zakłada, że odpowiednie komponenty (silnik, GUI, worker) już istnieją.
> Pracuj na osobnej gałęzi (np. `fix-...`), zrób PR jak zwykle.

## PROMPT D1 — GUI: wybór urządzenia Docling (cpu/cuda/auto)

> Wymaga: DoclingEngine (Etap 8), okno ustawień (Etap 7), ConversionWorker (Etap 6), config.toml (Etap 1).

```
Dodaj możliwość wyboru urządzenia dla silnika Docling (cpu / cuda / auto),
zapisywaną w config.toml i przekazywaną z GUI przez ConversionWorker do DoclingEngine.
Najpierw sprawdź faktyczne API zainstalowanej wersji docling (accelerator_options).

1. core/config.py
- Dodaj do Settings pole: docling_device: str = "auto"  (dozwolone: "auto", "cpu", "cuda")
- Upewnij się że jest odczytywane z config.toml i zapisywane przez save_settings()

2. engines/docling_engine.py
- W convert() dodaj parametr device: str = "auto"
- Zmapuj string na enum Docling. Oczekiwane API (zweryfikuj w zainstalowanej wersji):
    from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.base_models import InputFormat
    _MAP = {"auto": AcceleratorDevice.AUTO, "cpu": AcceleratorDevice.CPU, "cuda": AcceleratorDevice.CUDA}
    accel = AcceleratorOptions(device=_MAP[device])
    popts = PdfPipelineOptions(); popts.accelerator_options = accel
    converter = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=popts)})
- GRACEFUL FALLBACK: jeśli device == "cuda" ale torch.cuda.is_available() == False,
  zaloguj ostrzeżenie i użyj CPU zamiast rzucać błędem. "auto" zostaw bez sprawdzania
  (Docling sam wykryje). Import torch tylko w tej gałęzi, nie na górze pliku.
- Zachowaj dotychczasowe is_available() przez importlib.metadata (bez importu docling).

3. core/converter.py
- Rozszerz Converter.convert() o parametr engine_options: dict | None = None
- Przekaż go do silnika: engine.convert(pdf_path, **(engine_options or {}))
- Dzięki temu device trafia do DoclingEngine jako engine_options={"device": ...}

4. gui/workers.py (ConversionWorker)
- W __init__ przyjmij/odczytaj docling_device z settings (get_settings().docling_device)
- W run(), gdy wybrany silnik to Docling, wywołaj converter.convert(..., engine_options={"device": self.docling_device})
- Dla innych silników engine_options pomiń (lub przekaż pusty)

5. gui/settings_dialog.py
- W zakładce "Domyślne ustawienia" dodaj etykietę "Docling device" i QComboBox
  z pozycjami: "auto", "cpu", "cuda"
- Przy otwarciu okna ustaw bieżącą wartość z get_settings().docling_device
- Przy zapisie (OK/Zastosuj) zapisz wybór do config.toml przez core/config.save_settings()
  (NIE QSettings — trzymamy jedno źródło prawdy w config.toml)
- Opcjonalnie: jeśli torch.cuda niedostępne, dodaj przy "cuda" dopisek w tooltipie
  "GPU niewykryte — zostanie użyte CPU"

6. Testy
- tests/unit/test_config.py: docling_device domyślnie "auto", zapis/odczyt z config.toml
- tests/unit/test_docling_engine.py (mock): device="cuda" przy braku GPU → fallback na CPU
  bez wyjątku; sprawdź że poprawny AcceleratorDevice jest budowany dla każdej opcji
- tests/unit/test_converter.py: engine_options przekazywane do engine.convert()

Po zakończeniu pokaż diff i uruchom: uv run pytest tests/unit -v
Nie uruchamiaj ciężkiej konwersji automatycznie.
```

---

## PROMPT D2 — Naprawa: testy Markera zawieszają WSL (dławienie zasobów)

> Wymaga: zaimplementowany MarkerEngine i jego testy (Etap 3). Dla słabszego sprzętu
> (≤16 GB RAM / ≤8 GB VRAM), gdzie Marker spawnuje workery na każdym rdzeniu i wyczerpuje
> pamięć, wieszając całą maszynę WSL.
>
> **Po stronie użytkownika (poza Claude Code), wykonaj najpierw:**
> 1. Ustaw `.wslconfig` z limitami RAM/swap/procesorów (PROJEKT.md, KROK 6b) i `wsl --shutdown`.
> 2. Utwórz jednostronicowy fixture `tests/fixtures/test_text_1page.pdf` (bogaty w tekst).
> 3. Pobierz modele Markera POZA pytestem: `TORCH_DEVICE=cpu uv run marker_single tests/fixtures/test_text_1page.pdf --output_dir /tmp/mk`
> 4. Testy `heavy` uruchamiaj świadomie, z monitorowaniem (`watch -n1 free -h`, `nvidia-smi -l 1`).

```
Mamy już zaimplementowany MarkerEngine i testy, ale testy Markera zawieszają WSL
(Marker spawnuje workery = liczba rdzeni CPU, wyczerpuje RAM/VRAM). Pracuję na słabym
sprzęcie: GTX 1070 8 GB VRAM, 16 GB RAM. Wprowadź następujące poprawki:

1. tests/conftest.py — utwórz jeśli nie istnieje, ustaw PRZED importem marker:
   import os
   os.environ.setdefault("PDFTEXT_WORKERS", "1")
   os.environ.setdefault("TORCH_DEVICE", "cpu")

2. engines/marker_engine.py — w convert() wymuś zachowawcze ustawienia:
   - disable_multiprocessing=True (nowsze API) lub NUM_WORKERS=1 (starsze)
   - pdftext_workers=1
   - respektuj TORCH_DEVICE z env
   - dodaj parametry konfigurowalne z config.toml: marker_device, marker_workers, marker_max_pages
   Sprawdź NAJPIERW faktyczne API zainstalowanej wersji marker-pdf (marker/settings.py).

3. tests/integration/test_marker.py — przerób:
   - oznacz cały moduł @pytest.mark.heavy
   - używaj jednostronicowego fixture test_text_1page.pdf (nie skanów wielostronicowych)
   - w teście przekaż disable_multiprocessing=True, ogranicz do 1 strony

4. pyproject.toml — dodaj (jeśli jeszcze nie ma):
   [tool.pytest.ini_options]
   markers = ["heavy: ciezkie testy ML, uruchamiane recznie"]
   addopts = "-m 'not heavy'"

Po zmianach pokaż diff i NIE uruchamiaj testów heavy automatycznie.
```

---

## PROMPT D3 — Docling/CUDA: realny test GPU zamiast samego is_available()

> Wymaga: DoclingEngine (Etap 8), `detection/dependencies.py` (Etap 1).
> Powód: na starszych kartach (np. GTX 1070, sm_61) `torch.cuda.is_available()` zwraca True,
> ale kernel nie istnieje → `cudaErrorNoKernelImageForDevice` przy faktycznym wykonaniu.
> `device="auto"` wybierał wtedy GPU i Docling się wywracał.

```
DoclingEngine z device="auto" crashuje na starej karcie (GTX 1070, sm_61): torch.cuda.is_available()
zwraca True, ale kernel nie istnieje → cudaErrorNoKernelImageForDevice. Napraw detekcję GPU.

1. detection/dependencies.py — dodaj funkcję cuda_usable() -> bool:
   - jeśli torch niezaimportowalny lub torch.cuda.is_available() == False → False
   - w przeciwnym razie zrób SMOKE TEST: x = torch.zeros(1).cuda(); torch.cuda.synchronize()
   - jeśli rzuci wyjątek (np. AcceleratorError/RuntimeError) → zwróć False
   - wynik zcache'uj (functools.lru_cache), żeby nie testować przy każdym wywołaniu

2. engines/docling_engine.py — w mapowaniu device:
   - "cpu" → CPU
   - "cuda" → jeśli cuda_usable(): CUDA; inaczej loguj ostrzeżenie i CPU
   - "auto" → jeśli cuda_usable(): CUDA; inaczej CPU (NIE polegaj na samym AcceleratorDevice.AUTO,
     bo Docling/torch wykrywa niekompatybilne GPU jako dostępne i crashuje)

3. Zastosuj cuda_usable() też w przyszłych silnikach GPU (Marker device, VLM) — wspólne źródło prawdy.

4. doctor: w komendzie `pdf2md doctor` pokazuj wynik cuda_usable() (a nie tylko torch.cuda.is_available()),
   żeby od razu było widać "CUDA obecne, ale nieużywalne na tej karcie".

5. Testy (mock): cuda_usable() False → device auto/cuda dają CPU bez wyjątku.

Pokaż diff, uruchom uv run pytest tests/unit -v.
```

---

## PROMPT D4 — GUI: bezpieczne otwieranie folderu wyników (WSL/cross-platform)

> Wymaga: GUI (Etap 6/7). Powód: `_open_output_folder()` woła `xdg-open`, którego w WSL nie ma
> → FileNotFoundError; dodatkowo było wołane nawet po nieudanej konwersji.

```
_open_output_folder() crashuje w WSL (brak xdg-open) i jest wołane nawet po nieudanej konwersji.

1. utils/open_path.py — funkcja open_in_file_manager(path) odporna na brak narzędzia:
   - Windows: os.startfile
   - macOS: "open"
   - WSL (wykryj: "microsoft" w platform.uname().release.lower()): "wslview" jeśli jest (shutil.which),
     inaczej "explorer.exe". UWAGA: explorer.exe zwraca kod wyjścia 1 nawet przy sukcesie —
     NIE traktuj niezerowego return code jako błędu.
   - Linux: "xdg-open" jeśli jest (shutil.which)
   - całość w try/except — brak narzędzia LOGUJE ostrzeżenie, NIE rzuca wyjątku

2. gui/main_window.py:
   - _open_output_folder() używa open_in_file_manager() i łapie wyjątki
   - w _show_done_message(): proponuj/otwieraj folder TYLKO gdy success > 0

3. Testy (mock subprocess): brak narzędzia → brak wyjątku (tylko log); na WSL wybierany explorer.exe.

Pokaż diff, uruchom uv run pytest tests/unit -v.
```

---

## PROMPT D5 — Migracja GeminiProvider na google-genai (nowe SDK)

> Wymaga: GeminiProvider (Etap 4). Powód: stare SDK `google-generativeai` jest EOL od sierpnia 2025;
> zastąpione przez `google-genai` (`from google import genai`, wzorzec klienta). Nowsze modele
> Gemini idą przez nowe SDK.

```
Stare SDK google-generativeai jest EOL (sierpień 2025). Przemigruj GeminiProvider na google-genai.

1. pyproject.toml — w grupie llm zamień google-generativeai na google-genai.

2. llm/gemini_provider.py — przepisz na nowy wzorzec:
   - is_available(): importlib.metadata.version("google-genai") w try/except + klucz w settings
   - postprocess(markdown, mode, instructions):
       from google import genai
       from google.genai import types
       client = genai.Client(api_key=settings.gemini_api_key)
       model = settings.gemini_model or self.default_model
       resp = client.models.generate_content(
           model=model,
           contents=POST_PROCESSING_PROMPT + "\n\n" + markdown,
           config=types.GenerateContentConfig(temperature=0.1),
       )
       return LLMResult(text=resp.text, provider_used=self.name)
   - default_model jako BEZPIECZNY fallback (np. "gemini-2.5-flash"), nadpisywany z configu.
     Nazwy modeli Gemini szybko się zmieniają — użytkownik ustawia aktualny przez config.
   - import google.genai tylko wewnątrz metody, nie na górze pliku
   - obsłuż chunkowanie wg mode (jak inni providerzy)

3. Komunikat braku SDK zmień na "google-genai nie jest zainstalowany" (był google-generativeai).

4. Testy (mock genai.Client): is_available bez paczki → False; postprocess zwraca LLMResult.

Pokaż diff, uruchom uv run pytest tests/unit -v.
```

---

## PROMPT D6 — Izolacja testów config od `.env` i zmiennych środowiskowych

> Wymaga: testy config (Etap 1/9). Powód: na maszynie z plikiem `.env` (lub ustawionymi
> zmiennymi `OPENAI_API_KEY` itd.) testy `test_config.py` padają, bo `.env`/env nadpisują
> config także w testach. Objaw po migracji: `assert ... == "dev-key"` dostaje `sk-...`
> (placeholder z `.env`). Testy są wtedy zależne od maszyny / „flaky".

```
Testy test_config.py padają na maszynie, która ma plik .env z kluczami API
(OPENAI_API_KEY, ANTHROPIC_API_KEY itd.), bo .env/zmienne środowiskowe nadpisują config
także w testach. Napraw IZOLACJĘ testów config, nie zmieniając zachowania aplikacji.

1. W fixture isolated_config (lub w conftest dla testów config):
   - przez monkeypatch USUŃ zmienne środowiskowe kluczy/configu na czas testu:
     monkeypatch.delenv dla: ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY,
     OLLAMA_MODEL, OLLAMA_URL (i innych, które config czyta z env) — raising=False
   - zapobiegnij wczytaniu .env z katalogu projektu: monkeypatch.chdir(tmp_path)
     ORAZ jeśli config jawnie ładuje .env (load_dotenv / pydantic-settings env_file),
     wskaż nieistniejącą ścieżkę .env albo wyłącz to ładowanie w testach
   - dopiero potem zwróć izolowaną ścieżkę config.toml

2. Sprawdź w core/config.py, JAK .env jest wczytywany i czy override z env stosuje się
   też przy jawnym Settings(...) — jeśli tak, rozważ, by override z env/.env dotyczył tylko
   get_settings() (ładowania z dysku), a nie jawnej konstrukcji obiektu Settings.

3. Po poprawce uruchom: uv run pytest tests/unit/test_config.py -v
   Testy mają przechodzić niezależnie od tego, czy w systemie jest .env z kluczami.

Pokaż diff.
```

---

## PROMPT D7 — MinerU: konfigurowalny backend + logowanie stderr przy błędzie

> Wymaga: adapter MinerU (Etap 8). Powód: domyślny backend MinerU (hybrid → vLLM →
> flashinfer) wymaga JIT-kompilacji kerneli i na świeżej maszynie/nowym GPU pada
> (`Failed to find C compiler` bez build-essential; `Could not find nvcc` przez bug
> flashinfer 0.4.0+ bez CUDA Toolkit). Backend `pipeline` omija cały stos vLLM/flashinfer
> i działa niezawodnie na GPU przez torch. Dodatkowo adapter łapie CalledProcessError, ale
> NIE pokazuje stderr/stdout MinerU — w GUI widać tylko „exit status 1" bez przyczyny, co
> uniemożliwia diagnozę.

```
W engines/mineru_engine.py popraw adapter MinerU. NIE zmieniaj architektury (dalej
subprocess + shutil.which), tylko dwie rzeczy:

1. KONFIGUROWALNY BACKEND:
   - Dodaj do config.toml pole mineru_backend: str = "pipeline" (bezpieczny domyślny).
     Zaktualizuj model konfiguracji (core/config.py) i — jeśli masz GUI ustawień —
     pole wyboru, ale to opcjonalne.
   - W convert() doklej do komendy: "-b", <backend z configu>.
     Czyli: [mineru_path, "-p", pdf_path, "-o", out_dir, "-b", backend].
   - Uzasadnienie domyślnego "pipeline": backend vLLM/VLM wymaga sprawnego stosu
     vLLM + flashinfer + nvcc/CUDA Toolkit, co na nowym GPU (np. Blackwell sm_120)
     bywa kruche. "pipeline" omija to i działa na GPU przez torch. Użytkownik z działającym
     stackiem VLM może przełączyć w config.toml na wariant vlm.

2. ENV DLA BACKENDU VLM (żeby vlm ruszył bez CUDA Toolkitu):
   - Gdy wybrany backend to wariant vlm (nazwa zaczyna się od "vlm" / nie jest "pipeline"),
     ustaw w środowisku subprocesu: VLLM_USE_FLASHINFER_SAMPLER=0.
     Przekaż env do subprocess.run jako env={**os.environ, "VLLM_USE_FLASHINFER_SAMPLER": "0"}.
   - Powód: na nowym GPU (np. Blackwell sm_120) flashinfer nie ma gotowego cubina i
     JIT-kompiluje sampler przez nvcc — bez CUDA Toolkitu to pada. Ta zmienna wymusza
     natywny sampler PyTorch (atencja i tak idzie przez FLASH_ATTN), więc vlm startuje
     bez nvcc, kosztem nieistotnie wolniejszego samplingu (wąskim gardłem jest enkoder
     wizyjny, nie sampling). Dla backendu "pipeline" zmiennej NIE ustawiaj (zbędna).

3. LOGOWANIE BŁĘDU:
   - Owiń subprocess.run(...) w try/except subprocess.CalledProcessError as e.
   - W except: zaloguj logger.error z e.stderr i e.stdout (każde obetnij do ~2000 znaków,
     żeby nie zalać logu), zanim podniesiesz wyjątek / zwrócisz ConversionResult z błędem.
   - Komunikat błędu zwracany do GUI ma zawierać skróconą końcówkę stderr (ostatnie ~500
     znaków), żeby przyczyna była widoczna bez grzebania w terminalu.

4. Zachowaj capture_output=True, text=True i check=True (check przez try/except).

5. Jeśli masz test adaptera MinerU, dodaj/zaktualizuj testy:
   - komenda zawiera "-b pipeline" przy domyślnym configu (mock subprocess.run, asercja na argv);
   - dla backendu vlm w env subprocesu jest VLLM_USE_FLASHINFER_SAMPLER=0, a dla pipeline nie ma.

Pokaż diff.
```

> Uwaga (poza promptem, do INSTALL.md / troubleshooting): backend `vlm` MinerU wymaga
> `build-essential` (gcc dla Tritona — inaczej „Failed to find C compiler"). Dodatkowo na
> nowym GPU flashinfer JIT-kompiluje sampler przez nvcc i bez CUDA Toolkitu pada
> („Could not find nvcc" / `FileNotFoundError: 'nvcc'`). Właściwy, najlżejszy fix to
> `VLLM_USE_FLASHINFER_SAMPLER=0` (adapter ustawia to sam — patrz pkt 2). UWAGA: cofanie
> flashinfera do 0.3.0 NIE pomaga na świeżej architekturze (np. Blackwell sm_120), bo brak
> gotowego cubina wymusza JIT niezależnie od wersji — to ślepa uliczka. Backend `pipeline`
> nie wymaga ani gcc-do-flashinfera, ani nvcc.

---

## PROMPT D8 — Marker: konfigurowalne rozmiary batchy GPU + TORCH_DEVICE

> Wymaga: adapter Marker (Etap 8). Powód: Marker (surya) używa GPU, ale domyślne rozmiary
> batchy są zachowawcze (pod małe karty), więc na mocnym GPU (RTX 5090, 24 GB) karta jest
> niedociążona. Główna dźwignia wydajności to env-vary batchy surya, ustawiane PRZED
> importem markera. Marker jest silnikiem importowanym w procesie, więc nie da się ich
> podać flagą CLI per-wywołanie — trzeba ustawić os.environ zanim zaimportujesz/uruchomisz
> marker w convert(). UWAGA: to NIE zrobi z Markera vLLM — pełne nasycenie GPU to rola
> MinerU/vlm; D8 tylko podnosi wykorzystanie Markera z domyślnego „zachowawczego" wyżej.

```
W engines/marker_engine.py dodaj konfigurowalne strojenie GPU dla Markera (surya).
NIE zmieniaj architektury (dalej leniwy import w convert()).

1. KONFIG:
   - Dodaj do config.toml (i modelu w core/config.py) pola, wszystkie opcjonalne (None = nie ruszaj):
     marker_torch_device: str | None = None          # np. "cuda", "cpu"
     marker_recognition_batch_size: int | None = None
     marker_detector_batch_size: int | None = None
     marker_layout_batch_size: int | None = None
     marker_table_rec_batch_size: int | None = None
   - Dokładna lista nazw env surya bywa wersjozależna — odczytaj aktualny zestaw z
     surya/settings.py w zainstalowanej wersji i zmapuj tylko te, które istnieją.

2. USTAWIANIE PRZED IMPORTEM:
   - W convert(), PRZED self._load_marker_api()/importem markera, dla każdego pola != None
     ustaw odpowiedni os.environ:
       marker_torch_device          -> TORCH_DEVICE
       marker_recognition_batch_size -> RECOGNITION_BATCH_SIZE
       marker_detector_batch_size    -> DETECTOR_BATCH_SIZE
       marker_layout_batch_size      -> LAYOUT_BATCH_SIZE
       marker_table_rec_batch_size   -> TABLE_REC_BATCH_SIZE
     (wartości int jako str). Jeśli pole None — NIE ustawiaj env (zostaw auto-dobór surya).
   - Zrób to idempotentnie i tylko dla istniejących w danej wersji nazw (patrz pkt 1).

3. DOKUMENTACJA/UX:
   - W komentarzu/docstringu zaznacz: batche dobiera się empirycznie patrząc na
     `nvidia-smi -l 1`; podnoś aż VRAM/util sensownie rośnie, ale przed OOM. Na 24 GB
     jest duży zapas (rząd ~50-280 MB VRAM na element batcha, zależnie od modelu/wersji).
   - Zaznacz, że batche działają niezależnie od dławienia multiprocessingu z D2
     (disable_multiprocessing dotyczy CPU-side, nie GPU batchy).

4. TEST: jeśli masz test adaptera Markera, dodaj test sprawdzający, że przy ustawionym
   marker_recognition_batch_size w configu odpowiedni os.environ jest ustawiony przed importem
   (monkeypatch os.environ + mock importu/_load_marker_api, asercja na wartość).

Pokaż diff.
```

> Uwaga (poza promptem): D8 to nie jest „tryb pełnego GPU jak MinerU". Marker (surya) to
> zwykłe modele PyTorch uruchamiane sekwencyjnie (detekcja → layout → rozpoznawanie), bez
> serwerowego silnika typu vLLM. Na pojedynczym, małym dokumencie 5090 i tak będzie
> niedociążony — to natura Markera, nie wada configu. Do faktycznego nasycenia karty służy
> MinerU/vlm. D8 jest komplementarny: poprawia wykorzystanie Markera tam, gdzie batch realnie
> rośnie (większe/wielostronicowe skany, wsad plików).

---

## PROMPT D9 — PaddleOCR-VL: `is_available()` pinguje serwer + konwersja po HTTP

> Wymaga: adapter PaddleOCR-VL (Etap 12). Powód: PaddleOCR-VL to **silnik-usługa** — model
> stoi w izolowanym serwerze vLLM (API zgodne z OpenAI na `paddleocr_vl_url`), a adapter gada
> z nim po HTTP, jak OllamaProvider. Obecny `is_available()` sprawdza import `paddle`/
> `paddlepaddle`, co jest błędne na dwa sposoby: (1) do samego VLM `paddle` nie jest potrzebny
> (framework layoutu to osobna, opcjonalna warstwa), (2) „dostępność" silnika-usługi to
> **osiągalność serwera**, nie obecność pakietu w venv. Efekt: `doctor` pokazuje ❌
> „Niezainstalowany" z błędną podpowiedzią „pip install paddlepaddle", mimo że serwer działa
> i poprawnie zwraca OCR. To świadome odstępstwo od domyślnej reguły „`is_available()` przez
> `importlib.metadata`" — uzasadnione typem silnika (usługa, nie pakiet).

```
W engines/paddleocr_vl_engine.py popraw adapter PaddleOCR-VL. Architektura bez zmian
(silnik-usługa, klient HTTP). Zmień cztery rzeczy:

1. is_available() = PING SERWERA, nie import paddle:
   - Dodaj do konfiguracji (core/config.py) pola:
       paddleocr_vl_url: str = "http://localhost:8000/v1"
       paddleocr_vl_model: str = "PaddlePaddle/PaddleOCR-VL-1.6"
       paddleocr_vl_prompt: str = "OCR:"
       paddleocr_vl_timeout: float = 120.0   # sekundy na stronę
   - is_available() robi krótki GET na {paddleocr_vl_url}/models (serwery OpenAI-compatible
     wystawiają /v1/models), timeout ~2-3 s. Zwróć True przy HTTP 200, False przy
     ConnectionError/Timeout/innym wyjątku. is_available() NIGDY nie rzuca wyjątku i NIE
     importuje paddle/paddlepaddle.
   - Użyj tego samego klienta HTTP co OllamaProvider (httpx/requests).

2. POPRAW PODPOWIEDŹ (hint) w metadanych silnika:
   - Zamiast „pip install paddlepaddle..." daj sens usługi:
     „Uruchom serwer: VLLM_USE_FLASHINFER_SAMPLER=0 vllm serve PaddlePaddle/PaddleOCR-VL-1.6
      --trust-remote-code --no-enable-prefix-caching (zob. SILNIKI_INSTALACJA.md 2.8)".
   - Jeśli masz pole opisujące, co znaczy „dostępny", napisz: „serwer pod paddleocr_vl_url
     odpowiada".

3. convert() = OCR strony po HTTP (zostaw renderowanie stron w vlm_base):
   - Renderowanie PDF→obraz i pętla po stronach/batchach zostają w vlm_base (preprocessing:
     DPI, PIL). W metodzie, którą vlm_base woła per-stronę (tej, którą nadpisuje adapter),
     zamiast lokalnego modelu wyślij obraz po HTTP:
       * zakoduj stronę PNG → base64,
       * POST na {paddleocr_vl_url}/chat/completions z ciałem:
         {
           "model": <paddleocr_vl_model>,
           "messages": [{"role":"user","content":[
             {"type":"image_url","image_url":{"url":"data:image/png;base64,<B64>"}},
             {"type":"text","text": <paddleocr_vl_prompt>}]}],
           "temperature": 0.0
         }
       * timeout = paddleocr_vl_timeout,
       * tekst strony = resp["choices"][0]["message"]["content"].
   - Składanie stron w jeden Markdown jak w pozostałych silnikach VLM (separator stron
     zgodny z konwencją vlm_base).

4. unload_model() = no-op z logiem:
   - Silnik-usługa nie trzyma modelu w procesie pdf2md — VRAM jest po stronie serwera.
     Nie zabijaj serwera z adaptera (cykl życia serwera jest zewnętrzny/user-managed w v1.0).
     unload_model() zaloguj na DEBUG: „PaddleOCR-VL to serwer zewnętrzny; VRAM zwalnia się
     przez zatrzymanie serwera (pkill -f 'vllm serve')".

OBSŁUGA BŁĘDÓW w convert():
   - ConnectionError/Timeout → ConversionResult z błędem:
     „Serwer PaddleOCR-VL pod {paddleocr_vl_url} nie odpowiada — uruchom go
      (SILNIKI_INSTALACJA.md 2.8)".
   - HTTP != 200 → zaloguj logger.error ze statusem i obciętym body (~500 znaków) i zwróć
     ConversionResult z błędem zawierającym tę końcówkę.

TESTY (mock klienta HTTP, bez realnego serwera):
   - is_available(): True gdy GET /models zwraca 200; False gdy klient rzuca ConnectionError.
   - convert(): asercja na kształcie POST (url /chat/completions, model z configu, content
     ma image_url+text, temperature 0.0); poprawne wyciągnięcie choices[0].message.content.
   - is_available() nie woła importu paddle (np. brak paddle w środowisku testowym nie psuje testu).

Pokaż diff.
```

> Uwaga (poza promptem): docelowo PaddleOCR-VL jako silnik-usługa korzysta najlepiej z trwałego
> serwera (model ciepły, szybkie strony — dobre do wsadu/książek). Zarządzanie cyklem życia
> serwera (start/stop, ~92% VRAM) jest w v1.0 ręczne; ewentualne automatyczne podnoszenie/
> ubijanie serwera z poziomu pdf2md to osobny feature, nie ten prompt. Przepis startu serwera
> i test `curl` — SILNIKI_INSTALACJA.md sek. 2.8.

---

## PROMPT D10 — olmOCR: izolowany silnik subprocess (DO WYKONANIA PÓŹNIEJ)

> ⏳ **Status: odłożony.** Etap 12 jest już domknięty na MinerU/vlm + PaddleOCR-VL — olmOCR NIE
> jest wymagany do jego ukończenia. To kandydat na **drugi/trzeci silnik VLM-OCR**, gdy zechcesz
> rozszerzyć zestaw. Adapter `olmocr_engine.py` już istnieje (z pierwotnego Etapu 12) i importuje
> się poprawnie (izolowany — nie ciągnie `olmocr` do procesu), ale **nie jest przetestowany
> end-to-end** i wymaga (a) instalacji izolowanego środowiska, (b) weryfikacji wywołania
> subprocess pod aktualne API olmOCR.
>
> Powód architektury: olmOCR-2-7B to ciężki stos vLLM, konfliktuje z głównym środowiskiem →
> żyje w OSOBNYM venv i jest wołany przez subprocess (jak MinerU). `is_available()` sprawdza
> obecność środowiska, NIE importuje `olmocr`. unload = zamknięcie procesu (VRAM zwalnia OS).

```
KROK 1 — ŚRODOWISKO (to nie jest kod; zrób wg SILNIKI_INSTALACJA.md sek. 2.7):
- uv venv ~/.venvs/olmocr, instalacja olmocr + model (allenai/olmOCR-2-...-FP8; FP8 OK na sm_120).
- ZWERYFIKUJ AKTUALNĄ komendę pipeline'u i nazwę modelu w dokumentacji olmOCR — to ruchomy cel,
  nie polegaj na pamięci. Sprawdź, jak uruchomić olmOCR na pojedynczym PDF/obrazie i w jakim
  formacie zwraca wynik (Markdown / JSON per strona).

KROK 2 — ADAPTER engines/olmocr_engine.py (ExternalVLMEngine/izolowany; wzór: PROMPT D7 MinerU):
Architektura bez zmian (subprocess + osobny venv). Upewnij się / popraw:

1. is_available() = obecność środowiska, BEZ importu olmocr:
   - config.toml: olmocr_python: str | None (ścieżka do pythona z ~/.venvs/olmocr).
   - is_available(): (olmocr_python istnieje LUB komenda olmOCR w PATH przez shutil.which)
     ORAZ has_gpu(). Nigdy nie rzuca wyjątku, nie importuje olmocr.

2. convert() = subprocess do pipeline'u olmOCR (aktualna komenda z KROKU 1):
   - Uruchom przez olmocr_python: [olmocr_python, "-m", "olmocr.pipeline", ...] (lub aktualna forma).
   - env = {**os.environ, "VLLM_USE_FLASHINFER_SAMPLER": "0"} — bez tego flashinfer JIT-uje
     sampler przez nvcc i pada na nowym GPU (ten sam fix co MinerU/vlm i PaddleOCR-VL).
   - Wynik per strona złóż do Markdown wg konwencji vlm_base (work/md_pages/), sprzątnij PNG-i.

3. OBSŁUGA BŁĘDÓW (jak D7):
   - try/except subprocess.CalledProcessError; w except zaloguj logger.error z e.stderr/e.stdout
     (obetnij ~2000 znaków), a do GUI zwróć błąd z końcówką stderr (~500 znaków).

4. unload_model() = zamknięcie procesu (terminate + wait); VRAM zwalnia OS przy wyjściu.

KROK 3 — VRAM (krytyczne na 24 GB):
   - olmOCR-2-7B to ~7-8 GB. Jeśli inny silnik-usługa (np. serwer PaddleOCR-VL ~22 GB) chodzi,
     olmOCR się NIE zmieści — najpierw zatrzymaj tamten serwer (pkill -f "vllm serve").
   - Nigdy dwa modele VLM naraz; to ta sama zasada co sekwencja z Etapu 13.

KROK 4 — TEST end-to-end:
   - uv run pdf2md convert test_scan.pdf --engine olmocr -o /tmp/olmocr.md
   - Porównaj jakość z PaddleOCR-VL i Markerem na tej samej stronie.

Pokaż diff (KROK 2) i wynik testu (KROK 4).
```

> Uwaga: instalacja izolowanego środowiska olmOCR — SILNIKI_INSTALACJA.md sek. 2.7. Sekcja
> „olmOCR" w (historycznym) PROMPCIE #12 jest referencją projektową tego adaptera.

---

## PROMPT D11 — Korekta przez dedykowaną metodę `LLMProvider.correct()` (dopełnienie Etapu 13)

> Powód: Etap 13 zaimplementowany, ale korekta woła `postprocess()`, które prependuje
> `POST_PROCESSING_PROMPT` (ogólne czyszczenie/reformatowanie) i dokleja `SCAN_CORRECTION_PROMPT`
> obok — to **instrukcje sprzeczne** (ogólny prompt: „posprzątaj, popraw formatowanie"; korekta:
> „nie zmieniaj nic poza błędami OCR, nie parafrazuj"). Ryzyko: model parafrazuje/reformatuje
> zamiast tylko naprawić literówki — wbrew celowi korekty i wbrew wierności źródłu. Brak też
> kontroli temperatury (konserwatywna korekta potrzebuje `temp=0`). Rozwiązanie (zatwierdzona,
> **addytywna** zmiana interfejsu — zasada nr 1): dedykowana metoda `correct()`. `postprocess()`
> zostaje nietknięte (kompatybilność wstecz, Faza 1 bez zmian).

```
Dopełnienie Etapu 13. Zmiana ADDYTYWNA — postprocess() NIE zmieniane.

1. LLMProvider (klasa bazowa) — nowa metoda:
   def correct(self, text: str, *, system_prompt: str, temperature: float = 0.0) -> str
   - wysyła do modelu DOKŁADNIE: system = system_prompt, user = text. Nic więcej.
   - NIE prependuje POST_PROCESSING_PROMPT ani żadnego innego promptu.
   - jeśli base ma wspólną ścieżkę wysyłki — zaimplementuj correct() raz w base;
     jeśli nie — dodaj abstrakcyjną sygnaturę i zaimplementuj w KAŻDYM providerze (krok 2).
   - postprocess() bez zmian.

2. Implementacja correct() w każdym providerze (równolegle do postprocess()):
   - Ollama: messages=[{role:"system",content:system_prompt},{role:"user",content:text}],
     "options":{"temperature":temperature}, ORAZ "think": False na POZIOMIE GŁÓWNYM body
     (NIE w options — tam ignorowane; qwen3 ma thinking domyślnie ON, a przy korekcie nie chcemy
     rozumowania/„ulepszania"). Reużyj istniejącej obsługi think z postprocess()/PROMPT #4.
   - Claude: system=system_prompt, messages=[{role:"user",content:text}], temperature=temperature.
   - OpenAI: messages=[{role:"system",content:system_prompt},{role:"user",content:text}], temperature.
   - Gemini: system_instruction=system_prompt, contents=text, generation_config z temperature.
   - Zwróć czysty tekst odpowiedzi (jak postprocess()).

3. scan/correction.py — przełącz korektę na correct():
   - correct_page(md, provider):
       provider.correct(md, system_prompt=SCAN_CORRECTION_PROMPT, temperature=0.0)
     zamiast postprocess(..., instructions=SCAN_CORRECTION_PROMPT).
   - Puste/nieczytelne strony NADAL pomijają LLM (zostaw obecną logikę).
   - correct_pages_batch, log_free_vram, release_ollama_model (keep_alive=0) — bez zmian.

4. test_correction.py — zaktualizuj/dodaj asercje (mock LLM):
   - correct() dostaje system == SCAN_CORRECTION_PROMPT i NIE zawiera POST_PROCESSING_PROMPT
     (asercja na przekazanym system prompt; brak fragmentu ogólnego promptu czyszczenia).
   - przekazywane temperature == 0.0.
   - (Ollama) "think" == False na poziomie głównym; keep_alive == 0 przy release.
   - zostaw istniejącą asercję, że treść promptu zawiera zakaz parafrazy.
   - pusta strona → LLM NIE wołany.

5. Nie zmieniaj innych miejsc wołających postprocess() (Faza 1 bez zmian). ruff + mypy czyste.

Pokaż diff.
```

> Po zielonych testach: **jeden commit na cały Etap 13** (z tą metodą) → merge jak zielone.
> Bez osobnego checkpoint-commita wersji z mieszanymi promptami.

---

## PROMPT D12 — GUI: zmiana domyślnego modelu Ollama (naprawa precedencji + persystencja)

> Powód: w ustawieniach Ollamy w GUI wybór innego dostępnego modelu jako domyślnego nie działa —
> konwersja zawsze używa modelu „przypisanego z linii poleceń"/z konstruktora, ignorując wybór z
> GUI. To klasyczny błąd **źródła prawdy + precedencji**: GUI zapisuje wybór gdzie indziej, niż
> czyta go ścieżka konwersji, albo provider/konwerter trzyma model ustawiony przy starcie i nie
> odświeża go po zmianie. Cel: `config.ollama_model` jako **jedno źródło prawdy** domyślnego
> modelu; GUI go edytuje i utrwala; konwersja go czyta; jawny override z CLI działa
> per-uruchomienie i nie kasuje na stałe ustawienia z GUI.

```
Najpierw ZDIAGNOZUJ, potem napraw. NIE zgaduj — pokaż znaleziony łańcuch.

KROK A — DIAGNOZA (zrelacjonuj zwięźle, zanim ruszysz kod):
- Skąd ścieżka konwersji bierze model Ollamy? (argument konstruktora OllamaProvider / pole configu
  / flaga CLI / wartość zahardkodowana). Prześledź od GUI „Konwertuj" do faktycznego wywołania Ollamy.
- Gdzie GUI zapisuje wybór z dropdowna ustawień modelu? (zmienna widgetu / config / nigdzie).
- Wskaż DOKŁADNY punkt rozjazdu, dlaczego wybór z GUI nie trafia do konwersji. Typowe przyczyny:
  „GUI ustawia tylko pole widgetu, nie zapisuje configu", albo „konwerter/provider tworzony raz przy
  starcie z modelem z X i nie czyta configu ponownie", albo „precedencja arg-konstruktora > config,
  a GUI pisze do config".

KROK B — NAPRAWA (źródło prawdy + precedencja):
1. core/config.py: ollama_model = JEDNO źródło prawdy domyślnego modelu (jeśli pola brak — dodaj;
   jeśli jest — użyj). Zapis do ~/.config/pdf2md/config.toml.
2. GUI (ustawienia Ollamy):
   - dropdown wypełniany REALNIE dostępnymi modelami z Ollamy (zapytanie /api/tags), preselekcja =
     aktualny config.ollama_model.
   - po zmianie wyboru: zapisz do config.ollama_model i UTRWAL config.toml (save). Zmiana ma być
     trwała (zostaje po restarcie GUI).
3. Ścieżka konwersji — precedencja:
   jawny override per-uruchomienie (CLI --ollama-model / ewentualny wybór ad hoc)
     > config.ollama_model (domyślny, edytowalny z GUI)
     > sensowny fallback.
   - W trybie GUI NIE może istnieć „cichy" model z konstruktora nadpisujący config. Jeśli
     OllamaProvider trzyma model jako pole ustawiane przy tworzeniu — albo ODŚWIEŻ je po zmianie w
     GUI, albo czytaj config leniwie przy każdym żądaniu, żeby aktualny wybór realnie trafiał do
     konwersji (gdyby konwerter był tworzony raz przy starcie GUI — zadbaj, by używał bieżącej
     wartości configu, nie zamrożonej z momentu startu).
4. CLI bez regresji: pdf2md convert --ollama-model X nadal nadpisuje model dla TEGO uruchomienia,
   ale NIE kasuje na stałe domyślnego z GUI (chyba że istnieje osobna jawna komenda do ustawiania
   domyślnego — wtedy jej nie zmieniaj).

KROK C — TESTY:
- wybór modelu w GUI zapisuje config.ollama_model i przetrwa reload configu.
- konwersja bez jawnego override używa config.ollama_model (NIE starej/konstruktorowej wartości).
- jawny override (CLI --ollama-model) wygrywa dla danego uruchomienia.
- dropdown listuje modele z /api/tags i preselekcjonuje bieżący domyślny.

ruff + mypy czyste. Pokaż diff i KRÓTKIE podsumowanie znalezionego root-cause'u.
```

> Po naprawie: w GUI zmień domyślny na np. `qwen3.6:27b`, zrób konwersję i potwierdź w logu, że
> poszedł wybrany model (log konwertera już wypisuje silnik/model). Jeśli chcesz dodatkowo wybór
> modelu **per-konwersję** (dropdown na ekranie konwersji, niezależny od trwałego domyślnego) — to
> osobny, mały feature; ten prompt naprawia „domyślny ustawiony z GUI realnie się stosuje".

---

## PROMPT D13 — Refaktor lazy-import: graceful degradation silników

> Powód: łańcuch `engines/__init__.py` → `olmocr_engine` → `vlm_base` → `scan/preprocessing` →
> `import cv2`/`import pymupdf` jest **eager** (na poziomie modułów). Brak JEDNEJ opcjonalnej
> zależności wywala **całą aplikację** — nie wstaje nawet PyMuPDF4LLM, który z cv2 nie ma nic
> wspólnego. Wpadliśmy na to dwa razy w jednej sesji (brak cv2 → crash, potem brak pymupdf →
> crash). To łamie inwarianty projektu: „`is_available()` przez `importlib.metadata`, nie import",
> „core/ bez frameworków", graceful degradation silników. Cel: import pakietu silników (i start
> aplikacji) jest **tani** — żadnych ciężkich third-party na imporcie; ciężkie importy w
> `convert()`/`load_model()`; brakujący silnik = „niedostępny" w `doctor`, błąd dopiero przy
> realnym użyciu.

```
ZASADA: żaden moduł silnika ani wspólny helper (vlm_base, scan/preprocessing, engines/base) NIE
importuje ciężkich third-party (cv2, pymupdf, torch, surya, marker, docling, pymupdf4llm, olmocr,
...) na poziomie modułu. Ciężkie importy → WEWNĄTRZ metod, które ich używają. Stałe (np.
DPI_OLD_BOOKS) i sygnatury zostają na górze.

1. scan/preprocessing.py:
   - przenieś `import cv2` i `import pymupdf` (oraz inne ciężkie) z góry modułu DO WNĘTRZA funkcji,
     które ich używają (renderowanie stron, iter_page_batches, ...). numpy: jeśli tylko w funkcjach
     — też lokalnie.
   - stałe (DPI_OLD_BOOKS itp.) i czysto-stdlib zostają na górze.
   - PO zmianie: `import pdf2md.scan.preprocessing` musi działać BEZ zainstalowanego cv2/pymupdf.

2. engines/vlm_base.py:
   - `from ...scan.preprocessing import DPI_OLD_BOOKS, iter_page_batches` jest OK PO kroku 1
     (preprocessing nie ciągnie już cv2/pymupdf na imporcie). Upewnij się, że vlm_base nie ma innych
     ciężkich importów na górze (torch jest już leniwy w has_gpu() — zostaw).
   - definicje klas bazowych muszą być importowalne bez GPU/torch/cv2.

3. Każdy moduł silnika (engines/*_engine.py — Faza 1 i 2):
   - ZERO ciężkich importów na górze (surya, marker, docling, pymupdf4llm/pymupdf, olmocr, torch).
     Przenieś je do convert()/load_model().
   - Definicja klasy + is_available() NIE importują biblioteki silnika.

4. is_available() wszędzie — przez importlib.metadata, NIE import:
   - in-process: importlib.metadata.version("<dist>") w try/except PackageNotFoundError → False
     (+ has_gpu() gdzie wymagane). Nigdy `import marker`/`import surya`/...
   - izolowane/usługa: jak dotąd (ping serwera / shutil.which / ścieżka venv) — też bez importu.
   - Zweryfikuj nazwy DYSTRYBUCJI (np. "marker-pdf", "surya-ocr", "pymupdf4llm", "docling").

5. engines/base.py i core/: bez ciężkich importów na górze (inwariant „core/ bez frameworków").

6. Zachowanie konwersji BEZ zmian: gdy zależność JEST — convert() działa identycznie (import po
   prostu dzieje się w metodzie). Gdy zależności BRAK i ktoś użyje silnika → czytelny błąd w
   convert() („silnik X wymaga <pakiet>; zob. SILNIKI_INSTALACJA.md"), NIE crash na starcie.

TESTY:
   - regresja „brak ciężkich importów na starcie": w IZOLOWANYM subprocess wykonaj
     `import pdf2md.engines` i sprawdź, że w sys.modules NIE ma {'cv2','pymupdf','fitz','surya',
     'marker','docling'} (subprocess, bo inne testy mogły je zaimportować). To łapie ponowne
     dodanie top-level importu w przyszłości.
   - is_available(): monkeypatch importlib.metadata.version → PackageNotFoundError ⇒ is_available()
     zwraca False BEZ importu biblioteki i bez wyjątku.
   - start aplikacji nie crashuje przy „brakującej" zależności (doctor/list-engines przechodzi).
   - istniejące 203 testy nadal zielone.

ruff + mypy czyste. Pokaż diff i potwierdź wynikiem testu regresyjnego (sys.modules po imporcie).
```

> Komplementarna decyzja (POZA tym promptem): rozważ przeniesienie `pymupdf4llm`/`pymupdf` do
> GŁÓWNYCH zależności (nie tylko `engines-core`), żeby minimalna instalacja zawsze miała ≥1
> działający silnik bazowy. To kwestia grupowania zależności, niezależna od mechaniki lazy-import —
> ale ładnie się uzupełniają: lazy-import sprawia, że brak silnika nie wywala startu, a pymupdf4llm
> w bazie gwarantuje, że zawsze jest czym konwertować.

---

## PROMPT D14 — Domknięcie stosu zależności + usunięcie silnika pdf-craft (commit fixu)

> Powód: wojna zależności rozwiązana ręcznie w pyproject (przypięcie `marker-pdf>=1.10,<2`,
> wyrzucenie pdf-craft z extra, zdjęcie pinu opencv). Skutek: **marker 1.10.x + surya 0.17.x
> działają in-process**, oba silniki konwertują (potwierdzone). Ten prompt: (a) utrwala docelowy
> stan pyproject, (b) usuwa SILNIK pdf-craft z kodu, (c) weryfikuje, (d) commituje całość jako jeden
> spójny fix-PR. **NIE dotyka Etapu 13** (osobny, zatwierdzony commit). **Najpierw wgraj do repo
> poprawione `PROJEKT.md`/`ROADMAP.md`/`FEATURES.md`** — wejdą do tego samego PR.

```
GAŁĄŹ: fix/engine-stack-marker-pin-drop-pdfcraft  (osobny branch; BRAK auto-push; czekaj na zgodę przed PR)

1. pyproject.toml — UPEWNIJ SIĘ, że jest dokładnie tak (jeśli już jest — nie zmieniaj):
   [project.optional-dependencies]
   - marker = ["marker-pdf>=1.10,<2"]
   - engines-core zawiera "marker-pdf>=1.10,<2" (NIE ">=0.2")
   - ZERO pdf-craft: brak grupy  "pdf-craft" = []  i brak  engines-optional = ["pdf-craft>=0.1"]
   - [project.dependencies] NIE zawiera opencv-python-headless (surya 0.17.x dostarcza
     ==4.11.0.86 sama; własny pin koliduje z jej dokładną wersją)
   - z [[tool.mypy.overrides]] usuń "pdf_craft.*" z listy modułów (kosmetyka)
   Po zmianach: `uv lock && uv sync --extra engines-core`; potwierdź marker 1.10.x, surya 0.17.x,
   transformers 4.56.x oraz `import marker.config.parser` OK.

2. Usuń SILNIK pdf-craft z kodu (porzucony — `transformers<4.48` nie do pogodzenia z surya 0.17.1):
   - skasuj  src/pdf2md/engines/pdf_craft_engine.py
   - usuń import + rejestrację PdfCraftEngine w  src/pdf2md/engines/__init__.py
   - usuń wpis/hint pdf-craft z komendy `doctor` i z `list-engines` (cli), jeśli są
   - usuń/zaktualizuj testy odwołujące się do pdf-craft (np. test_registry, test_engines, test doctora)
   - kontrola: `grep -rIn "pdf_craft\|pdf-craft\|PdfCraft" src tests` → ZERO trafień w kodzie
   (Adapter NIE wraca. Gdyby kiedyś był potrzebny → izolacja jak MinerU, patrz PROJEKT macierz zgodności.)

3. Weryfikacja:
   - `uv run pytest`  → wszystkie zielone (testy po usunięciu pdf-craft zaktualizowane, nie wyłączone)
   - ruff + mypy czyste
   - `uv run pdf2md doctor`  → pdf-craft NIE pojawia się już na liście; marker/surya/docling/pymupdf4llm widoczne
   - smoke (oba mają utworzyć .md):
       uv run --extra engines-core pdf2md convert tests/fixtures/test_scan.pdf       --engine surya  -o /tmp/s.md
       uv run --extra engines-core pdf2md convert tests/fixtures/test_text_1page.pdf --engine marker -o /tmp/m.md

4. Commit (Conventional Commits) — JEDEN spójny PR:
   - tytuł:  fix(deps): przypnij marker-pdf do 1.x, usuń pdf-craft, napraw resolucję silników
   - obejmij:  pyproject.toml, uv.lock, skasowany pdf_craft_engine.py + zdjęta rejestracja/hint,
               zaktualizowane testy, ORAZ wgrane poprawione docs (PROJEKT.md/ROADMAP.md/FEATURES.md)
   - opis PR (krótko, root-cause): nieprzypięty marker → resolver cichcem cofał do 0.3.10 (stare API,
     objaw `ModuleNotFoundError: No module named 'marker.config'`); pdf-craft wymaga `transformers<4.48`,
     surya 0.17.1 `>=4.56.1` — nie do pogodzenia; pdf-craft siedział w DWÓCH extra, blokując cały lock.
     Skutek: marker 1.10.x + surya 0.17.x in-process, Surya potwierdzona konwersją skanu.
   - BRAK auto-push. Poczekaj na moją zgodę przed otwarciem PR.

Rule #1: bez zmian publicznego interfejsu pozostałych silników (usunięcie pdf-craft jest celem, nie naruszeniem).
```

> Po tym PR stos `engines-core` jest spójny i utrwalony w `uv.lock` (marker 1.10.x + surya 0.17.x +
> docling + pymupdf4llm + transformers 4.56.x). Etap 13 (D11) commituj osobno — przed albo po tym
> PR, własny branch.

---

## PROMPT D15 — Marker: konwertuj WSZYSTKIE strony (nie tylko pierwszą)

> Objaw: na 99-stronicowym `text_test.pdf` Marker zwraca jedną stronę i kończy. marker-pdf 1.10.x
> domyślnie robi cały PDF, więc limit jest po naszej stronie.

```
GAŁĄŹ: fix/marker-all-pages  (osobny branch; bez auto-push; czekaj na zgodę przed PR)

1. Diagnoza — przeczytaj engines/marker_engine.py: convert() + _load_marker_api(). Szukaj:
   - czy do marker.config.parser.ConfigParser trafia page_range / max_pages ograniczające do 1 strony
   - czy adapter sam nie pre-renderuje/nie wycina TYLKO 1 strony przed podaniem do Markera
   - czy montaż wyniku (markdown) nie urywa się po pierwszej stronie
   - marker 1.10.x: PdfConverter(...)(filepath) robi CAŁY dokument — limit jest u nas
2. Fix: adapter konwertuje wszystkie strony wejścia. Jeśli istnieje opcjonalny page_range/max_pages,
   ma być DOMYŚLNIE pusty (cały dokument) i ustawiany wyłącznie na jawne żądanie (CLI/parametr),
   nigdy na sztywno.
3. Test: konwersja wielostronicowego PDF (wytnij ~3-5 stron z text_test.pdf przez pymupdf) → wynik ma
   >1 stronę, treść/sekcje odpowiadają wejściu. Dodaj mały wielostronicowy fixture + test do suite.

ruff + mypy czyste. Pokaż diff i wynik konwersji wielostronicowej (liczba stron/sekcji wyniku).
```

---

## PROMPT D16 — Surya: wymuś GPU (CUDA), nie CPU

> Objaw: silnik Surya liczy na CPU mimo RTX 5090. surya 0.17.x wybiera urządzenie przez
> `surya.settings` (autodetekcja cuda) lub kwarg `device` predyktorów — adapter najpewniej go nie ustawia.

```
GAŁĄŹ: fix/surya-gpu  (osobny branch; bez auto-push; czekaj na zgodę przed PR)

1. Diagnoza:
   - `uv run python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"`
     → potwierdź, że w venv projektu torch widzi CUDA (RTX 5090). Jeśli NIE — problem jest w torchu, nie w adapterze (wtedy zgłoś).
   - przeczytaj engines/surya_engine.py load_model(): jak tworzy FoundationPredictor / DetectionPredictor /
     RecognitionPredictor — czy w ogóle przekazuje device / ustawia surya.settings.TORCH_DEVICE.
   - sprawdź mechanizm device w surya 0.17.x: settings.TORCH_DEVICE vs kwarg `device`/`dtype` predyktora — użyj właściwego.
2. Fix: w load_model PRZED utworzeniem predyktorów wykryj CUDA i wymuś GPU — przez ustawienie
   surya (TORCH_DEVICE=cuda) ALBO przekazanie device='cuda' (+ dtype fp16, jeśli API przyjmuje).
   Fallback na CPU tylko gdy brak CUDA. Zaloguj wykryte urządzenie: "Surya: device=cuda".
3. Weryfikacja: w trakcie konwersji `nvidia-smi` pokazuje zajęty GPU + proces python; recognition
   wyraźnie szybsze niż na CPU. (To samo dotyczy ewentualnie Markera, jeśli też szedł na CPU — sprawdź.)

ruff + mypy czyste. Pokaż diff + log z "device=cuda" + potwierdzenie z nvidia-smi.
```

---

## PROMPT D17 — GUI: skuteczne anulowanie konwersji + czyszczenie VRAM

> Cel: przycisk, który REALNIE zatrzymuje trwającą konwersję i zwalnia VRAM. Anulowanie kooperatywne
> (QThread) — marker/surya liczą w torch/C i nie da się ich przerwać w połowie strony; anulowanie
> wchodzi na NAJBLIŻSZEJ granicy (między stronami / między plikami), potem czyści VRAM.

```
GAŁĄŹ: feat/gui-cancel-vram  (osobny branch; bez auto-push; czekaj na zgodę przed PR)

1. ConversionWorker (gui/workers.py) — kooperatywne anulowanie:
   - QThread.requestInterruption()/isInterruptionRequested() ALBO własna flaga thread-safe (threading.Event)
   - sprawdzaj flagę MIĘDZY stronami i MIĘDZY plikami w pętli; po wykryciu — przerwij pętlę CZYSTO
   - NIE używaj QThread.terminate() (korumpuje stan, cieknie VRAM/zasoby)
   - już ukończone pliki zostają; bieżący (przerwany) plik nie jest traktowany jako kompletny
2. Po anulowaniu — zwolnij VRAM przez engine.unload_model():
   - in-process (Surya/Marker): ZWALIDUJ, że unload_model faktycznie zwalnia — usuń referencje do
     modelu/predyktorów, gc.collect(), torch.cuda.empty_cache(); potwierdź spadek w nvidia-smi
   - izolowane (PaddleOCR-VL/olmOCR): unload = kill procesu/serwera (wzorzec już jest)
   - jeśli trwała korekta LLM (Ollama): release_ollama_model (keep_alive=0) — klocek z Etapu 13
3. GUI: przycisk „Anuluj" aktywny tylko w trakcie konwersji → woła worker.cancel()/requestInterruption();
   worker emituje sygnał „anulowano"; UI wraca do spoczynku (odblokowane kontrolki, reset paska postępu).
4. Test: start konwersji wielostronicowej → Anuluj w trakcie → zatrzymanie na najbliższej granicy,
   VRAM zwolniony (nvidia-smi), GUI odblokowane, brak wiszących wątków/procesów. (Sekcja testów GUI — marker `gui`.)

ruff + mypy czyste. Pokaż diff; opisz, na jakiej granicy realnie zatrzymuje i jak potwierdziłeś zwolnienie VRAM.
```

> Uwaga do D17: anulowanie kooperatywne nie przerwie POJEDYNCZEJ długiej strony (np. 12 s w Markerze) —
> czeka do jej końca. Jeśli chcesz **natychmiastowego** anulowania, silniki in-process musiałyby
> działać w **osobnym procesie** (kill = natychmiast, VRAM zwalnia OS) jak izolowane — to większa
> zmiana architektury. Wersja kooperatywna jest pragmatycznym pierwszym krokiem; subprocess-cancel
> ewentualnie później jako osobny feature.

---

## PROMPT D18 — `marker_device`: domyślnie „auto" (GPU gdy dostępne) — follow-up do D16

> Powód: Marker domyślnie idzie na CPU — to **świadomy default** `marker_device="cpu"` z Etapu 3
> (stabilność WSL), nie bug. Na wielostronicowych dokumentach CPU boli, a karta (RTX 5090) jest. Ten PR
> robi dla Markera to, co D16 dla Suryi — domyślne GPU — ale przez **zmianę domyślnej wartości configu**
> (osobna decyzja, Rule #1). KLUCZOWE: **nie wolno po cichu nadpisać istniejących configów z jawnym
> „cpu"** — bo nie odróżnisz „user świadomie wybrał cpu" od „stary default cpu".

```
GAŁĄŹ: feat/marker-device-auto  (osobny branch; bez auto-push; czekaj na zgodę przed PR)

0. PRECONDITION (zrób i POKAŻ wynik): potwierdź, że powód „stabilność WSL" z Etapu 3 jest nieaktualny —
   kilka WIELOSTRONICOWYCH konwersji Markera na GPU pod WSL bez OOM/zwiechy:
     uv run --extra engines-core python -c "import torch; print('cuda', torch.cuda.is_available())"
     # marker_device=cuda w config.toml (lub kwarg), potem:
     uv run --extra engines-core pdf2md convert /tmp/text5.pdf --engine marker -o /tmp/m.md
   (+ nvidia-smi w trakcie). Jeśli niestabilne — STOP, zgłoś; NIE zmieniaj defaultu.

1. Wartość „auto": dorzuć „auto" do dozwolonych wartości marker_device (obok „cpu"/„cuda"). W adapterze
   (load_model/_load_marker_api), gdy marker_device=="auto": wykryj torch.cuda.is_available() → „cuda",
   inaczej „cpu"; przekaż ROZWIĄZANE urządzenie do Markera. Zaloguj: „Marker: device=auto→cuda".
   (Wzorzec jak istniejące docling_device: auto/cpu/cuda.)

2. Zmień DEFAULT dla NOWYCH configów: marker_device domyślnie „auto" (w core/config.py, model
   pydantic-settings). Świeża instalacja bez configu → Marker bierze GPU, gdy jest.

3. Istniejący userzy — BEZ cichego nadpisania: jeśli wczytany config ma marker_device=="cpu" ORAZ
   torch.cuda.is_available() → zaloguj JEDNORAZOWĄ, nieinwazyjną podpowiedź („Marker na cpu, a wykryto
   GPU — ustaw marker_device='auto'/'cuda', by przyspieszyć"). NIE zmieniaj wartości automatycznie.
   (Pełna infrastruktura config_version + migracji to osobny, szerszy temat — tu wystarczy ostrzeżenie,
   bo jawnego „cpu" i tak nie wolno nadpisywać.)

4. Testy: „auto" rozwiązuje się na „cuda" gdy CUDA dostępne i „cpu" gdy nie (zamockuj
   torch.cuda.is_available()); default nowego configu == „auto"; podpowiedź pojawia się dla cpu+CUDA,
   a NIE pojawia się dla cpu-bez-CUDA ani dla jawnego cuda/auto; walidacja odrzuca śmieciowe wartości.

5. Dokumentacja: zaktualizuj notkę o marker_device w PROJEKT (default teraz „auto"; „cpu" jako opcja
   stabilnościowa) — spójnie z sekcją „Konfiguracja".

ruff + mypy czyste. Pokaż diff + log „device=auto→cuda" + potwierdzenie GPU (nvidia-smi) na wielu stronach.
```

> To samodzielny PR (zmiana defaultu = świadoma decyzja, nie naprawa). Pełny `config_version` + migracja
> ustawień (dla całej rodziny aplikacji z platformdirs) to osobny, większy temat — tutaj go nie ruszaj;
> dla `marker_device` ostrzeżenie wystarcza, bo jawnej wartości usera i tak nie wolno nadpisać.

---

## PROMPT D19 — olmOCR: finalizacja adaptera + parking silnika + doc (domknięcie D10)

> Stan po długim debugu: olmOCR-2-7B FP8 **działa technicznie** — gołe `vllm serve --max-model-len
> 16384 --gpu-memory-utilization 0.90` wstaje na 24 GB, a `olmocr.pipeline` przepuszcza te flagi
> (default `--max_model_len` to już 16384) i ma tryb `--server`. ALE: w trybie spawn-per-plik
> serwer-dziecko olmocr nie wstaje pod nightly-vLLM/transformers 5.x (stderr połykany — health-poll
> w nieskończoność); silnik zajmuje ~całą kartę (model 9.5 + KV 9.3 + grafy ≈ 24 GB) → **nie
> współistnieje z modelem korekty w pipelinie**; start 90-150 s/wywołanie; anglocentryczny.
> **DECYZJA: adapter zostaje (działający, zarejestrowany), silnik ZAPARKOWANY** — commitujemy
> poprawny adapter + udokumentowaną receptę. NIE drążymy transformers-5.x (kolejny rabbit hole).

```
GAŁĄŹ: feat/olmocr-adapter-d10  (osobny branch; bez auto-push; czekaj na zgodę przed PR)

1. engines/olmocr_engine.py — doprowadź adapter do stanu docelowego (zastosuj czego brak; idempotentnie):
   a) ENV subprocessu — PATH z binem izolowanego venv (olmocr shelluje CLI `vllm` po gołej nazwie →
      FileNotFoundError: 'vllm'):
        venv_bin = Path(venv_python).parent
        env = os.environ.copy()
        env["PATH"] = f"{venv_bin}{os.pathsep}" + env.get("PATH", "")
        env["VIRTUAL_ENV"] = str(venv_bin.parent)
        env["VLLM_USE_FLASHINFER_SAMPLER"] = "0"      # fix Blackwell (jak MinerU/vlm, Paddle)
      przekaż env= do Popen.
   b) FLAGI vLLM — dołóż do komendy olmocr.pipeline: --max_model_len i --gpu_memory_utilization z pól
      configu olmocr_max_model_len (default 16384) i olmocr_gpu_memory_utilization (default 0.90).
      Bez nich olmocr spawnuje vLLM z domyślnym 128k KV-cache → "No available memory for cache blocks"
      na 24 GB.
   c) NAPRAW logowanie błędu w except — teraz leci literalnie "kod %d / stdout %s / stderr %s"
      (argumenty NIE podstawione) → zamień na f-string albo poprawne argumenty logger.*, żeby
      stderr/stdout dziecka REALNIE trafiał do logu i GUI. (To ukrywało prawdziwe błędy przez cały debug.)
   d) is_available() — sprawdzaj obecność venv_bin/"vllm" (NIE sam python) + has_gpu(); półzłożony venv
      (olmocr bez vllm) ma dawać ❌, nie fałszywe ✅. (Dokładnie ten przypadek nas ugryzł.)

   OPCJONALNIE (zalecane jako jedyny sensowny tryb produkcyjny — możesz dołożyć teraz LUB jako osobny
   follow-up, jeśli chcesz minimalny PR):
   e) pole configu olmocr_server_url → gdy ustawione, przekaż `--server <url>` do olmocr.pipeline
      (olmocr pomija spawn lokalnego vLLM). Wskazujesz własny, raz wystartowany serwer (wzorzec
      "serwer user-managed" PaddleOCR-VL) — znosi 90-150 s startu/plik i pozwala zarządzać VRAM.
      Puste → zachowanie jak dotąd (spawn lokalny).

   Bez zmian publicznego interfejsu poza dodaniem powyższych pól configu. Silnik POZOSTAJE
   zarejestrowany (to działający silnik opcjonalny, nie usuwamy go jak pdf-craft).

2. Doc SILNIKI_INSTALACJA.md sek. 2.7 (olmOCR) — uzgodnij z rzeczywistością:
   - środowisko: venv ~/.venvs/olmocr → `uv pip install olmocr` → DODATKOWO nightly-vLLM jak Paddle
     (sek. 2.8): `uv pip install -U vllm --pre --torch-backend=auto --extra-index-url
     https://wheels.vllm.ai/nightly`. (Samo `uv pip install olmocr` NIE ciągnie torch/vllm — to było źródłem błędu.)
   - uruchomienie: VLLM_USE_FLASHINFER_SAMPLER=0 + --max_model_len 16384 --gpu_memory_utilization 0.90
     (na 24 GB; przy OOM zejdź do 0.80). Gołe `vllm serve` z tymi flagami POTWIERDZONE jako działające.
   - PARKING (jawnie): w trybie spawn-per-plik serwer-dziecko olmocr nie wstaje pod nightly-vLLM/
     transformers 5.x (stderr połykany; podejrzenie: transformers 5.x w ścieżce processora/chat-template).
     Silnik zajmuje ~całą kartę → NIE współistnieje z modelem korekty w pipelinie; start 90-150 s/
     wywołanie; anglocentryczny. ZAPARKOWANY — dla dokumentów PL używać PaddleOCR-VL/Surya. Jedyny realny
     tryb produkcyjny: external-server (`--server` / pole olmocr_server_url), nie spawn per-plik.

3. Weryfikacja:
   - uv run pytest (zielone), ruff + mypy czyste.
   - uv run pdf2md doctor → olmOCR status zależny od venv (❌ na maszynie bez kompletnego venv — OK i zamierzone).
   - NIE wymagaj zielonego e2e konwersji olmOCR (silnik zaparkowany; e2e blokuje środowisko, nie kod).

4. Commit (Conventional Commits) — jeden PR:
   - tytuł: feat(engines): adapter olmOCR (izolowany vLLM) + recepta VRAM; silnik zaparkowany
   - opis: co działa (adapter, PATH, flagi, --server, gołe vllm serve), co blokuje (spawn pod
     transformers 5.x, ekonomia VRAM 24 GB, koszt startu 90-150 s, EN-centryczny), dlaczego parking;
     adapter gotowy do trybu external-server, gdyby zaszła potrzeba.
   - BRAK auto-push; czekaj na zgodę.
```

> **Osobny follow-up (NIE w tym PR): widoczność postępu silników-usług.** Buforowany `Popen+communicate`
> daje zamrożony spinner przez 90-150 s startu serwera (dotyczy też PaddleOCR-VL). Streamuj stderr albo
> pokaż status „startuję serwer (~1-2 min)". Wyszło przy olmOCR, ale wartość ogólna — własny prompt.

---

## PROMPT D20 — torch CUDA na Windowsie: wymuś indeks cu130 w pyproject (sys_platform=='win32')

> Powód: na natywnym Windowsie `uv sync` instaluje torcha z PyPI = wariant **CPU-only** (`+cpu`),
> więc Surya i Marker liczą na CPU mimo RTX 5090 (`doctor` → CUDA ❌). Ręczny `uv pip install
> --reinstall` z indeksu cu130 daje `2.12.1+cu130 True`, ale jest NIETRWAŁY — następny `uv sync`
> cofa torcha na `+cpu` (lock o nim nie wie). Trwałe rozwiązanie: źródło CUDA-torcha w pyproject,
> **warunkowane `sys_platform=='win32'`**, żeby NIE ruszać działającego stosu Linux/WSL.
> **Tag `cu130` wybrany świadomie:** daje torcha **2.12.1** — DOKŁADNIE tę wersję, którą trzyma lock
> projektu (cu128 wymuszałby downgrade do 2.11.0). Czyli żadnego cofania wersji i żadnego konfliktu
> z pinem — a dodatkowo TEN SAM toolkit co WSL (cu130), więc spójność po obu stronach. To realny błąd
> projektu na Windowsie (dotyczy każdego użytkownika), nie tylko jednej maszyny.

```
GAŁĄŹ: build/torch-cuda-windows  (osobny branch; bez auto-push; czekaj na zgodę przed PR)

1. Dodaj do pyproject.toml źródło CUDA-torcha tylko dla Windowsa:

   [tool.uv.sources]
   torch = [{ index = "pytorch-cu130", marker = "sys_platform == 'win32'" }]
   torchvision = [{ index = "pytorch-cu130", marker = "sys_platform == 'win32'" }]

   [[tool.uv.index]]
   name = "pytorch-cu130"
   url = "https://download.pytorch.org/whl/cu130"
   explicit = true

   - explicit=true → indeks używany WYŁĄCZNIE dla pakietów, które go jawnie wskażą (torch/torchvision),
     nie dla reszty zależności.
   - marker sys_platform=='win32' → CUDA-torch tylko na Windowsie; Linux/WSL bierze swój stos — NIE dotykać.
   - nazwa w [tool.uv.sources] MUSI zgadzać się z [[tool.uv.index]].name (pytorch-cu130).
   - cu130 ma torch 2.12.1 = wersja z locka, więc NIE trzeba ruszać żadnych pinów (inaczej niż cu128).

2. Przelicz lock i zsynchronizuj, potem TEST TRWAŁOŚCI (to jest sedno — uv sync ma ZOSTAWIĆ CUDA):
   uv lock
   uv sync
   uv run python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
   OCZEKIWANE na Windowsie: 2.12.1+cu130  True  (a NIE +cpu).

   - jeśli wróci +cpu → literówka w marker/nazwie indeksu (nazwa w sources ≠ index.name); popraw, powtórz.
   - konfliktu wersji NIE powinno być (cu130 = 2.12.1 = lock). Gdyby jednak resolver marudził → wklej błąd.

3. Weryfikacja końcowa:
   - uv run pdf2md doctor → sekcja GPU: CUDA ✅, smoke test ✅, urządzenie = RTX 5090.
   - (opcjonalnie) krótka konwersja Surya/Marker → nvidia-smi pokazuje zajęty GPU.
   - uv run pytest (zielone — sam wpis źródła nie powinien nic zepsuć), ruff/mypy bez zmian.

4. Commit (Conventional Commits), jeden PR:
   - tytuł: build(deps): wymuś torch CUDA (cu130) na Windowsie przez uv index (sys_platform=='win32')
   - opis: PyPI torch na Windowsie = +cpu → Surya/Marker na CPU; źródło cu130 (torch 2.12.1, zgodne z
     lockiem i z toolkitem WSL) z markerem win32 naprawia to dla wszystkich userów Windows, nie ruszając
     stosu Linux/WSL.
   - obejmij: pyproject.toml, uv.lock. BRAK auto-push; czekaj na zgodę.

UWAGA: to zmiana zależności krytyczna dla działania na Windowsie. NIE zmieniaj nic w konfiguracji
Linux/WSL (marker sys_platform=='win32' to gwarantuje).
```

> Po tym PR `doctor` na Windowsie pokaże CUDA ✅, a Surya/Marker pójdą na GPU także natywnie (nie tylko
> w WSL). Tag `cu130` dobrany świadomie: torch **2.12.1** = wersja z locka (zero downgrade'u, zero
> konfliktu pinu) i ten sam toolkit co WSL. Notkę o tej pułapce („PyPI torch=+cpu na Windowsie; wymusić
> uv index cuXXX z markerem win32; cu130→2.12.1 zgodne z lockiem") warto dopisać do PROJEKT, sekcja
> środowiska — spójnie z lekcjami o pinach.

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
