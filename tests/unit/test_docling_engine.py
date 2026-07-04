"""Testy jednostkowe adaptera Docling bez uruchamiania konwersji ML."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from types import SimpleNamespace
from typing import Any, ClassVar

import pytest

from pdf2md.engines import docling_engine
from pdf2md.engines.docling_engine import DoclingEngine


class _FakeAcceleratorDevice(StrEnum):
    AUTO = "auto"
    CPU = "cpu"
    CUDA = "cuda"


class _FakeAcceleratorOptions:
    def __init__(self, device: _FakeAcceleratorDevice, num_threads: int = 4) -> None:
        self.device = device
        self.num_threads = num_threads


class _FakePdfPipelineOptions:
    def __init__(self) -> None:
        self.accelerator_options: _FakeAcceleratorOptions | None = None
        self.generate_page_images = False
        self.generate_picture_images = False
        self.images_scale = 1.0


class _FakePdfFormatOption:
    def __init__(self, pipeline_options: _FakePdfPipelineOptions) -> None:
        self.pipeline_options = pipeline_options


class _FakeDocumentConverter:
    built_devices: ClassVar[list[_FakeAcceleratorDevice]] = []
    built_pipeline_options: ClassVar[list[_FakePdfPipelineOptions]] = []
    document: ClassVar[object | None] = None

    def __init__(self, format_options: dict[object, _FakePdfFormatOption]) -> None:
        option = next(iter(format_options.values()))
        accelerator_options = option.pipeline_options.accelerator_options
        assert accelerator_options is not None
        self.built_devices.append(accelerator_options.device)
        self.built_pipeline_options.append(option.pipeline_options)

    def convert(self, _pdf_path: str, **_kwargs: object) -> object:
        if self.document is not None:
            return SimpleNamespace(document=self.document)
        document = SimpleNamespace(
            pages=[object()],
            export_to_markdown=lambda: "# Docling",
        )
        return SimpleNamespace(document=document)


def _install_fake_docling(monkeypatch: pytest.MonkeyPatch, cuda_is_usable: bool) -> None:
    _FakeDocumentConverter.built_devices = []
    _FakeDocumentConverter.built_pipeline_options = []
    _FakeDocumentConverter.document = None
    image_ref_mode = SimpleNamespace(REFERENCED="referenced")

    modules = {
        "docling.document_converter": SimpleNamespace(
            DocumentConverter=_FakeDocumentConverter,
            PdfFormatOption=_FakePdfFormatOption,
        ),
        "docling.datamodel.base_models": SimpleNamespace(InputFormat=SimpleNamespace(PDF="pdf")),
        "docling.datamodel.pipeline_options": SimpleNamespace(
            PdfPipelineOptions=_FakePdfPipelineOptions
        ),
        "docling.datamodel.accelerator_options": SimpleNamespace(
            AcceleratorDevice=_FakeAcceleratorDevice,
            AcceleratorOptions=_FakeAcceleratorOptions,
        ),
        "docling_core.types.doc.base": SimpleNamespace(ImageRefMode=image_ref_mode),
    }

    def fake_import_module(name: str) -> Any:
        if name in modules:
            return modules[name]
        raise AssertionError(f"Nieoczekiwany import: {name}")

    monkeypatch.setattr("importlib.import_module", fake_import_module)
    monkeypatch.setattr(docling_engine, "cuda_usable", lambda: cuda_is_usable)
    monkeypatch.setattr(DoclingEngine, "is_available", lambda _self: True)


@pytest.mark.parametrize(
    ("device", "cuda_is_usable", "expected"),
    [
        ("auto", True, _FakeAcceleratorDevice.CUDA),
        ("auto", False, _FakeAcceleratorDevice.CPU),
        ("cpu", False, _FakeAcceleratorDevice.CPU),
        ("cuda", True, _FakeAcceleratorDevice.CUDA),
        ("cuda", False, _FakeAcceleratorDevice.CPU),
    ],
)
def test_docling_builds_accelerator_device(
    monkeypatch: pytest.MonkeyPatch,
    device: str,
    cuda_is_usable: bool,
    expected: _FakeAcceleratorDevice,
) -> None:
    """DoclingEngine mapuje wybór device na używalny AcceleratorDevice."""
    _install_fake_docling(monkeypatch, cuda_is_usable=cuda_is_usable)

    result = DoclingEngine().convert("doc.pdf", device=device)

    assert result.markdown == "# Docling"
    assert _FakeDocumentConverter.built_devices == [expected]


def test_docling_cuda_falls_back_to_cpu_when_gpu_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """device='cuda' bez używalnej CUDA buduje AcceleratorOptions dla CPU."""
    _install_fake_docling(monkeypatch, cuda_is_usable=False)

    result = DoclingEngine().convert("doc.pdf", device="cuda")

    assert result.markdown == "# Docling"
    assert _FakeDocumentConverter.built_devices == [_FakeAcceleratorDevice.CPU]


def test_docling_default_device_is_auto(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Brak parametru device używa domyślnego auto i wybiera CPU, gdy CUDA nieużywalna."""
    _install_fake_docling(monkeypatch, cuda_is_usable=False)

    result = DoclingEngine().convert("doc.pdf")

    assert result.markdown == "# Docling"
    assert _FakeDocumentConverter.built_devices == [_FakeAcceleratorDevice.CPU]


