"""Adapter silnika PaddleOCR-VL jako klient HTTP serwera OpenAI-compatible (vLLM).

PaddleOCR-VL działa jako zewnętrzna usługa (serwer vLLM z modelem PaddleOCR-VL), a pdf2md
jest tylko klientem HTTP — nie importuje paddle/paddlepaddle ani nie trzyma modelu w procesie.
Cykl życia serwera jest zarządzany przez użytkownika (zob. SILNIKI_INSTALACJA.md 2.8).

is_available() pinguje serwer (GET /models). VRAM jest po stronie serwera, więc
unload_model() to no-op — model zwalnia się przez zatrzymanie serwera.
"""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from contextlib import suppress
from pathlib import Path

from loguru import logger

from pdf2md.core.config import get_settings
from pdf2md.engines.base import ConversionResult
from pdf2md.engines.vlm_base import VLMEngine


class _PaddleOCRServerError(RuntimeError):
    """Serwer PaddleOCR-VL nie odpowiada albo zwrócił błąd HTTP."""


class PaddleOCRVLEngine(VLMEngine):
    """Adapter PaddleOCR-VL — klient HTTP zewnętrznego serwera vLLM (OpenAI-compatible)."""

    name = "PaddleOCR-VL"
    description = "Serwer pod paddleocr_vl_url odpowiada — wielojęzyczny parser dokumentów VLM"
    package_name = "paddleocr"

    def _base_url(self) -> str:
        return get_settings().paddleocr_vl_url.rstrip("/") or "http://localhost:8000/v1"

    def is_available(self) -> bool:
        """Ping serwera: GET {url}/models. True przy HTTP 200, False przy każdym błędzie.

        Nigdy nie rzuca i nie importuje paddle — sprawdza wyłącznie dostępność usługi.
        """
        try:
            with urllib.request.urlopen(f"{self._base_url()}/models", timeout=3) as resp:
                return bool(resp.status == 200)
        except Exception:
            return False

    def load_model(self) -> None:
        """Silnik-usługa: brak lokalnego modelu do załadowania (model żyje na serwerze)."""
        logger.debug("PaddleOCR-VL: silnik-usługa, brak lokalnego modelu do załadowania")

    def unload_model(self) -> None:
        """No-op: VRAM jest po stronie serwera, nie zabijamy go z adaptera (v1.0)."""
        logger.debug(
            "PaddleOCR-VL to serwer zewnętrzny; VRAM zwalnia się przez zatrzymanie serwera "
            "(pkill -f 'vllm serve')"
        )

    def convert(self, pdf_path: str, **kwargs: object) -> ConversionResult:
        """Render+pętla po stronach z vlm_base; OCR per strona po HTTP. Błędy serwera →
        ConversionResult z komunikatem (markdown pusty, warnings=[komunikat])."""
        base_url = self._base_url()
        if not self.is_available():
            msg = (
                f"Serwer PaddleOCR-VL pod {base_url} nie odpowiada — uruchom go "
                "(SILNIKI_INSTALACJA.md 2.8)"
            )
            logger.error(msg)
            return self._error_result(pdf_path, msg)
        try:
            return super().convert(pdf_path, **kwargs)
        except _PaddleOCRServerError as exc:
            logger.error(str(exc))
            return self._error_result(pdf_path, str(exc))

    def _ocr_page(self, image_path: str) -> str:
        """OCR jednej strony: PNG → base64 → POST /chat/completions, zwraca treść odpowiedzi."""
        settings = get_settings()
        b64 = base64.b64encode(Path(image_path).read_bytes()).decode("ascii")
        payload = json.dumps(
            {
                "model": settings.paddleocr_vl_model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{b64}"},
                            },
                            {"type": "text", "text": settings.paddleocr_vl_prompt},
                        ],
                    }
                ],
                "temperature": 0.0,
            }
        ).encode()
        url = f"{self._base_url()}/chat/completions"
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=settings.paddleocr_vl_timeout) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            detail = ""
            with suppress(Exception):
                detail = exc.read().decode("utf-8", errors="replace")
            logger.error("PaddleOCR-VL HTTP %s: %s", exc.code, detail[:500])
            raise _PaddleOCRServerError(f"PaddleOCR-VL HTTP {exc.code}: {detail[:500]}") from exc
        except OSError as exc:
            raise _PaddleOCRServerError(
                f"Serwer PaddleOCR-VL pod {self._base_url()} nie odpowiada — uruchom go "
                "(SILNIKI_INSTALACJA.md 2.8)"
            ) from exc
        return str(data["choices"][0]["message"]["content"])

    def _error_result(self, pdf_path: str, message: str) -> ConversionResult:
        return ConversionResult(
            markdown="",
            engine_used=self.name,
            pages=0,
            warnings=[message],
            metadata={"source": str(pdf_path), "error": message},
        )
