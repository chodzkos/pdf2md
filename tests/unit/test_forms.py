"""Testy ekstrakcji pól formularzy PDF (F10) — parser, serializery i komenda CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from pdf2md.cli.main import cli
from pdf2md.core.forms import (
    FormField,
    extract_form_fields,
    to_csv,
    to_json,
    to_markdown,
)


def _write_form_pdf(path: Path, fields: list[tuple[str, str]]) -> Path:
    """Buduje PDF z AcroForm — każde pole na osobnej stronie (test wielostronicowości)."""
    from pypdf import PdfWriter
    from pypdf.generic import (
        ArrayObject,
        DictionaryObject,
        NameObject,
        NumberObject,
        TextStringObject,
    )

    writer = PdfWriter()
    refs = []
    for name, value in fields:
        page = writer.add_blank_page(width=300, height=300)
        field = DictionaryObject()
        field[NameObject("/FT")] = NameObject("/Tx")
        field[NameObject("/T")] = TextStringObject(name)
        field[NameObject("/V")] = TextStringObject(value)
        field[NameObject("/Subtype")] = NameObject("/Widget")
        field[NameObject("/Rect")] = ArrayObject([NumberObject(n) for n in (50, 50, 250, 70)])
        ref = writer._add_object(field)
        page[NameObject("/Annots")] = ArrayObject([ref])
        refs.append(ref)
    acro = DictionaryObject()
    acro[NameObject("/Fields")] = ArrayObject(refs)
    writer._root_object[NameObject("/AcroForm")] = acro
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


# ── parser (prawdziwy round-trip pypdf) ──────────────────────────────────────


def test_extract_form_fields_multipage(tmp_path: Path) -> None:
    pdf = _write_form_pdf(tmp_path / "form.pdf", [("imie", "Jan"), ("nazwisko", "Kowalski")])

    fields = extract_form_fields(pdf)

    assert [f.name for f in fields] == ["imie", "nazwisko"]
    assert [f.value for f in fields] == ["Jan", "Kowalski"]
    assert all(f.field_type == "text" for f in fields)


def test_extract_form_fields_no_form(tmp_path: Path) -> None:
    pdf = _plain_pdf(tmp_path / "plain.pdf")
    assert extract_form_fields(pdf) == []


# ── serializery ──────────────────────────────────────────────────────────────

_FIELDS = [FormField("imie", "Jan", "text"), FormField("zgoda", "/Yes", "button")]


def test_to_json_roundtrips() -> None:
    data = json.loads(to_json(_FIELDS))
    assert data == [
        {"name": "imie", "value": "Jan", "field_type": "text"},
        {"name": "zgoda", "value": "/Yes", "field_type": "button"},
    ]


def test_to_csv_has_header_and_rows() -> None:
    lines = to_csv(_FIELDS).splitlines()
    assert lines[0] == "name,value,type"
    assert lines[1] == "imie,Jan,text"
    assert lines[2] == "zgoda,/Yes,button"


def test_to_markdown_table_and_escaping() -> None:
    md = to_markdown([FormField("a|b", "x\ny", "text")])
    assert md.startswith("| Pole | Wartość | Typ |\n| --- | --- | --- |\n")
    # pionowa kreska w treści jest zescapowana, nowa linia zamieniona na spację
    assert "| a\\|b | x y | text |" in md


# ── komenda CLI ──────────────────────────────────────────────────────────────


@pytest.fixture()
def cli_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    from pdf2md.core import config

    config_dir = tmp_path / "config"
    monkeypatch.setattr(config, "_CONFIG_DIR", config_dir)
    monkeypatch.setattr(config, "_CONFIG_FILE", config_dir / "config.toml")
    monkeypatch.setattr(config, "_settings_cache", None)
    monkeypatch.setattr("pdf2md.cli.main.setup_logging", lambda verbose=False: None)
    return tmp_path


def test_forms_cli_json_to_stdout(cli_env: Path) -> None:
    pdf = _write_form_pdf(cli_env / "form.pdf", [("imie", "Jan")])

    result = CliRunner().invoke(cli, ["forms", str(pdf), "--format", "json"])

    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == [{"name": "imie", "value": "Jan", "field_type": "text"}]


def test_forms_cli_writes_output_file(cli_env: Path) -> None:
    pdf = _write_form_pdf(cli_env / "form.pdf", [("imie", "Jan"), ("nazwisko", "Kowalski")])
    out = cli_env / "out.csv"

    result = CliRunner().invoke(cli, ["forms", str(pdf), "--format", "csv", "--output", str(out)])

    assert result.exit_code == 0, result.output
    rows = out.read_text(encoding="utf-8").splitlines()
    assert rows[0] == "name,value,type"
    assert "imie,Jan,text" in rows


def test_forms_cli_no_fields_exits_cleanly(cli_env: Path) -> None:
    pdf = _plain_pdf(cli_env / "plain.pdf")

    result = CliRunner().invoke(cli, ["forms", str(pdf)])

    assert result.exit_code == 0
    assert "Brak pól formularza" in result.output


def test_forms_cli_rejects_non_pdf(cli_env: Path) -> None:
    txt = cli_env / "plik.txt"
    txt.write_text("nie pdf", encoding="utf-8")

    result = CliRunner().invoke(cli, ["forms", str(txt)])

    assert result.exit_code != 0
    assert "tylko pliki PDF" in result.output


def test_forms_cli_missing_file(cli_env: Path) -> None:
    result = CliRunner().invoke(cli, ["forms", str(cli_env / "nie_ma.pdf")])

    assert result.exit_code != 0
    assert "Plik nie istnieje" in result.output
