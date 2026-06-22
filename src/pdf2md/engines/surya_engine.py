"""Adapter silnika Surya (layout + OCR + reading order).

Dobry jako kontrola/fallback dla pozostałych silników VLM. Korzysta z API surya:
FoundationPredictor → RecognitionPredictor + DetectionPredictor (zweryfikowane na
surya-ocr 0.17.1). Import surya następuje dopiero w load_model(), nie w is_available().
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from pdf2md.engines.vlm_base import VLMEngine


class SuryaEngine(VLMEngine):
    """Adapter OCR Surya — detekcja linii + rozpoznawanie tekstu z reading order."""

    name = "Surya"
    description = "Layout + OCR + reading order, dobry jako kontrola/fallback"
    package_name = "surya-ocr"

    def __init__(self) -> None:
        super().__init__()
        self._recognition: Any = None
        self._detection: Any = None
        self._foundation: Any = None

    def load_model(self) -> None:
        """Tworzy predyktory Surya, JAWNIE wymuszając urządzenie wg wykrytej CUDA.

        Domyślne `device` predyktorów surya to `settings.TORCH_DEVICE_MODEL` — wartość
        domyślna parametru zamrożona przy imporcie modułu z env `TORCH_DEVICE` (które
        marker_engine/conftest mogły ustawić na "cpu"). Przekazujemy device jawnie, więc
        Surya używa GPU niezależnie od ambientowego env. dtype zostawiamy surya (per-model,
        device-aware: cuda→fp16, cpu→fp32).
        """
        from surya.detection import DetectionPredictor
        from surya.foundation import FoundationPredictor
        from surya.recognition import RecognitionPredictor

        device = "cuda" if self.has_gpu() else "cpu"
        self._foundation = FoundationPredictor(device=device)
        self._recognition = RecognitionPredictor(self._foundation)
        self._detection = DetectionPredictor(device=device)
        self._model = self._recognition
        logger.info(f"Surya: device={device} (foundation + recognition + detection)")

    def unload_model(self) -> None:
        """Czyści predyktory Surya, potem zwalnia VRAM przez bazę."""
        self._recognition = None
        self._detection = None
        self._foundation = None
        super().unload_model()

    def _ocr_page(self, image_path: str) -> str:
        """OCR jednej strony: rozpoznawanie z detekcją linii, posortowane reading order."""
        from PIL import Image

        image = Image.open(image_path).convert("RGB")
        predictions = self._recognition(
            [image],
            det_predictor=self._detection,
            sort_lines=True,
        )
        result = predictions[0]
        lines = [line.text for line in result.text_lines if line.text and line.text.strip()]
        return "\n\n".join(lines)
