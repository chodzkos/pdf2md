"""Główny entry point CLI — będzie rozbudowany w kolejnych etapach."""

from __future__ import annotations

import click

from pdf2md import __version__


@click.group()
@click.version_option(__version__, prog_name="pdf2md")
def cli() -> None:
    """Konwerter PDF do Markdown z obsługą wielu silników i modeli LLM."""
