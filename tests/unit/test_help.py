"""Testy okna pomocy: pakowane pliki Markdown (jeden plik prawdy) + pokrycie funkcji."""

from __future__ import annotations

from pdf2md.gui.help_window import HELP_SECTIONS, help_doc_path

# ── strażnik pakowania (Qt-free — działa też headless) ───────────────────────


def test_help_docs_present_and_nonempty() -> None:
    """Każdy plik .md wskazywany przez kod ISTNIEJE w pakiecie i nie jest pusty."""
    for _title, filename in HELP_SECTIONS:
        path = help_doc_path(filename)
        assert path.is_file(), f"brak pliku pomocy: {filename}"
        assert path.read_text(encoding="utf-8").strip(), f"pusty plik pomocy: {filename}"


def test_help_sections_titles_stable() -> None:
    """Kolejność i tytuły zakładek zachowane (6 zakładek)."""
    titles = [title for title, _ in HELP_SECTIONS]
    assert titles == [
        "Silniki konwersji",
        "Instalacja silników",
        "Post-processing LLM",
        "Profile skanowania",
        "CLI",
        "Model AI / Ollama",
    ]


# ── audyt kompletności (treść pokrywa nowe funkcje) ──────────────────────────


def test_cli_tab_covers_all_commands_and_flags() -> None:
    cli = help_doc_path("cli.md").read_text(encoding="utf-8").lower()
    for keyword in (
        "compare",
        "forms",
        "history",
        "--password",
        "--epub-backend",
        "--extract-images",
        "--profile",
        "jpg",
        "anuluj",
    ):
        assert keyword in cli, f"pomoc CLI nie opisuje: {keyword}"


def test_epub_backends_documented() -> None:
    profiles = help_doc_path("profiles.md").read_text(encoding="utf-8").lower()
    for backend in ("pandoc", "native", "calibre"):
        assert backend in profiles, f"brak backendu EPUB w pomocy: {backend}"
