# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build for the core pdf2md distribution.

This spec intentionally bundles only the lightweight core engines:
PyMuPDF4LLM and Docling. Marker, MinerU, pdf-craft and future VLM engines
are excluded from the frozen application for license and size reasons.
Their adapter modules remain in pdf2md, but their third-party packages are
not bundled.
"""

from __future__ import annotations

from pathlib import Path

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_submodules,
    copy_metadata,
)

PROJECT_ROOT = Path.cwd()
SRC_DIR = PROJECT_ROOT / "src"
ICON_SVG = SRC_DIR / "pdf2md" / "gui" / "assets" / "icon.svg"


def safe_collect_submodules(package: str) -> list[str]:
    """Collect hidden imports only when the package exists in the build env."""
    try:
        return collect_submodules(package, on_error="warn once")
    except Exception:
        return []


def safe_collect_data_files(package: str) -> list[tuple[str, str]]:
    """Collect package data without making the spec fail for optional packages."""
    try:
        return collect_data_files(package)
    except Exception:
        return []


def safe_copy_metadata(distribution: str, *, recursive: bool = False) -> list[tuple[str, str]]:
    """Bundle distribution metadata needed by importlib.metadata.version()."""
    try:
        return copy_metadata(distribution, recursive=recursive)
    except Exception:
        return []


PYMUPDF_PACKAGES = (
    "pymupdf4llm",
    "pymupdf",
    "fitz",
)

CORE_HIDDENIMPORTS = [
    "pymupdf4llm",
    "pymupdf",
    "docling",
    "docling.document_converter",
    "docling.datamodel.base_models",
    "docling.datamodel.pipeline_options",
    "docling.datamodel.accelerator_options",
]
for package in PYMUPDF_PACKAGES:
    CORE_HIDDENIMPORTS.extend(safe_collect_submodules(package))
CORE_HIDDENIMPORTS = sorted(set(CORE_HIDDENIMPORTS))

COMMON_DATAS = [
    (str(ICON_SVG), "pdf2md/gui/assets"),
]
for package in ("pymupdf4llm", "pymupdf", "docling", "docling_core", "docling_parse"):
    COMMON_DATAS.extend(safe_collect_data_files(package))
for distribution in (
    "pymupdf4llm",
    "PyMuPDF",
    "docling",
    "docling-core",
    "docling-parse",
    "docling-ibm-models",
):
    COMMON_DATAS.extend(safe_copy_metadata(distribution, recursive=True))

EXCLUDED_OPTIONAL_ENGINES = [
    "marker",
    "marker_pdf",
    "surya",
    "pdftext",
    "texify",
    "mineru",
    "magic_pdf",
    "pdf_craft",
    "olmocr",
    "vllm",
    "docling.experimental",
    "docling.experimental.datamodel.table_crops_layout_options",
    "docling.experimental.datamodel.threaded_layout_vlm_pipeline_options",
    "docling.experimental.models.table_crops_layout_model",
    "docling.experimental.pipeline.threaded_layout_vlm_pipeline",
]

CLI_EXCLUDES = [
    *EXCLUDED_OPTIONAL_ENGINES,
    "PySide6",
    "shiboken6",
    "pdf2md.gui",
]

GUI_EXCLUDES = [
    *EXCLUDED_OPTIONAL_ENGINES,
]

cli_analysis = Analysis(
    [str(SRC_DIR / "pdf2md" / "cli" / "main.py")],
    pathex=[str(SRC_DIR)],
    binaries=[],
    datas=COMMON_DATAS,
    hiddenimports=CORE_HIDDENIMPORTS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=CLI_EXCLUDES,
    noarchive=False,
    optimize=0,
)
cli_pyz = PYZ(cli_analysis.pure)
pdf2md_cli = EXE(
    cli_pyz,
    cli_analysis.scripts,
    cli_analysis.binaries,
    cli_analysis.datas,
    [],
    name="pdf2md",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

gui_analysis = Analysis(
    [str(SRC_DIR / "pdf2md" / "gui" / "app.py")],
    pathex=[str(SRC_DIR)],
    binaries=[],
    # PyInstaller's PySide6 hooks collect Qt libraries/plugins for imported
    # modules (QtWidgets, QtGui, QtCore). Do not collect the whole PySide6 tree,
    # because that pulls WebEngine/Multimedia/SQL plugins not used by pdf2md.
    datas=COMMON_DATAS,
    hiddenimports=CORE_HIDDENIMPORTS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=GUI_EXCLUDES,
    noarchive=False,
    optimize=0,
)
gui_pyz = PYZ(gui_analysis.pure)
pdf2md_gui = EXE(
    gui_pyz,
    gui_analysis.scripts,
    gui_analysis.binaries,
    gui_analysis.datas,
    [],
    name="pdf2md-gui",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
