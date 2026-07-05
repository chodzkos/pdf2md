"""Testy GUI dla per-sesyjnej ekstrakcji obrazów."""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtWidgets import QApplication, QCheckBox

from pdf2md.core.image_extraction import ExtractedImage
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


def test_extract_images_checkbox_disabled_for_in_place_engines(qapp: QApplication) -> None:
    checkbox = QCheckBox()
    window = SimpleNamespace(_extract_images=checkbox)

    MainWindow._sync_extract_images_enabled(window, "Marker")
    assert checkbox.isEnabled() is False
    assert "in-place" in checkbox.toolTip()

    MainWindow._sync_extract_images_enabled(window, "Docling")
    assert checkbox.isEnabled() is False
    assert "in-place" in checkbox.toolTip()


def test_extract_images_checkbox_enabled_for_ocr_engines(qapp: QApplication) -> None:
    checkbox = QCheckBox()
    window = SimpleNamespace(_extract_images=checkbox)

    MainWindow._sync_extract_images_enabled(window, "PaddleOCR-VL")

    assert checkbox.isEnabled() is True
    assert "Surya" in checkbox.toolTip()


class _FakeConverter:
    def convert(self, *args: object, **kwargs: object) -> ConversionResult:
        return ConversionResult(markdown="# wynik\n", engine_used="FakeOCR", pages=1)


def test_worker_extracts_images_for_ocr_engine(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")
    output_dir = tmp_path / "out"
    calls: list[tuple[str | Path, Path, int]] = []

    def fake_extract(
        pdf_path: str | Path, output_path: Path, *, min_size: int
    ) -> list[ExtractedImage]:
        calls.append((pdf_path, output_path, min_size))
        return [
            ExtractedImage(
                path=output_path / "page1_img1.png",
                page=1,
                index=1,
                width=120,
                height=120,
            )
        ]

    monkeypatch.setattr("pdf2md.gui.workers.extract_pdf_images", fake_extract)
    worker = ConversionWorker(
        files=[str(pdf)],
        engine_name="FakeOCR",
        output_dir=str(output_dir),
        extract_images=True,
    )
    done: list[tuple[str, str, float]] = []
    errors: list[tuple[str, str]] = []
    worker.file_done.connect(lambda path, out, elapsed: done.append((path, out, elapsed)))
    worker.file_error.connect(lambda path, error: errors.append((path, error)))

    engine = SimpleNamespace(name="PaddleOCR-VL", supports_ocr=True)
    worker._convert_all(_FakeConverter(), engine, None)

    output_path = output_dir / "doc.md"
    assert calls == [(str(pdf), output_dir / "doc_images", 100)]
    assert "![](<doc_images/page1_img1.png>)" in output_path.read_text(encoding="utf-8")
    assert len(done) == 1
    assert not errors


@pytest.mark.parametrize("engine_name", ["Marker", "Docling"])
def test_worker_skips_extract_images_for_in_place_engines(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, engine_name: str
) -> None:
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")

    def fail_extract(*args: object, **kwargs: object) -> list[ExtractedImage]:
        raise AssertionError("extract_pdf_images should not be called")

    monkeypatch.setattr("pdf2md.gui.workers.extract_pdf_images", fail_extract)
    worker = ConversionWorker(
        files=[str(pdf)],
        engine_name=engine_name,
        output_dir=str(tmp_path / "out"),
        extract_images=True,
    )
    errors: list[tuple[str, str]] = []
    worker.file_error.connect(lambda path, error: errors.append((path, error)))

    engine = SimpleNamespace(name=engine_name, supports_ocr=True)
    worker._convert_all(_FakeConverter(), engine, None)

    assert not errors


def test_worker_skips_extract_images_for_image_inputs(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    image = tmp_path / "doc.png"
    image.write_bytes(b"png")

    def fail_extract(*args: object, **kwargs: object) -> list[ExtractedImage]:
        raise AssertionError("extract_pdf_images should not be called for image inputs")

    monkeypatch.setattr("pdf2md.gui.workers.extract_pdf_images", fail_extract)
    worker = ConversionWorker(
        files=[str(image)],
        engine_name="FakeOCR",
        output_dir=str(tmp_path / "out"),
        extract_images=True,
    )
    errors: list[tuple[str, str]] = []
    worker.file_error.connect(lambda path, error: errors.append((path, error)))

    engine = SimpleNamespace(name="Surya", supports_ocr=True)
    worker._convert_all(_FakeConverter(), engine, None)

    assert not errors


def test_worker_reports_extract_images_error(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")

    def fake_extract(*args: object, **kwargs: object) -> list[ExtractedImage]:
        raise RuntimeError("Ekstrakcja obrazów wymaga: pip install 'pdf2md[images]'")

    monkeypatch.setattr("pdf2md.gui.workers.extract_pdf_images", fake_extract)
    worker = ConversionWorker(
        files=[str(pdf)],
        engine_name="FakeOCR",
        output_dir=str(tmp_path / "out"),
        extract_images=True,
    )
    errors: list[tuple[str, str]] = []
    done: list[tuple[str, str, float]] = []
    worker.file_error.connect(lambda path, error: errors.append((path, error)))
    worker.file_done.connect(lambda path, out, elapsed: done.append((path, out, elapsed)))

    engine = SimpleNamespace(name="Surya", supports_ocr=True)
    worker._convert_all(_FakeConverter(), engine, None)

    assert len(errors) == 1
    assert "pip install 'pdf2md[images]'" in errors[0][1]
    assert not done
