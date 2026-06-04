"""Silniki konwersji PDF → Markdown (pymupdf4llm, marker-pdf, docling, MinerU, pdf-craft)."""

from pdf2md.core.registry import engine_registry
from pdf2md.engines.pymupdf4llm_engine import PyMuPDF4LLMEngine

engine_registry.register(PyMuPDF4LLMEngine())

__all__ = ["PyMuPDF4LLMEngine"]
