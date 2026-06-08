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

## Rozwiązywanie problemów (Windows)

- **Przeciąganie plików do okna nie działa.** Nie uruchamiaj aplikacji jako administrator —
  Windows blokuje wtedy drag-and-drop z Eksploratora (różne poziomy uprawnień, UIPI).
  Uruchamiaj `pdf2md-gui` ze zwykłego PowerShell/terminala.

- **„command not found" przy `pdf2md` / `marker_single` itp.** Pod `uv` programy projektu nie
  trafiają do PATH. Wołaj je przez `uv run pdf2md ...` albo aktywuj środowisko
  (`.venv\Scripts\activate`) na czas sesji.

- **Docling: „CUDA error: no kernel image is available" / crash przy konwersji.** Twoje GPU jest
  zbyt stare dla aktualnego PyTorch (np. GTX 10xx, architektura Pascal sm_61). Wymuś CPU:
  `uv run pdf2md config set docling_device cpu`. Ustawienie „auto" też jest bezpieczne, jeśli
  masz poprawkę z realnym testem CUDA (Etap/PROMPT D3).

- **LLM: „HTTP Error 404: Not Found" (Ollama).** Skonfigurowany model nie jest pobrany.
  Sprawdź `ollama list`, a potem ustaw model, który faktycznie masz, np.
  `uv run pdf2md config set ollama_model qwen2.5:7b`. Duże modele (14B) wymagają dużo VRAM —
  na ≤8 GB VRAM używaj wariantu 7B albo LLM w chmurze.

- **Gemini: „klucz jest, ale pakiet ... nie jest zainstalowany".** Zainstaluj NOWE SDK:
  `uv pip install google-genai` (stare `google-generativeai` jest wycofane / EOL).

- **MinerU nie instaluje się na Pythonie 3.13.** Jego zależność `ray` nie wspiera 3.13 na Windows.
  Instaluj izolowanie na 3.12: `uv tool install mineru --with mineru[all] --python 3.12`.

- **Konwersja skanów daje pusty/zły tekst.** Skany wymagają OCR — zainstaluj Tesseract dla
  Windows (build UB Mannheim) i dodaj do PATH. `uv run pdf2md doctor` podpowie, jeśli go brakuje.
  Dla zwykłych PDF-ów z tekstem Tesseract nie jest potrzebny.

- **Marker/Docling działają bardzo wolno.** Na CPU lub starym GPU to normalne (Marker potrafi
  liczyć stronę wiele minut). Do PDF-ów z tekstem używaj silnika PyMuPDF4LLM — jest błyskawiczny
  i nie wymaga GPU.

- **Diagnostyka.** W razie wątpliwości zacznij od `uv run pdf2md doctor` — pokaże stan GPU,
  Tesseract, silników i kluczy API oraz co doinstalować.
