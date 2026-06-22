"""Test kooperatywnego anulowania konwersji w GUI (ConversionWorker).

Sprawdza, że żądanie przerwania zatrzymuje pętlę na granicy STRONY (w VLMEngine.convert),
bieżący plik nie jest liczony jako ukończony, silnik zwalnia zasoby (unload_model) i worker
emituje `cancelled`. Bez realnego GPU/modelu — `_ocr_page` jest atrapą.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6.QtWidgets")
pytest.importorskip("pymupdf")

from PySide6.QtWidgets import QApplication

from pdf2md.core.converter import Converter
from pdf2md.engines.vlm_base import VLMEngine
from pdf2md.gui.workers import ConversionWorker

pytestmark = pytest.mark.gui


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    try:
        return QApplication.instance() or QApplication([])
    except Exception as exc:  # pragma: no cover - środowisko bez Qt
        pytest.skip(f"Qt niedostępne: {exc}")


class _FakeVLMEngine(VLMEngine):
    """Atrapa silnika VLM: bez modelu/GPU; liczy strony i wywołania unload."""

    name = "CancelTest"
    package_name = "x"

    def __init__(self) -> None:
        super().__init__()
        self.pages_done = 0
        self.unloaded = 0

    def is_available(self) -> bool:
        return True

    def load_model(self) -> None:
        return None

    def unload_model(self) -> None:
        self.unloaded += 1

    def _ocr_page(self, image_path: str) -> str:
        self.pages_done += 1
        return "tekst strony"


def _multipage_pdf(tmp_path: Path) -> Path:
    import pymupdf

    pdf = tmp_path / "multi.pdf"
    doc = pymupdf.open()
    for _ in range(3):
        doc.new_page()
    doc.save(str(pdf))
    doc.close()
    return pdf


def test_cancel_stops_on_page_boundary_and_releases(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Anulowanie zatrzymuje na granicy strony; plik niekompletny; unload wołany; sygnał cancelled."""
    pdf = _multipage_pdf(tmp_path)
    engine = _FakeVLMEngine()
    worker = ConversionWorker(
        files=[str(pdf)], engine_name="CancelTest", output_dir=str(tmp_path / "out")
    )

    # isInterruptionRequested: False (granica pliku), False (strona 1), True (strona 2 → cancel)
    calls = {"n": 0}

    def fake_interrupt() -> bool:
        calls["n"] += 1
        return calls["n"] > 2

    monkeypatch.setattr(worker, "isInterruptionRequested", fake_interrupt)

    cancelled: list[tuple[int, int, float]] = []
    done: list[tuple[int, int, float]] = []
    worker.cancelled.connect(lambda s, e, t: cancelled.append((s, e, t)))
    worker.all_done.connect(lambda s, e, t: done.append((s, e, t)))

    # wywołanie synchroniczne (bez startowania wątku) — sygnały lecą natychmiast
    worker._convert_all(Converter(), engine, None)

    assert engine.pages_done == 1  # zatrzymano po 1. stronie (check przed stroną 2.)
    assert engine.unloaded >= 1  # VLMEngine.convert zwolnił zasoby w finally
    assert cancelled and cancelled[0][0] == 0  # 0 ukończonych plików (bieżący niekompletny)
    assert not done  # NIE wyemitowano all_done


def test_no_cancel_completes_normally(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bez żądania przerwania konwersja kończy się normalnie (all_done, wszystkie strony)."""
    pdf = _multipage_pdf(tmp_path)
    engine = _FakeVLMEngine()
    worker = ConversionWorker(
        files=[str(pdf)], engine_name="CancelTest", output_dir=str(tmp_path / "out")
    )
    monkeypatch.setattr(worker, "isInterruptionRequested", lambda: False)

    done: list[tuple[int, int, float]] = []
    cancelled: list[tuple[int, int, float]] = []
    worker.all_done.connect(lambda s, e, t: done.append((s, e, t)))
    worker.cancelled.connect(lambda s, e, t: cancelled.append((s, e, t)))

    worker._convert_all(Converter(), engine, None)

    assert engine.pages_done == 3  # wszystkie strony
    assert done and done[0][0] == 1  # 1 ukończony plik
    assert not cancelled
