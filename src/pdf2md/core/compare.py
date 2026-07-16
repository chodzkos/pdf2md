"""Porównywarka silników — konwersja jednego pliku wieloma silnikami + metryki.

Warstwa niezależna od CLI: przyjmuje listę silników, konwertuje ten sam plik każdym
z nich, zapisuje wynik per silnik i liczy proste metryki (długość, nagłówki, tabele).
Błąd pojedynczego silnika nie przerywa całego porównania.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from pdf2md.core.converter import Converter
from pdf2md.engines.base import ConversionEngine
from pdf2md.llm.base import LLMProvider

#: Nagłówek Markdown: 1-6 „#" na początku wiersza (dopuszczamy do 3 spacji wcięcia),
#: po nich spacja i treść — tak, by nie łapać „#tag" ani wierszy z samym „#".
_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+\S", re.MULTILINE)

#: Ocena jakości Markdown przez LLM: prosimy o pojedynczą liczbę 0-100.
_SCORE_SYSTEM_PROMPT = (
    "Oceń jakość poniższego dokumentu Markdown powstałego z konwersji PDF. "
    "Weź pod uwagę czytelność, zachowanie struktury (nagłówki, listy, tabele) "
    "oraz kompletność tekstu. Odpowiedz WYŁĄCZNIE jedną liczbą całkowitą od 0 do 100 "
    "(0 = bezużyteczny, 100 = idealny). Bez komentarza."
)

#: Maksymalny fragment Markdown wysyłany do oceny LLM (ogranicza koszt/tokeny).
_SCORE_EXCERPT_CHARS = 6000

#: Funkcja oceny jakości: Markdown → wynik 0-100 albo None, gdy oceny nie da się ustalić.
LlmScorer = Callable[[str], int | None]


@dataclass
class MarkdownMetrics:
    """Proste metryki wyniku konwersji."""

    chars: int
    headings: int
    tables: int


@dataclass
class EngineComparison:
    """Wynik porównania dla pojedynczego silnika."""

    engine: str
    status: str  # "ok" albo "error"
    output_path: Path | None = None
    duration_s: float = 0.0
    metrics: MarkdownMetrics | None = None
    error: str | None = None
    llm_score: int | None = None


def _count_tables(markdown: str) -> int:
    """Liczy tabele Markdown po wierszach-separatorach (`| --- | --- |`).

    Każda tabela GFM ma dokładnie jeden wiersz separatora między nagłówkiem a treścią,
    więc ich liczba = liczba tabel. Wiersz separatora składa się wyłącznie z `|`, `-`,
    `:` i spacji, zawiera co najmniej jeden `|` oraz kreski — co odróżnia go od poziomej
    linii `---` (brak `|`) i od zwykłego tekstu z pojedynczym `|`.
    """
    count = 0
    for line in markdown.splitlines():
        stripped = line.strip()
        if "|" not in stripped or "-" not in stripped:
            continue
        core = stripped.replace("|", "").replace(":", "").replace(" ", "")
        if core and core.strip("-") == "":
            count += 1
    return count


def compute_metrics(markdown: str) -> MarkdownMetrics:
    """Liczy metryki wyniku: długość w znakach, liczbę nagłówków i tabel."""
    return MarkdownMetrics(
        chars=len(markdown),
        headings=len(_HEADING_RE.findall(markdown)),
        tables=_count_tables(markdown),
    )


def make_llm_scorer(provider: LLMProvider) -> LlmScorer:
    """Buduje funkcję oceniającą jakość Markdown przez danego dostawcę LLM.

    Ocena jest best-effort: błąd modelu albo brak liczby w odpowiedzi → ``None``
    (porównanie leci dalej bez oceny dla danego silnika).
    """

    def score(markdown: str) -> int | None:
        excerpt = markdown[:_SCORE_EXCERPT_CHARS]
        if not excerpt.strip():
            return None
        try:
            raw = provider.correct(excerpt, system_prompt=_SCORE_SYSTEM_PROMPT, temperature=0.0)
        except Exception as exc:  # dostawca LLM może rzucić czymkolwiek (sieć/API/parsowanie)
            logger.warning(f"Ocena LLM nieudana: {exc}")
            return None
        match = re.search(r"\d{1,3}", raw)
        if match is None:
            return None
        return max(0, min(100, int(match.group())))

    return score


def compare_engines(
    input_path: str | Path,
    engines: list[ConversionEngine],
    output_dir: str | Path,
    *,
    lang: str = "pol+eng",
    converter: Converter | None = None,
    llm_scorer: LlmScorer | None = None,
) -> list[EngineComparison]:
    """Konwertuje ``input_path`` każdym z ``engines`` i zwraca metryki per silnik.

    Wynik każdego silnika zapisywany jest jako ``<stem>_<silnik>.md`` w ``output_dir``.
    Wyjątek jednego silnika jest łapany i raportowany jako ``status="error"`` — reszta
    porównania leci dalej.

    Args:
        input_path: Ścieżka pliku wejściowego (PDF/obraz).
        engines: Silniki do porównania (wołający filtruje dostępność/OCR).
        output_dir: Katalog na wyniki per silnik.
        lang: Język OCR przekazywany do silników OCR.
        converter: Instancja ``Converter`` (wstrzykiwana w testach).
        llm_scorer: Opcjonalna funkcja oceny jakości; ``None`` = bez oceny.

    Returns:
        Lista wyników w kolejności ``engines``.
    """
    source = Path(input_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    converter = converter or Converter()

    results: list[EngineComparison] = []
    for engine in engines:
        out_path = out_dir / f"{source.stem}_{engine.name}.md"
        start = time.monotonic()
        try:
            engine_kwargs: dict[str, object] = {}
            if engine.supports_ocr:
                engine_kwargs["lang"] = lang
            engine_options: dict[str, object] = {}
            if engine.name.lower() in {"docling", "marker"}:
                engine_options["output_path"] = str(out_path)
            result = converter.convert(
                str(source),
                engine,
                output_path=str(out_path),
                llm_mode="none",
                engine_kwargs=engine_kwargs,
                engine_options=engine_options,
                record_history=False,
            )
            score = llm_scorer(result.markdown) if llm_scorer is not None else None
            results.append(
                EngineComparison(
                    engine=engine.name,
                    status="ok",
                    output_path=out_path,
                    duration_s=time.monotonic() - start,
                    metrics=compute_metrics(result.markdown),
                    llm_score=score,
                )
            )
        except Exception as exc:  # jeden silnik nie może wywalić całego porównania
            logger.warning(f"Silnik {engine.name} padł podczas porównania: {exc}")
            results.append(
                EngineComparison(
                    engine=engine.name,
                    status="error",
                    duration_s=time.monotonic() - start,
                    error=str(exc),
                )
            )
    return results
