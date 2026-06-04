"""Funkcje dzielenia tekstu Markdown na fragmenty do przetwarzania przez LLM."""

from __future__ import annotations

import re


def estimate_tokens(text: str) -> int:
    """Przybliżona liczba tokenów — ~4 znaki na token (reguła OpenAI/Anthropic).

    Args:
        text: Tekst do oszacowania.

    Returns:
        Przybliżona liczba tokenów.
    """
    return max(1, len(text) // 4)


def by_chunk(text: str, max_tokens: int = 4000) -> list[str]:
    """Dzieli tekst na fragmenty nieprzekraczające limitu tokenów.

    Stara się dzielić na granicy akapitów, nie w środku zdania.

    Args:
        text: Tekst wejściowy.
        max_tokens: Maksymalna liczba tokenów na fragment.

    Returns:
        Lista fragmentów tekstu.
    """
    if not text:
        return []

    max_chars = max_tokens * 4
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    paragraphs = re.split(r"\n{2,}", text)
    current: list[str] = []
    current_len = 0

    for para in paragraphs:
        para_len = len(para)
        if current_len + para_len + 2 > max_chars and current:
            chunks.append("\n\n".join(current))
            current = []
            current_len = 0
        # Pojedynczy akapit większy niż limit — dziel po znakach
        if para_len > max_chars:
            for i in range(0, para_len, max_chars):
                chunks.append(para[i : i + max_chars])
        else:
            current.append(para)
            current_len += para_len + 2

    if current:
        chunks.append("\n\n".join(current))

    return chunks


def by_heading(text: str) -> list[str]:
    """Dzieli tekst Markdown wg nagłówków (# ## ###…).

    Każda sekcja nagłówkowa staje się osobnym fragmentem.
    Tekst przed pierwszym nagłówkiem trafia do pierwszego fragmentu.

    Args:
        text: Tekst Markdown do podziału.

    Returns:
        Lista sekcji, każda zaczyna się od nagłówka (lub jest preambułą).
    """
    if not text:
        return []

    heading_pattern = re.compile(r"^#{1,6} ", re.MULTILINE)
    matches = list(heading_pattern.finditer(text))

    if not matches:
        return [text]

    sections: list[str] = []

    # Tekst przed pierwszym nagłówkiem
    if matches[0].start() > 0:
        preamble = text[: matches[0].start()].strip()
        if preamble:
            sections.append(preamble)

    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        section = text[start:end].strip()
        if section:
            sections.append(section)

    return sections


def by_page(pages: list[str]) -> list[str]:
    """Zwraca niepuste strony jako osobne fragmenty do przetwarzania przez LLM.

    Args:
        pages: Lista tekstów stron w kolejności z dokumentu.

    Returns:
        Lista niepustych stron po przycięciu białych znaków.
    """
    return [page.strip() for page in pages if page.strip()]
