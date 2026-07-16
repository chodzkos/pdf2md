# Uzycie pdf2md

Ten dokument opisuje codzienna prace z GUI i CLI pdf2md. Konfiguracja jest wspolna dla obu interfejsow i jest zapisywana w `~/.config/pdf2md/config.toml`.

## GUI krok po kroku

Uruchom aplikacje:

```bash
pdf2md-gui
```

Mozesz tez przekazac pliki startowe:

```bash
pdf2md-gui raport.pdf skan.pdf
```

### Elementy okna

| Element | Do czego sluzy |
|---|---|
| `Dodaj pliki...` | Otwiera wybor plikow PDF i dodaje je do listy konwersji. |
| `Wyczysc liste` | Usuwa wszystkie pliki z aktualnej kolejki. |
| Lista plikow | Pokazuje PDF-y, ktore zostana przetworzone. |
| `Silnik` | Wybiera engine konwersji. Niedostepne silniki sa wyszarzone. |
| `Wlacz post-processing LLM` | Uruchamia opcjonalne czyszczenie Markdown przez LLM. |
| `Dostawca` | Wybiera LLM: Ollama, Claude, OpenAI albo Gemini. |
| `Model` | Nadpisuje domyslny model tylko dla aktualnego uruchomienia. Puste pole oznacza fallback providera. |
| `Folder wynikowy` | Katalog dla plikow `.md`. Puste pole zapisuje wynik obok pliku zrodlowego. |
| Pasek postepu | Pokazuje aktualnie przetwarzany plik i procent wykonania. |
| `KONWERTUJ` | Startuje konwersje calej kolejki. |
| `Log` | Pokazuje start, sukcesy, bledy i podsumowanie. |
| `Podglad` | Pokazuje ostatni zapisany Markdown. |

### Typowy workflow

1. Kliknij `Dodaj pliki...` i wybierz jeden lub wiele PDF-ow.
2. Wybierz silnik. Dla prostych PDF-ow tekstowych zacznij od PyMuPDF4LLM, dla skanow od Markera albo Doclinga.
3. Opcjonalnie wlacz LLM i wybierz dostawce oraz model.
4. Ustaw folder wynikowy albo zostaw pole puste, zeby zapisac Markdown obok PDF-a.
5. Kliknij `KONWERTUJ`.
6. Sprawdz zakladke `Log`, a po sukcesie `Podglad`.
7. Po zakonczonej konwersji mozesz otworzyc folder wynikowy. Przycisk pojawia sie tylko wtedy, gdy co najmniej jeden plik zostal zapisany.
8. Jesli Pandoc jest dostepny, okno podsumowania moze zaoferowac eksport ostatnich wynikow do EPUB.

### Ustawienia GUI

Menu `Plik -> Ustawienia` albo skrot `Ctrl+,` otwiera wspolny dialog ustawien.

| Zakladka | Ustawienia |
|---|---|
| `Klucze API` | Anthropic, OpenAI i Gemini. Przyciski `Testuj` sprawdzaja, czy klucz jest wpisany i czy SDK jest dostepne. |
| `Domyslne ustawienia` | Domyslny silnik, domyslny folder wynikowy, jezyk OCR i `Docling device`. |
| `Ollama` | URL lokalnej Ollamy i wykrywanie zainstalowanych modeli. |

`Docling device` przyjmuje `auto`, `cpu` albo `cuda`. Tryb `auto` uzywa wspolnego smoke testu CUDA, wiec stare lub niekompatybilne GPU nie powinno powodowac crasha silnika.

### Diagnostyka GUI (log)

Na Windows `pdf2md-gui` jest gui-scriptem (exe bez okna konsoli), wiec komunikaty nie ida na stdout. Diagnostyke znajdziesz w pliku logu: `~/.config/pdf2md/logs/gui.log` (rotacja 5 MB, poziom INFO). Na wszystkich platformach dziala tez zakladka `Log` w oknie. Gdy zglaszasz problem z GUI, dolacz `gui.log`.

## CLI reference

Glowne polecenie:

```bash
pdf2md [OPTIONS] COMMAND [ARGS]...
```

Wersja:

```bash
pdf2md --version
```

### `pdf2md convert`

Konwertuje jeden lub wiele plikow PDF do Markdown albo EPUB.

