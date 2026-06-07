# Changelog

## v1.0.0 — Initial release

- CLI `pdf2md` z komendami `convert`, `list-engines`, `list-llm`, `doctor` i `config`.
- GUI `pdf2md-gui` z kolejka plikow, wyborem silnika, opcjonalnym LLM, logiem, podgladem Markdown i eksportem EPUB przez Pandoc.
- Wymienne silniki konwersji: PyMuPDF4LLM, Marker, Docling, MinerU i pdf-craft.
- OCR dla skanow oraz obsluga dokumentow mieszanych, wielokolumnowych, tabel i materialow naukowych.
- Wspolny `config.toml` dla CLI i GUI oraz `.env` jako override deweloperski.
- Dostawcy LLM: Ollama, Anthropic Claude, OpenAI i Google Gemini.
- Diagnostyka `pdf2md doctor` dla zaleznosci systemowych, silnikow, LLM, Tesseracta, Pandoca, Ollamy oraz realnej uzywalnosci CUDA.
- Eksport Markdown i EPUB.
- Testy jednostkowe dla konfiguracji, CLI, convertera, silnikow, dostawcow LLM, detekcji zaleznosci i eksporterow.
