# Konfiguracja pdf2md

Źródłem prawdy jest plik `~/.config/pdf2md/config.toml`. Plik tworzony jest automatycznie przy pierwszym uruchomieniu z wartościami domyślnymi. Plik `.env` w katalogu roboczym jest override **deweloperskim** i jest ładowany **tylko w trybie dev** — gdy ustawisz zmienną `PDF2MD_DEV=1`. Produkcyjnie `.env` jest **ignorowany** (żeby cudzy `.env` w katalogu uruchomienia nie nadpisał po cichu ustawień, np. kluczy API czy providera LLM). Fakt załadowania lub pominięcia `.env` jest logowany na poziomie INFO wraz z pełną ścieżką.

Edytuj konfigurację przez CLI:

```bash
pdf2md config show
pdf2md config set conversion.default_engine docling
pdf2md config edit
```

lub bezpośrednio w edytorze — plik to zwykły TOML.

### Typy wartości i walidacja

`config set` rzutuje wartość na typ pola z modelu ustawień, więc podajesz zwykły tekst:

- **bool** (np. `llm.enabled`): `true/false`, `1/0`, `yes/no`, `tak/nie`, `on/off`;
- **int** (np. `marker.marker_workers`, `olmocr_max_model_len`): liczba całkowita;
- **float** (np. `olmocr_gpu_memory_utilization`, `paddleocr_vl_timeout`): liczba zmiennoprzecinkowa, np. `0.85`;
- **string** (reszta): wartość dosłowna.

Błędne wejście kończy się czytelnym komunikatem, a **plik configu pozostaje nietknięty** —
np. `config set olmocr_gpu_memory_utilization abc` → „musi być liczbą zmiennoprzecinkową",
a wartość spoza dozwolonego zbioru (walidatory pól) → „Nieprawidłowa wartość dla `<pole>`: …"
(np. `config set theme purple` wypisze dozwolone `auto, light albo dark`).

---

## Pełny plik domyślny

```toml
[llm]
enabled = false
provider = "none"
mode = "none"
anthropic_model = ""
openai_model = ""
gemini_model = ""
ollama_model = "qwen2.5:14b"
ollama_url = "http://localhost:11434"

[conversion]
default_engine = "pymupdf4llm"
default_output_dir = ""
default_language = "pol+eng"
epub_backend = "pandoc"

[marker]
marker_device = "cpu"
marker_workers = 1
marker_max_pages = 1
marker_torch_device = ""
marker_recognition_batch_size = 0
marker_detector_batch_size = 0
marker_layout_batch_size = 0
marker_table_rec_batch_size = 0

[docling]
docling_device = "auto"

[mineru]
mineru_backend = "pipeline"

[api_keys]
anthropic_api_key = ""
openai_api_key = ""
gemini_api_key = ""
```

---

## Sekcja `[llm]`

| Klucz | Typ | Domyślnie | Opis |
|---|---|---|---|
| `enabled` | bool | `false` | Włącza post-processing LLM. |
| `provider` | str | `"none"` | Dostawca: `none`, `ollama`, `claude`, `openai`, `gemini`. |
| `mode` | str | `"none"` | Tryb chunkowania: `none`, `whole_document`, `by_page`, `by_chunk`, `by_heading`. |
| `anthropic_model` | str | `""` | Model Claude, np. `claude-sonnet-4-6`. Puste = fallback providera. |
| `openai_model` | str | `""` | Model OpenAI, np. `gpt-4.1-mini`. Puste = fallback providera. |
| `gemini_model` | str | `""` | Model Gemini, np. `gemini-2.5-flash`. Puste = fallback providera. |
| `ollama_model` | str | `"qwen2.5:14b"` | Model Ollama. |
| `ollama_url` | str | `"http://localhost:11434"` | Adres usługi Ollama. |

### Tryby chunkowania LLM

| Tryb | Kiedy używać |
|---|---|
| `none` | Bez post-processingu LLM. |
| `whole_document` | Cały Markdown jako jeden prompt. Działa tylko dla krótkich dokumentów. |
| `by_page` | Jeden prompt na stronę. Dobry dla raportów stronicowanych. |
| `by_chunk` | Dzieli tekst na fragmenty o maksymalnej liczbie tokenów. Bezpieczny dla długich dokumentów. |
| `by_heading` | Dzieli po nagłówkach Markdown. Dobry dla dokumentów ze strukturą rozdziałów. |

---

## Sekcja `[conversion]`

| Klucz | Typ | Domyślnie | Opis |
|---|---|---|---|
| `default_engine` | str | `"pymupdf4llm"` | Domyślny silnik: `pymupdf4llm`, `marker`, `docling`, `mineru`. |
| `default_output_dir` | str | `""` | Domyślny katalog wynikowy. Puste = obok pliku źródłowego. |
| `default_language` | str | `"pol+eng"` | Język OCR w formacie Tesseracta, np. `pol+eng`, `deu`, `chi_sim`. |
| `epub_backend` | str | `"pandoc"` | Backend eksportu EPUB: `pandoc` (domyślny), `native` (wbudowany builder `ebooklib` — TOC, obrazy, CSS, metadane, okładka; bez Pandoca) lub `calibre` (`ebook-convert`; gdy niedostępny, fallback na Pandoc). |

