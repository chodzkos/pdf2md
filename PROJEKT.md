# pdf2md — Dokument Projektowy

> Konwerter PDF do Markdown z wieloma silnikami, GUI, CLI i opcjonalnym wsparciem LLM

---

## Spis treści
1. [Cel i zakres projektu](#cel-i-zakres-projektu)
2. [Stack technologiczny](#stack-technologiczny)
3. [Architektura](#architektura)
4. [Co musisz przygotować SAM](#co-musisz-przygotować-sam)
5. [Powiązane dokumenty](#powiązane-dokumenty)

---

## Cel i zakres projektu

### Problem
Konwersja PDF → Markdown jest trudna bo PDF to format prezentacyjny (pozycje pikseli), a Markdown strukturalny (semantyka). Nie istnieje jedno idealne narzędzie — każde sprawdza się lepiej w innym rodzaju dokumentu.

### Rozwiązanie
Aplikacja będąca **orkiestratorem** gotowych, sprawdzonych silników konwersji. Użytkownik wybiera silnik odpowiedni do swojego dokumentu, opcjonalnie wspomaga go lokalnym lub chmurowym LLM.

### Zakres v1.0
- Obsługa 5 silników konwersji (od trywialnych do zaawansowanych)
- Opcjonalne wspomaganie LLM (lokalny Ollama lub chmura: Claude/OpenAI/Gemini)
- Interfejs GUI (okienkowy, drag & drop)
- Interfejs CLI (terminal, batch processing, skrypty)
- Wyjście: Markdown (opcjonalnie EPUB przez Pandoc jeśli zainstalowany)
- Działanie w 100% lokalnie (LLM chmurowy — opcjonalne)
- Cross-platform: Windows (WSL), Linux, macOS

---

## Stack technologiczny

### Język
**Python 3.11+** — najlepsze wsparcie bibliotek konwersji PDF

### Silniki konwersji (adaptery)

| Silnik | Pip | Mocna strona | Trudność instalacji |
|---|---|---|---|
| **PyMuPDF4LLM** | `pymupdf4llm` | Najszybszy, natywny tekst | ⭐ Trywialna |
| **Marker** | `marker-pdf` | Uniwersalny, OCR, `--use_llm` | ⭐⭐ Łatwa |
| **MinerU** | `mineru` | Naukowe, wielokolumnowe, CJK | ⭐⭐⭐ Średnia |
| **Docling** | `docling` | Enterprise, tabele, RAG | ⭐⭐ Łatwa |
| **pdf-craft** | `pdf-craft` | Skanowane książki → EPUB | ⭐⭐ Łatwa |

### Dostawcy LLM

| Dostawca | Typ | SDK | Klucz API |
|---|---|---|---|
| **Ollama** | Lokalny | HTTP REST | ❌ nie potrzeba |
| **Claude** (Anthropic) | Chmura | `anthropic` | ✅ wymagany |
| **OpenAI** | Chmura | `openai` | ✅ wymagany |
| **Gemini** (Google) | Chmura | `google-generativeai` | ✅ wymagany |

### Interfejsy
- **GUI:** `PySide6` (Qt 6) — nowoczesny, natywny wygląd
- **CLI:** `click` — czytelna składnia, dobre helpsy

### Narzędzia pomocnicze
| Cel | Biblioteka |
|---|---|
| Progress bars CLI | `rich` |
| Konfiguracja + walidacja | `pydantic-settings` |
| Logowanie | `loguru` |
| Testy | `pytest` + `pytest-cov` |
| Linter/formatter | `ruff` |
| Statyczne typy | `mypy` |
| Menedżer pakietów | `uv` |
| Hooki git | `pre-commit` |
| Pakowanie do exe | `PyInstaller` |

### Opcjonalne (systemowe)
- **Pandoc** — eksport MD → EPUB (jeśli zainstalowany, pojawia się przycisk w GUI)
- **Tesseract** — wymagany przez część silników (Marker, Docling)
- **Poppler** — wymagany przez pdf2image (używany przez niektóre silniki)
- **Ollama** — osobny serwis dla lokalnego LLM

---

## Architektura

### Struktura katalogów

```
pdf2md/
├── src/pdf2md/
│   ├── __init__.py
│   │
│   ├── engines/                    # Adaptery silników konwersji
│   │   ├── __init__.py
│   │   ├── base.py                 # Abstrakcja ConversionEngine + ConversionResult
│   │   ├── pymupdf4llm_engine.py   # Adapter PyMuPDF4LLM
│   │   ├── marker_engine.py        # Adapter Marker
│   │   ├── mineru_engine.py        # Adapter MinerU
│   │   ├── docling_engine.py       # Adapter Docling
│   │   └── pdf_craft_engine.py     # Adapter pdf-craft
│   │
│   ├── llm/                        # Dostawcy LLM do post-processingu
│   │   ├── __init__.py
│   │   ├── base.py                 # Abstrakcja LLMProvider
│   │   ├── ollama_provider.py      # Lokalny Ollama
│   │   ├── anthropic_provider.py   # Claude API
│   │   ├── openai_provider.py      # OpenAI API
│   │   └── gemini_provider.py      # Google Gemini API
│   │
│   ├── core/                       # Logika rdzeniowa
│   │   ├── __init__.py
│   │   ├── registry.py             # Wykrywanie dostępnych silników i LLM
│   │   ├── converter.py            # Orkiestrator konwersji
│   │   └── config.py               # Ustawienia (pydantic-settings, TOML)
│   │
│   ├── cli/                        # Interfejs linii komend
│   │   ├── __init__.py
│   │   └── main.py                 # click commands
│   │
│   ├── gui/                        # Interfejs graficzny
│   │   ├── __init__.py
│   │   ├── app.py                  # QApplication setup
│   │   ├── main_window.py          # Główne okno
│   │   ├── workers.py              # QThread workers (nieblokujące UI)
│   │   ├── settings_dialog.py      # Okno ustawień
│   │   └── widgets/
│   │       ├── engine_selector.py  # Widget wyboru silnika
│   │       ├── llm_selector.py     # Widget wyboru LLM
│   │       ├── file_list.py        # Lista plików do konwersji
│   │       └── log_panel.py        # Panel logów
│   │
│   └── utils/
│       ├── __init__.py
│       ├── logging.py              # Konfiguracja loguru
│       └── pandoc.py               # Opcjonalny eksport przez Pandoc
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/                   # Przykładowe PDF-y do testów
│
├── docs/
│   ├── README.md
│   └── USAGE.md
│
├── .github/
│   └── workflows/
│       ├── ci.yml                  # Testy + lint na każdy PR
│       └── release.yml             # Build exe na tag v*
│
├── pyproject.toml                  # Konfiguracja projektu (uv)
├── .env.example                    # Przykładowy plik z kluczami API
├── .gitignore
├── .pre-commit-config.yaml
├── LICENSE                         # MIT
├── README.md
├── ROADMAP.md                      # → roadmap.md
├── PROMPTS.md                      # → prompts.md (tylko dla ciebie, nie do repo)
└── FEATURES.md                     # → features.md
```

### Wzorzec adaptera — serce architektury

Każdy silnik implementuje ten sam interfejs:

```python
# engines/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

@dataclass
class ConversionResult:
    markdown: str           # Wynikowy Markdown
    engine_used: str        # Nazwa silnika
    pages: int              # Liczba stron
    warnings: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

class ConversionEngine(ABC):
    name: str               # "PyMuPDF4LLM"
    description: str        # "Szybki, dla natywnych PDF"
    supports_ocr: bool      # Czy radzi ze skanami?
    supports_llm: bool      # Czy ma wbudowany tryb LLM?
    requires_gpu: bool      # Czy potrzebuje GPU?

    @abstractmethod
    def is_available(self) -> bool:
        """Sprawdź czy biblioteka jest zainstalowana."""

    @abstractmethod
    def convert(self, pdf_path: str, **kwargs) -> ConversionResult:
        """Wykonaj konwersję PDF → Markdown."""
```

### Registry — co jest zainstalowane?

```python
# core/registry.py
class EngineRegistry:
    def get_available_engines(self) -> list[ConversionEngine]:
        """Zwróć tylko silniki które dają True na is_available()"""

    def get_available_llm_providers(self) -> list[LLMProvider]:
        """Zwróć dostępne dostawców LLM (sprawdź klucze API + Ollama)"""
```

GUI pokazuje tylko dostępne opcje. Niedostępne są szare z tooltipem "Jak zainstalować?".

### Przepływ konwersji

```
Użytkownik wybiera PDF + silnik + opcje LLM
            ↓
     Converter.convert()
            ↓
    Engine.convert(pdf)
            ↓
   [jeśli LLM włączony]
   LLMProvider.postprocess(markdown)
            ↓
      Zapis .md do dysku
            ↓
   [jeśli Pandoc dostępny i żądany]
   pandoc input.md -o output.epub
```

### LLM jako post-processing (nie per-strona)

Kluczowe uproszczenie względem poprzedniego projektu: LLM **nie** przetwarza każdej strony osobno. Zamiast tego:

1. Silnik robi pełną konwersję → surowy Markdown
2. LLM opcjonalnie czyści wynik: usuwa artefakty OCR, naprawia tabelki, poprawia kolejność tekstu
3. Jeden call API zamiast N (gdzie N = liczba stron)

Wyjątek: Marker ma wbudowany `--use_llm` który działa per-strona — tam korzystamy z jego własnej implementacji.

---

## Co musisz przygotować SAM

> Wykonaj te kroki **przed** uruchomieniem Claude Code. Zajmą ok. 30-45 minut.

### KROK 1 — Konto GitHub
Jeśli nie masz: https://github.com/signup
Zapamiętaj nazwę użytkownika (przyda się w KROKU 4).

### KROK 2 — Klucz SSH dla GitHub
Otwórz terminal WSL i wykonaj:
```bash
ssh-keygen -t ed25519 -C "twoj@email.com"
# Naciśnij Enter 3 razy (domyślne ustawienia)

cat ~/.ssh/id_ed25519.pub
# Skopiuj cały output
```
Wejdź na https://github.com/settings/keys → **New SSH key** → wklej → zapisz.

Sprawdź:
```bash
ssh -T git@github.com
# Powinieneś zobaczyć: Hi <twoja-nazwa>! You've successfully authenticated...
```

### KROK 3 — Konfiguracja Git
```bash
git config --global user.name "Twoje Imię"
git config --global user.email "twoj@email.com"
git config --global init.defaultBranch main
```

### KROK 4 — Nowe repozytorium na GitHub
1. Wejdź na https://github.com/new
2. Name: `pdf2md`
3. Description: `PDF to Markdown converter with multiple engines, GUI and CLI`
4. Public lub Private — twój wybór
5. **NIE zaznaczaj** żadnych checkboxów (Add README, .gitignore, license)
6. Kliknij **Create repository**
7. Zapisz URL w formacie: `git@github.com:TWOJ-USER/pdf2md.git`

### KROK 5 — Instalacja uv (menedżer pakietów Python)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
uv --version   # powinno pokazać wersję
```

### KROK 6 — Pakiety systemowe w WSL
```bash
sudo apt update && sudo apt install -y \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-pol \
    tesseract-ocr-eng \
    libgl1 \
    libglib2.0-0

# Sprawdź:
pdftotext --version
tesseract --version
```

### KROK 7 — (Opcjonalne) Klucze API dla LLM w chmurze
Tylko jeśli chcesz używać chmurowych LLM do post-processingu:

- **Anthropic Claude:** https://console.anthropic.com → API Keys
- **OpenAI:** https://platform.openai.com/api-keys
- **Gemini:** https://aistudio.google.com/app/apikey

Klucze wpisz dopiero w `.env` PO stworzeniu projektu (KROK 9).

### KROK 8 — (Opcjonalne) Pandoc — eksport do EPUB
```bash
sudo apt install -y pandoc
pandoc --version
```
Jeśli zainstalowany, aplikacja automatycznie udostępni opcję eksportu do EPUB.

### KROK 9 — Klonowanie repo i pierwsze uruchomienie
```bash
mkdir -p ~/projekty
cd ~/projekty
git clone git@github.com:TWOJ-USER/pdf2md.git
cd pdf2md

# Skopiuj dokumenty projektowe do repozytorium
# (PROJEKT.md, ROADMAP.md, PROMPTS.md, FEATURES.md)

# Jeśli masz klucze API, utwórz .env:
cat > .env << 'EOF'
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AI...
EOF
```

### KROK 10 — Otwórz projekt w VS Code + Claude Code
```bash
code .
# W terminalu VS Code (Ctrl+`):
claude
```

**Od tego momentu Claude Code przejmuje inicjalizację projektu.**
Wklej Prompt #0 z pliku PROMPTS.md i postępuj zgodnie z instrukcjami.

### KROK 11 — Pliki testowe PDF
Zbierz różne PDF-y i wgraj do `tests/fixtures/`:
- `test_text.pdf` — zwykły ebook/artykuł (tekst selectable)
- `test_columns.pdf` — wielokolumnowy (np. gazeta, artykuł naukowy)
- `test_tables.pdf` — z tabelami (raport, specyfikacja)
- `test_scan.pdf` — zeskanowany dokument (fotografia strony)
- `test_mixed.pdf` — mieszany (część tekst, część scan)

---

## Powiązane dokumenty

| Plik | Zawartość |
|---|---|
| `ROADMAP.md` | Etapy projektu, timeline, checklist |
| `PROMPTS.md` | Gotowe promty do wklejenia w Claude Code |
| `FEATURES.md` | Plany na przyszłość po ukończeniu v1.0 |
