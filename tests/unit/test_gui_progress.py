"""Testy monotonicznego postępu batcha (B11): sygnał workera i etykieta paska.

Sygnał `progress` niesie (nazwa_pliku, indeks_1based, procent_batcha) i jest monotoniczny —
nie miesza już procentu per-plik z procentem batcha (pasek nie skacze 100→33).
"""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)

from PySide6.QtWidgets import QApplication, QProgressBar

from pdf2md.engines.base import ConversionResult
from pdf2md.gui.main_window import MainWindow
from pdf2md.gui.workers import ConversionWorker

pytestmark = pytest.mark.gui


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    try:
        return QApplication.instance() or QApplication([])
    except Exception as exc:  # pragma: no cover - środowisko bez Qt
        pytest.skip(f"Qt niedostępne: {exc}")


class _OkConverter:
    def convert(self, *args: object, **kwargs: object) -> ConversionResult:
        return ConversionResult(markdown="# x", engine_used="FakeOCR", pages=1)


class _BoomConverter:
    def convert(self, *args: object, **kwargs: object) -> ConversionResult:
        raise RuntimeError("boom")


def _run(worker: ConversionWorker, converter: object) -> list[tuple[str, int, int]]:
    events: list[tuple[str, int, int]] = []
    worker.progress.connect(lambda name, idx, pct: events.append((name, idx, pct)))
    engine = SimpleNamespace(name="FakeOCR", supports_ocr=False)
    worker._convert_all(converter, engine, None)
    return events


def test_progress_is_monotonic_for_two_files(qapp: QApplication, tmp_path: Path) -> None:
    """Dwa pliki → procent batcha rośnie monotonicznie (0…50…100), bez per-plikowego 100 w środku."""
    files = []
    for name in ("a.pdf", "b.pdf"):
        path = tmp_path / name
        path.write_bytes(b"%PDF-1.7\n")
        files.append(str(path))
    worker = ConversionWorker(files=files, engine_name="FakeOCR", output_dir=str(tmp_path / "out"))

    events = _run(worker, _OkConverter())

    percents = [pct for _, _, pct in events]
    assert percents == sorted(percents)  # monotoniczny, bez skoków w tył
    assert percents[0] == 0
    assert percents[-1] == 100
    assert 100 not in percents[:-1]  # brak per-plikowego 100 przed końcem batcha
    assert {idx for _, idx, _ in events} == {1, 2}  # indeksy 1-based
    file1_end = max(pct for _, idx, pct in events if idx == 1)
    file2_start = min(pct for _, idx, pct in events if idx == 2)
    assert file2_start >= file1_end  # start pliku 2 nie cofa paska


def test_progress_reaches_100_even_on_error(qapp: QApplication, tmp_path: Path) -> None:
    """Błąd pliku też domyka batch (100%) — koniec pliku emituje procent i przy błędzie."""
    path = tmp_path / "bad.pdf"
    path.write_bytes(b"%PDF-1.7\n")
    worker = ConversionWorker(
        files=[str(path)], engine_name="FakeOCR", output_dir=str(tmp_path / "out")
    )

    events = _run(worker, _BoomConverter())

    percents = [pct for _, _, pct in events]
    assert percents[-1] == 100


def test_on_progress_label_shows_index_and_total(qapp: QApplication) -> None:
    """Slot GUI formatuje etykietę paska jako [indeks/total] nazwa procent%."""
    bar = QProgressBar()
    window = SimpleNamespace(_progress=bar, _batch_total=3)

    MainWindow._on_progress(window, "doc.pdf", 2, 66)

    assert bar.value() == 66
    assert bar.format() == "[2/3] doc.pdf  66%"