def test_docling_enables_picture_images_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Docling generuje obrazy figur, ale nie zrzuty całych stron."""
    _install_fake_docling(monkeypatch, cuda_is_usable=False)

    DoclingEngine().convert("doc.pdf")

    pipeline_options = _FakeDocumentConverter.built_pipeline_options[0]
    assert pipeline_options.generate_picture_images is True
    assert pipeline_options.generate_page_images is False
    assert pipeline_options.images_scale == 2.0


def test_docling_allows_overriding_picture_image_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Użytkownik może nadal nadpisać opcje pipeline przez kwargs."""
    _install_fake_docling(monkeypatch, cuda_is_usable=False)

    DoclingEngine().convert("doc.pdf", generate_picture_images=False, images_scale=1.0)

    pipeline_options = _FakeDocumentConverter.built_pipeline_options[0]
    assert pipeline_options.generate_picture_images is False
    assert pipeline_options.images_scale == 1.0


def test_docling_saves_markdown_with_referenced_images_when_output_path_known(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Ze ścieżką wyniku Docling zapisuje artefakty i zwraca zapisany Markdown."""
    _install_fake_docling(monkeypatch, cuda_is_usable=False)
    output_path = tmp_path / "out" / "doc.md"
    calls: dict[str, object] = {}

    def save_as_markdown(
        filename: str | Path,
        *,
        artifacts_dir: Path | None = None,
        image_mode: object | None = None,
    ) -> None:
        calls["filename"] = Path(filename)
        calls["artifacts_dir"] = artifacts_dir
        calls["image_mode"] = image_mode
        assert artifacts_dir is not None
        artifact_dir = Path(filename).parent / artifacts_dir
        artifact_dir.mkdir(parents=True, exist_ok=True)
        (artifact_dir / "image_0.png").write_bytes(b"png")
        absolute_ref = (artifact_dir / "image_0.png").resolve().as_posix()
        Path(filename).write_text(f"![]({absolute_ref})\n", encoding="utf-8")

    document = SimpleNamespace(
        pages=[object()],
        export_to_markdown=lambda: pytest.fail("fallback export_to_markdown should not run"),
        save_as_markdown=save_as_markdown,
    )
    _FakeDocumentConverter.document = document

    result = DoclingEngine().convert("doc.pdf", output_path=str(output_path))

    assert result.markdown == "![](doc_artifacts/image_0.png)\n"
    assert calls == {
        "filename": output_path,
        "artifacts_dir": Path("doc_artifacts"),
        "image_mode": "referenced",
    }
    assert (tmp_path / "out" / "doc_artifacts" / "image_0.png").is_file()


def test_docling_falls_back_to_export_to_markdown_without_output_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bez ścieżki wyniku Docling zachowuje stare zachowanie bez zapisu artefaktów."""
    _install_fake_docling(monkeypatch, cuda_is_usable=False)
    calls = {"export": 0}

    def export_to_markdown() -> str:
        calls["export"] += 1
        return "# Placeholder"

    document = SimpleNamespace(
        pages=[object()],
        export_to_markdown=export_to_markdown,
        save_as_markdown=lambda *args, **kwargs: pytest.fail("save_as_markdown should not run"),
    )
    _FakeDocumentConverter.document = document

    result = DoclingEngine().convert("doc.pdf")

    assert result.markdown == "# Placeholder"
    assert calls["export"] == 1
