"""Testy zbierania haseł do zaszyfrowanych PDF w GUI (F12) — logika bez realnego dialogu."""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)

from pdf2md.gui import main_window as mw

pytestmark = pytest.mark.gui


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


def _scripted_prompt(answers: list[str | None]) -> tuple[Callable[[str, bool], str | None], list]:
    calls: list[tuple[str, bool]] = []
    iterator = iter(answers)

    def prompt(name: str, wrong: bool) -> str | None:
        calls.append((name, wrong))
        return next(iterator)

    return prompt, calls


def test_collect_passwords_correct_first_try(tmp_path: Path) -> None:
    enc = _encrypted_pdf(tmp_path / "enc.pdf", "haslo")
    prompt, calls = _scripted_prompt(["haslo"])

    result = mw._collect_pdf_passwords([str(enc)], prompt)

    assert result == {str(enc): "haslo"}
    assert calls == [("enc.pdf", False)]


def test_collect_passwords_retries_on_wrong(tmp_path: Path) -> None:
    enc = _encrypted_pdf(tmp_path / "enc.pdf", "haslo")
    prompt, calls = _scripted_prompt(["zle", "haslo"])

    result = mw._collect_pdf_passwords([str(enc)], prompt)

    assert result == {str(enc): "haslo"}
    assert calls == [("enc.pdf", False), ("enc.pdf", True)]  # druga próba z wrong=True


def test_collect_passwords_cancel_returns_none(tmp_path: Path) -> None:
    enc = _encrypted_pdf(tmp_path / "enc.pdf", "haslo")
    prompt, _calls = _scripted_prompt([None])

    assert mw._collect_pdf_passwords([str(enc)], prompt) is None


def test_collect_passwords_skips_plain_pdf(tmp_path: Path) -> None:
    plain = _plain_pdf(tmp_path / "plain.pdf")

    def prompt(name: str, wrong: bool) -> str | None:  # nie powinno zostać wywołane
        raise AssertionError("prompt nie powinien być wołany dla nieszyfrowanego PDF")

    assert mw._collect_pdf_passwords([str(plain)], prompt) == {}
