# Instalacja pdf2md

`pdf2md` jest publikowany jako pakiet Python. Domyslny pakiet zawiera orkiestrator, CLI i GUI, ale nie bundluje ciezkich ani copyleftowych silnikow konwersji. Silniki dokladasz w swoim srodowisku.

## Sam orkiestrator

Najprostsza instalacja jako narzedzie uzytkownika:

```bash
uv tool install pdf2md
pdf2md doctor
```

Alternatywnie, w aktywnym virtualenv:

```bash
uv pip install pdf2md
pdf2md doctor
```

## Dokladanie silnikow

W aktywnym virtualenv instaluj wybrane silniki bezposrednio:

```bash
uv pip install pymupdf4llm
uv pip install docling
uv pip install marker-pdf
uv pip install pdf-craft
```

Jesli uzywasz izolowanego `uv tool`, dolacz zaleznosci do srodowiska narzedzia przy instalacji:

```bash
uv tool install pdf2md --with pymupdf4llm --with docling
```

Po instalacji sprawdz status:

```bash
pdf2md doctor
pdf2md list-engines
```

## LLM

Lokalny provider Ollama nie wymaga SDK Pythona, ale wymaga dzialajacej uslugi Ollama.

SDK dla providerow chmurowych:

```bash
uv pip install anthropic
uv pip install openai
uv pip install google-genai
```

Potrzebne klucze ustawiasz w `~/.config/pdf2md/config.toml` albo przez zmienne srodowiskowe:

```bash
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
GEMINI_API_KEY=...
```

## MinerU

MinerU jest silnikiem CLI i nie jest extra pakietu `pdf2md`. Instaluj go jako osobne narzedzie:

```bash
uv tool install mineru --with mineru[all]
mineru --help
```

`pdf2md doctor` sprawdzi, czy komenda `mineru` jest widoczna w `PATH`.

## Pierwsza diagnostyka

Po instalacji uruchom:

```bash
pdf2md doctor
```

Komenda pokazuje brakujace SDK, Tesseracta, Poppler, Pandoc, status Ollamy, status silnikow i realny wynik `cuda_usable()`.

## Szybki test

```bash
pdf2md list-engines
pdf2md convert tests/fixtures/test_text_1page.pdf --engine pymupdf4llm
```

Jesli silnik nie jest dostepny, `pdf2md` zakonczy sie czytelnym bledem i podpowie, co doinstalowac.
