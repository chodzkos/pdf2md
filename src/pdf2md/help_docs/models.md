# Model AI / Ollama

Post-processing LLM działa lokalnie przez **Ollama** — bez kluczy i bez wysyłania danych.
Rekomendowany model korekty: `qwen3:14b`.

**VRAM:** model 14B mieści się swobodnie na 24 GB. Większe modele (np. 27B/30B) dają lepszą
jakość korekty, jeśli starcza pamięci. Na mniejszej karcie wybierz mniejszy model (np. 7B/8B) —
inaczej Ollama zejdzie na CPU i korekta będzie wolna.

Model korekty wskażesz w **Ustawieniach** albo komendą `pdf2md config set ollama_model qwen3:14b`.

**Wskazówka:** do obróbki tekstu lepszy jest **zwykły** `qwen3:14b` niż wariant vision
(`qwen3-vl`) — na etapie korekty (tekst→tekst) zdolności wizyjne nie są używane, a VL oddaje
część parametrów na vision. VL ma sens osobno (np. opis wyciąganych obrazów), nie jako model
korekty.

**Modele dostępne w Twoim środowisku** (i status serwera Ollama) zobaczysz w `pdf2md doctor` —
listy modeli nie wpisujemy tu na sztywno, bo zmienia się z instalacją.

Klucze API dostawców chmurowych (Anthropic / OpenAI / Gemini) sprawdzisz w `pdf2md doctor`
(sekcja Klucze API), a ustawisz w **Ustawieniach** lub przez `pdf2md config set`.
