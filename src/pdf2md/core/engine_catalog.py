"""Katalog silników konwersji — neutralne dane współdzielone przez CLI i GUI.

Wydzielone z ``cli/main.py``, żeby GUI (np. ``widgets/engine_selector``) mogło czerpać metadane
silników (opis, hint instalacyjny, próg VRAM, flagi wykonalności) bez importowania modułu CLI.
"""

from __future__ import annotations

ENGINE_CATALOG: tuple[dict[str, object], ...] = (
    {
        "key": "pymupdf4llm",
        "name": "PyMuPDF4LLM",
        "package": "pymupdf4llm",
        "scope": "Core",
        "ocr": False,
        "llm": False,
        "license": "AGPL/kom.",
        "hint": "uv pip install pymupdf4llm",
        "min_vram_gb": 0,  # CPU — zawsze wykonalny
        "description": "Szybki ekstraktor tekstu z natywnych PDF-ów.",
    },
    {
        "key": "marker",
        "name": "Marker",
        "package": "marker-pdf",
        "scope": "Core",
        "ocr": True,
        "llm": True,
        "license": "GPL",
        "hint": "uv pip install marker-pdf",
        "min_vram_gb": 4,  # przybliżone; działa też na CPU (wolno)
        "description": "Uniwersalny konwerter z OCR i trybem LLM.",
    },
    {
        "key": "docling",
        "name": "Docling",
        "package": "docling",
        "scope": "Core",
        "ocr": True,
        "llm": False,
        "license": "MIT",
        "hint": "uv pip install docling",
        "min_vram_gb": 2,  # przybliżone; działa też na CPU (wolno)
        "description": "Enterprise parser dokumentów, tabele, RAG.",
    },
    {
        "key": "mineru",
        "name": "MinerU",
        "package": "mineru",
        "scope": "Opc.",
        "ocr": True,
        "llm": False,
        "linux_only_local": True,  # lokalny proces vLLM — tylko Linux/WSL
        "license": "AGPL",
        "hint": "uv tool install mineru --with mineru[all]",
        "min_vram_gb": 6,  # backend pipeline; backend vlm ~12 GB (cięższy)
        "description": "Dokumenty naukowe, layout, CJK. Backend pipeline (lekki) lub vlm (~12 GB).",
    },
    {
        "key": "olmocr",
        "name": "olmOCR",
        "package": "olmocr",
        "scope": "Opc.",
        "ocr": True,
        "llm": False,
        "gpu": True,
        "linux_only_local": True,  # tryb spawn: lokalny proces vLLM — tylko Linux/WSL
        # Gdy olmocr_server_url ustawiony → silnik-usługa (klient serwera, bez lokalnego GPU).
        "server_url_setting": "olmocr_server_url",
        "license": "Apache-2.0",
        "hint": "pip install olmocr (osobne środowisko + CUDA)",
        "min_vram_gb": 24,  # zmierzone: 9.5 GB model + 9.3 GB KV-cache + grafy CUDA
        "description": "VLM 7B do skanów: czysty Markdown, równania, tabele.",
    },
    {
        "key": "paddleocr-vl",
        "name": "PaddleOCR-VL",
        "package": "paddleocr",
        "scope": "Opc.",
        "ocr": True,
        "llm": False,
        "gpu": True,
        # Klient HTTP serwera vLLM — wykonalny też z Windows, gdy serwer stoi (WSL2).
        "server_backed": True,
        "license": "Apache-2.0",
        "hint": (
            "Uruchom serwer: VLLM_USE_FLASHINFER_SAMPLER=0 vllm serve "
            "PaddlePaddle/PaddleOCR-VL-1.6 --trust-remote-code --no-enable-prefix-caching "
            "(zob. INSTALL.md 7.3)"
        ),
        "min_vram_gb": 12,  # przybliżone (serwowany VLM)
        "description": "Serwer VLM (OpenAI-compatible): wielojęzyczny parser dokumentów.",
    },
    {
        "key": "surya",
        "name": "Surya",
        "package": "surya-ocr",
        "scope": "Opc.",
        "ocr": True,
        "llm": False,
        "gpu": True,
        "license": "GPL/komercyjna",
        "hint": "uv pip install surya-ocr",
        "min_vram_gb": 6,  # przybliżone
        "description": "Layout + OCR + reading order, kontrola/fallback.",
    },
    {
        "key": "scan-pipeline",
        "name": "Scan Pipeline (premium)",
        "package": "surya-ocr",
        "scope": "Opc.",
        "ocr": True,
        "llm": True,
        "gpu": True,
        "license": "różne (zależnie od silnika OCR)",
        "hint": "uv pip install surya-ocr ebooklib (+ GPU); zob. INSTALL.md",
        "min_vram_gb": 6,  # przybliżone (domyślnie Surya)
        "description": "Skan książki → VLM-OCR, korekta LLM, składanie, EPUB/Markdown.",
    },
)


def _normalize(name: str) -> str:
    return name.lower().replace(" ", "").replace("-", "").replace("_", "")


def catalog_entry(engine_name: str) -> dict[str, object] | None:
    """Wpis katalogu dla nazwy silnika (dopasowanie po znormalizowanej nazwie albo kluczu)."""
    wanted = _normalize(engine_name)
    for item in ENGINE_CATALOG:
        if _normalize(str(item["name"])) == wanted or str(item["key"]) == wanted:
            return item
    return None


def hint_for_engine(engine_name: str) -> str | None:
    """Hint instalacyjny/uruchomieniowy silnika z katalogu (np. serwer vLLM dla PaddleOCR-VL)."""
    entry = catalog_entry(engine_name)
    return str(entry["hint"]) if entry is not None else None
