"""Testy slotu GUI obsługującego zakończony plik."""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)

from PySide6.QtWidgets import QApplication

from pdf2md.engines.base import ConversionResult
from pdf2md.gui import main_window as mw
from pdf2md.gui.main_window import MainWindow
from pdf2md.gui.workers import ConversionWorker
from pdf2md.scan import profiles

pytestmark = pytest.mark.gui


class _SignalStub:
    def connect(self, _callback: Callable[[object], None]) -> None:
        return None


class _ThemeManagerStub:
    setting = "auto"
    theme_changed = _SignalStub()

    def attach_titlebar(self, _window: object) -> None:
        return None


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    try:
        return QApplication.instance() or QApplication([])
    except Exception as exc:  # pragma: no cover - środowisko bez Qt
        pytest.skip(f"Qt niedostępne: {exc}")


@pytest.fixture()
def window(qapp: QApplication, monkeypatch: pytest.MonkeyPatch) -> MainWindow:
    monkeypatch.setattr(
        mw,
        "get_settings",
        lambda: SimpleNamespace(
            default_engine="pymupdf4llm",
            default_output_dir="",
            default_language="pol+eng",
        ),
    )
    main_window = MainWindow(_ThemeManagerStub())
    try:
        yield main_window
    finally:
        main_window.deleteLater()


def test_on_file_done_ignores_empty_output_path(window: MainWindow) -> None:
    window._on_file_done("in.pdf", "", 1.0)

    assert window._last_markdown_outputs == []


def test_on_file_done_previews_real_markdown_file(window: MainWindow, tmp_path: Path) -> None:
    output = tmp_path / "out.md"
    output.write_text("# Wynik", encoding="utf-8")

    window._on_file_done("in.pdf", str(output), 1.0)

    assert window._last_markdown_outputs == [output]
    assert window._preview.toPlainText() == "# Wynik"
    assert window._tabs.currentWidget() is window._preview


class _FakeScanConverter:
    def __init__(self, book_md_path: Path | None) -> None:
        self._book_md_path = book_md_path

    def convert(self, *args: object, **kwargs: object) -> ConversionResult:
        assert kwargs["output_path"] is None
        engine_kwargs = kwargs["engine_kwargs"]
        assert isinstance(engine_kwargs, dict)
        assert engine_kwargs["output_dir"]
        metadata: dict[str, object] = {}
        if self._book_md_path is not None:
            metadata["book_md_path"] = str(self._book_md_path)
        return ConversionResult(
            markdown="# Book",
            engine_used="Scan Pipeline",
            pages=1,
            metadata=metadata,
        )


def test_scan_pipeline_file_done_emits_book_markdown_path(
    qapp: QApplication,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pdf = tmp_path / "scan.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")
    output_dir = tmp_path / "out"
    book_md = output_dir / "book.md"
    book_md.parent.mkdir(parents=True)
    book_md.write_text("# Book", encoding="utf-8")
    monkeypatch.setattr(
        profiles,
        "load_profile",
        lambda _name: SimpleNamespace(model_dump=lambda: {}),
    )
    worker = ConversionWorker(
        files=[str(pdf)],
        engine_name="Scan Pipeline",
        output_dir=str(output_dir),
        scan_profile="balanced",
    )
    done: list[tuple[str, str, float]] = []
    worker.file_done.connect(lambda src, dst, elapsed: done.append((src, dst, elapsed)))

    engine = SimpleNamespace(name="Scan Pipeline", supports_ocr=False)
    worker._convert_all(_FakeScanConverter(book_md), engine, None)

    assert len(done) == 1
    assert done[0][0] == str(pdf)
    assert done[0][1] == str(book_md)


def test_scan_pipeline_file_done_falls_back_to_empty_path_without_book_file(
    qapp: QApplication,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pdf = tmp_path / "scan.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")
    monkeypatch.setattr(
        profiles,
        "load_profile",
        lambda _name: SimpleNamespace(model_dump=lambda: {}),
    )
    worker = ConversionWorker(
        files=[str(pdf)],
        engine_name="Scan Pipeline",
        output_dir=str(tmp_path / "out"),
        scan_profile="balanced",
    )
    done: list[tuple[str, str, float]] = []
    worker.file_done.connect(lambda src, dst, elapsed: done.append((src, dst, elapsed)))

    engine = SimpleNamespace(name="Scan Pipeline", supports_ocr=False)
    worker._convert_all(_FakeScanConverter(None), engine, None)

    assert len(done) == 1
    assert done[0][1] == ""
