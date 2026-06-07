"""Testy jednostkowe adaptera Docling bez uruchamiania konwersji ML."""

from __future__ import annotations

from enum import StrEnum
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


class _FakePdfFormatOption:
    def __init__(self, pipeline_options: _FakePdfPipelineOptions) -> None:
        self.pipeline_options = pipeline_options


class _FakeDocumentConverter:
    built_devices: ClassVar[list[_FakeAcceleratorDevice]] = []

    def __init__(self, format_options: dict[object, _FakePdfFormatOption]) -> None:
        option = next(iter(format_options.values()))
        accelerator_options = option.pipeline_options.accelerator_options
        assert accelerator_options is not None
        self.built_devices.append(accelerator_options.device)

    def convert(self, _pdf_path: str, **_kwargs: object) -> object:
        document = SimpleNamespace(
            pages=[object()],
            export_to_markdown=lambda: "# Docling",
        )
        return SimpleNamespace(document=document)


def _install_fake_docling(monkeypatch: pytest.MonkeyPatch, cuda_is_usable: bool) -> None:
    _FakeDocumentConverter.built_devices = []

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
