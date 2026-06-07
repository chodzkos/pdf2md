# pdf2md

[![CI](https://github.com/chodzkos/pdf2md/actions/workflows/ci.yml/badge.svg)](https://github.com/chodzkos/pdf2md/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](pyproject.toml)

pdf2md konwertuje pliki PDF do Markdown przez kilka wymiennych silnikow: szybkie ekstraktory tekstu, OCR i parsery dokumentow z tabelami. Aplikacja ma CLI, GUI oraz opcjonalny post-processing LLM dla czyszczenia i strukturyzowania wyniku.

## ✨ Funkcje

- Konwersja pojedynczych PDF-ow i batchy do Markdown.
- GUI w PySide6 oraz CLI oparte o Click.
- Silniki: PyMuPDF4LLM, Marker, Docling, MinerU i pdf-craft.
- OCR dla skanow, dokumentow wielokolumnowych, tabel i materialow naukowych.
- Opcjonalne LLM: Ollama, Anthropic Claude, OpenAI i Google Gemini.
- Eksport do Markdown i EPUB przez Pandoc.
- `pdf2md doctor` do diagnozy Tesseracta, Pandoca, Ollamy, PyTorch/CUDA i zainstalowanych silnikow.
- Wspolny `config.toml` dla CLI i GUI.

## 🔧 Silniki konwersji

| Silnik | Typ dokumentu | OCR | Instalacja |
|---|---|---:|---|
| PyMuPDF4LLM | Natywne PDF-y z warstwa tekstowa | Nie | `uv pip install "pdf2md[pymupdf]"` |
| Marker | Skanowane i mieszane PDF-y, OCR, layout | Tak | `uv pip install "pdf2md[marker]"` |
| Docling | Tabele, dokumenty biznesowe, RAG | Tak | `uv pip install "pdf2md[docling]"` |
| MinerU | Artykuly naukowe, CJK, wielokolumnowe uklady | Tak | `uv tool install mineru --with mineru[all]` |
| pdf-craft | Skanowane ksiazki, EPUB/Markdown | Tak | `uv pip install "pdf2md[pdf-craft]"` |

MinerU jest celowo instalowany jako izolowane narzedzie `uv tool`, a nie jako dependency projektu, bo jego wymagania moga konfliktowac z Markerem.

## 📦 Instalacja

### Wymagania wstępne (systemowe)

- Python 3.11 lub nowszy.
- `uv` do instalacji i uruchamiania projektu.
- Tesseract OCR dla workflow OCR.
- Poppler, gdy silnik lub narzedzie pomocnicze wymaga narzedzi PDF z systemu.
- Pandoc, jesli eksportujesz do EPUB.
- Opcjonalnie Ollama dla lokalnego LLM.
- Opcjonalnie CUDA/PyTorch dla silnikow GPU; `pdf2md doctor` sprawdza tez realna uzywalnosc CUDA.

### Instalacja aplikacji

```bash
uv pip install pdf2md
```

Do pracy z repozytorium:

```bash
git clone https://github.com/chodzkos/pdf2md
cd pdf2md
uv sync
```

### Instalacja silników (opcjonalnie)

```bash
uv pip install "pdf2md[pymupdf]"
uv pip install "pdf2md[marker]"
uv pip install "pdf2md[docling]"
uv pip install "pdf2md[pdf-craft]"
uv pip install "pdf2md[llm]"
```

Agregat dla glownych silnikow:

```bash
uv pip install "pdf2md[engines-core,llm]"
```

MinerU:

```bash
uv tool install mineru --with mineru[all]
mineru --help
```

## 🚀 Użycie

### GUI

![GUI pdf2md](docs/assets/gui-screenshot.svg)

Uruchom:

```bash
pdf2md-gui
```

Mozesz tez przekazac pliki startowe:

```bash
pdf2md-gui dokument.pdf skan.pdf
```

W GUI dodajesz pliki PDF, wybierasz silnik, opcjonalnie dostawce LLM, folder wynikowy i uruchamiasz konwersje. Panel logow pokazuje postep i bledy, a zakladka podgladu pokazuje ostatnio utworzony Markdown.

### CLI

Lista silnikow:

```bash
$ pdf2md list-engines
Silniki konwersji
PyMuPDF4LLM  Dostępny/Niezainstalowany  Core
Marker       Dostępny/Niezainstalowany  Core
Docling      Dostępny/Niezainstalowany  Core
MinerU       Dostępny/Niezainstalowany  Opc.
pdf-craft    Dostępny/Niezainstalowany  Opc.
```

Konwersja pojedynczego pliku:

```bash
$ pdf2md convert dokument.pdf --engine pymupdf4llm
Raport końcowy
Pliki: 1/1
Silnik: PyMuPDF4LLM
```

Batch do katalogu:

```bash
pdf2md convert "pdfy/*.pdf" --engine docling --output-dir ./markdown
```

Plan bez konwersji:

```bash
pdf2md convert dokument.pdf --dry-run
```

Konwersja z LLM:

```bash
pdf2md convert dokument.pdf --engine marker --llm ollama --llm-mode by_heading
```

Diagnoza srodowiska:

```bash
pdf2md doctor
```

Konfiguracja:

```bash
pdf2md config show
pdf2md config set conversion.default_engine docling
pdf2md config set docling.docling_device auto
pdf2md config edit
```

## ⚙️ Konfiguracja

Zrodlem prawdy jest:

```text
~/.config/pdf2md/config.toml
```

Plik `.env` jest traktowany jako override deweloperski i moze nadpisac wartosci lokalnie. Nie jest docelowym miejscem konfiguracji produkcyjnej.

Najwazniejsze ustawienia:

| Klucz | Znaczenie |
|---|---|
| `conversion.default_engine` | Domyslny silnik: `pymupdf4llm`, `marker`, `docling`, `mineru`, `pdf-craft` |
| `conversion.default_output_dir` | Domyslny katalog wynikowy |
| `conversion.default_language` | Jezyk OCR, np. `pol+eng` |
| `marker.marker_device` | `auto`, `cpu` albo `cuda` |
| `marker.marker_workers` | Liczba workerow Markera |
| `marker.marker_max_pages` | Limit stron dla Markera, `0` oznacza brak limitu |
| `docling.docling_device` | `auto`, `cpu` albo `cuda`; `auto` uzywa smoke testu CUDA |
| `llm.provider` | `none`, `ollama`, `claude`, `openai`, `gemini` |
| `llm.mode` | `none`, `whole_document`, `by_page`, `by_chunk`, `by_heading` |

Zmienne i klucze LLM:

- `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`
- `ANTHROPIC_MODEL`, `OPENAI_MODEL`, `GEMINI_MODEL`, `OLLAMA_MODEL`
- `OLLAMA_URL`

Domyslny lokalny model Ollama to `qwen2.5:14b`.

## 🤝 Współtworzenie

Plan rozwoju jest w [docs/ROADMAP.md](docs/ROADMAP.md), a szczegoly uzycia w [docs/USAGE.md](docs/USAGE.md).

Przed PR-em uruchom:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src/
uv run pytest --cov=pdf2md
```

Testy integracyjne i heavy uruchamiaj swiadomie, z odpowiednimi zaleznosciami i zasobami.

## License

MIT © 2025 Marcin
