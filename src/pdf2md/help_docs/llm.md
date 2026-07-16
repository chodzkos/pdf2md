# Post-processing LLM

Po konwersji opcjonalny model LLM poprawia i porządkuje wygenerowany Markdown (operacja
tekst→tekst — obraz strony NIE jest podawany do modelu).

## Tryby chunkowania

- `whole_document` — cały dokument naraz
- `by_page` — strona po stronie
- `by_chunk` — fragmenty tekstu
- `by_heading` — sekcje wg nagłówków

## Dostawcy

- **Ollama** — lokalny, domyślny (bez kluczy, bez wysyłania danych)
- **Claude (Anthropic), OpenAI, Gemini** — chmurowe (wymagają klucza API)

Klucze API ustawisz w oknie **Ustawienia** albo w pliku `~/.config/pdf2md/config.toml`.

**W GUI:** dostawcę i model wskazuje selektor LLM pod wyborem silnika; w CLI odpowiadają za to
flagi `--llm`, `--llm-model`, `--llm-mode` komendy `convert`.
