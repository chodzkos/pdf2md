# Profile skanowania (Scan Pipeline)

Profil to jeden plik YAML opisujący cały przebieg premium scan pipeline: DPI renderowania,
preprocessing obrazu, silnik(i) VLM-OCR, korektę LLM, post-processing składania i format
wyjścia. Wybierasz profil zamiast ręcznie ustawiać kilkanaście flag.

```bash
pdf2md list-profiles
pdf2md scan ksiazka.pdf --profile balanced -o output/
```

## Profile wbudowane

| Profil | DPI | OCR | Korekta LLM | Postprocess | Wyjście | Kiedy używać |
|---|---|---|---|---|---|---|
| **fast** | 300 | paddleocr | qwen3:14b (per strona) | — | MD + EPUB | Czyste, współczesne druki; szybki zrzut do edycji. Minimalny preprocessing (sam deskew). |
| **balanced** | 400 | paddleocr-vl | qwen3:14b (per strona) | nagłówki/stopki, akapity, dzielenie wyrazów | MD + EPUB + raport | Domyślny wybór dla większości skanów książek. Dobry kompromis jakość/czas. |
| **premium** | 400 | olmocr (+ surya kontrolnie) | qwen3:14b (konserwatywnie, page→chapter) | + przypisy, detekcja TOC | MD + EPUB + raport HTML | Trudne/stare skany, gdy liczy się maksymalna wierność. Wolny: dwa silniki + walidacja + rerun trudnych stron. |

> Silniki VLM-OCR wymagają GPU. Jeśli silnik z profilu jest niedostępny (np. serwer PaddleOCR-VL
> nie działa), pipeline robi fallback na Surya i kontynuuje. Korekta LLM jest pomijana, gdy żaden
> dostawca LLM nie jest dostępny (wynik = surowy OCR).

## Sekwencja VRAM
Pipeline ładuje model VLM, OCR-uje WSZYSTKIE strony, **zwalnia VRAM** (`unload_model()`), a dopiero
potem uruchamia korektę LLM (po niej `keep_alive=0` zwalnia model korekty). Dwa duże modele nigdy
nie są w pamięci jednocześnie — kluczowe na 24 GB VRAM.

## Struktura profilu (YAML)

```yaml
name: balanced
dpi: 400
preprocess: {deskew: true, denoise: true, dewarp: auto, crop: auto}
layout: {engine: surya}                  # opcjonalne
ocr: {engine: paddleocr-vl, gpu: true}   # albo: {primary: olmocr, secondary: surya, compare_outputs: true}
llm_cleanup: {enabled: true, provider: ollama, model: qwen3:14b, chunk: page, mode: conservative}
postprocess: {remove_headers_footers: true, merge_paragraphs: true, fix_hyphenation: true,
              footnotes: true, toc_detection: true}
validation: {detect_low_confidence_pages: true, rerun_bad_pages: true}
output: {markdown: true, epub: true, quality_report: true, html_report: true}
```

Nieznane klucze są odrzucane przy walidacji (literówka w YAML → czytelny błąd, nie ciche zignorowanie).

## Własny profil

1. Skopiuj wbudowany profil jako bazę i zmień, co trzeba:
   ```bash
   pdf2md list-profiles        # zobacz dostępne
   ```
2. Utwórz `~/.config/pdf2md/profiles/moj.yaml` (ta sama struktura co wyżej). Pojawi się
   automatycznie na liście i użyjesz go: `pdf2md scan ksiazka.pdf --profile moj`.
3. Z GUI: wybierz silnik **Scan Pipeline (premium)**, kliknij **Edytuj profil**, ustaw DPI/wyjście
   i zapisz pod własną nazwą (trafi do `~/.config/pdf2md/profiles/`).

Profile użytkownika mają pierwszeństwo nad wbudowanymi o tej samej nazwie.