```bash
pdf2md convert FILES... [OPTIONS]
```

| Opcja | Znaczenie |
|---|---|
| `--engine`, `-e` | Silnik konwersji, np. `pymupdf4llm`, `marker`, `docling`, `mineru`, `pdf-craft`. Bez opcji uzywa `conversion.default_engine`. |
| `--output`, `-o` | Plik wyjsciowy `.md`/`.epub` dla jednego pliku albo katalog dla wielu plikow. |
| `--output-dir` | Katalog wynikowy dla batcha. Nie lacz z `--output`. |
| `--epub-backend` | Backend eksportu EPUB: `pandoc`, `native`, `calibre`. Bez opcji uzywa `conversion.epub_backend` (domyslnie `pandoc`). Dziala tylko przy wyjsciu `.epub`. |
| `--llm` | Dostawca LLM: `none`, `ollama`, `claude`, `openai`, `gemini`. Domyslnie `none`. |
| `--llm-model` | Model LLM dla tego uruchomienia, np. `gpt-4.1-mini` albo `qwen2.5:14b`. |
| `--llm-mode` | Tryb LLM: `none`, `whole_document`, `by_page`, `by_chunk`, `by_heading`. |
| `--lang` | Jezyk OCR, domyslnie `pol+eng`. |
| `--dry-run` | Pokazuje plan konwersji bez zapisu plikow. |
| `--verbose`, `-v` | Wlacza bardziej szczegolowy output. |

Przyklady:

```bash
pdf2md convert dokument.pdf --engine pymupdf4llm
```

```text
Raport koncowy
Pliki: 1/1
Silnik: PyMuPDF4LLM
```

Batch z jawnym katalogiem wynikowym:

```bash
pdf2md convert "pdfy/*.pdf" --engine docling --output-dir ./markdown
```

Eksport EPUB:

```bash
pdf2md convert ksiazka.pdf --engine pymupdf4llm --output ksiazka.epub
```

Wybor backendu EPUB (`pandoc` domyslnie, `native` = wbudowany builder `ebooklib` bez Pandoca,
`calibre` = `ebook-convert` z fallbackiem na Pandoc):

```bash
pdf2md convert ksiazka.pdf --output ksiazka.epub --epub-backend native
```

Plan bez konwersji:

```bash
pdf2md convert dokument.pdf --engine marker --dry-run
```

LLM przez Ollama:

```bash
pdf2md convert dokument.pdf --engine marker --llm ollama --llm-mode by_heading --llm-model qwen2.5:14b
```

LLM przez API:

```bash
ANTHROPIC_API_KEY=... pdf2md convert raport.pdf --llm claude --llm-mode whole_document
```

### `pdf2md list-engines`

Pokazuje katalog znanych silnikow, status instalacji, OCR, LLM, licencje i podpowiedz instalacji.

```bash
pdf2md list-engines
```

### `pdf2md list-llm`

Pokazuje status dostawcow LLM, domyslne modele i wymagania kluczy API.

```bash
pdf2md list-llm
```

### `pdf2md doctor`

Diagnozuje srodowisko:

- system i Python,
- PyTorch, `torch.cuda.is_available()` i realny `cuda_usable()` smoke test,
- Tesseract i jezyki `pol`/`eng`,
- Poppler,
- Pandoc,
- Ollama i modele,
- silniki konwersji,
- obecne klucze API.

```bash
pdf2md doctor
```

To polecenie jest pierwszym miejscem do sprawdzenia problemow typu: CUDA jest widoczna dla PyTorcha, ale kernel dla danej karty nie istnieje i silnik musi przejsc na CPU.

### `pdf2md config`

Konfiguracja jest zapisywana w `~/.config/pdf2md/config.toml`.

```bash
pdf2md config show
```

```bash
pdf2md config set conversion.default_engine docling
pdf2md config set conversion.default_output_dir /home/user/markdown
pdf2md config set conversion.default_language pol+eng
pdf2md config set docling.docling_device auto
pdf2md config set llm.provider ollama
pdf2md config set llm.mode by_heading
```

Edycja w domyslnym edytorze:

```bash
EDITOR="code --wait" pdf2md config edit
```

Bez `EDITOR` uzywany jest `nano`.

## Konfiguracja

