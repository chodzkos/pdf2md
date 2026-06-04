"""Ręczny test konwersji PDF do Markdown."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def _find_engine(engine_name: str, engines: list[object]) -> object | None:
    for engine in engines:
        if engine.name.lower() == engine_name.lower():
            return engine
    return None


def main() -> int:
    """Uruchamia testową konwersję z linii komend."""
    parser = argparse.ArgumentParser(description="Testowa konwersja PDF do Markdown.")
    parser.add_argument("pdf_path", help="Ścieżka do pliku PDF")
    parser.add_argument("--engine", default="pymupdf4llm", help="Nazwa silnika")
    args = parser.parse_args()

    import pdf2md.engines  # noqa: F401  # rejestruje wbudowane silniki
    from pdf2md.core.converter import ConversionError, Converter
    from pdf2md.core.registry import engine_registry

    engines = engine_registry.get_all()
    engine = _find_engine(args.engine, engines)
    if engine is None:
        available = ", ".join(e.name for e in engines) or "brak"
        print(f"Nieznany silnik: {args.engine}. Zarejestrowane: {available}", file=sys.stderr)
        return 2

    start = time.monotonic()
    try:
        result = Converter().convert(args.pdf_path, engine)
    except (ConversionError, RuntimeError) as exc:
        print(f"Błąd konwersji: {exc}", file=sys.stderr)
        if not engine.is_available():
            print(
                "Zainstaluj silnik poleceniem: uv pip install pymupdf4llm",
                file=sys.stderr,
            )
        return 1
    elapsed = time.monotonic() - start

    print(result.markdown[:500])
    print()
    print(f"Silnik: {result.engine_used}")
    print(f"Strony: {result.pages}")
    print(f"Czas konwersji: {elapsed:.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
