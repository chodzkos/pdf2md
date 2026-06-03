"""Testy konwertera PDF → Markdown."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pdf2md.core.converter import ConversionError, Converter
from pdf2md.engines.base import ConversionEngine, ConversionResult
from pdf2md.llm.base import LLMProvider, LLMResult


def _make_engine(available: bool = True, markdown: str = "# wynik") -> ConversionEngine:
    """Tworzy mock silnika konwersji."""
    engine = MagicMock(spec=ConversionEngine)
    engine.name = "mock_engine"
    engine.is_available.return_value = available
    engine.convert.return_value = ConversionResult(
        markdown=markdown, engine_used="mock_engine", pages=3
    )
    return engine


def _make_llm(output: str = "# wynik [LLM]") -> LLMProvider:
    """Tworzy mock dostawcy LLM."""
    llm = MagicMock(spec=LLMProvider)
    llm.name = "mock_llm"
    llm.postprocess.return_value = LLMResult(text=output, provider_used="mock_llm")
    return llm


class TestConverter:
    def test_convert_basic(self, tmp_path: Path) -> None:
        """convert() zwraca ConversionResult z Markdown."""
        pdf = tmp_path / "doc.pdf"
        pdf.write_bytes(b"fake pdf")
        engine = _make_engine(markdown="# Hello")

        result = Converter().convert(str(pdf), engine)

        assert result.markdown == "# Hello"
        assert result.engine_used == "mock_engine"
        engine.convert.assert_called_once_with(str(pdf))

    def test_convert_with_llm(self, tmp_path: Path) -> None:
        """convert() z LLM przekazuje Markdown do post-processingu."""
        pdf = tmp_path / "doc.pdf"
        pdf.write_bytes(b"fake pdf")
        engine = _make_engine(markdown="# surowy")
        llm = _make_llm(output="# poprawiony")

        result = Converter().convert(str(pdf), engine, llm=llm)

        assert result.markdown == "# poprawiony"
        llm.postprocess.assert_called_once_with("# surowy")

    def test_convert_saves_output_file(self, tmp_path: Path) -> None:
        """convert() z output_path zapisuje plik .md."""
        pdf = tmp_path / "doc.pdf"
        pdf.write_bytes(b"fake pdf")
        out = tmp_path / "output.md"
        engine = _make_engine(markdown="# treść")

        Converter().convert(str(pdf), engine, output_path=str(out))

        assert out.exists()
        assert out.read_text(encoding="utf-8") == "# treść"

    def test_convert_raises_when_file_not_found(self) -> None:
        """convert() rzuca ConversionError gdy plik nie istnieje."""
        engine = _make_engine()
        with pytest.raises(ConversionError, match="nie istnieje"):
            Converter().convert("/nieistniejacy/plik.pdf", engine)

    def test_convert_raises_when_engine_unavailable(self, tmp_path: Path) -> None:
        """convert() rzuca ConversionError gdy silnik niedostępny."""
        pdf = tmp_path / "doc.pdf"
        pdf.write_bytes(b"fake pdf")
        engine = _make_engine(available=False)

        with pytest.raises(ConversionError, match="nie jest dostępny"):
            Converter().convert(str(pdf), engine)

    def test_convert_records_time(self, tmp_path: Path) -> None:
        """convert() ustawia conversion_time > 0."""
        pdf = tmp_path / "doc.pdf"
        pdf.write_bytes(b"fake pdf")
        engine = _make_engine()

        result = Converter().convert(str(pdf), engine)

        assert result.conversion_time >= 0.0

    def test_convert_batch(self, tmp_path: Path) -> None:
        """convert_batch() przetwarza wszystkie pliki i zwraca wyniki."""
        pdfs = []
        for i in range(3):
            p = tmp_path / f"doc{i}.pdf"
            p.write_bytes(b"fake pdf")
            pdfs.append(str(p))
        engine = _make_engine()

        results = Converter().convert_batch(pdfs, engine)

        assert len(results) == 3
        assert engine.convert.call_count == 3

    def test_convert_batch_continues_on_error(self, tmp_path: Path) -> None:
        """convert_batch() nie przerywa gdy jeden plik nie istnieje."""
        pdf_ok = tmp_path / "ok.pdf"
        pdf_ok.write_bytes(b"fake pdf")
        engine = _make_engine()

        results = Converter().convert_batch(["/nieistniejacy.pdf", str(pdf_ok)], engine)

        assert len(results) == 2
        # Pierwszy plik — błąd, pusty markdown z ostrzeżeniem
        assert results[0].markdown == ""
        assert len(results[0].warnings) > 0
        # Drugi plik — OK
        assert results[1].markdown != ""
