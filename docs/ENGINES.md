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
uv sync --extra engines-core
```

albo:

```bash
uv add pymupdf4llm
```

**Znane ograniczenia:** nie rozpoznaje skanow bez warstwy tekstowej. Przy bardzo zlozonym
layoucie tabele i kolumny moga wymagac silnika OCR/layout.

## Marker

**Opis i mocne strony:** uniwersalny konwerter z OCR, obsluga kolumn, tabel i opcjonalnym
post-processingiem LLM. Ma duze mozliwosci, ale potrafi byc zasobozerny.

**Kiedy uzywac:** skany, dokumenty mieszane, PDF-y z trudniejszym ukladem, gdy jakosc
Markdown jest wazniejsza niz czas konwersji.

**Instalacja:**

```bash
uv sync --extra engines-core
```

albo:

```bash
uv add marker-pdf
```

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
uv sync --extra engines-core
```

albo:

```bash
uv add docling
```

**Znane ograniczenia:** import Docling moze ladowac ciezsze zaleznosci, dlatego adapter sprawdza
dostepnosc przez metadata i importuje biblioteke dopiero w `convert()`. Adapter domyslnie
uruchamia Docling na CPU; mozna to nadpisac przez `docling_device`, `DOCLING_DEVICE` albo
`TORCH_DEVICE`.

## MinerU

**Opis i mocne strony:** silnik nastawiony na dokumenty naukowe, wielokolumnowe uklady i CJK.
W pdf2md adapter korzysta z CLI `magic-pdf`.

**Kiedy uzywac:** artykuly naukowe, preprinty, materialy z wieloma wzorami, kolumnami albo
jezykami CJK.

**Instalacja:**

```bash
uv sync --extra engines-optional
```

albo:

```bash
uv add mineru
```

Po instalacji sprawdz, czy `magic-pdf` jest widoczne w `PATH`.

**Znane ograniczenia:** adapter uruchamia zewnetrzny proces i szuka wygenerowanego pliku `.md`.
Na Windows lokalizacja binarki musi przechodzic przez `shutil.which()`, bo nazwa moze miec
rozszerzenie `.exe`, `.cmd` albo podobne.

## pdf-craft

**Opis i mocne strony:** silnik wyspecjalizowany w skanowanych ksiazkach. Aktualne API PyPI
udostepnia `transform_markdown()` oraz natywny eksport EPUB przez `transform_epub()`.

**Kiedy uzywac:** skanowane ksiazki, dlugie publikacje z okladka, przypisami, ilustracjami,
tabelami albo wzorami.

**Instalacja:**

```bash
uv sync --extra engines-optional
```

albo:

```bash
uv add pdf-craft
```

Wymagany jest Poppler dostepny w systemie.

**Znane ograniczenia:** konwersja OCR moze wymagac srodowiska CUDA i pobrania modeli. Adapter
sprawdza instalacje przez metadata, a biblioteke importuje dopiero przy realnej konwersji.
