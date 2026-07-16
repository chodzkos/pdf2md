# Profile skanowania

Profile sterują skanowaniem książek (silnik **Scan Pipeline**): DPI, korekta LLM, wyjścia.
Wbudowane: **fast** / **balanced** / **premium** (domyślny **balanced**).

| Profil | Co robi / kiedy |
| --- | --- |
| fast | Niższy DPI, lekki tryb — szybki podgląd, gdy jakość mniej istotna |
| balanced | Kompromis jakość/czas — domyślny, dobry do większości skanów |
| premium | Najwyższy DPI + pełny tryb (VLM-OCR, korekta LLM, raport) — książki, materiał docelowy |

Własny profil zapiszesz przez **Edytuj profil** (DPI, wyjścia EPUB / raport jakości, backend
EPUB); trafia do `~/.config/pdf2md/profiles/`. Użycie z CLI: `pdf2md scan skan.pdf --profile premium`.

## Profile skanu a presety konwersji — to dwie różne rzeczy

- **Profile skanowania** (tu) dotyczą silnika **Scan Pipeline** (książki, `pdf2md scan`).
- **Presety konwersji** to nazwane zestawy ustawień zwykłej konwersji (silnik / język / LLM)
  dla `pdf2md convert --profile <nazwa>` (YAML). Pozwalają zapisać np. „artykuł-naukowy” albo
  „skan-pl” i wołać jedną flagą zamiast wielu opcji.

## Backendy eksportu EPUB

Eksport do EPUB (w Scan Pipeline i przy eksporcie po konwersji) ma trzy wymienne backendy:

| Backend | Czym jest | Uwagi |
| --- | --- | --- |
| `pandoc` | Konwersja przez Pandoc | domyślny; wymaga Pandoca w PATH |
| `native` | Wbudowany builder `ebooklib` | bez Pandoca; TOC, obrazy, CSS, metadane, okładka |
| `calibre` | Konwersja przez `ebook-convert` | wymaga Calibre; gdy niedostępny — fallback na Pandoc |

Backend wybierzesz w **Edytuj profil** (GUI), kluczem `[conversion].epub_backend` w configu albo
flagą `pdf2md convert --epub-backend`. Dostępność Pandoca/Calibre pokazuje `pdf2md doctor`.
