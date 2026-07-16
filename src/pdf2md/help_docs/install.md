# Instalacja silników

## Silniki rdzeniowe

```
uv sync --extra engines-core
```

Instaluje PyMuPDF4LLM, Marker, Docling i Surya. torch z CUDA (`cu130`) wchodzi automatycznie.

## Narzędzia systemowe

- **Tesseract** (+ język **pol**) — OCR skanów w Marker/Docling
- **Poppler** (`pdftoppm`) — PDF → obraz

Oba muszą być w PATH.

**Windows:** Tesseract — instalator UB Mannheim (zaznacz Polish); Poppler — rozpakuj ZIP i
dodaj `C:\poppler\Library\bin` do PATH.

```
# WSL / Ubuntu:
sudo apt install tesseract-ocr tesseract-ocr-pol poppler-utils
```

## GPU / CUDA

torch instaluje się jako `+cu130` (CUDA 13) przy `uv sync` (Windows i WSL) — jeden, testowany
toolkit. Do pracy na GPU potrzebny jest **aktualny sterownik NVIDIA wspierający CUDA 13**. Bez
aktualnego sterownika aplikacja działa na CPU (nie schodzimy z `+cu130`).

**VRAM decyduje, które silniki ruszą:** skromna karta (np. 8 GB) → Marker / Surya / Docling na
GPU, ale bez ciężkich serwowanych VLM-ów; pełna Faza 2 (z olmOCR) dopiero przy ~24 GB.

Sprawdź `pdf2md doctor` — pokaże, co Twój konkretny sprzęt uciągnie (✅ / ⚠️ / ❌ per silnik) i
czy sterownik jest wystarczająco nowy (karta wykryta, ale za stary sterownik → komunikat o
aktualizacji). Pełna tabela sprzętowa: **INSTALL.md** sekcja 12.

Jeśli CUDA jest niedostępna albo torch wszedł jako `+cpu`:

```
uv lock --upgrade-package torch --upgrade-package torchvision
uv sync --extra engines-core
```

## Silniki-usługi (zaawansowane)

MinerU, PaddleOCR-VL i olmOCR (zaparkowany) są izolowane w osobnych środowiskach i działają
**tylko w WSL** — vLLM nie wspiera natywnego Windows. Szczegóły w INSTALL.md.

Pełna instrukcja krok po kroku: **INSTALL.md** w repozytorium (przycisk „Strona projektu” w
oknie **O programie**).
