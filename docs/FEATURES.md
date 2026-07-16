# pdf2md Squeezer — Funkcje Przyszłości (Post v1.0)

> Pomysły na rozbudowę po ukończeniu podstawowej wersji.
> Każda sekcja zawiera: opis, trudność implementacji i szacowany czas.

---

## Priorytet 1 — Naturalne rozszerzenia v1.0

### F01 — Konwersja do EPUB (natywna, bez Pandoc)

> **STATUS: ✅ ZREALIZOWANE (lipiec 2026, PR #94).** Natywny backend EPUB przez `ebooklib` —
> izolowany builder w `src/pdf2md/exporters/epub/` (typy `EpubMetadata`/`EpubChapter`/`EpubInput`,
> `build_epub()` + `from_markdown()`) oraz `NativeEpubExporter`. Builder nie importuje niczego z
> `pdf2md` (tylko `ebooklib` + parser Markdown + stdlib), pod przyszłe wyjęcie do EpubForge. Składa
> TOC z nagłówków, osadza obrazy, CSS, metadane i opcjonalną okładkę. Wybór backendu
> `pandoc|native|calibre` przez `[conversion].epub_backend` lub `convert --epub-backend`. Odblokował
> też 2 testy pomijane wcześniej na brak `ebooklib`.

**Opis:** Zamiast wywoływać Pandoc jako subprocess, własna implementacja EPUB buildery z `ebooklib`. Pozwoli na lepszą kontrolę nad formatowaniem, TOC, metadanymi i stylami CSS.

**Funkcje:**
- automatyczny spis treści z nagłówków Markdown
- zachowanie obrazów osadzonych w PDF
- customizowalne CSS (czcionka, marginesy, interlinia)
- metadata (autor, tytuł, język, data)
- opcjonalna okładka (pierwsza strona PDF jako obraz)

**Trudność:** ⭐⭐⭐☆☆ Średnia  
**Czas:** ~5 dni  
**Zależności:** `ebooklib`, `Pillow`  
**Gdzie:** nowy moduł `src/pdf2md/exporters/epub_exporter.py`

---

### F02 — Własny silnik ekstrakcji (bez zewnętrznych narzędzi)
> ⚠️ **Częściowo zrealizowane w Fazie 2 roadmapy.** Premium scan pipeline (etapy 11–15) pokrywa OCR skanów przez VLM, preprocessing, korektę LLM i walidację. Poniższy opis dotyczy pozostałej części — własnego silnika do **natywnych** PDF-ów (bez skanów).

**Opis:** Własna implementacja pipeline'u ekstrakcji dla natywnych PDF-ów zamiast polegania na PyMuPDF4LLM/Marker/Docling. Daje pełną kontrolę i brak zależności.

**Komponenty do implementacji (część nieobjęta Fazą 2):**
- **Detektor typu PDF** — tekst vs skan vs mieszany (per strona)
- **Ekstraktor tekstu** — pdfplumber + pdfminer.six, wykrywanie nagłówków (rozmiar fontu), list, akapitów
- **Detektor kolumn** — KMeans na pozycjach X słów, prawidłowa kolejność czytania
- **Ekstraktor tabel** — camelot (lattice + stream), konwersja do MD table

(Komponenty OCR/preprocessing/korekta/walidacja → już w Fazie 2 roadmapy)

**Trudność:** ⭐⭐⭐⭐☆ Wysoka (po odjęciu części z Fazy 2)
**Czas:** ~2 tygodnie
**Zależności:** `pdfplumber`, `pdfminer.six`, `camelot-py`

---

### F03 — Batch processing z harmonogramem
**Opis:** Możliwość zaplanowania konwersji na noc, watchdog dla folderów (automatyczna konwersja nowych PDF-ów).

**Funkcje:**
- `pdf2md watch /folder/` — konwertuj każdy nowy PDF automatycznie
- integracja z cron/Task Scheduler
- powiadomienia systemowe po skończeniu

**Trudność:** ⭐⭐☆☆☆ Łatwa  
**Czas:** ~2 dni  
**Zależności:** `watchdog`

---

### F04 — Historia konwersji
**Opis:** Lokalna baza danych z historią wszystkich konwersji — kiedy, co, jakim silnikiem, wyniki.

**Funkcje:**
- SQLite jako backend
- filtrowanie i wyszukiwanie
- ponowne uruchomienie poprzedniej konwersji
- statystyki (najczęstszy silnik, czas konwersji)
- eksport historii do CSV

**Trudność:** ⭐⭐☆☆☆ Łatwa  
**Czas:** ~2 dni  
**Zależności:** SQLite (wbudowane w Python)

---

## Priorytet 2 — Zaawansowane funkcje

### F05 — Web UI (alternatywa dla desktop GUI)
**Opis:** Interfejs webowy obok desktop GUI — dostępny przez przeglądarkę, przydatny do użytku na serwerze lub przez sieć lokalną.

**Stack:** FastAPI (backend) + React lub HTMX (frontend)

**Funkcje:**
- upload PDF przez przeglądarkę
- wybór silnika i opcji
- pobieranie wynikowego Markdown/EPUB
- opcjonalne API REST dla integracji

**Trudność:** ⭐⭐⭐☆☆ Średnia  
**Czas:** ~1 tydzień  
**Zależności:** `fastapi`, `uvicorn`, `python-multipart`

---

### F06 — Plugin/extensibility system
**Opis:** System wtyczek pozwalający dodawać nowe silniki bez modyfikacji kodu głównego.

**Jak działa:**
- silniki jako zewnętrzne pakiety Pythona z entry pointem `pdf2md.engines`
- `pyproject.toml` pluginu: `[project.entry-points."pdf2md.engines"]`
- auto-odkrywanie przez `importlib.metadata.entry_points()`

**Trudność:** ⭐⭐⭐☆☆ Średnia  
**Czas:** ~3 dni  
**Wartość:** Społeczność może dodawać własne silniki bez forka projektu

---

### F07 — Porównywarka silników
**Opis:** Funkcja "compare mode" — konwertuj ten sam PDF wszystkimi dostępnymi silnikami i pokaż wyniki side by side.

**GUI:** podzielony panel z zakładkami (jedna zakładka = jeden silnik)  
**CLI:** `pdf2md compare plik.pdf --output-dir wyniki/` — tworzy `plik_pymupdf4llm.md`, `plik_marker.md` itd.

**Metryki do porównania:**
- czas konwersji
- długość tekstu (w znakach)
- liczba wykrytych nagłówków
- liczba tabel
- (opcjonalnie) ocena jakości przez LLM

**Trudność:** ⭐⭐☆☆☆ Łatwa  
**Czas:** ~2 dni

---

### F08 — Profil konwersji (presets)
**Opis:** Zapisywanie i ładowanie zestawów ustawień jako "profile".

**Przykłady presetów:**
- `artykuł-naukowy` → MinerU, lang: eng, bez LLM
- `skan-pl` → Marker + OCR, lang: pol, Claude post-processing
- `szybki-podgląd` → PyMuPDF4LLM, bez LLM

**Trudność:** ⭐☆☆☆☆ Bardzo łatwa  
**Czas:** ~1 dzień  
**Format:** TOML

---

### F09 — Integracja z Calibre
**Opis:** Wywołanie Calibre (jeśli zainstalowane) jako dodatkowy backend do konwersji i edycji ebooków.

**Funkcje:**
- konwersja PDF → EPUB przez Calibre (wysoka jakość)
- otwieranie wynikowego EPUB w Calibre
- metadane przez Calibre API

**Trudność:** ⭐⭐☆☆☆ Łatwa  
**Czas:** ~1 dzień  
**Zależności:** Calibre zainstalowane lokalnie

---

## Priorytet 3 — Specjalistyczne funkcje

### F10 — Obsługa formularzy PDF
**Opis:** Ekstrakcja pól formularzy PDF do struktury danych (JSON, CSV, MD table).

**Funkcje:**
- wykrywanie pól formularzy (pypdf)
- ekstrakcja nazw i wartości
- eksport do JSON / CSV / tabeli MD
- obsługa formularzy wielostronicowych

**Trudność:** ⭐⭐⭐☆☆ Średnia  
**Czas:** ~3 dni  
**Zależności:** `pypdf`

---

### F11 — Ekstrakcja obrazów
**Opis:** Opcja wyciągania wszystkich obrazów z PDF i zapisywania ich obok pliku MD (z referencjami w Markdownzie).

**Funkcje:**
- `![Rysunek 1](images/page1_img1.png)` zamiast pomijania obrazów
- opcja opisu obrazów przez LLM vision (Claude, GPT-4V)
- filter rozmiaru (pomijaj małe ikony/dekoracje)

**Trudność:** ⭐⭐⭐☆☆ Średnia  
**Czas:** ~3 dni  
**Zależności:** `pymupdf`, `Pillow`

---

### F12 — Obsługa zaszyfrowanych PDF
**Opis:** Konwersja zaszyfrowanych PDF po podaniu hasła.

**Funkcje:**
- dialog hasła w GUI
- flaga `--password` w CLI
- obsługa różnych metod szyfrowania

**Trudność:** ⭐⭐☆☆☆ Łatwa  
**Czas:** ~1 dzień  
**Zależności:** `pypdf` (już obsługuje hasła)

---

### F13 — Tłumaczenie dokumentów
**Opis:** Opcjonalne tłumaczenie wynikowego Markdown przez LLM lub dedykowane API.

**Funkcje:**
- tłumaczenie przez Claude/GPT (przez istniejących providerów)
- tłumaczenie przez LibreTranslate (lokalnie, OpenSource)
- tłumaczenie przez DeepL API
- zachowanie formatowania Markdown podczas tłumaczenia
- obsługa dokumentów wielojęzycznych

**Trudność:** ⭐⭐⭐☆☆ Średnia  
**Czas:** ~4 dni  
**Zależności:** istniejące LLM providers + opcjonalnie `libretranslate`

---

### F14 — RAG-ready chunks
**Opis:** Tryb eksportu dla AI/RAG pipeline — zamiast jednego pliku .md, podziel dokument na semantyczne fragmenty (chunks) z metadanymi.

**Output format:**
```json
{
  "chunks": [
    {
      "id": "chunk_001",
      "page": 1,
      "content": "...",
      "type": "paragraph|heading|table",
      "metadata": {"source": "plik.pdf", "section": "Wprowadzenie"}
    }
  ]
}
```

**Trudność:** ⭐⭐☆☆☆ Łatwa  
**Czas:** ~2 dni  
**Użytkownicy docelowi:** deweloperzy AI, data scientists

---

### F15 — Obsługa OCR dla zdjęć (nie tylko PDF)
**Opis:** Rozszerzenie aplikacji o konwersję zdjęć dokumentów (JPG, PNG, TIFF) do Markdown.

**Funkcje:**
- drag & drop zdjęć obok PDF-ów
- auto-detekcja typu pliku
- preprocessing identyczny jak dla skanów PDF
- wsparcie dla zdjęć wielostronicowych (TIFF)

**Trudność:** ⭐⭐☆☆☆ Łatwa  
**Czas:** ~2 dni  
**Zależności:** `Pillow`, istniejący OCR stack

---

## Infrastruktura i DevOps

### F16 — Telemetria (opt-in)
**Opis:** Opcjonalna, anonimowa telemetria — które silniki są najczęściej używane, typowe błędy — do poprawy produktu.

**Ważne:** Domyślnie wyłączona, wyraźna zgoda użytkownika, zero PII, lokalny opt-out.

**Trudność:** ⭐⭐⭐☆☆ Średnia  
**Czas:** ~3 dni

---

### F17 — Auto-update
**Opis:** Sprawdzanie dostępności nowej wersji i automatyczna aktualizacja (lub powiadomienie).

**Mechanizm:** GitHub Releases API → porównanie wersji → pobieranie binary

**Trudność:** ⭐⭐⭐☆☆ Średnia  
**Czas:** ~2 dni

---

### F18 — Docker image
**Opis:** Oficjalny obraz Docker dla CLI (bez GUI) — idealne do deploymentu serwerowego.

```dockerfile
FROM python:3.11-slim
RUN apt-get install -y tesseract-ocr poppler-utils
RUN pip install pdf2md[marker,docling]
ENTRYPOINT ["pdf2md"]
```

**Trudność:** ⭐⭐☆☆☆ Łatwa  
**Czas:** ~1 dzień  
**Publikacja:** GitHub Container Registry (ghcr.io)

### F19 — Surya 2.0 jako izolowany silnik VLM-OCR
**Opis:** Surya 2.0 (`datalab-to/surya`, v0.20+) to przebudowa w pojedynczy VLM ~650M (OCR + layout
+ tabele), serwowany przez vllm (GPU) lub llama.cpp (CPU / Apple Silicon), SOTA w klasie <3B
(~83% olmOCR-bench). Wpięcie jako **silnik-usługa** (klient HTTP, jak PaddleOCR-VL — `is_available()`
pinguje serwer) w **izolowanym venv**. To **inny byt** niż predyktorowa `surya-ocr 0.17.x`, która
**już działa in-process** w głównym venv (ciągnie ją marker-pdf 1.10.x — silnik `surya` jest
gotowy i przetestowany). F19 dotyczy **wyłącznie** wariantu serwowanego VLM 2.0.

**Dlaczego odłożone:** potrzebę „Surya działa" pokrywa już silnik in-process (0.17.x). Surya 2.0 jako
usługa na NVIDIA dubluje PaddleOCR-VL/MinerU, które też działają. Realna przewaga 2.0 to tryb
**llama.cpp (CPU / Apple Silicon)** — jedyny VLM-OCR bez karty NVIDIA — oraz ewentualnie lepsza
jakość tabel. Wdrożyć, gdy pojawi się potrzeba (np. wsparcie nie-NVIDIA).

**Trudność:** ⭐⭐⭐ (izolacja + serwowanie vllm/llama.cpp + adapter HTTP)  
**Czas:** ~2-3 dni  
**Zależność:** wzorzec adaptera-usługi z PaddleOCR-VL (PROMPT D9)

---

## Matryca priorytetów

| ID | Funkcja | Trudność | Czas | Wartość | Priorytet |
|---|---|---|---|---|---|
| F01 | EPUB native | ⭐⭐⭐ | 5d | Wysoka | ✅ Zrobione (PR #94) |
| F02 | Własny silnik | ⭐⭐⭐⭐⭐ | 4tyg | Wysoka | 🟡 Średni |
| F03 | Batch/watchdog | ⭐⭐ | 2d | Średnia | 🔴 Wysoki |
| F04 | Historia | ⭐⭐ | 2d | Średnia | 🔴 Wysoki |
| F05 | Web UI | ⭐⭐⭐ | 1tyg | Wysoka | 🟡 Średni |
| F06 | Plugin system | ⭐⭐⭐ | 3d | Wysoka | 🟡 Średni |
| F07 | Porównywarka | ⭐⭐ | 2d | Średnia | 🔴 Wysoki |
| F08 | Presety | ⭐ | 1d | Średnia | 🔴 Wysoki |
| F09 | Calibre | ⭐⭐ | 1d | Niska | 🟢 Niski |
| F10 | Formularze | ⭐⭐⭐ | 3d | Niska | 🟢 Niski |
| F11 | Ekstrakcja obrazów | ⭐⭐⭐ | 3d | Wysoka | 🟡 Średni |
| F12 | Hasła PDF | ⭐⭐ | 1d | Średnia | 🔴 Wysoki |
| F13 | Tłumaczenie | ⭐⭐⭐ | 4d | Wysoka | 🟡 Średni |
| F14 | RAG chunks | ⭐⭐ | 2d | Wysoka | 🟡 Średni |
| F15 | Zdjęcia → MD | ⭐⭐ | 2d | Wysoka | 🔴 Wysoki |
| F16 | Telemetria | ⭐⭐⭐ | 3d | Niska | 🟢 Niski |
| F17 | Auto-update | ⭐⭐⭐ | 2d | Średnia | 🟢 Niski |
| F18 | Docker | ⭐⭐ | 1d | Wysoka | 🔴 Wysoki |
| F19 | Surya 2.0 (izolowany VLM) | ⭐⭐⭐ | 2-3d | Średnia | 🟢 Niski |

---

## Rekomendowana kolejność po v1.0

**v1.1 — "Quick wins"** (~1-2 tygodnie)
- F08 Presety (1d)
- F12 Hasła PDF (1d)
- F03 Watchdog (2d)
- F04 Historia (2d)
- F07 Porównywarka (2d)

**v1.2 — "Power features"** (~2-3 tygodnie)
- F15 Zdjęcia → MD (2d)
- F11 Ekstrakcja obrazów (3d)
- ✅ F01 EPUB native (PR #94)
- F18 Docker (1d)

**v2.0 — "Platform"** (~1-2 miesiące)
- F02 Własny silnik ekstrakcji
- F05 Web UI
- F06 Plugin system
- F13 Tłumaczenie
- F14 RAG chunks
