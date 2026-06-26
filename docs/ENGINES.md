# Silniki konwersji PDF -> Markdown

pdf2md rejestruje wszystkie znane silniki, ale traktuje je jako zaleznosci opcjonalne.
`is_available()` nie importuje ciezkich bibliotek ML i ma zwracac `False`, gdy pakiet lub CLI
nie sa zainstalowane.

## PyMuPDF4LLM

**Opis i mocne strony:** szybki ekstraktor tekstu dla natywnych PDF-ow. Dobrze sprawdza sie
w dokumentach, ktore maja warstwe tekstowa i prosty uklad.

**Kiedy uzywac:** pierwszy wybor dla cyfrowych PDF-ow: raporty, instrukcje, dokumentacja,
faktury bez potrzeby OCR.

**Instalacja:**

```bash
uv pip install pymupdf4llm
```

Dla instalacji developerskiej z repozytorium:

```bash
uv sync --extra engines-core
```

**Znane ograniczenia:** nie rozpoznaje skanow bez warstwy tekstowej. Przy bardzo zlozonym
layoucie tabele i kolumny moga wymagac silnika OCR/layout.

---

## Marker

**Opis i mocne strony:** uniwersalny konwerter z OCR, obsluga kolumn, tabel i opcjonalnym
post-processingiem LLM. Ma duze mozliwosci, ale potrafi byc zasobozerny.

**Kiedy uzywac:** skany, dokumenty mieszane, PDF-y z trudniejszym ukladem, gdy jakosc
Markdown jest wazniejsza niz czas konwersji.

**Instalacja:**

```bash
uv pip install marker-pdf
```

Dla instalacji developerskiej z repozytorium:

```bash
uv sync --extra engines-core
```

