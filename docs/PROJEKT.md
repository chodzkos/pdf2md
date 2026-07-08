# pdf2md Squeezer — Dokument Projektowy

> Konwerter PDF do Markdown z wieloma silnikami, GUI, CLI i opcjonalnym wsparciem LLM
>
> **Nazwa produktu:** pdf2md Squeezer · **Pakiet/komenda:** `pdf2md` (bez spacji — wymóg nazewnictwa Pythona)

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
- **3 silniki rdzeniowe** (stabilne, testowane): PyMuPDF4LLM, Marker, Docling
- **1 silnik opcjonalny** (izolowany, dwa backendy): MinerU (`pipeline` domyślny, `vlm` dla maksymalnej jakości)
- **pdf-craft — wykluczony** (nieusuwalny konflikt `transformers` z Markerem; redundantny — zob. macierz zgodności silników)
- Opcjonalne wspomaganie LLM (lokalny Ollama lub chmura: Claude/OpenAI/Gemini), z trybami chunkowania
- Interfejs GUI (okienkowy, drag & drop)
- Interfejs CLI (terminal, batch processing, skrypty) + komenda diagnostyczna `pdf2md doctor`
- Wyjście: Markdown (opcjonalnie EPUB przez Pandoc jeśli zainstalowany)
- Działanie w 100% lokalnie (LLM chmurowy — opcjonalne)
- Cross-platform: Windows (WSL), Linux, macOS

> **Uwaga o skanach w v1.0:** v1.0 obsługuje proste skany przez istniejące silniki (Marker/Docling z OCR), ale **bez gwarancji jakości książkowej**. Lepszą jakość daje MinerU (backend `vlm` na GPU), a wysokiej jakości pipeline do skanowanych książek to dopiero Faza 2 (premium scan pipeline).

### Zakres Fazy 2 (premium scan pipeline)
Po ukończeniu v1.0 — dedykowany pipeline do skanowanych książek oparty na VLM-OCR (olmOCR / PaddleOCR-VL / Surya), z preprocessingiem obrazu, korektą LLM per-strona, walidacją jakości i składaniem książki do Markdown/EPUB. Szczegóły w ROADMAP (etapy 11–15). Materiał źródłowy: notatki z badań nad modelami OCR/LLM do skanów książek.

> **⚠️ Dwa twarde ograniczenia Fazy 2 na sprzęcie 24 GB VRAM:**
> 1. **VRAM — modele NIE współistnieją.** olmOCR-2-7B (~7–8 GB) i qwen3:14b (~9–10 GB) + narzut PyTorch + bufory obrazów 400–600 DPI przebiją 24 GB → OOM CUDA. Pipeline musi działać **sekwencyjnie**: najpierw cała faza VLM-OCR, potem **wyładowanie modelu wizyjnego** (Ollama: `keep_alive=0`; vLLM: zamknięcie procesu/`torch.cuda.empty_cache()`), dopiero potem faza korekty LLM. Nigdy oba modele załadowane naraz.
> 2. **Dysk — preprocessing strumieniowo.** 500 stron PNG przy 600 DPI to 15–25 GB plików tymczasowych. Pipeline przetwarza strony **paczkami** (np. po 20): preprocessing → OCR → zapis MD/JSON → natychmiastowe usunięcie PNG paczki. `work/` czyszczony automatycznie po udanym buildzie EPUB.

### Poziomy sprzętu — co realnie zadziała na danej maszynie
Projekt celuje docelowo w mocny sprzęt (RTX 5090 Laptop 24 GB / 128 GB RAM), ale część prac robisz na słabszym notebooku. To są realne granice:

| Komponent | Słaby (16 GB RAM, GTX 1070 8 GB) | Mocny (128 GB RAM, RTX 5090 24 GB) |
|---|---|---|
| PyMuPDF4LLM (bez ML) | ✅ idealny, podstawowy silnik | ✅ |
| Docling (CPU) | ✅ działa | ✅ |
| Marker | ⚠️ tylko pojedyncze, małe pliki, multiprocessing OFF, 1 worker | ✅ |
| LLM lokalny (Ollama) | ⚠️ tylko małe modele (~7B Q4, ~5 GB); 14B się nie zmieści | ✅ qwen3:14b (lub 27–32B przy 24 GB) |
| LLM chmurowy (Claude/Gemini) | ✅ zalecany do post-processingu | ✅ |
| Faza 2 — VLM-OCR (olmOCR FP8) | ❌ **niewykonalne** (Pascal nie ma FP8; 7B nie zmieści się w 8 GB) | ✅ |

