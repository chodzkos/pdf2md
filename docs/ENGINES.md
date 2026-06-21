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

## pdf-craft — WYKLUCZONY z v1.0

pdf-craft zostal wykluczony z v1.0 ze wzgledu na nieusuwalny konflikt zaleznosci:
wymaga `transformers<4.48`, a Marker i Docling wymagaja `transformers>=4.48` (symbol
`ALL_ATTENTION_FUNCTIONS` dodany w 4.48). Oba nie moga wspolistniec w jednym srodowisku.
Dodatkowo jego scenariusz uzycia (skanowane ksiazki) jest pokryty przez MinerU (backend `vlm`).

Silnik moze zostac przywrocony w Fazie 2 jako izolowane narzedzie CLI (analogicznie do MinerU),
jesli okaże sie potrzebny.

Nie instaluj `pdf-craft` w srodowisku z `marker-pdf` lub `docling` — spowoduje downgrade
`transformers` i crash tych silnikow.