**Strojenie GPU:** Rozmiary batchy surya (`marker_recognition_batch_size`,
`marker_detector_batch_size`, `marker_layout_batch_size`, `marker_table_rec_batch_size`) mozna
ustawiac w `config.toml`. Domyslnie `0` oznacza auto-doborow surya. Szczegoły w
[CONFIGURATION.md](CONFIGURATION.md#sekcja-marker).

**Znane ograniczenia:** laduje modele ML i domyslnie moze uruchamiac wiele workerow. W pdf2md
adapter wymusza konserwatywne ustawienia workerow i respektuje `TORCH_DEVICE`, ale realne
konwersje nadal warto uruchamiac swiadomie na slabszym sprzecie.

## Docling

**Opis i mocne strony:** enterprise-grade parser dokumentow rozwijany przez IBM Research.
Mocny w tabelach, strukturze dokumentu i zastosowaniach RAG.

**Kiedy uzywac:** raporty, dokumenty biznesowe, techniczne PDF-y z tabelami i sytuacje,
w ktorych wazna jest struktura wyjsciowa.

**Instalacja:**

```bash
uv pip install docling
```

Dla instalacji developerskiej z repozytorium:

```bash
uv sync --extra engines-core
```

**Znane ograniczenia:** import Docling moze ladowac ciezsze zaleznosci, dlatego adapter sprawdza
dostepnosc przez metadata i importuje biblioteke dopiero w `convert()`. Adapter domyslnie
uruchamia Docling na CPU; mozna to nadpisac przez `docling_device`, `DOCLING_DEVICE` albo
`TORCH_DEVICE`.

## MinerU

**Opis i mocne strony:** silnik nastawiony na dokumenty naukowe, wielokolumnowe uklady i CJK.
W pdf2md adapter korzysta z CLI `mineru`.

**Kiedy uzywac:** artykuly naukowe, preprinty, materialy z wieloma wzorami, kolumnami albo
jezykami CJK.

**Instalacja:**

```bash
uv tool install mineru --with mineru[all]
```

MinerU jest instalowany izolowanie, poza srodowiskiem projektu, bo wymaga `pillow>=11`,
a Marker przypina `pillow<11`. Po instalacji sprawdz, czy `mineru` jest widoczne w `PATH`.
Stara komenda `magic-pdf` dotyczy wersji 1.x i nie jest uzywana przez adapter.

**Backend:** konfigurowalne przez `mineru.mineru_backend` w `config.toml`:
- `pipeline` (domyslny) — dziala na GPU przez PyTorch bez vLLM/nvcc; bezpieczny na nowym GPU.
- `vlm` — maksymalna jakosc skanow; wymaga vLLM + flashinfer. Adapter automatycznie ustawia
  `VLLM_USE_FLASHINFER_SAMPLER=0`, zeby ominac JIT-kompilacje nvcc na nowych architekturach.

**Znane ograniczenia:** adapter uruchamia zewnetrzny proces i szuka wygenerowanego pliku `.md`.
Na Windows lokalizacja binarki musi przechodzic przez `shutil.which()`, bo nazwa moze miec
rozszerzenie `.exe`, `.cmd` albo podobne.

## Surya

**Opis i mocne strony:** layout + OCR + reading order (predyktorowy `surya-ocr 0.17.x`), dziala
**in-process** na GPU. Ciagnie go marker-pdf 1.10.x, wiec w srodowisku z Markerem jest od razu
dostepny.

**Kiedy uzywac:** skany i dokumenty, gdzie wazna jest kontrola ukladu i kolejnosci czytania;
kontrola jakosci / fallback obok Markera.

**Instalacja:**

```bash
uv pip install surya-ocr
# albo w ramach repo:
uv sync --extra engines-core
```

Wymaga GPU (CUDA). Na Windows torch musi byc wariantem `+cu130` (zob. INSTALL.md, sekcja Windows).

**Znane ograniczenia:** to predyktorowy `surya-ocr 0.17.x`, **nie** serwowany VLM „Surya 2.0"
(ten jest osobnym, odlozonym pomyslem — zob. FEATURES F19). Wymaga `transformers>=4.56.1`.

## PaddleOCR-VL

**Opis i mocne strony:** wielojezyczny parser dokumentow jako **serwer VLM** (OpenAI-compatible),
serwowany przez vLLM. Dobre wyniki na dokumentach wielojezycznych, w tym polskich.

**Kiedy uzywac:** skany i dokumenty wielojezyczne, gdy zalezy ci na wysokiej jakosci VLM-OCR
i mozesz postawic lokalny serwer.

**Instalacja i uruchomienie:** silnik-usluga — `is_available()` pinguje serwer. Serwer stawiasz
w izolowanym srodowisku (vLLM), `pdf2md` jest jego klientem HTTP:

```bash
VLLM_USE_FLASHINFER_SAMPLER=0 vllm serve PaddlePaddle/PaddleOCR-VL \
  --trust-remote-code --no-enable-prefix-caching
```

Szczegoly (izolowany venv, nightly-vLLM na Blackwell) w INSTALL.md.

**Znane ograniczenia:** wymaga dzialajacego serwera vLLM (GPU); na natywnym Windows nie ruszy
(vLLM tylko Linux/WSL).

## olmOCR — ZAPARKOWANY (adapter gotowy)

**Opis:** olmOCR-2-7B FP8 (`allenai/olmOCR-2-7B-1025-FP8`) — VLM 7B do skanow (czysty Markdown,
rownania, tabele), serwowany przez vLLM.

**Status:** adapter jest **gotowy i poprawny** (uruchamia wlasciwa komende, przekazuje
`--max_model_len 16384 --gpu_memory_utilization 0.90`, obsluguje tryb `--server`), a model
**serwuje** na 24 GB. Mimo to silnik jest **zaparkowany**:

- zajmuje **~cala karte** (model ~9.5 GB + KV ~9.3 GB + grafy ≈ 24 GB) → **nie wspolistnieje
  z modelem korekty LLM** w pipelinie;
- **start serwera 90–150 s** na wywolanie (ladowanie + kompilacja + capture grafow CUDA);
- jest **anglocentryczny** — dla dokumentow PL Paddle/Surya daja lepsze wyniki i juz dzialaja;
- w trybie spawn-per-plik serwer-dziecko olmocr nie wstaje pod nightly-vLLM/transformers 5.x.

**Kiedy rozwazyc:** wylacznie tryb **external-server** (`--server` / pole `olmocr_server_url`) —
wlasny, raz wystartowany serwer, gdybys potrzebowal olmOCR „na zadanie". Dla typowego uzycia:
Surya lub PaddleOCR-VL.

**Instalacja (gdy naprawde potrzebny):** izolowany venv + nightly-vLLM — zob. INSTALL.md.

## pdf-craft — WYKLUCZONY (trwale)

pdf-craft jest **trwale wykluczony** z powodu nieusuwalnego konfliktu zaleznosci: wymaga
`transformers<4.48` (symbol `LlamaFlashAttention2`, usuniety w 4.48), a Marker 1.10.x ciagnie
`surya-ocr 0.17.1` wymagajaca `transformers>=4.56.1` — wspolnej wersji nie ma (przepasc wieksza
niz samo `>=4.48`). Feralny import siedzi w zdalnym kodzie modelu DeepSeek-OCR (`trust_remote_code`),
nie w samym pdf-craft, wiec forka sie nie oplaca.

Faza 2 **nie** przywrocila pdf-craft — jego scenariusz (skanowane ksiazki) pokrywaja Marker,
MinerU (backend `vlm`), PaddleOCR-VL i Surya. Gdyby kiedys byl konieczny, jedyna droga to izolacja
jak MinerU (subprocess + wlasne srodowisko z `transformers<4.48`).

Nie instaluj `pdf-craft` w srodowisku z `marker-pdf` lub `docling` — wymusi downgrade
`transformers` i crash tych silnikow.
