"""pdf2md — konwerter PDF do Markdown z obsługą wielu silników i modeli LLM."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("pdf2md")
except PackageNotFoundError:  # pragma: no cover - uruchomienie z drzewa bez instalacji pakietu
    __version__ = "0.0.0+unknown"

__all__ = ["__version__"]