**Wniosek dla słabego notebooka:** rozwijaj i używaj Fazy 1 z PyMuPDF4LLM jako głównym silnikiem, Markera tylko zachowawczo na małych plikach, a post-processing przez **chmurę** (nie lokalny 14B). Fazę 2 (VLM, skany książek) zostaw na maszynę z RTX 5090 — na GTX 1070 nie ruszy.

---

## Stack technologiczny

### Język
**Python 3.11+** — najlepsze wsparcie bibliotek konwersji PDF

### Silniki konwersji (adaptery)

| Silnik | Pip | Mocna strona | Trudność | Licencja |
|---|---|---|---|---|
| **PyMuPDF4LLM** | `pymupdf4llm` | Najszybszy, natywny tekst | ⭐ Trywialna | AGPL/komercyjna |
| **Marker** | `marker-pdf` | Uniwersalny, OCR, `--use_llm` | ⭐⭐ Łatwa | **GPL** (wyjątek <$2M) |
| **MinerU** | `uv tool` (izolowany) | Naukowe, wielokolumnowe, CJK | ⭐⭐⭐ Średnia | AGPL |
| **Docling** | `docling` | Enterprise, tabele, RAG | ⭐⭐ Łatwa | MIT |
| **pdf-craft** | ~~`pdf-craft`~~ | Skanowane książki | ❌ wykluczony | sprawdź |

> **⚠️ Uwaga licencyjna (ważna dla dystrybucji).** Sam kod pdf2md Squeezer jest MIT, ale kilka silników ma licencje copyleft (Marker — GPL, MinerU **i PyMuPDF/PyMuPDF4LLM** — AGPL). Dlatego **główny kanał dystrybucji v1.0 to pakiet pip/uv**: publikujesz wyłącznie swój kod MIT, a silniki copyleft instaluje sam użytkownik u siebie (`uv pip install ...`) — to nie jest dystrybucja tych pakietów przez Ciebie. Problem pojawiłby się dopiero przy **wkompilowaniu silnika copyleft w jedno frozen binary** — wtedy dystrybucja binarki musiałaby respektować GPL/AGPL. Stąd: frozen binary dopiero w Etapie 10b (po Fazie 2), bundlujące **wyłącznie własny silnik MIT** (F02: pdfplumber/pdfminer.six/Tesseract — permisywne) i żadnego copyleft. Dotyczy to też przyszłego camelot (F02): sam camelot jest MIT, ale jego historyczna zależność Ghostscript to AGPL — w aktualnych wersjach camelota domyślny backend to pdfium (BSD), więc używaj pdfium i nie instaluj Ghostscriptu.

> **⚙️ Dwie kategorie silników — ważne dla instalacji i konfliktów zależności.**
> - **Importowane w procesie** (PyMuPDF4LLM, Marker, Docling) — żyją we wspólnym środowisku projektu (`uv add ...`) i **nawzajem ograniczają zależności**. Stąd realne konflikty: Marker/Docling vs pdf-craft kłócą się o wersję `transformers` (zob. macierz zgodności). Marker/surya deklarują też `pillow<11`, ale ten cap jest **przeterminowany** — projekt nadpisuje go do `pillow>=12.2` przez `[tool.uv] override-dependencies` (łata CVE parsera obrazów; empirycznie potwierdzone na GPU, że Surya/Marker działają na 12.2 — zob. „Override pillow" w „Kluczowych wnioskach").
> - **Wołane przez CLI/subprocess** (MinerU) — instalowane **izolowanie** przez `uv tool install mineru --with mineru[all]`, w osobnym środowisku. Powód izolacji to **ciężki, kolidujący stos MinerU** (vLLM/flashinfer/nvcc, własny torch/transformers), **nie** pillow — od czasu override wspólne środowisko i tak pracuje na `pillow>=12.2` (`pillow>=11` MinerU nie byłoby już samo w sobie konfliktem). Adapter znajduje komendę przez `shutil.which("mineru")`. **MinerU nie jest zależnością pip projektu.** (CLI nazywa się `mineru` w wersji 2.x+; `magic-pdf` to przestarzała komenda 1.x.)

#### Macierz zgodności silników (zweryfikowana empirycznie, czerwiec 2026)

