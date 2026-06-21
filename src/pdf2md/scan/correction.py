"""Korekta OCR per strona przez LLM z Fazy 1 (preferowany lokalny Ollama + Qwen3 14B).

KOLEJNOŚĆ I VRAM: faza korekty uruchamia się DOPIERO po tym, jak silnik VLM zwolnił VRAM
(``engine.unload_model()`` z Etapu 12). Pełną sekwencję (cały OCR → unload VLM → korekta)
wymusza ScanPipelineEngine (Etap 14). Tu dajemy:
- ``log_free_vram()`` jako guard przed startem korekty (ostrzega, gdy model wizyjny nie zniknął),
- ``release_ollama_model()`` do wyładowania modelu korekty po jej zakończeniu (Ollama domyślnie
  trzyma model 5 min w VRAM; ``keep_alive=0`` zwalnia go natychmiast).
"""

from __future__ import annotations

from pathlib import Path

from loguru import logger

from pdf2md.core.prompts import SCAN_CORRECTION_PROMPT
from pdf2md.llm.base import LLMProvider

#: Próg ostrzeżenia: jeśli wolne VRAM < tego ułamka całości, model wizyjny pewnie nie zniknął.
_LOW_VRAM_FRACTION = 0.4


def correct_page(md: str, provider: LLMProvider) -> str:
    """Koryguje OCR jednej strony konserwatywnie (SCAN_CORRECTION_PROMPT).

    Puste strony zwraca bez zmian (nie marnuje wywołania LLM). Korekta NIE parafrazuje
    ani nie streszcza — prompt wymusza poprawę wyłącznie oczywistych błędów OCR.
    """
    if not md.strip():
        return md
    return provider.correct(md, system_prompt=SCAN_CORRECTION_PROMPT, temperature=0.0)


def correct_pages_batch(
    md_dir: str,
    provider: LLMProvider,
    output_dir: str,
) -> list[str]:
    """Koryguje wszystkie strony ``*.md`` z ``md_dir`` i zapisuje do ``output_dir``.

    Przed startem loguje wolne VRAM (guard), po zakończeniu wyładowuje model korekty.
    Zwraca listę ścieżek zapisanych plików w kolejności stron.
    """
    src = Path(md_dir)
    dst = Path(output_dir)
    dst.mkdir(parents=True, exist_ok=True)

    log_free_vram("przed korektą LLM")

    written: list[str] = []
    for md_file in sorted(src.glob("*.md")):
        corrected = correct_page(md_file.read_text(encoding="utf-8"), provider)
        out_path = dst / md_file.name
        out_path.write_text(corrected, encoding="utf-8")
        written.append(str(out_path))
    logger.info(f"Korekta zakończona: {len(written)} stron → {dst}")

    release_ollama_model(provider)
    return written


def log_free_vram(label: str = "") -> float | None:
    """Loguje wolne VRAM (GB) i ostrzega, jeśli wygląda na to, że VLM nie zwolnił pamięci.

    Zwraca wolne GB albo None, gdy CUDA/torch niedostępne. Nigdy nie rzuca.
    """
    try:
        import torch

        if not torch.cuda.is_available():
            return None
        free, total = torch.cuda.mem_get_info()
        free_gb = free / 1024**3
        total_gb = total / 1024**3
        logger.info(f"VRAM ({label}): wolne {free_gb:.1f} / {total_gb:.1f} GB")
        if total and free / total < _LOW_VRAM_FRACTION:
            logger.warning(
                "Mało wolnego VRAM przed korektą — czy silnik VLM wywołał unload_model()? "
                "Korekta i model wizyjny nie mogą być załadowane jednocześnie (OOM na 24 GB)."
            )
        return free_gb
    except Exception:
        return None


def release_ollama_model(provider: LLMProvider) -> bool:
    """Best-effort: wyładuj model Ollamy z VRAM (keep_alive=0). Zwraca True przy sukcesie.

    Działa tylko dla dostawcy Ollama (rozpoznanego po nazwie i metodzie ``_base_url``).
    Dla innych dostawców (chmura) to no-op. Nigdy nie rzuca.
    """
    base_url_fn = getattr(provider, "_base_url", None)
    if not callable(base_url_fn) or "ollama" not in provider.name.lower():
        return False
    try:
        import json
        import urllib.request

        from pdf2md.core.config import get_settings

        model = get_settings().ollama_model or provider.default_model
        payload = json.dumps({"model": model, "keep_alive": 0}).encode()
        req = urllib.request.Request(
            f"{base_url_fn()}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10):
            pass
        logger.debug(f"Ollama: wysłano keep_alive=0 dla modelu {model} (zwolnienie VRAM)")
        return True
    except Exception as exc:
        logger.debug(f"Ollama keep_alive=0 nie powiodło się (pomijam): {exc}")
        return False
