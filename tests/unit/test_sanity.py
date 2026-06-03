"""Test podstawowy — sprawdza że pakiet importuje się poprawnie."""

from __future__ import annotations


def test_package_imports() -> None:
    """Pakiet pdf2md musi być importowalny."""
    import pdf2md

    assert pdf2md is not None


def test_version_defined() -> None:
    """Wersja musi być zdefiniowana w __init__.py i być niepustym stringiem."""
    import pdf2md

    assert hasattr(pdf2md, "__version__")
    assert isinstance(pdf2md.__version__, str)
    assert len(pdf2md.__version__) > 0


def test_version_contains_digits() -> None:
    """Wersja musi zawierać cyfry (format PEP 440)."""
    import pdf2md

    assert any(c.isdigit() for c in pdf2md.__version__)
