"""Silniki konwersji PDF → Markdown (pymupdf4llm, marker-pdf, docling, MinerU, pdf-craft)."""

from pdf2md.core.registry import engine_registry
from pdf2md.engines.docling_engine import DoclingEngine
from pdf2md.engines.marker_engine import MarkerEngine
from pdf2md.engines.mineru_engine import MinerUEngine
from pdf2md.engines.pdf_craft_engine import PdfCraftEngine
from pdf2md.engines.pymupdf4llm_engine import PyMuPDF4LLMEngine

engine_registry.register(PyMuPDF4LLMEngine())
engine_registry.register(MarkerEngine())
engine_registry.register(DoclingEngine())
engine_registry.register(MinerUEngine())
engine_registry.register(PdfCraftEngine())

__all__ = [
    "DoclingEngine",
    "MarkerEngine",
    "MinerUEngine",
    "PdfCraftEngine",
    "PyMuPDF4LLMEngine",
]
