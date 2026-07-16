# Silniki konwersji

| Silnik | Typ dokumentu | OCR | Grupa |
| --- | --- | --- | --- |
| PyMuPDF4LLM | Natywne PDF z warstwą tekstową (raporty, instrukcje) — najszybszy | Nie | główne |
| Marker | Skany, dokumenty mieszane, trudniejszy layout; opcjonalny LLM | Tak (CPU) | główne |
| Docling | Tabele, dokumenty biznesowe, struktura, RAG | Tak | główne |
| Surya | Layout + OCR + reading order, GPU, in-process | Tak | GPU (też Windows) |
| MinerU | Artykuły naukowe, CJK, wielokolumnowe układy | Tak | izolowany — Linux/WSL |
| PaddleOCR-VL | Wielojęzyczny VLM-OCR (serwer vLLM) | Tak | izolowany — Linux/WSL |
| olmOCR | VLM 7B do skanów (zaparkowany, anglocentryczny) | Tak | izolowany — Linux/WSL |

Silniki dzielą się na trzy grupy: **główne** (PyMuPDF4LLM / Marker / Docling — działają
wszędzie), **Surya** (GPU, ale dzieli środowisko projektu — działa też pod Windows) oraz
**izolowane usługi VLM-OCR** (MinerU / PaddleOCR-VL / olmOCR) oparte na vLLM. Tu liczy się
tryb: **proces lokalny** (MinerU, olmOCR bez `server_url`) uruchamia vLLM u siebie i
**działa tylko pod Linux/WSL**; **silnik-usługa / klient HTTP** (PaddleOCR-VL, olmOCR z
ustawionym `server_url`) **działa też spod Windows**, gdy serwer stoi w WSL2/Linux.
**olmOCR** jest dodatkowo **zaparkowany** (anglocentryczny, zajmuje ~całą kartę); dla
skanów po polsku użyj PaddleOCR-VL lub Surya.

**Scan Pipeline** to nie osobny model, tylko meta-silnik do skanowanych książek: prowadzi
dokument przez preprocessing → OCR (VLM) → korektę LLM → walidację → składanie → Markdown/EPUB
wg wybranego profilu (patrz zakładka „Profile skanowania”, komenda `pdf2md scan`).

Co jest zainstalowane i dostępne w **Twoim** środowisku — wraz ze statusem GPU/CUDA, Ollamy,
narzędzi i kluczy API — sprawdzisz komendą `pdf2md doctor`.

**Kiedy który:** natywny tekst → PyMuPDF4LLM; skan / mieszane → Marker; tabele / biznes →
Docling; kontrola layoutu → Surya; nauka / CJK / wielokolumnowe → MinerU; wielojęzyczny VLM →
PaddleOCR-VL.