Wersje testowe: docling 2.100.0, marker-pdf 1.10.2, surya-ocr 0.17.1. Zgodności bywają wersjozależne — przy aktualizacjach warto je przejrzeć ponownie.

| Silnik | Środowisko | Wymóg `transformers` | Wymogi runtime | Status v1.0 |
|---|---|---|---|---|
| **PyMuPDF4LLM** | wspólne | brak (nie używa) | brak | ✅ podstawowy, zawsze działa |
| **Marker** (surya 0.17.x) | wspólne | **≥4.56.1** (wymusza `surya-ocr 0.17.1`; sam Marker ≥4.48 przez `ALL_ATTENTION_FUNCTIONS`) | Tesseract do skanów | ✅ (marker-pdf **przypięty `>=1.10,<2`**) |
| **Docling** | wspólne | **≥4.48** (zgodny z Markerem po aktualizacji Doclinga) | — | ✅ |
| **MinerU `pipeline`** | izolowane (`uv tool`) | n/d (osobne env) | omija vLLM/flashinfer; działa na GPU przez torch | ✅ pewny domyślny |
| **MinerU `vlm`** | izolowane (`uv tool`) | n/d (osobne env) | `build-essential` (gcc dla Tritona) + `VLLM_USE_FLASHINFER_SAMPLER=0` na nowym GPU | ✅ max jakość skanów |
| **pdf-craft** (DeepSeek-OCR) | wspólne | **<4.48** (symbol `LlamaFlashAttention2`, usunięty w 4.48) | — | ❌ **WYKLUCZONY** |

**Kluczowe wnioski:**
- **Marker, Docling i surya 0.17.x pogodzone** na `transformers>=4.56,<5`. Realny dolny próg podnosi **`surya-ocr 0.17.1` (wymaga `transformers>=4.56.1`)**, którą ciągnie marker-pdf 1.10.x; Docling 2.97 współistnieje. **Krytyczne: `marker-pdf` MUSI być przypięty do `>=1.10,<2`** — bez pinu resolver po cichu cofa go do **0.3.10** (stare API, pin `surya 0.6.x`), co objawia się `ModuleNotFoundError: No module named 'marker.config'` przy konwersji. **Pin przyjęty** w extra `engines-core`:

```toml
[project.optional-dependencies]
marker = ["marker-pdf>=1.10,<2"]
engines-core = [
    "pymupdf4llm>=0.0.17",
    "marker-pdf>=1.10,<2",     # PIN OBOWIĄZKOWY — bez niego resolver bierze 0.3.10 (inne API)
    "docling>=2.0",
]
# opencv NIE pinujemy — surya 0.17.x wymaga DOKŁADNIE opencv-python-headless==4.11.0.86 i sama je dostarcza
```
> Górne ograniczenie `<5` jest świadome: linia `transformers 5.x` reorganizuje moduły (m.in. przeniesienie `ALL_ATTENTION_FUNCTIONS`) i potrafi zepsuć surya/Docling. Zdejmij je dopiero, gdy biblioteki ogłoszą wsparcie 5.x. Nie dodawaj własnego pinu `opencv-python-headless` — koliduje z dokładnym `==4.11.0.86` od surya 0.17.x.


- **Override pillow (`>=12.2`).** marker-pdf i surya-ocr deklarują `pillow<11`, ale najnowsze wydania (marker-pdf 1.10.2, surya-ocr 0.20.0) wciąż trzymają ten cap mimo że realnie działają na pillow 12 — potwierdzone empirycznie na GPU (Surya recognition/detection + Marker + `--extract-images`/`PIL.verify()` na pillow 12.2). Cap nadpisany w `pyproject.toml`:

  ```toml
  [tool.uv]
  override-dependencies = ["pillow>=12.2"]
  ```

  Powód: wciągnięcie łat CVE (CVE-2026-25990/40192/42310/42311, PYSEC-2026-165) w parserze obrazów — lepsze niż downgrade do pillow 10.x + `pip-audit --ignore-vuln` na niezałatane podatności. **Uwaga:** override zdejmuje *wszystkie* ograniczenia na pillow, także `<13` od doclinga — przy każdym podbiciu marker/surya/docling zweryfikuj ponownie (docelowo zawęź do `pillow>=12.2,<13`).

