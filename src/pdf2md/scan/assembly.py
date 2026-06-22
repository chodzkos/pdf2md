"""Składanie poprawionych stron OCR w spójną książkę Markdown.

Czyste przetwarzanie tekstu (stdlib `re`) — bez ML, bez ciężkich zależności. Operuje na
liście stron Markdown (po korekcie LLM) i scala je w jeden dokument z rozdziałami i TOC.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Linia jest nagłówkiem rozdziału, gdy to nagłówek Markdown (#..###) albo „Rozdział/Chapter…".
_MD_HEADING_RE = re.compile(r"^\s{0,3}(#{1,3})\s+(?P<title>.+?)\s*#*\s*$")
_CHAPTER_RE = re.compile(
    r"^\s*(?:Rozdzia[łl]|Chapter|Cz[ęe][śs][ćc])\b.*$",
    re.IGNORECASE,
)
# Linia czysto numeryczna / numer strony (arabski lub rzymski) — typowa stopka.
# Klasa znaku obejmuje hyphen oraz pauzy (en/em) jako separatory numeru strony.
_PAGE_NUMBER_RE = re.compile(
    r"^\s*[-–—]?\s*(?:\d{1,4}|[ivxlcdmIVXLCDM]{1,7})\s*[-–—]?\s*$"  # noqa: RUF001
)


@dataclass
class Chapter:
    """Pojedynczy rozdział książki."""

    title: str
    body: str
    level: int = 1
    anchor: str = field(default="")

    def __post_init__(self) -> None:
        if not self.anchor:
            self.anchor = _slugify(self.title)


def _slugify(text: str) -> str:
    """Zamienia tytuł na kotwicę: małe litery, spacje→myślniki, bez znaków specjalnych."""
    slug = text.strip().lower()
    slug = re.sub(r"[^\w\s-]", "", slug, flags=re.UNICODE)
    slug = re.sub(r"[\s_]+", "-", slug).strip("-")
    return slug or "rozdzial"


# ---------------------------------------------------------------------------
# Nagłówki / stopki
# ---------------------------------------------------------------------------


def remove_repeated_headers_footers(pages: list[str]) -> list[str]:
    """Usuwa linie powtarzające się na wielu stronach (żywa pagina, stopki, numery stron).

    Linia jest uznana za nagłówek/stopkę, gdy (po strip) jest krótka i pojawia się na co
    najmniej połowie stron (min. 2). Numery stron usuwane są zawsze.
    """
    if not pages:
        return []

    counts: dict[str, int] = {}
    for page in pages:
        seen_on_page = {ln.strip() for ln in page.splitlines() if ln.strip()}
        for line in seen_on_page:
            counts[line] = counts.get(line, 0) + 1

    threshold = max(2, len(pages) // 2)
    repeated = {
        line
        for line, c in counts.items()
        if c >= threshold and len(line) <= 80 and not line.startswith("#")
    }

    cleaned: list[str] = []
    for page in pages:
        kept = [
            ln
            for ln in page.splitlines()
            if ln.strip() not in repeated and not _PAGE_NUMBER_RE.match(ln)
        ]
        cleaned.append("\n".join(kept).strip())
    return cleaned


# ---------------------------------------------------------------------------
# Łączenie akapitów / dzielenie wyrazów
# ---------------------------------------------------------------------------


def fix_hyphenation(text: str) -> str:
    """Scala wyrazy podzielone myślnikiem na końcu wiersza: ``sło-\\nwo`` → ``słowo``."""
    # litera + myślnik + (opcjonalne spacje) + nowa linia + (spacje) + litera → scal
    return re.sub(r"(\w)[-­]\s*\n\s*(\w)", r"\1\2", text)


def merge_paragraphs_across_pages(pages: list[str]) -> str:
    """Scala strony w jeden tekst, łącząc akapity przerwane na granicy strony.

    Jeśli poprzednia strona nie kończy się znakiem końca zdania, a następna zaczyna się
    małą literą — traktujemy to jako kontynuację akapitu (łączenie spacją). W przeciwnym
    razie wstawiamy pełny odstęp akapitu.
    """
    sentence_end = '.!?:…"”»)'
    out = ""
    for i, page in enumerate(pages):
        chunk = page.strip("\n")
        if i == 0:
            out = chunk
            continue
        prev = out.rstrip()
        nxt = chunk.lstrip()
        if not nxt:
            continue
        if not prev:
            out = nxt
            continue
        if prev[-1] not in sentence_end and nxt[:1].islower():
            out = f"{prev} {nxt}"
        else:
            out = f"{prev}\n\n{nxt}"
    return out


# ---------------------------------------------------------------------------
# Interpunkcja
# ---------------------------------------------------------------------------


def normalize_punctuation(text: str) -> str:
    """Normalizuje myślniki, wielokropek i cudzysłowy proste na polskie typograficzne."""
    text = text.replace("---", "—").replace("--", "—")
    text = re.sub(r"(?<!\.)\.\.\.(?!\.)", "…", text)
    # proste cudzysłowy „"" → polskie „ … " (naprzemiennie otwierający/zamykający)
    result: list[str] = []
    opening = True
    for ch in text:
        if ch == '"':
            result.append("„" if opening else "”")
            opening = not opening
        else:
            result.append(ch)
    return "".join(result)


# ---------------------------------------------------------------------------
# Rozdziały i spis treści
# ---------------------------------------------------------------------------


def detect_chapters(text: str) -> list[Chapter]:
    """Dzieli tekst na rozdziały po nagłówkach Markdown i frazach „Rozdział/Chapter".

    Gdy nie wykryto żadnego nagłówka, zwraca jeden rozdział z całością tekstu.
    """
    lines = text.splitlines()
    boundaries: list[tuple[int, str, int]] = []  # (indeks_linii, tytuł, poziom)
    for idx, line in enumerate(lines):
        md = _MD_HEADING_RE.match(line)
        if md:
            boundaries.append((idx, md.group("title").strip(), len(md.group(1))))
        elif _CHAPTER_RE.match(line) and len(line.strip()) <= 80:
            boundaries.append((idx, line.strip(), 1))

    if not boundaries:
        body = text.strip()
        return [Chapter(title="Tekst", body=body)] if body else []

    chapters: list[Chapter] = []
    # Materiał przed pierwszym nagłówkiem (przedmowa) — dołącz jako rozdział bez tytułu.
    first_idx = boundaries[0][0]
    preface = "\n".join(lines[:first_idx]).strip()
    if preface:
        chapters.append(Chapter(title="Wstęp", body=preface))

    for n, (line_idx, title, level) in enumerate(boundaries):
        end = boundaries[n + 1][0] if n + 1 < len(boundaries) else len(lines)
        body = "\n".join(lines[line_idx + 1 : end]).strip()
        chapters.append(Chapter(title=title, body=body, level=level))
    return chapters


def build_toc(chapters: list[Chapter]) -> str:
    """Buduje spis treści jako listę Markdown z odnośnikami do kotwic rozdziałów."""
    if not chapters:
        return ""
    lines = ["# Spis treści", ""]
    for ch in chapters:
        indent = "  " * (max(1, ch.level) - 1)
        lines.append(f"{indent}- [{ch.title}](#{ch.anchor})")
    return "\n".join(lines)
