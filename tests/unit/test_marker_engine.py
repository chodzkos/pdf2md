"""Lekkie testy adaptera Marker bez uruchamiania modeli."""

from __future__ import annotations

import importlib.metadata
import os
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
        lambda: SimpleNamespace(
            marker_device="cpu",
            marker_workers=1,
            marker_max_pages=1,
            marker_torch_device="",
            marker_recognition_batch_size=0,
            marker_detector_batch_size=0,
            marker_layout_batch_size=0,
            marker_table_rec_batch_size=0,
        ),
    )
    monkeypatch.setattr(
        engine,
        "_load_marker_api",
        lambda: (
            FakeConfigParser,
            FakePdfConverter,
            fake_create_model_dict,
            fake_text_from_rendered,
            lambda image: image,
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


def test_convert_saves_marker_inline_images_next_to_output_markdown(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """Obrazy zwrócone przez Markera są zapisywane pod ścieżkami użytymi w Markdown."""
    pil_image: Any = pytest.importorskip("PIL.Image")
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")
    output_path = tmp_path / "out" / "doc.md"
    image = pil_image.new("RGBA", (12, 10), color=(255, 0, 0, 128))
    nested_image = pil_image.new("RGB", (8, 8), color=(0, 255, 0))
    captured: dict[str, Any] = {}

    class FakeConfigParser:
        def __init__(self, config: dict[str, object]) -> None:
            return None

        def generate_config_dict(self) -> dict[str, object]:
            return {}

        def get_processors(self) -> list[object]:
            return []

        def get_renderer(self) -> str:
            return "renderer"

        def get_llm_service(self) -> None:
            return None

    class FakePdfConverter:
        def __init__(self, **kwargs: object) -> None:
            return None

        def __call__(self, path: str) -> object:
            return type("Rendered", (), {"metadata": {}})()

    def fake_text_from_rendered(
        rendered: object,
    ) -> tuple[str, dict[str, object], dict[str, object]]:
        markdown = "![](x.png)\n\n![](sub/y.png)\n"
        return markdown, {}, {"x.png": image, "sub/y.png": nested_image}

    def fake_convert_if_not_rgb(img: Any) -> Any:
        captured.setdefault("converted", []).append(img)
        return img.convert("RGB")

    class FakeDoc:
        def __len__(self) -> int:
            return 1

        def close(self) -> None:
            return None

    class FakePymupdf:
        @staticmethod
        def open(path: str) -> FakeDoc:
            return FakeDoc()

    engine = MarkerEngine()
    monkeypatch.setattr(engine, "is_available", lambda: True)
    monkeypatch.setattr(engine, "_configure_torch_device", lambda torch_device: None)
    monkeypatch.setattr(engine, "_configure_worker_env", lambda workers: None)
    monkeypatch.setattr(
        "pdf2md.engines.marker_engine.get_settings",
        lambda: SimpleNamespace(
            marker_device="cpu",
            marker_workers=1,
            marker_max_pages=1,
            marker_torch_device="",
            marker_recognition_batch_size=0,
            marker_detector_batch_size=0,
            marker_layout_batch_size=0,
            marker_table_rec_batch_size=0,
        ),
    )
    monkeypatch.setattr(
        engine,
        "_load_marker_api",
        lambda: (
            FakeConfigParser,
            FakePdfConverter,
            lambda: {},
            fake_text_from_rendered,
            fake_convert_if_not_rgb,
        ),
    )
    monkeypatch.setattr(
        "pdf2md.engines.marker_engine.importlib.import_module", lambda name: FakePymupdf
    )

    result = engine.convert(str(pdf), output_path=str(output_path))

    assert result.markdown == "![](x.png)\n\n![](sub/y.png)\n"
    assert (tmp_path / "out" / "x.png").is_file()
    assert (tmp_path / "out" / "sub" / "y.png").is_file()
    assert captured["converted"] == [image, nested_image]


def test_convert_raises_when_marker_unavailable(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """Brak Markera daje czytelny błąd instalacji."""
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")

    engine = MarkerEngine()
    monkeypatch.setattr(engine, "is_available", lambda: False)

    with pytest.raises(RuntimeError, match="uv sync --extra engines-core"):
        engine.convert(str(pdf))


def test_convert_falls_back_without_llm_when_service_unavailable(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """use_llm=True bez usługi LLM → ostrzeżenie i konwersja bez post-processingu LLM."""
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")
    captured: dict[str, Any] = {}

    class FakeConfigParser:
        instances = 0

        def __init__(self, config: dict[str, object]) -> None:
            FakeConfigParser.instances += 1
            captured["last_config"] = config

        def generate_config_dict(self) -> dict[str, object]:
            return {"generated": True}

        def get_processors(self) -> list[object]:
            return ["processor"]

        def get_renderer(self) -> str:
            return "renderer"

        def get_llm_service(self) -> object:
            raise RuntimeError("brak skonfigurowanej usługi LLM w tej wersji Markera")

    class FakePdfConverter:
        def __init__(self, **kwargs: object) -> None:
            captured["converter_kwargs"] = kwargs

        def __call__(self, path: str) -> object:
            return type("Rendered", (), {"metadata": {}})()

    def fake_text_from_rendered(
        rendered: object,
    ) -> tuple[str, dict[str, object], dict[str, object]]:
        return "# Marker bez LLM", {}, {}

    class FakeDoc:
        def __len__(self) -> int:
            return 1

        def close(self) -> None:
            return None

    class FakePymupdf:
        @staticmethod
        def open(path: str) -> FakeDoc:
            return FakeDoc()

    engine = MarkerEngine()
    monkeypatch.setattr(engine, "is_available", lambda: True)
    monkeypatch.setattr(engine, "_configure_torch_device", lambda torch_device: None)
    monkeypatch.setattr(engine, "_configure_worker_env", lambda workers: None)
    monkeypatch.setattr(
        "pdf2md.engines.marker_engine.get_settings",
        lambda: SimpleNamespace(
            marker_device="cpu",
            marker_workers=1,
            marker_max_pages=1,
            marker_torch_device="",
            marker_recognition_batch_size=0,
            marker_detector_batch_size=0,
            marker_layout_batch_size=0,
            marker_table_rec_batch_size=0,
        ),
    )
    monkeypatch.setattr(
        engine,
        "_load_marker_api",
        lambda: (
            FakeConfigParser,
            FakePdfConverter,
            lambda: {"model": "fake"},
            fake_text_from_rendered,
            lambda image: image,
        ),
    )
    monkeypatch.setattr(
        "pdf2md.engines.marker_engine.importlib.import_module",
        lambda name: FakePymupdf,
    )

    result = engine.convert(str(pdf), use_llm=True, page_range="0")

    assert result.markdown == "# Marker bez LLM"
    # Po nieudanym get_llm_service konwerter dostaje llm_service=None i nie wybucha.
    assert captured["converter_kwargs"]["llm_service"] is None
    # Config przebudowany bez use_llm w ścieżce fallback.
    assert captured["last_config"]["use_llm"] is False
    assert FakeConfigParser.instances == 2


def _capture_marker_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
    *,
    settings_max_pages: int,
    convert_kwargs: dict[str, Any],
) -> dict[str, Any]:
    """Uruchamia convert() na atrapach i zwraca config przekazany do ConfigParser."""
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")
    captured: dict[str, Any] = {}

    class FakeConfigParser:
        def __init__(self, config: dict[str, object]) -> None:
            captured["config"] = config

        def generate_config_dict(self) -> dict[str, object]:
            return {}

        def get_processors(self) -> list[object]:
            return []

        def get_renderer(self) -> str:
            return "renderer"

        def get_llm_service(self) -> None:
            return None

    class FakePdfConverter:
        def __init__(self, **kwargs: object) -> None:
            pass

        def __call__(self, path: str) -> object:
            return type("Rendered", (), {"metadata": {}})()

    class FakeDoc:
        def __len__(self) -> int:
            return 3

        def close(self) -> None:
            return None

    class FakePymupdf:
        @staticmethod
        def open(path: str) -> FakeDoc:
            return FakeDoc()

    engine = MarkerEngine()
    monkeypatch.setattr(engine, "is_available", lambda: True)
    monkeypatch.setattr(engine, "_configure_torch_device", lambda torch_device: None)
    monkeypatch.setattr(engine, "_configure_worker_env", lambda workers: None)
    monkeypatch.setattr(
        "pdf2md.engines.marker_engine.get_settings",
        lambda: SimpleNamespace(
            marker_device="cpu",
            marker_workers=1,
            marker_max_pages=settings_max_pages,
            marker_torch_device="",
            marker_recognition_batch_size=0,
            marker_detector_batch_size=0,
            marker_layout_batch_size=0,
            marker_table_rec_batch_size=0,
        ),
    )
    monkeypatch.setattr(
        engine,
        "_load_marker_api",
        lambda: (
            FakeConfigParser,
            FakePdfConverter,
            lambda: {},
            lambda r: ("md", {}, {}),
            lambda image: image,
        ),
    )
    monkeypatch.setattr(
        "pdf2md.engines.marker_engine.importlib.import_module", lambda name: FakePymupdf
    )
    engine.convert(str(pdf), **convert_kwargs)
    return captured["config"]


def test_default_converts_whole_document_no_page_range(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    """Domyślnie (marker_max_pages=0) adapter NIE ustawia page_range → cały dokument."""
    config = _capture_marker_config(monkeypatch, tmp_path, settings_max_pages=0, convert_kwargs={})
    assert "page_range" not in config


def test_explicit_max_pages_limits_page_range(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    """Jawny marker_max_pages>0 ogranicza zakres stron (page_range '0-(n-1)')."""
    config = _capture_marker_config(monkeypatch, tmp_path, settings_max_pages=3, convert_kwargs={})
    assert config["page_range"] == "0-2"


def test_marker_helper_methods_parse_limits_and_metadata() -> None:
    engine = MarkerEngine()

    assert engine._limited_page_range(None, 1) == "0"
    assert engine._limited_page_range("", 3) == "0-2"
    assert engine._limited_page_range("0-5,2", 3) == "0,1,2"
    assert engine._limited_page_range(range(5), 2) == "0,1"
    assert engine._limited_page_range({"3", "1"}, 5) == "1,3"
    assert engine._limited_page_range(object(), 2) is not None
    assert engine._coerce_positive_int("0", default=7) == 1
    assert engine._coerce_positive_int("bad", default=7) == 7
    assert engine._coerce_optional_positive_int("3") == 3
    assert engine._coerce_optional_positive_int("-1") is None
    assert engine._extract_metadata(SimpleNamespace(metadata={"a": 1})) == {"a": 1}
    assert engine._extract_metadata(SimpleNamespace(metadata=["bad"])) == {}


def test_configure_gpu_batches_sets_env_for_nonzero_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Niezerowe batch size w configu ustawiają odpowiednie env vars surya przed importem."""
    for key in (
        "RECOGNITION_BATCH_SIZE",
        "DETECTOR_BATCH_SIZE",
        "LAYOUT_BATCH_SIZE",
        "TABLE_REC_BATCH_SIZE",
        "TORCH_DEVICE",
    ):
        monkeypatch.delenv(key, raising=False)

    settings = SimpleNamespace(
        marker_torch_device="cuda",
        marker_recognition_batch_size=64,
        marker_detector_batch_size=32,
        marker_layout_batch_size=16,
        marker_table_rec_batch_size=0,
    )
    MarkerEngine()._configure_gpu_batches(settings)

    assert os.environ["TORCH_DEVICE"] == "cuda"
    assert os.environ["RECOGNITION_BATCH_SIZE"] == "64"
    assert os.environ["DETECTOR_BATCH_SIZE"] == "32"
    assert os.environ["LAYOUT_BATCH_SIZE"] == "16"
    assert "TABLE_REC_BATCH_SIZE" not in os.environ


def test_configure_gpu_batches_respects_existing_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Istniejące env vars nie są nadpisywane (setdefault)."""
    monkeypatch.setenv("RECOGNITION_BATCH_SIZE", "8")

    settings = SimpleNamespace(
        marker_torch_device="",
        marker_recognition_batch_size=128,
        marker_detector_batch_size=0,
        marker_layout_batch_size=0,
        marker_table_rec_batch_size=0,
    )
    MarkerEngine()._configure_gpu_batches(settings)

    assert os.environ["RECOGNITION_BATCH_SIZE"] == "8"  # zachowane, nie nadpisane


def test_configure_worker_env_sets_worker_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PDFTEXT_WORKERS", raising=False)
    monkeypatch.delenv("NUM_WORKERS", raising=False)

    MarkerEngine()._configure_worker_env(2)

    assert os.environ["PDFTEXT_WORKERS"] == "2"
    assert os.environ["NUM_WORKERS"] == "2"


def test_configure_torch_device_respects_existing_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TORCH_DEVICE", "cuda")

    MarkerEngine()._configure_torch_device("cpu")

    assert os.environ["TORCH_DEVICE"] == "cuda"


def test_configure_torch_device_uses_explicit_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TORCH_DEVICE", raising=False)

    MarkerEngine()._configure_torch_device("cpu")

    assert os.environ["TORCH_DEVICE"] == "cpu"


def test_configure_torch_device_falls_back_to_cpu_on_torch_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TORCH_DEVICE", raising=False)

    def fake_import_module(name: str) -> object:
        assert name == "torch"
        raise RuntimeError("torch broken")

    monkeypatch.setattr("pdf2md.engines.marker_engine.importlib.import_module", fake_import_module)

    MarkerEngine()._configure_torch_device(None)

    assert os.environ["TORCH_DEVICE"] == "cpu"


def test_configure_torch_device_forces_cpu_for_unsupported_cuda(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TORCH_DEVICE", raising=False)

    class FakeCuda:
        @staticmethod
        def is_available() -> bool:
            return True

        @staticmethod
        def get_device_capability(_index: int) -> tuple[int, int]:
            return (6, 1)

        @staticmethod
        def get_arch_list() -> list[str]:
            return ["sm_75", "sm_86"]

    class FakeTorch:
        cuda = FakeCuda()

    monkeypatch.setattr(
        "pdf2md.engines.marker_engine.importlib.import_module",
        lambda name: FakeTorch,
    )

    MarkerEngine()._configure_torch_device(None)

    assert os.environ["TORCH_DEVICE"] == "cpu"


def test_load_marker_api_returns_expected_objects(monkeypatch: pytest.MonkeyPatch) -> None:
    convert_if_not_rgb = object()
    modules = {
        "marker.config.parser": SimpleNamespace(ConfigParser=object()),
        "marker.converters.pdf": SimpleNamespace(PdfConverter=object()),
        "marker.models": SimpleNamespace(create_model_dict=lambda: {}),
        "marker.output": SimpleNamespace(
            text_from_rendered=lambda rendered: ("", {}, {}),
            convert_if_not_rgb=convert_if_not_rgb,
        ),
    }

    monkeypatch.setattr(
        "pdf2md.engines.marker_engine.importlib.import_module",
        lambda name: modules[name],
    )

    config_parser, converter, create_model_dict, text_from_rendered, convert_rgb = (
        MarkerEngine()._load_marker_api()
    )

    assert config_parser is modules["marker.config.parser"].ConfigParser
    assert converter is modules["marker.converters.pdf"].PdfConverter
    assert create_model_dict is modules["marker.models"].create_model_dict
    assert text_from_rendered is modules["marker.output"].text_from_rendered
    assert convert_rgb is convert_if_not_rgb
