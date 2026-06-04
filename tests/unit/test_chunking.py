"""Testy dzielenia tekstu dla trybów LLM."""

from __future__ import annotations

from pdf2md.utils.chunking import by_chunk, by_heading, by_page, estimate_tokens


def test_estimate_tokens_returns_at_least_one() -> None:
    """estimate_tokens() nigdy nie zwraca zera."""
    assert estimate_tokens("") == 1
    assert estimate_tokens("abcd") == 1
    assert estimate_tokens("abcdefgh") == 2


def test_by_chunk_returns_empty_for_empty_text() -> None:
    """Pusty tekst daje pustą listę fragmentów."""
    assert by_chunk("") == []


def test_by_chunk_keeps_short_text_as_single_chunk() -> None:
    """Krótki tekst pozostaje jednym fragmentem."""
    assert by_chunk("krótki tekst", max_tokens=100) == ["krótki tekst"]


def test_by_chunk_splits_long_text() -> None:
    """Długi tekst jest dzielony na kilka fragmentów."""
    chunks = by_chunk("aaaa\n\nbbbb\n\ncccc", max_tokens=1)

    assert len(chunks) > 1
    assert all(chunks)


def test_by_heading_splits_markdown_sections() -> None:
    """Markdown jest dzielony według nagłówków."""
    text = "Intro\n\n# A\nTreść A\n\n## B\nTreść B"

    assert by_heading(text) == ["Intro", "# A\nTreść A", "## B\nTreść B"]


def test_by_heading_without_headings_returns_whole_text() -> None:
    """Tekst bez nagłówków pozostaje jednym fragmentem."""
    assert by_heading("Akapit\n\nDrugi akapit") == ["Akapit\n\nDrugi akapit"]


def test_by_page_strips_and_skips_empty_pages() -> None:
    """by_page() zwraca niepuste strony jako osobne fragmenty."""
    assert by_page([" strona 1 ", "", " \n ", "strona 2"]) == ["strona 1", "strona 2"]
