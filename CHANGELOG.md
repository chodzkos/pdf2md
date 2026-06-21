# Changelog

## v1.0.0

### Dodane

- CLI `pdf2md` z komendami `convert`, `list-engines`, `list-llm`, `doctor` i `config`.
- GUI `pdf2md-gui` (PySide6) z kolejką plików, wyborem silnika, opcjonalnym LLM, logiem, podglądem Markdown i eksportem EPUB przez Pandoc.
- Silniki konwersji: PyMuPDF4LLM, Marker, Docling, MinerU.
- OCR dla skanów oraz obsługa dokumentów mieszanych, wielokolumnowych, tabel i materiałów naukowych.
- Wspólny `~/.config/pdf2md/config.toml` dla CLI i GUI; `.env` jako override deweloperski.
- Dostawcy LLM: Ollama, Anthropic Claude, OpenAI, Google Gemini.
- Tryby post-processingu LLM: `whole_document`, `by_page`, `by_chunk`, `by_heading`.
- `pdf2md doctor` — diagnostyka zależności systemowych, silników, LLM, Tesseracta, Pandoca, Ollamy i realnej używalności CUDA.
- Eksport Markdown i EPUB (przez Pandoc).
- Preprocessing skanów (`scan/preprocessing.py`): wyrównanie, deskewing, denoising, kontrast — fundament dla Fazy 2 VLM-OCR.
- Konfigurowalne rozmiary batchy GPU dla Markera/surya (`marker_recognition_batch_size`, `marker_detector_batch_size`, `marker_layout_batch_size`, `marker_table_rec_batch_size`).
- Konfigurowalne backendy MinerU (`mineru_backend`: `pipeline` lub `vlm`); backend `vlm` automatycznie ustawia `VLLM_USE_FLASHINFER_SAMPLER=0` dla kompatybilności z nowymi GPU (Blackwell sm_120).
- Testy jednostkowe: konfiguracja, CLI, converter, silniki, dostawcy LLM, detekcja zależności, eksportery, preprocessing.

### Ograniczenia v1.0

- Wymagany Python 3.11–3.12 (ekosystem ML nie obsługuje 3.13+).
- pdf-craft wykluczony z powodu nieusuwalnego konfliktu `transformers` z Markerem i Doclingiem.
- Faza 2 (VLM-OCR, skanowane książki wysokiej jakości) — po v1.0, wymaga GPU ≥24 GB VRAM.
