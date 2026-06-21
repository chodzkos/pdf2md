"""Heurystyki jakości OCR per strona — bez ML, bez LLM.

Służą do wykrycia stron, które trzeba przepuścić ponownie dokładniejszym silnikiem lub
wyższym DPI (zob. scan/rerun.py). Wszystkie metryki są tanie i deterministyczne.
"""

from __future__ import annotations

import difflib
import re

#: Znak zastępczy Unicode (�) — typowy objaw nieudanego dekodowania / OCR.
REPLACEMENT_CHAR = "�"

#: Marker niepewnego fragmentu wstawiany przez korektę (SCAN_CORRECTION_PROMPT).
UNREADABLE_MARKER = "[nieczytelne]"

#: Strona krótsza niż tyle znaków (po strip) jest podejrzanie krótka.
SHORT_PAGE_CHARS = 30

#: Wzorce częstych pomyłek OCR: „rn"→„m", cyfra 0 w słowie, litera O w liczbie, samotne l/I.
_SUSPICIOUS_PATTERNS = (
    re.compile(r"rn"),
    re.compile(r"[A-Za-ząćęłńóśźżĄĆĘŁŃÓŚŹŻ]0[A-Za-ząćęłńóśźżĄĆĘŁŃÓŚŹŻ]"),
    re.compile(r"\d[Oo]\d"),
    re.compile(r"(?<=\s)[lI](?=\s)"),
)

#: Domyślne progi do decyzji o ponownym przebiegu strony.
DEFAULT_THRESHOLDS = {
    "min_chars": SHORT_PAGE_CHARS,
    "max_replacement_chars": 0,
    "max_unreadable_markers": 3,
    "max_suspicious_patterns": 25,
}


def page_quality_score(md: str) -> dict[str, int]:
    """Zwraca słownik metryk jakości jednej strony Markdown.

    Wartości bool (is_empty, is_suspiciously_short) są podtypem int — przechowywane jako
    prawdziwe wartości logiczne, więc porównania ``is True/is False`` działają.
    """
    stripped = md.strip()
    char_count = len(stripped)
    replacement_char_count = md.count(REPLACEMENT_CHAR)
    unreadable_markers = md.count(UNREADABLE_MARKER)
    suspicious_patterns = sum(len(pattern.findall(md)) for pattern in _SUSPICIOUS_PATTERNS)
    return {
        "char_count": char_count,
        "replacement_char_count": replacement_char_count,
        "unreadable_markers": unreadable_markers,
        "suspicious_patterns": suspicious_patterns,
        "is_empty": char_count == 0,
        "is_suspiciously_short": 0 < char_count < SHORT_PAGE_CHARS,
    }


def should_rerun_page(score: dict[str, int], thresholds: dict[str, int] | None = None) -> bool:
    """Decyduje, czy stronę należy przepuścić ponownie, na podstawie metryk i progów."""
    th = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    if score["is_empty"] or score["is_suspiciously_short"]:
        return True
    return (
        score["replacement_char_count"] > th["max_replacement_chars"]
        or score["unreadable_markers"] > th["max_unreadable_markers"]
        or score["suspicious_patterns"] > th["max_suspicious_patterns"]
    )


def detect_low_quality_pages(
    pages: list[str],
    thresholds: dict[str, int] | None = None,
) -> list[int]:
    """Zwraca indeksy (0-based) stron o niskiej jakości, kwalifikujących się do ponownego OCR."""
    return [
        i for i, md in enumerate(pages) if should_rerun_page(page_quality_score(md), thresholds)
    ]


def compare_ocr_outputs(md_a: str, md_b: str) -> float:
    """Podobieństwo wyników dwóch silników OCR (0.0-1.0), SequenceMatcher.ratio()."""
    return difflib.SequenceMatcher(None, md_a, md_b).ratio()
