"""Silniki konwersji PDF → Markdown.

Faza 1: pymupdf4llm, marker-pdf, docling, MinerU.
Faza 2 (VLM-OCR, wymaga GPU): olmOCR, PaddleOCR-VL, Surya.
"""

from pdf2md.core.registry import engine_registry
from pdf2md.engines.docling_engine import DoclingEngine
from pdf2md.engines.marker_engine import MarkerEngine
from pdf2md.engines.mineru_engine import MinerUEngine
from pdf2md.engines.olmocr_engine import OlmOCREngine
from pdf2md.engines.paddleocr_vl_engine import PaddleOCRVLEngine
from pdf2md.engines.pymupdf4llm_engine import PyMuPDF4LLMEngine
from pdf2md.engines.surya_engine import SuryaEngine

# Faza 1 — silniki CPU/opcjonalne GPU
engine_registry.register(PyMuPDF4LLMEngine())
engine_registry.register(MarkerEngine())
engine_registry.register(DoclingEngine())
engine_registry.register(MinerUEngine())

# Faza 2 — silniki VLM-OCR (wymagają GPU)
engine_registry.register(OlmOCREngine())
engine_registry.register(PaddleOCRVLEngine())
engine_registry.register(SuryaEngine())

__all__ = [
    "DoclingEngine",
    "MarkerEngine",
    "MinerUEngine",
    "OlmOCREngine",
    "PaddleOCRVLEngine",
    "PyMuPDF4LLMEngine",
    "SuryaEngine",
]
