# pdf2md

Konwerter PDF do Markdown z obsługą wielu silników ekstrakcji i modeli LLM.

---

## Features

*(TODO — zostanie uzupełnione wraz z implementacją kolejnych etapów)*

- [ ] Wiele silników konwersji: pymupdf4llm, marker-pdf, docling, MinerU, pdf-craft
- [ ] Integracja z LLM: Anthropic Claude, OpenAI GPT, Google Gemini, Ollama
- [ ] Konwersja wsadowa wielu plików
- [ ] Interfejs CLI i GUI (PySide6)
- [ ] Eksport do pliku, Obsidian, Notion

---

## Installation

*(TODO)*

```bash
# Instalacja podstawowa
uv pip install pdf2md

# Z silnikami konwersji
uv pip install "pdf2md[engines-core]"

# Z obsługą LLM
uv pip install "pdf2md[llm]"

# Pełna instalacja
uv pip install "pdf2md[engines-core,llm]"
```

---

## Usage

*(TODO)*

```bash
# Konwersja pojedynczego pliku
pdf2md convert dokument.pdf

# Konwersja z wyborem silnika
pdf2md convert dokument.pdf --engine marker

# Konwersja wsadowa
pdf2md batch *.pdf --output ./markdown/
```

---

## Development

```bash
# Klonowanie i setup
git clone https://github.com/chodzkos/pdf2md
cd pdf2md
uv sync

# Testy
uv run pytest

# Lint i format
uv run ruff check . --fix
uv run ruff format .

# Type check
uv run mypy src/
```

---

## Roadmap

Zobacz [docs/ROADMAP.md](docs/ROADMAP.md) po szczegółowy plan rozwoju.

---

## License

MIT © 2025 Marcin