- **pdf-craft wzajemnie wyklucza się z Markerem — USUNIĘTY z projektu.** pdf-craft (przez DeepSeek-OCR → `doc-page-extractor`) wymaga `transformers<4.48` (`LlamaFlashAttention2`), a Marker 1.10.x ciągnie surya 0.17.1 z `transformers>=4.56.1` — przepaść jeszcze większa niż samo `≥4.48`. Nie istnieje wspólna wersja. pdf-craft jest też redundantny (skany obsługują Marker i MinerU). **Wyrzucony z pyproject całkowicie.**
  - **Pułapka, która nas kosztowała kilka rund:** pdf-craft był zadeklarowany w **dwóch** extra naraz — w samodzielnej grupie `"pdf-craft"` **oraz** w `engines-optional = ["pdf-craft>=0.1"]`. uv rozwiązuje **wszystkie** extra do jednego spójnego locka, więc nawet niezainstalowany pdf-craft blokował resolucję marker-pdf 1.10.x. Usunięcie go z jednej grupy nie wystarczało — trzeba było wyczyścić **obie**. Wniosek: porzucając opcjonalny silnik, usuń jego deklarację ze **wszystkich** extra (i z `engines/__init__.py`), nie tylko z jednej.
  - **Gdyby pdf-craft był jednak potrzebny:** da się go zizolować jak MinerU (subprocess + własne środowisko z `transformers<4.48`), ale trudniej — pdf-craft to biblioteka bez CLI, więc trzeba dorobić cienki wrapper. **Forka NIE rób** — feralny import siedzi w zdalnym kodzie modelu DeepSeek-OCR (`modeling_deepseekv2.py`, `trust_remote_code`), nie w pdf-craft. **Najpierw porównaj jakość pdf-craft vs MinerU/vlm na realnym skanie** — izoluj tylko, jeśli pdf-craft wyraźnie wygrywa.
- **MinerU/vlm na premierowym GPU** (np. Blackwell sm_120): flashinfer nie ma gotowego cubina i JIT-kompiluje sampler przez nvcc; bez CUDA Toolkitu pada. Fix to `VLLM_USE_FLASHINFER_SAMPLER=0` (natywny sampler PyTorch) — **nie** cofanie flashinfera do 0.3.0 (na nowej architekturze JIT i tak wymuszony). Adapter ustawia tę zmienną sam dla backendu vlm (zob. PROMPT D7).


#### Silniki VLM-OCR (Faza 2 — premium scan pipeline)

Te silniki wchodzą do gry dopiero w Fazie 2 (zob. ROADMAP, etapy 11–15). Są oparte na modelach wizyjno-językowych (VLM), wymagają GPU i są zaprojektowane pod skanowane książki. Idealnie pasują do Twojego sprzętu (RTX 5090 Laptop 24 GB VRAM + 128 GB RAM).

| Silnik | Typ | Mocna strona | GPU |
|---|---|---|---|
| **olmOCR** (olmOCR-2-7B) | VLM 7B | Czysty Markdown, równania, tabele, kolejność czytania | ✅ wymagany |
| **PaddleOCR-VL** | VLM lekki (0.9B) | Wydajny parser dokumentów, wielojęzyczny | ✅ **potwierdzony na Blackwellu** (zob. niżej) |
| **Surya** | OCR + layout | Layout, reading order, detekcja + OCR per-strona | ✅ **działa in-process** (surya 0.17.x, predyktory — patrz niżej) |

