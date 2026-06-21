"""Adapter silnika PaddleOCR-VL (lekki parser dokumentów oparty na VLM).

PaddleOCR-VL jest dostarczany jako pipeline w dystrybucji `paddleocr` (3.2+) i wymaga
`paddlepaddle-gpu`. is_available() sprawdza obecność pakietu `paddleocr` oraz GPU, bez
importu samej biblioteki. Konwersja działa per-strona (obraz) przez wspólną logikę VLMEngine.
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from pdf2md.engines.vlm_base import VLMEngine


class PaddleOCRVLEngine(VLMEngine):
    """Adapter PaddleOCR-VL — wielojęzyczny, wydajny parser dokumentów VLM."""

    name = "PaddleOCR-VL"
    description = "Lekki parser dokumentów VLM, wielojęzyczny, wydajny"
    package_name = "paddleocr"

    def load_model(self) -> None:
        """Tworzy pipeline PaddleOCR-VL na GPU."""
        from paddleocr import PaddleOCRVL

        self._model = PaddleOCRVL()
        logger.info("PaddleOCR-VL: pipeline załadowany")

    def _ocr_page(self, image_path: str) -> str:
        """OCR jednej strony przez pipeline PaddleOCR-VL; ekstrahuje Markdown."""
        output = self._model.predict(image_path)
        return self._extract_markdown(output)

    @staticmethod
    def _extract_markdown(output: Any) -> str:
        """Defensywnie wyciąga Markdown z wyniku PaddleOCR-VL (lista wyników stron).

        Wynik udostępnia atrybut/pole ``markdown`` — czasem jako string, czasem jako
        dict z kluczem ``markdown_texts``. Obsługujemy oba warianty.
        """
        parts: list[str] = []
        for res in output or []:
            markdown = getattr(res, "markdown", None)
            if markdown is None and isinstance(res, dict):
                markdown = res.get("markdown")
            if isinstance(markdown, dict):
                markdown = markdown.get("markdown_texts", "")
            if markdown:
                parts.append(str(markdown))
        return "\n\n".join(parts)
