"""Lekkie testy adaptera Marker bez uruchamiania modeli."""

from __future__ import annotations

import importlib.metadata
from types import SimpleNamespace
from typing import Any

import pytest

from pdf2md.engines.marker_engine import MarkerEngine


def test_is_available_true_when_marker_package_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    """is_available() sprawdza metadane pakietu bez importu Markera."""

    def fake_version(package_name: str) -> str:
        assert package_name == "marker-pdf"
        return "1.10.2"

    monkeypatch.setattr(importlib.metadata, "version", fake_version)

    assert MarkerEngine().is_available() is True


def test_is_available_false_when_marker_package_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Brak marker-pdf zwraca False zamiast importować ciężki pakiet."""

    def fake_version(package_name: str) -> str:
        assert package_name == "marker-pdf"
        raise importlib.metadata.PackageNotFoundError

    monkeypatch.setattr(importlib.metadata, "version", fake_version)

    assert MarkerEngine().is_available() is False


def test_convert_uses_marker_api_without_loading_real_models(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """convert() skleja ConfigParser, PdfConverter i text_from_rendered."""
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")
    captured: dict[str, Any] = {}

    class FakeConfigParser:
        def __init__(self, config: dict[str, object]) -> None:
            captured["config"] = config

        def generate_config_dict(self) -> dict[str, object]:
            return {"generated": True}

        def get_processors(self) -> list[object]:
            return ["processor"]

        def get_renderer(self) -> str:
            return "renderer"

        def get_llm_service(self) -> None:
            return None

    class FakePdfConverter:
        def __init__(self, **kwargs: object) -> None:
            captured["converter_kwargs"] = kwargs

        def __call__(self, path: str) -> object:
            captured["path"] = path
            return type("Rendered", (), {"metadata": {"title": "Doc"}})()

    def fake_create_model_dict() -> dict[str, object]:
        return {"model": "fake"}

    def fake_text_from_rendered(
        rendered: object,
    ) -> tuple[str, dict[str, object], dict[str, object]]:
        captured["rendered"] = rendered
        return "# Marker\n\nText", {}, {}

    class FakeDoc:
        def __len__(self) -> int:
            return 2

        def close(self) -> None:
            captured["closed"] = True

    class FakePymupdf:
        @staticmethod
        def open(path: str) -> FakeDoc:
            captured["opened"] = path
            return FakeDoc()

    def fake_import_module(name: str) -> object:
        assert name == "pymupdf"
        return FakePymupdf

    engine = MarkerEngine()
    monkeypatch.setattr(engine, "is_available", lambda: True)
    monkeypatch.setattr(engine, "_configure_torch_device", lambda torch_device: None)
    monkeypatch.setattr(engine, "_configure_worker_env", lambda workers: None)
    monkeypatch.setattr(
        "pdf2md.engines.marker_engine.get_settings",
        lambda: SimpleNamespace(marker_device="cpu", marker_workers=1, marker_max_pages=1),
    )
    monkeypatch.setattr(
        engine,
        "_load_marker_api",
        lambda: (
            FakeConfigParser,
            FakePdfConverter,
            fake_create_model_dict,
            fake_text_from_rendered,
        ),
    )
    monkeypatch.setattr("pdf2md.engines.marker_engine.importlib.import_module", fake_import_module)

    result = engine.convert(str(pdf), use_llm=True, lang="pl,en", page_range="0")

    assert result.markdown == "# Marker\n\nText"
    assert result.engine_used == "Marker"
    assert result.pages == 2
    assert result.metadata == {"title": "Doc"}
    assert captured["config"] == {
        "output_format": "markdown",
        "use_llm": True,
        "languages": "pl,en",
        "page_range": "0",
        "disable_multiprocessing": True,
        "pdftext_workers": 1,
    }
    assert captured["converter_kwargs"] == {
        "config": {"generated": True},
        "artifact_dict": {"model": "fake"},
        "processor_list": ["processor"],
        "renderer": "renderer",
        "llm_service": None,
    }
    assert captured["path"] == str(pdf)
    assert captured["opened"] == str(pdf)
    assert captured["closed"] is True


def test_convert_raises_when_marker_unavailable(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """Brak Markera daje czytelny błąd instalacji."""
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")

    engine = MarkerEngine()
    monkeypatch.setattr(engine, "is_available", lambda: False)

    with pytest.raises(RuntimeError, match="uv sync --extra engines-core"):
        engine.convert(str(pdf))