> **PaddleOCR-VL — zweryfikowany na RTX 5090 (Blackwell sm_120), czerwiec 2026.** Działa jako
> **trwały serwer HTTP** (OpenAI-compatible), nie podproces — startuje raz, model siedzi ciepły,
> kolejne strony lecą szybko. To czyni go **dobrym do wsadu / całych książek**; do pojedynczych
> konwersji prostszy operacyjnie jest MinerU (podproces, bez serwera do pilnowania).
> - **Środowisko:** osobny venv `~/.venvs/paddleocr`, izolowany od projektu (ma `transformers 5.x`
>   z nightly — nie wolno mieszać z `engines-core`, które jest `<5`). Adapter `paddleocr_vl_engine.py`
>   to tylko klient HTTP na `http://localhost:8000/v1`. **`is_available()` pinguje serwer**
>   (`GET {paddleocr_vl_url}/models`), a NIE importuje `paddle` — bo dostępność silnika-usługi to
>   osiągalność serwera, nie obecność pakietu (poprawka: PROMPT D9).
> - **Przepis instalacji (Blackwell):** świeży venv → `uv pip install -U vllm --pre
>   --torch-backend=auto --extra-index-url https://wheels.vllm.ai/nightly` (NIE wymuszać ręcznie
>   `cu129` + `unsafe-best-match` — daje rozjazd cu12/cu13 i `libcudart.so.13`). Start:
>   `VLLM_USE_FLASHINFER_SAMPLER=0 vllm serve PaddlePaddle/PaddleOCR-VL-1.6 --trust-remote-code
>   --no-enable-prefix-caching` (env wymagane — flashinfer JIT-uje sampler i pada na nvcc, ten sam
>   fix co MinerU/vlm). `paddle` (framework) niepotrzebny do samego VLM; pełny pipeline z layoutem
>   = osobny venv-klient. Szczegóły krok po kroku w INSTALL.md (sek. 2.8).
> - **Jakość (skan polskiej książki historycznej):** bardzo dobra — poprawne diakrytyki, zachowane
>   akapity, wierne odtworzenie nawiasów kwadratowych z oryginału. Drobne artefakty na zawijaniach
>   wierszy (sklejone słowa, pojedyncze literówki) — do dobicia modelem korekty w Etapie 13.
> - **VRAM:** serwer bierze domyślnie ~92% (`--gpu-memory-utilization=0.92`, ~22 GB z 24). Obok nie
>   zmieści się model korekty — stąd sekwencja „zabij serwer → załaduj qwen3" w Etapie 13.

> **Surya — DZIAŁA in-process (czerwiec 2026, potwierdzone konwersją).** marker-pdf **1.10.x**
> pinuje `surya-ocr 0.17.x` — nowe, **predyktorowe API** (`DetectionPredictor`, `FoundationPredictor`,
> `RecognitionPredictor`), dokładnie to, pod które pisany jest adapter `surya_engine.py`. Surya
> ładuje predyktory i konwertuje skan w głównym venv (torch, transformers ≥4.56.1 z surya 0.17.1).
> NIE jest redundantna z Markerem: choć Marker używa surya wewnętrznie, to inna ścieżka wyniku —
> Surya jako samodzielny silnik daje detekcję + OCR per-strona bez warstwy struktury Markera.
>
> > **KOREKTA wcześniejszego, błędnego wniosku.** Przez chwilę dokumentacja mówiła „Surya
> > zablokowana na 0.6.x, redundantna, odłożona". To była **pomyłka diagnostyczna** spowodowana
> > **cichym downgrade'em marker-pdf do 0.3.10**: nieprzypięty `marker-pdf>=0.2` pozwalał resolverowi
> > cofnąć się do prastarej 0.3.10, która pinuje `surya-ocr 0.6.x` (funkcyjne API: `batch_text_detection`).
> > Odczyt `marker.requires()` na 0.3.10 pokazywał `surya-ocr<0.7.0` — i stąd fałszywy wniosek. Po
> > przypięciu `marker-pdf>=1.10,<2` wraca surya 0.17.x i adapter działa. **Reguła:** marker-pdf MUSI
> > być przypięty do 1.x (bez pinu → 0.3.10 → `ModuleNotFoundError: No module named 'marker.config'`,
> > bo 0.3.10 ma zupełnie inne API).
>
> Nowoczesna **Surya 2.0** (v0.20+, pojedynczy VLM ~650M serwowany przez vllm/llama.cpp) to **inny
> byt** niż predyktorowa 0.17.x — silnik-usługa jak PaddleOCR-VL, i jako taki dubluje
> PaddleOCR-VL/MinerU na NVIDIA. Tylko **ona** zostaje w FEATURES (F19) jako ewentualne przyszłe
> wdrożenie izolowanego silnika — 0.17.x in-process już pokrywa potrzebę „Surya działa".

### Dostawcy LLM

| Dostawca | Typ | SDK | Klucz API |
|---|---|---|---|
| **Ollama** | Lokalny | HTTP REST | ❌ nie potrzeba |
| **Claude** (Anthropic) | Chmura | `anthropic` | ✅ wymagany |
| **OpenAI** | Chmura | `openai` | ✅ wymagany |
| **Gemini** (Google) | Chmura | `google-genai` | ✅ wymagany |