---

## Sekcja `[marker]`

| Klucz | Typ | Domyślnie | Opis |
|---|---|---|---|
| `marker_device` | str | `"cpu"` | Urządzenie dla Markera: `auto`, `cpu`, `cuda`. |
| `marker_workers` | int | `1` | Liczba workerów CPU (pdftext). Wartość ≥1. |
| `marker_max_pages` | int | `1` | Limit stron na konwersję. `0` = brak limitu. |
| `marker_torch_device` | str | `""` | Explicit override dla `TORCH_DEVICE`. Puste = użyj `marker_device`. |
| `marker_recognition_batch_size` | int | `0` | Rozmiar batcha surya — rozpoznawanie tekstu. `0` = auto (8 CPU / 256 GPU). |
| `marker_detector_batch_size` | int | `0` | Rozmiar batcha surya — detekcja tekstu. `0` = auto (2 CPU / 32 GPU). |
| `marker_layout_batch_size` | int | `0` | Rozmiar batcha surya — layout. `0` = auto. |
| `marker_table_rec_batch_size` | int | `0` | Rozmiar batcha surya — rozpoznawanie tabel. `0` = auto. |

### Strojenie batchy GPU (marker)

Wartości dobierasz empirycznie obserwując `nvidia-smi -l 1`. Podnoś wartość, aż VRAM i utilizacja GPU rosną, ale zatrzymaj się przed OOM. Na 24 GB VRAM jest duży zapas — rząd 50–280 MB na element batcha zależnie od modelu. Batche GPU działają niezależnie od `marker_workers` (który dotyczy tylko CPU-side pdftext).

Przykład dla mocnego GPU:

```toml
[marker]
marker_device = "cuda"
marker_recognition_batch_size = 128
marker_detector_batch_size = 32
marker_layout_batch_size = 16
marker_table_rec_batch_size = 8
```

---

## Sekcja `[docling]`

| Klucz | Typ | Domyślnie | Opis |
|---|---|---|---|
| `docling_device` | str | `"auto"` | Urządzenie dla Doclinga: `auto`, `cpu`, `cuda`. Tryb `auto` wykonuje smoke test CUDA. |

---

## Sekcja `[mineru]`

| Klucz | Typ | Domyślnie | Opis |
|---|---|---|---|
| `mineru_backend` | str | `"pipeline"` | Backend MinerU: `pipeline` (bezpieczny, torch bez vLLM) lub `vlm` (maksymalna jakość, wymaga vLLM + flashinfer). |

Backend `pipeline` działa na GPU przez PyTorch bez potrzeby kompilatora CUDA (nvcc). Backend `vlm` daje lepsze wyniki na skanach, ale wymaga sprawnego stosu vLLM + flashinfer. Przy uruchomieniu `vlm` adapter automatycznie ustawia `VLLM_USE_FLASHINFER_SAMPLER=0`, co pozwala ominąć JIT-kompilację przez nvcc na nowym GPU (np. Blackwell sm_120).

---

## Sekcja `[api_keys]`

| Klucz | Typ | Domyślnie | Opis |
|---|---|---|---|
| `anthropic_api_key` | str | `""` | Klucz API Anthropic. Można też ustawić przez `ANTHROPIC_API_KEY`. |
| `openai_api_key` | str | `""` | Klucz API OpenAI. Można też ustawić przez `OPENAI_API_KEY`. |
| `gemini_api_key` | str | `""` | Klucz API Google Gemini. Można też ustawić przez `GEMINI_API_KEY`. |

Klucze przechowywane w `config.toml` są plaintext. Bezpieczniej trzymać je w `.env` lub zmiennych środowiskowych.

---

## Zmienne środowiskowe

Wszystkie pola konfiguracji można nadpisać zmienną środowiskową o nazwie odpowiadającej polu (uppercase). Zmienne środowiskowe i `.env` mają wyższy priorytet niż `config.toml`.

| Zmienna | Odpowiada polu |
|---|---|
| `ANTHROPIC_API_KEY` | `api_keys.anthropic_api_key` |
| `OPENAI_API_KEY` | `api_keys.openai_api_key` |
| `GEMINI_API_KEY` | `api_keys.gemini_api_key` |
| `ANTHROPIC_MODEL` | `llm.anthropic_model` |
| `OPENAI_MODEL` | `llm.openai_model` |
| `GEMINI_MODEL` | `llm.gemini_model` |
| `OLLAMA_MODEL` | `llm.ollama_model` |
| `OLLAMA_URL` | `llm.ollama_url` |
| `LLM_PROVIDER` | `llm.provider` |
| `LLM_MODE` | `llm.mode` |
| `DEFAULT_ENGINE` | `conversion.default_engine` |
| `EPUB_BACKEND` | `conversion.epub_backend` |
| `MINERU_BACKEND` | `mineru.mineru_backend` |

---

## Priorytet ładowania

```
zmienne środowiskowe / .env  (najwyższy)
        ↓
  config.toml
        ↓
  wartości domyślne  (najniższy)
```
