"""Ekstrakcja pól formularzy PDF (AcroForm) do JSON / CSV / Markdown.

Warstwa niezależna od CLI: czyta pola przez ``pypdf`` i serializuje do trzech
formatów. `pypdf.PdfReader.get_fields()` agreguje pola z całego dokumentu
(także wielostronicowego), więc obsługa wielu stron jest darmowa.
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict, dataclass
from pathlib import Path

#: Mapowanie surowych typów pól PDF (/FT) na czytelne etykiety.
_FIELD_TYPE_LABELS = {
    "/Tx": "text",
    "/Btn": "button",
    "/Ch": "choice",
    "/Sig": "signature",
}


@dataclass
class FormField:
    """Pojedyncze pole formularza PDF."""

    name: str
    value: str
    field_type: str


def _label_type(raw: object) -> str:
    if raw is None:
        return ""
    return _FIELD_TYPE_LABELS.get(str(raw), str(raw))


def _stringify(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def extract_form_fields(pdf_path: str | Path) -> list[FormField]:
    """Zwraca pola formularza PDF w kolejności dokumentu.

    Brak warstwy AcroForm (PDF bez pól) → pusta lista. Wielostronicowe formularze
    obsługiwane są przez ``get_fields()``, które zbiera pola z całego dokumentu.
    """
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    fields = reader.get_fields()
    if not fields:
        return []
    return [
        FormField(
            name=str(name),
            value=_stringify(getattr(field, "value", None)),
            field_type=_label_type(getattr(field, "field_type", None)),
        )
        for name, field in fields.items()
    ]


def to_json(fields: list[FormField]) -> str:
    """Serializuje pola do JSON (lista obiektów name/value/field_type)."""
    return json.dumps([asdict(field) for field in fields], ensure_ascii=False, indent=2)


def to_csv(fields: list[FormField]) -> str:
    """Serializuje pola do CSV z nagłówkiem ``name,value,type``."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["name", "value", "type"])
    for field in fields:
        writer.writerow([field.name, field.value, field.field_type])
    return buffer.getvalue()


def _md_escape(text: str) -> str:
    """Chroni komórkę tabeli Markdown: `|` i nowe linie łamią tabelę."""
    return (
        text.replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("\r\n", " ")
        .replace("\n", " ")
        .replace("\r", " ")
    )


def to_markdown(fields: list[FormField]) -> str:
    """Serializuje pola do tabeli Markdown (`Pole | Wartość | Typ`)."""
    lines = ["| Pole | Wartość | Typ |", "| --- | --- | --- |"]
    for field in fields:
        lines.append(
            f"| {_md_escape(field.name)} | {_md_escape(field.value)} | {_md_escape(field.field_type)} |"
        )
    return "\n".join(lines) + "\n"


def render(fields: list[FormField], output_format: str) -> str:
    """Renderuje pola w wybranym formacie: ``md`` / ``json`` / ``csv``."""
    renderers = {"md": to_markdown, "json": to_json, "csv": to_csv}
    return renderers[output_format](fields)
