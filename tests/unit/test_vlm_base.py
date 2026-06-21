"""Testy jednostkowe bazy VLMEngine — bez GPU i bez modeli."""

from __future__ import annotations

from pathlib import Path

import pytest

from pdf2md.engines import vlm_base
from pdf2md.engines.olmocr_engine import OlmOCREngine
from pdf2md.engines.paddleocr_vl_engine import PaddleOCRVLEngine
from pdf2md.engines.surya_engine import SuryaEngine
from pdf2md.engines.vlm_base import VLMEngine


class _FakeVLMEngine(VLMEngine):
    """Podklasa testowa: _ocr_page zwraca numer strony bez ładowania modelu."""

    name = "FakeVLM"
    description = "test"
    package_name = "fake-vlm"

    def __init__(self) -> None:
        super().__init__()
        self.loaded = False
        self.unloaded = False
        self.pages_seen: list[str] = []

    def load_model(self) -> None:
        self.loaded = True

    def unload_model(self) -> None:
        self.unloaded = True
        super().unload_model()

    def _ocr_page(self, image_path: str) -> str:
        self.pages_seen.append(image_path)
        return f"# {Path(image_path).stem}"


def test_has_gpu_false_when_torch_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """has_gpu() zwraca False bez błędu, gdy import torch padnie."""
    import builtins

    real_import = builtins.__import__

    def fake_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "torch":
            raise ImportError("no torch")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert VLMEngine.has_gpu() is False


def test_is_available_false_without_package(monkeypatch: pytest.MonkeyPatch) -> None:
    """Brak pakietu → is_available() False, nawet jeśli GPU jest."""
    monkeypatch.setattr(VLMEngine, "has_gpu", staticmethod(lambda: True))
    engine = _FakeVLMEngine()
    # fake-vlm nie jest zainstalowany
    assert engine.is_available() is False


def test_is_available_false_without_gpu(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pakiet jest, ale brak GPU → is_available() False."""
    monkeypatch.setattr(VLMEngine, "has_gpu", staticmethod(lambda: False))
    monkeypatch.setattr(vlm_base.importlib.metadata, "version", lambda _pkg: "1.0.0")
    engine = _FakeVLMEngine()
    assert engine.is_available() is False


def test_is_available_true_with_package_and_gpu(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pakiet + GPU → is_available() True."""
    monkeypatch.setattr(VLMEngine, "has_gpu", staticmethod(lambda: True))
    monkeypatch.setattr(vlm_base.importlib.metadata, "version", lambda _pkg: "1.0.0")
    engine = _FakeVLMEngine()
    assert engine.is_available() is True


def test_convert_raises_when_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    """convert() na niedostępnym silniku rzuca czytelny błąd."""
    engine = _FakeVLMEngine()
    monkeypatch.setattr(engine, "is_available", lambda: False)
    with pytest.raises(RuntimeError, match="nie jest dostępny"):
        engine.convert("doc.pdf")


def test_convert_batched_pipeline(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """convert() ładuje model, OCR-uje każdą stronę, zwalnia VRAM i usuwa PNG."""
    pymupdf = pytest.importorskip("pymupdf")
    pdf = tmp_path / "scan.pdf"

    doc = pymupdf.open()
    for _ in range(3):
        doc.new_page()
    doc.save(str(pdf))
    doc.close()

    engine = _FakeVLMEngine()
    monkeypatch.setattr(engine, "is_available", lambda: True)

    out_dir = tmp_path / "out"
    result = engine.convert(str(pdf), output_dir=str(out_dir), dpi=72, batch_size=2)

    assert engine.loaded is True
    assert engine.unloaded is True
    assert result.pages == 3
    assert result.engine_used == "FakeVLM"
    # 3 strony Markdown sklejone separatorem
    assert result.markdown.count("---") == 2
    # zapisane pliki md_pages i ocr_json
    assert len(list((out_dir / "md_pages").glob("*.md"))) == 3
    assert len(list((out_dir / "ocr_json").glob("*.json"))) == 3
    # PNG usunięte po przetworzeniu paczek
    assert list((out_dir / "png").glob("*.png")) == []


def test_unload_model_clears_reference() -> None:
    """unload_model() z bazy czyści self._model bez błędu (bez GPU)."""
    engine = _FakeVLMEngine()
    engine._model = object()
    engine.unload_model()
    assert engine._model is None


@pytest.mark.parametrize(
    ("engine_cls", "expected_name", "expected_pkg", "requires_gpu"),
    [
        (OlmOCREngine, "olmOCR", "olmocr", True),
        (PaddleOCRVLEngine, "PaddleOCR-VL", "paddleocr", True),
        (SuryaEngine, "Surya", "surya-ocr", True),
    ],
)
def test_engine_metadata(
    engine_cls: type[VLMEngine],
    expected_name: str,
    expected_pkg: str,
    requires_gpu: bool,
) -> None:
    """Każdy silnik VLM ma poprawne metadane i requires_gpu."""
    engine = engine_cls()
    assert engine.name == expected_name
    assert engine.package_name == expected_pkg
    assert engine.requires_gpu is requires_gpu
    assert engine.supports_ocr is True
    assert engine.supports_llm is False


def test_vlm_engines_not_available_without_gpu(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bez GPU żaden silnik VLM nie jest dostępny (nawet z zainstalowanym pakietem)."""
    monkeypatch.setattr(VLMEngine, "has_gpu", staticmethod(lambda: False))
    for engine_cls in (OlmOCREngine, PaddleOCRVLEngine, SuryaEngine):
        assert engine_cls().is_available() is False
