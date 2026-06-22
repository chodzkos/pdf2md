"""Testy składania książki (scan/assembly) — czysty tekst, bez ML."""

from __future__ import annotations

from pdf2md.scan.assembly import (
    Chapter,
    build_toc,
    detect_chapters,
    fix_hyphenation,
    merge_paragraphs_across_pages,
    normalize_punctuation,
    remove_repeated_headers_footers,
)


def test_fix_hyphenation_joins_split_word() -> None:
    """Wyraz podzielony myślnikiem na końcu wiersza jest scalany."""
    assert fix_hyphenation("sło-\nwo i koniec") == "słowo i koniec"
    assert fix_hyphenation("przed-\n  miot") == "przedmiot"
    # myślnik nie na granicy wiersza zostaje nietknięty
    assert fix_hyphenation("biało-czarny") == "biało-czarny"


def test_merge_paragraphs_continuation_across_pages() -> None:
    """Akapit przerwany na granicy strony (brak kropki + mała litera) jest łączony."""
    pages = ["To jest zdanie bez", "kropki kontynuacja."]
    assert merge_paragraphs_across_pages(pages) == "To jest zdanie bez kropki kontynuacja."


def test_merge_paragraphs_keeps_break_after_sentence_end() -> None:
    """Gdy strona kończy się kropką, kolejna zaczyna nowy akapit."""
    pages = ["Koniec zdania.", "Nowy akapit zaczyna się tutaj."]
    merged = merge_paragraphs_across_pages(pages)
    assert "Koniec zdania.\n\nNowy akapit" in merged


def test_remove_repeated_headers_footers() -> None:
    """Linia powtarzająca się na wielu stronach (żywa pagina) jest usuwana."""
    pages = [
        "NAGŁÓWEK KSIĄŻKI\n\nTreść pierwszej strony.",
        "NAGŁÓWEK KSIĄŻKI\n\nTreść drugiej strony.",
        "NAGŁÓWEK KSIĄŻKI\n\nTreść trzeciej strony.",
    ]
    cleaned = remove_repeated_headers_footers(pages)
    assert all("NAGŁÓWEK KSIĄŻKI" not in p for p in cleaned)
    assert "Treść pierwszej strony." in cleaned[0]


def test_remove_page_numbers() -> None:
    """Linie będące samym numerem strony są usuwane."""
    pages = ["Treść.\n\n12", "Inna treść.\n\n13"]
    cleaned = remove_repeated_headers_footers(pages)
    assert "12" not in cleaned[0].splitlines()
    assert "Treść." in cleaned[0]


def test_normalize_punctuation() -> None:
    """Cudzysłowy proste → polskie, podwójny myślnik → pauza, ... → wielokropek."""
    out = normalize_punctuation('powiedział "tak" i--nie...')
    assert "„tak”" in out
    assert "—" in out
    assert "…" in out
    assert '"' not in out


def test_detect_chapters_markdown_headings() -> None:
    """Nagłówki Markdown wyznaczają granice rozdziałów."""
    text = "## Rozdział I\n\nTekst pierwszego.\n\n## Rozdział II\n\nTekst drugiego."
    chapters = detect_chapters(text)
    titles = [c.title for c in chapters]
    assert titles == ["Rozdział I", "Rozdział II"]
    assert "Tekst pierwszego." in chapters[0].body


def test_detect_chapters_no_heading_returns_single() -> None:
    """Brak nagłówków → jeden rozdział z całością."""
    chapters = detect_chapters("Zwykły tekst bez nagłówków.")
    assert len(chapters) == 1
    assert chapters[0].body == "Zwykły tekst bez nagłówków."


def test_detect_chapters_preface_before_first_heading() -> None:
    """Materiał przed pierwszym nagłówkiem trafia do rozdziału „Wstęp"."""
    text = "Przedmowa autora.\n\n# Rozdział 1\n\nWłaściwa treść."
    chapters = detect_chapters(text)
    assert chapters[0].title == "Wstęp"
    assert "Przedmowa autora." in chapters[0].body
    assert chapters[1].title == "Rozdział 1"


def test_build_toc_links_to_anchors() -> None:
    """TOC zawiera odnośniki do kotwic rozdziałów."""
    chapters = [Chapter(title="Gillan z opactwa", body=""), Chapter(title="Narzeczone", body="")]
    toc = build_toc(chapters)
    assert "# Spis treści" in toc
    assert "[Gillan z opactwa](#gillan-z-opactwa)" in toc
    assert "[Narzeczone](#narzeczone)" in toc