> **Dobór modelu Ollama (tylko sugestia — model ustawiasz w `config.toml` per-maszyna).** Do post-processingu (czyszczenie Markdown, naprawa tabel — zadanie instrukcyjne, nie rozumowanie) sprawdza się aktualny **Qwen3 instruct**: `qwen3:14b` jako wydajny domyślny, a na 24 GB VRAM można sięgnąć po `qwen3:27b`/`30b` (lub nowsze dense'y). Wyłącz tryb „thinking" — czyszczenie ma być dosłowne i szybkie. Alternatywa: `gemma4` (dobra wielojęzycznie). **Unikaj modeli rozumujących** (DeepSeek-R1) do tego zadania — chain-of-thought tylko spowalnia. Nazwy/tagi modeli zmieniają się często, więc zweryfikuj aktualne w bibliotece Ollamy; na słabym sprzęcie (≤8 GB VRAM) trzymaj się ~7–8B (np. `qwen3:8b`) albo LLM w chmurze.

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
│   │   └── docling_engine.py       # Adapter Docling
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
│   │   ├── config.py               # Ustawienia (pydantic-settings, config.toml + .env)
│   │   └── prompts.py              # Prompty LLM (post-processing, korekta skanów)
│   │
│   ├── detection/                  # Wykrywanie typu PDF i zależności
│   │   ├── __init__.py
│   │   ├── pdf_type.py             # native / scanned / mixed
│   │   └── dependencies.py         # Stan systemu (Tesseract, Poppler, Pandoc, GPU...)
│   │
│   ├── exporters/                  # Warstwa eksportu (od razu, choć na start tylko 2)
│   │   ├── __init__.py
│   │   ├── base.py                 # ABC BaseExporter
│   │   ├── markdown_exporter.py    # Zapis .md
│   │   └── pandoc_epub_exporter.py # EPUB przez Pandoc (natywny ebooklib → F01 później)
│   │
│   ├── cli/                        # Interfejs linii komend
│   │   ├── __init__.py
│   │   └── main.py                 # click commands (convert, doctor, list-*, config)
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
│       └── chunking.py             # Dzielenie tekstu na potrzeby LLM
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

> **⚡ Ważna zasada wydajności — `is_available()` NIE importuje silnika.** Registry odpytuje `is_available()` wszystkich silników przy każdym `--help`, starcie GUI czy `list-engines`. Gdyby `is_available()` robił `import marker`/`import docling`, ładowałby do pamięci gigabajty zależności (PyTorch, biblioteki wizyjne) — start trwałby kilkanaście sekund. Dlatego `is_available()` sprawdza tylko **obecność pakietu**, a fizyczny import dzieje się dopiero w `convert()`:
> ```python
> import importlib.metadata
> def is_available(self) -> bool:
>     try:
>         importlib.metadata.version("marker-pdf")  # tylko metadane, bez importu
>         return True
>     except importlib.metadata.PackageNotFoundError:
>         return False
> ```
> Konsekwencja dla packagingu: skoro import jest leniwy, PyInstaller nie wykryje silników automatycznie — trzeba je jawnie dodać do `hiddenimports` w `build.spec` (zob. Etap 10).

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

### LLM jako post-processing — z trybami chunkowania

LLM czyści surowy Markdown po konwersji (usuwa artefakty OCR, naprawia tabele). Dla krótkich dokumentów wystarczy jeden call, ale dla książek 300–800 stron przekroczy to context window modelu. Dlatego interfejs od początku przewiduje tryby chunkowania (`core/config.py` → `llm_mode`):

| Tryb | Działanie | Kiedy |
|---|---|---|
| `none` | Bez LLM | Domyślny |
| `whole_document` | Jeden call na całość | Krótkie PDF-y (< limit kontekstu) |
| `by_page` | Call per strona | Skany, dużo błędów OCR |
| `by_chunk` | Podział na bloki ~N tokenów | Długie dokumenty |
| `by_heading` | Podział wg nagłówków | Książki, raporty ze strukturą |

GUI na start może pokazywać tylko prosty checkbox „Włącz LLM" + wybór trybu, ale `utils/chunking.py` i interfejs `LLMProvider.postprocess()` muszą być gotowe na chunkowanie od pierwszej implementacji — dorobienie tego później oznaczałoby przeróbkę interfejsu.

Wyjątek: Marker ma wbudowany `--use_llm` działający per-strona — tam korzystamy z jego własnej implementacji.

### Konfiguracja — jedno źródło prawdy

Aby CLI i GUI nie rozjechały się z ustawieniami, jest **jeden** model konfiguracji:

- `~/.config/pdf2md/config.toml` — źródło prawdy (silnik domyślny, folder output, język, llm_mode, nazwy modeli, `docling_device`: auto/cpu/cuda)
- klucze API: `config.toml` lub systemowy keyring (docelowo), `.env` dopuszczalny w trybie deweloperskim
- `.env` **tylko jako override deweloperski** — nadpisuje wartości lokalnie, nie jest źródłem prawdy w produkcji

CLI i GUI czytają ten sam `config.toml` przez `core/config.py`. GUI zapisuje zmiany tam, nie do osobnego QSettings.

> **Zapis atomowy.** Skoro `config.toml` zapisuje i CLI (`config set`), i GUI, jednoczesny zapis mógłby uszkodzić plik (race condition). `save_settings()` pisze do pliku tymczasowego i robi `os.replace()` na docelowy — operacja atomowa na poziomie systemu plików, eliminuje uszkodzenie bez dodatkowych zależności. (Cięższy `filelock` nie jest konieczny dla narzędzia jednoosobowego.)

> **Pułapka: zmiana domyślnej wartości w kodzie NIE aktualizuje wstecz już zapisanych configów.** Kosztowała realne polowanie na bug: Marker robił tylko pierwszą stronę 99-stronicowego PDF, bo utrwalony `config.toml` miał `marker_max_pages = 1` (stary default). Poprawka defaultu na `0` zadziałała tylko dla **nowych** configów — istniejący plik (platformdirs: `~/.config/pdf2md/config.toml`) trzymał starą „1", dopóki user ręcznie jej nie zmienił/nie skasował pliku. **To dotyczy KAŻDEGO defaultu** (np. planowanej zmiany `marker_device` na auto/cuda — patrz niżej): zmiana w kodzie pomoże tylko świeżym instalacjom, nie istniejącym userom. Rozwiązania na przyszłość (dotyczy też pozostałych aplikacji z platformdirs — IcoForge, EpubForge):
> - **(a)** wersjonuj config: pole `config_version` w `config.toml` + migracja przy starcie (podbij wersję → przemapuj/usuń przestarzałe klucze, ustaw nowe defaulty), albo
> - **(b)** loader ostrzega o nieznanych/przestarzałych kluczach przy wczytaniu (mniej inwazyjne, ale nie naprawia automatycznie).
> Bez tego każda zmiana sensownego defaultu cicho omija istniejących userów.

> **`marker_device` — CPU to świadomy default, nie bug.** W przeciwieństwie do Suryi (która nie ustawiała device w ogóle — to była usterka, fix w D16), Marker celowo ma `marker_device = "cpu"` (decyzja z Etapu 3 — stabilność pod WSL). Dlatego osobno: GPU dla Markera włączasz `marker_device = "cuda"` (lub `auto`) w `config.toml`. Ewentualna zmiana defaultu na `auto` (cuda gdy dostępna, fallback cpu) to **osobna decyzja** (Rule #1) i osobny PR — przed nią: (1) potwierdź, że powód „stabilność WSL" z Etapu 3 jest już nieaktualny (kilka wielostronicowych konwersji Markera na GPU pod WSL bez OOM/zwiechy), (2) celuj w `"auto"`, nie twarde `"cuda"` (Marker bywa dystrybuowany na maszyny bez karty), (3) pamiętaj o pułapce migracji powyżej — istniejące configy mają `"cpu"` zapisane, więc sama zmiana defaultu ich nie ruszy.


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

### KROK 6b — Limity zasobów WSL2 (KONIECZNE — chroni przed zawieszeniem)
Bez tego ciężkie silniki (Marker, później VLM) potrafią wyczerpać RAM/CPU i zawiesić całą maszynę WSL razem z VS Code. Na Windows utwórz plik `C:\Users\<TwojUser>\.wslconfig`.

**Dla słabego sprzętu (16 GB RAM, np. notebook z GTX 1070):**
```ini
[wsl2]
memory=10GB
swap=16GB
processors=4
```
(Zostawia ~6 GB dla Windows. Swap na dysku ratuje przed twardym OOM, choć spowalnia.)

**Dla mocnego sprzętu (128 GB RAM, RTX 5090):**
```ini
[wsl2]
memory=32GB
swap=16GB
processors=8
```

Po zapisaniu, w PowerShell:
```powershell
wsl --shutdown
```
i otwórz WSL ponownie. Weryfikacja w WSL: `free -h` (RAM zgodny z limitem).

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