Zrodlem prawdy jest `config.toml`. Plik `.env` jest override deweloperskim i nadpisuje wartosci TOML oraz domyslne ustawienia.

Domyslny plik:

```toml
[llm]
enabled = false
provider = "none"
mode = "none"
anthropic_model = ""
openai_model = ""
gemini_model = ""
ollama_model = "qwen2.5:14b"
ollama_url = "http://localhost:11434"

[conversion]
default_engine = "pymupdf4llm"
default_output_dir = ""
default_language = "pol+eng"

[marker]
marker_device = "cpu"
marker_workers = 1
marker_max_pages = 1
marker_torch_device = ""
marker_recognition_batch_size = 0
marker_detector_batch_size = 0
marker_layout_batch_size = 0
marker_table_rec_batch_size = 0

[docling]
docling_device = "auto"

[mineru]
mineru_backend = "pipeline"

[api_keys]
anthropic_api_key = ""
openai_api_key = ""
gemini_api_key = ""
```

Pełna dokumentacja wszystkich pól konfiguracji — zob. [docs/CONFIGURATION.md](CONFIGURATION.md).

Najczestsze zmienne srodowiskowe:

| Zmienna | Znaczenie |
|---|---|
| `ANTHROPIC_API_KEY` | Klucz API Anthropic Claude. |
| `OPENAI_API_KEY` | Klucz API OpenAI. |
| `GEMINI_API_KEY` | Klucz API Google Gemini. |
| `ANTHROPIC_MODEL` | Model Claude dla uruchomienia. |
| `OPENAI_MODEL` | Model OpenAI dla uruchomienia. |
| `GEMINI_MODEL` | Model Gemini dla uruchomienia. |
| `OLLAMA_MODEL` | Model Ollama, domyslnie `qwen2.5:14b`. |
| `OLLAMA_URL` | URL Ollamy, domyslnie `http://localhost:11434`. |

## Ktory silnik wybrac?

| Sytuacja | Rekomendowany silnik | Dlaczego |
|---|---|---|
| PDF ma poprawna warstwe tekstowa i potrzebujesz szybkiego wyniku | PyMuPDF4LLM | Najmniejszy narzut, dobry start dla dokumentow cyfrowych. |
| PDF jest skanem albo ma slaba warstwe tekstowa | Marker | OCR i odtwarzanie ukladu sa glownym scenariuszem Markera. |
| Dokument ma tabele, formularze albo ma isc do RAG | Docling | Dobrze radzi sobie ze struktura dokumentow biznesowych i tabelami. |
| Artykul naukowy, wielokolumnowy layout, CJK | MinerU | Silnik celowany w publikacje naukowe i zlozony layout. |
| Skanowana ksiazka albo natywny EPUB | pdf-craft | Ma workflow nastawiony na ksiazki i eksport EPUB/Markdown. |
| Masz starsze GPU albo niepewne CUDA | Docling/Marker na CPU | `cuda_usable()` wykrywa niekompatybilne GPU i pozwala uniknac crasha. |

## Instalacja silnikow

Silniki instaluj w tym samym srodowisku Pythona, w ktorym dziala `pdf2md`. Dla aktywnego virtualenv:

```bash
uv pip install pymupdf4llm
uv pip install marker-pdf
uv pip install docling
```

Silniki opcjonalne i CLI:

```bash
uv pip install pdf-craft
uv tool install mineru --with mineru[all]
```

LLM:

```bash
uv pip install anthropic
uv pip install openai
uv pip install google-genai
```

Jesli `pdf2md` jest zainstalowany przez `uv tool`, dolacz zaleznosci do izolowanego srodowiska narzedzia:

```bash
uv tool install pdf2md --with pymupdf4llm --with docling
```

W repozytorium developerskim:

```bash
uv sync
uv run pdf2md doctor
```

## Testy developerskie

Domyslne uruchomienie omija testy integracyjne i heavy:

```bash
uv run pytest
```

Coverage:

```bash
uv run pytest --cov=pdf2md --cov-report=term-missing
```

Testy integracyjne uruchamiaj jawnie po zainstalowaniu zaleznosci:

```bash
uv run pytest -m integration
```

Ciezkie testy ML:

```bash
PDF2MD_RUN_MARKER_INTEGRATION=1 uv run pytest -m heavy
```

Kontrole przed PR-em:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src/
```
