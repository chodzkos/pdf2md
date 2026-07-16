"""Testy obsługi zaszyfrowanych PDF (F12) — rdzeń, integracja Converter i CLI."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from click.testing import CliRunner

from pdf2md.cli.main import cli
from pdf2md.core.converter import ConversionError, Converter
from pdf2md.core.encryption import (
    PdfPasswordError,
    decrypt_pdf,
    is_pdf_encrypted,
    verify_pdf_password,
)
from pdf2md.engines.base import ConversionEngine, ConversionResult


def _encrypted_pdf(path: Path, password: str) -> Path:
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.encrypt(password)
    with path.open("wb") as handle:
        writer.write(handle)
    return path


def _plain_pdf(path: Path) -> Path:
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    with path.open("wb") as handle:
        writer.write(handle)
    return path


# ── rdzeń ────────────────────────────────────────────────────────────────────


def test_is_pdf_encrypted(tmp_path: Path) -> None:
    assert is_pdf_encrypted(_encrypted_pdf(tmp_path / "enc.pdf", "haslo")) is True
    assert is_pdf_encrypted(_plain_pdf(tmp_path / "plain.pdf")) is False


def test_is_pdf_encrypted_corrupt_returns_false(tmp_path: Path) -> None:
    junk = tmp_path / "junk.pdf"
    junk.write_bytes(b"nie jest pdf")
    assert is_pdf_encrypted(junk) is False


def test_verify_pdf_password(tmp_path: Path) -> None:
    enc = _encrypted_pdf(tmp_path / "enc.pdf", "haslo")
    assert verify_pdf_password(enc, "haslo") is True
    assert verify_pdf_password(enc, "zle") is False
    assert verify_pdf_password(_plain_pdf(tmp_path / "plain.pdf"), "cokolwiek") is True


def test_decrypt_pdf_good_password(tmp_path: Path) -> None:
    enc = _encrypted_pdf(tmp_path / "enc.pdf", "haslo")
    out = decrypt_pdf(enc, "haslo", tmp_path / "dec")

    assert out.exists()
    assert out != enc
    assert is_pdf_encrypted(out) is False


def test_decrypt_pdf_missing_password(tmp_path: Path) -> None:
    enc = _encrypted_pdf(tmp_path / "enc.pdf", "haslo")
    with pytest.raises(PdfPasswordError):
        decrypt_pdf(enc, "", tmp_path / "dec")


def test_decrypt_pdf_wrong_password(tmp_path: Path) -> None:
    enc = _encrypted_pdf(tmp_path / "enc.pdf", "haslo")
    with pytest.raises(PdfPasswordError):
        decrypt_pdf(enc, "zle", tmp_path / "dec")


def test_decrypt_pdf_plain_returns_source(tmp_path: Path) -> None:
    plain = _plain_pdf(tmp_path / "plain.pdf")
    assert decrypt_pdf(plain, "", tmp_path / "dec") == plain


# ── integracja z Converter ───────────────────────────────────────────────────


class _FakeEngine(ConversionEngine):
    name = "Fake"
    description = "atrapa"
    supports_ocr = False
    supports_llm = False
    requires_gpu = False

    def __init__(self) -> None:
        self.seen_path: str | None = None

    def is_available(self) -> bool:
        return True

    def convert(self, pdf_path: str, **kwargs: object) -> ConversionResult:
        self.seen_path = pdf_path
        # silnik dostaje odszyfrowany plik — nie może być już zaszyfrowany
        assert is_pdf_encrypted(pdf_path) is False
        return ConversionResult(markdown="# ok", engine_used=self.name, pages=1)


def test_converter_decrypts_with_password(tmp_path: Path) -> None:
    enc = _encrypted_pdf(tmp_path / "enc.pdf", "haslo")
    engine = _FakeEngine()

    result = Converter().convert(str(enc), engine, password="haslo", record_history=False)

    assert result.markdown == "# ok"
    assert engine.seen_path is not None
    assert engine.seen_path != str(enc)  # dostał odszyfrowany temp, nie oryginał


def test_converter_missing_password_raises(tmp_path: Path) -> None:
    enc = _encrypted_pdf(tmp_path / "enc.pdf", "haslo")
    with pytest.raises(ConversionError):
        Converter().convert(str(enc), _FakeEngine(), record_history=False)


def test_converter_wrong_password_raises(tmp_path: Path) -> None:
    enc = _encrypted_pdf(tmp_path / "enc.pdf", "haslo")
    with pytest.raises(ConversionError):
        Converter().convert(str(enc), _FakeEngine(), password="zle", record_history=False)


# ── komenda CLI ──────────────────────────────────────────────────────────────


@pytest.fixture()
def cli_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    from pdf2md.core import config

    config_dir = tmp_path / "config"
    monkeypatch.setattr(config, "_CONFIG_DIR", config_dir)
    monkeypatch.setattr(config, "_CONFIG_FILE", config_dir / "config.toml")
    monkeypatch.setattr(config, "_settings_cache", None)
    monkeypatch.setattr("pdf2md.cli.main.setup_logging", lambda verbose=False: None)
    monkeypatch.setattr(
        "pdf2md.llm.ollama_provider.OllamaProvider.is_available", lambda self: False
    )
    return tmp_path


def test_convert_encrypted_without_password_errors(cli_env: Path) -> None:
    enc = _encrypted_pdf(cli_env / "enc.pdf", "haslo")

    result = CliRunner().invoke(cli, ["convert", str(enc), "--engine", "pymupdf4llm"])

    assert result.exit_code != 0
    assert "zaszyfrowany" in result.output.lower()
    assert "--password" in result.output


def test_convert_encrypted_with_password(cli_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    enc = _encrypted_pdf(cli_env / "enc.pdf", "haslo")
    out_dir = cli_env / "out"
    seen: dict[str, object] = {}
    fake_engine = SimpleNamespace(name="Fake", supports_ocr=False, is_available=lambda: True)

    class FakeConverter:
        def convert(self, *args: object, **kwargs: object) -> ConversionResult:
            seen["password"] = kwargs.get("password")
            return ConversionResult(markdown="# ok", engine_used="Fake", pages=1)

    def fake_export(markdown: str, output_path: Path, epub_backend: str = "pandoc") -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown, encoding="utf-8")
        return output_path

    monkeypatch.setattr("pdf2md.cli.main._select_engine", lambda name: fake_engine)
    monkeypatch.setattr("pdf2md.cli.main.Converter", FakeConverter)
    monkeypatch.setattr("pdf2md.cli.main._export_result", fake_export)

    result = CliRunner().invoke(
        cli,
        [
            "convert",
            str(enc),
            "--engine",
            "fake",
            "--output-dir",
            str(out_dir),
            "--password",
            "haslo",
        ],
    )

    assert result.exit_code == 0, result.output
    assert seen["password"] == "haslo"
    assert (out_dir / "enc.md").read_text(encoding="utf-8") == "# ok"
