"""Wykrywanie i odszyfrowywanie zabezpieczonych hasłem PDF (pypdf).

Warstwa niezależna od CLI/GUI: sprawdza szyfrowanie, weryfikuje hasło i zapisuje
odszyfrowaną kopię do katalogu tymczasowego, którą dalej przetwarza istniejący
przepływ konwersji (silniki dostają zwykły, nieszyfrowany PDF).
"""

from __future__ import annotations

from pathlib import Path

from loguru import logger


class PdfPasswordError(Exception):
    """Brak hasła do zaszyfrowanego PDF albo hasło nieprawidłowe."""


def is_pdf_encrypted(pdf_path: str | Path) -> bool:
    """Zwraca True, gdy PDF jest zaszyfrowany.

    Defensywnie: nieczytelny/uszkodzony plik → False (błąd zgłosi dopiero silnik
    konwersji z sensowniejszym komunikatem, zamiast wysypywać detekcję).
    """
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        return bool(PdfReader(str(pdf_path)).is_encrypted)
    except (PdfReadError, OSError, ValueError) as exc:
        logger.debug(f"Nie udało się sprawdzić szyfrowania {pdf_path}: {exc}")
        return False


def verify_pdf_password(pdf_path: str | Path, password: str) -> bool:
    """Sprawdza, czy ``password`` odblokowuje PDF (True także dla nieszyfrowanego)."""
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    if not reader.is_encrypted:
        return True
    return bool(reader.decrypt(password))


def decrypt_pdf(pdf_path: str | Path, password: str, output_dir: str | Path) -> Path:
    """Zapisuje odszyfrowaną kopię PDF w ``output_dir`` i zwraca jej ścieżkę.

    Gdy PDF nie jest zaszyfrowany, zwraca oryginalną ścieżkę (nic do roboty).

    Raises:
        PdfPasswordError: brak hasła do zaszyfrowanego pliku albo złe hasło.
    """
    from pypdf import PdfReader, PdfWriter

    source = Path(pdf_path)
    reader = PdfReader(str(source))
    if not reader.is_encrypted:
        return source
    if not password:
        raise PdfPasswordError("PDF jest zaszyfrowany — wymagane hasło.")
    if not reader.decrypt(password):
        raise PdfPasswordError("Nieprawidłowe hasło do PDF.")

    writer = PdfWriter()
    writer.append(reader)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{source.stem}_decrypted.pdf"
    with out_path.open("wb") as handle:
        writer.write(handle)
    return out_path
