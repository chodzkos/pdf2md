# CLI — komendy i funkcje

Te same konwersje co w GUI wykonasz z linii poleceń. Wszystkie komendy:

| Komenda | Co robi |
| --- | --- |
| `pdf2md convert` | Konwersja PDF/obrazów do Markdown lub EPUB (jeden plik lub batch) |
| `pdf2md scan` | Składanie skanowanej książki wg profilu (Scan Pipeline) → Markdown/EPUB |
| `pdf2md compare` | Konwersja jednego pliku wszystkimi dostępnymi silnikami + tabela metryk |
| `pdf2md forms` | Ekstrakcja pól formularza PDF → JSON / CSV / tabela Markdown |
| `pdf2md history` | Historia konwersji (filtr po silniku, eksport CSV, czyszczenie) |
| `pdf2md list-engines` | Katalog silników: status, OCR, wymóg GPU |
| `pdf2md list-llm` | Status dostawców LLM i modele domyślne |
| `pdf2md list-profiles` | Profile/presety (wbudowane + użytkownika) |
| `pdf2md doctor` | Diagnostyka środowiska (GPU/CUDA, Ollama, narzędzia, klucze API) |
| `pdf2md config` | `show` / `set` / `edit` — zarządzanie `config.toml` |

## convert — konwersja

```
pdf2md convert dokument.pdf --engine pymupdf4llm
pdf2md convert "pdfy/*.pdf" --engine docling --output-dir ./markdown
pdf2md convert dokument.pdf --engine marker --llm ollama --llm-mode by_heading
pdf2md convert dokument.pdf --dry-run        # plan bez konwersji
```

Najważniejsze flagi:

- `--engine` / `-e` — silnik (bez opcji: `conversion.default_engine`).
- `--output` / `-o`, `--output-dir` — plik `.md`/`.epub` albo katalog batcha.
- `--llm`, `--llm-model`, `--llm-mode` — post-processing LLM (patrz zakładka LLM).
- `--lang` — język OCR (domyślnie `pol+eng`).
- `--profile` / `-p` — **preset konwersji** (YAML): nazwany zestaw silnik/język/LLM.
- `--epub-backend` — backend EPUB `pandoc` | `native` | `calibre` (patrz „Profile skanowania”).
- `--extract-images` — wyciąga obrazy z PDF do `<output>_images/` i wstawia referencje `![]()`
  w Markdownie; `--image-min-size` filtruje drobne ikony (domyślnie 100 px).
- `--password` — hasło do **zaszyfrowanego PDF**; bez hasła zaszyfrowany plik kończy się
  czytelnym błędem z podpowiedzią.
- `--dry-run`, `--verbose`.

**Wejścia obrazkowe:** `convert` przyjmuje też zdjęcia dokumentów (JPG/PNG/TIFF, w tym
wielostronicowy TIFF) — trafiają tą samą ścieżką OCR co skany PDF (wymaga silnika OCR).

**Ekstrakcja obrazów:** silniki layoutowe (Marker, Docling) osadzają obrazy **in-place**
automatycznie; dla pozostałych użyj `--extract-images`.

## scan — skanowana książka

```
pdf2md scan skan.pdf --profile premium       # pipeline skanu książki → Markdown/EPUB
```

`--keep-work` zachowuje katalog roboczy `work/` (debug). Profile: patrz „Profile skanowania”.

## compare — porównywarka silników

```
pdf2md compare dokument.pdf --output-dir ./porownanie
```

Konwertuje plik wszystkimi dostępnymi silnikami, zapisuje wynik per silnik
(`<plik>_<silnik>.md`) i wypisuje tabelę metryk (czas, długość tekstu, liczba nagłówków, liczba
tabel). Niedostępne silniki są pomijane z adnotacją; błąd jednego nie przerywa reszty.
Opcjonalna ocena jakości przez LLM: `--llm-score` (domyślnie wyłączona).

## forms — pola formularza PDF

```
pdf2md forms formularz.pdf --format json --output pola.json
```

Wyciąga pola formularza (nazwa + wartość + typ) do `md` (domyślnie) / `json` / `csv`; bez
`--output` wynik idzie na stdout. Obsługuje formularze wielostronicowe; PDF bez pól → komunikat.

## history — historia konwersji

```
pdf2md history                       # ostatnie wpisy
pdf2md history --engine marker       # filtr po silniku
pdf2md history --csv historia.csv    # eksport do CSV
pdf2md history --clear               # wyczyść (z potwierdzeniem)
```

Każda konwersja (sukces i błąd) trafia do lokalnej bazy SQLite obok configu.

## Diagnostyka i konfiguracja

```
pdf2md list-engines          # silniki + wymóg GPU
pdf2md list-llm              # dostawcy LLM
pdf2md list-profiles         # profile skanowania i presety
pdf2md doctor                # diagnostyka środowiska

pdf2md config show                  # pokaż konfigurację
pdf2md config set KLUCZ WARTOŚĆ     # ustaw wartość (np. epub_backend calibre)
pdf2md config edit                  # otwórz config.toml w edytorze
```

## W GUI

To samo z poziomu okna:

- **Silnik / LLM / profil** — selektory nad przyciskiem KONWERTUJ.
- **Ekstrahuj obrazy z PDF** — checkbox per-sesja (wyszarzony dla Marker/Docling, które robią
  to in-place).
- **Folder wyjściowy** — pole ze ścieżką (puste = obok pliku źródłowego).
- **Zaszyfrowany PDF** — przy starcie konwersji pojawia się dialog hasła (maskowane echo,
  ponawianie przy złym haśle).
- **Anuluj** — przerywa konwersję na najbliższej granicy strony/pliku (ukończone pliki zostają).
- **Eksport do EPUB** — po konwersji okno podsumowania oferuje eksport wyniku do EPUB (backend
  wg profilu / configu: pandoc | native | calibre).
- **Ustawienia** (⚙) — klucze API, ustawienia domyślne, Ollama (przycisk „Wykryj modele”).
