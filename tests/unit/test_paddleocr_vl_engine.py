"""Testy adaptera PaddleOCR-VL — klient HTTP, mock urllib, bez realnego serwera."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from pdf2md.engines import paddleocr_vl_engine
from pdf2md.engines.paddleocr_vl_engine import PaddleOCRVLEngine

_SETTINGS = SimpleNamespace(
    paddleocr_vl_url="http://localhost:8000/v1",
    paddleocr_vl_model="PaddlePaddle/PaddleOCR-VL-1.6",
    paddleocr_vl_prompt="OCR:",
    paddleocr_vl_timeout=120.0,
)


def _patch_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(paddleocr_vl_engine, "get_settings", lambda: _SETTINGS)


class _FakeResp:
    def __init__(self, status: int = 200, body: bytes = b"{}") -> None:
        self.status = status
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeResp:
        return self

    def __exit__(self, *args: object) -> None:
        return None


# ---------------------------------------------------------------------------
# is_available — ping serwera
# ---------------------------------------------------------------------------


def test_is_available_true_on_http_200(monkeypatch: pytest.MonkeyPatch) -> None:
    """GET /models → 200 daje True."""
    _patch_settings(monkeypatch)
    captured: dict[str, Any] = {}

    def fake_urlopen(url: str, timeout: float | None = None) -> _FakeResp:
        captured["url"] = url
        return _FakeResp(status=200)

    monkeypatch.setattr(paddleocr_vl_engine.urllib.request, "urlopen", fake_urlopen)

    assert PaddleOCRVLEngine().is_available() is True
    assert captured["url"] == "http://localhost:8000/v1/models"


def test_is_available_false_on_connection_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """ConnectionError przy pingu → False, bez rzucania."""
    _patch_settings(monkeypatch)

    def fake_urlopen(url: str, timeout: float | None = None) -> _FakeResp:
        raise ConnectionError("refused")

    monkeypatch.setattr(paddleocr_vl_engine.urllib.request, "urlopen", fake_urlopen)

    assert PaddleOCRVLEngine().is_available() is False


def test_is_available_does_not_import_paddle(monkeypatch: pytest.MonkeyPatch) -> None:
    """is_available() nie importuje paddle (działa bez paddle w środowisku)."""
    import sys

    _patch_settings(monkeypatch)
    monkeypatch.setattr(
        paddleocr_vl_engine.urllib.request,
        "urlopen",
        lambda url, timeout=None: _FakeResp(status=200),
    )

    PaddleOCRVLEngine().is_available()
    assert "paddle" not in sys.modules
    assert "paddlepaddle" not in sys.modules


# ---------------------------------------------------------------------------
# _ocr_page — kształt POST i ekstrakcja treści
# ---------------------------------------------------------------------------


def test_ocr_page_posts_chat_completion(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """_ocr_page POST-uje poprawny payload i wyciąga choices[0].message.content."""
    _patch_settings(monkeypatch)
    png = tmp_path / "page.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\n-fake")
    captured: dict[str, Any] = {}

    def fake_urlopen(req: Any, timeout: float | None = None) -> _FakeResp:
        captured["url"] = req.full_url
        captured["method"] = req.get_method()
        captured["timeout"] = timeout
        captured["body"] = json.loads(req.data)
        body = json.dumps({"choices": [{"message": {"content": "# Strona\n\ntekst"}}]}).encode()
        return _FakeResp(status=200, body=body)

    monkeypatch.setattr(paddleocr_vl_engine.urllib.request, "urlopen", fake_urlopen)

    text = PaddleOCRVLEngine()._ocr_page(str(png))

    assert text == "# Strona\n\ntekst"
    assert captured["url"] == "http://localhost:8000/v1/chat/completions"
    assert captured["method"] == "POST"
    assert captured["timeout"] == 120.0
    body = captured["body"]
    assert body["model"] == "PaddlePaddle/PaddleOCR-VL-1.6"
    assert body["temperature"] == 0.0
    content = body["messages"][0]["content"]
    types = {part["type"] for part in content}
    assert types == {"image_url", "text"}
    image_part = next(p for p in content if p["type"] == "image_url")
    assert image_part["image_url"]["url"].startswith("data:image/png;base64,")
    text_part = next(p for p in content if p["type"] == "text")
    assert text_part["text"] == "OCR:"


def test_ocr_page_raises_on_connection_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Brak serwera w _ocr_page → _PaddleOCRServerError z podpowiedzią instalacji."""
    _patch_settings(monkeypatch)
    png = tmp_path / "page.png"
    png.write_bytes(b"x")

    def fake_urlopen(req: Any, timeout: float | None = None) -> _FakeResp:
        raise ConnectionError("refused")

    monkeypatch.setattr(paddleocr_vl_engine.urllib.request, "urlopen", fake_urlopen)

    with pytest.raises(paddleocr_vl_engine._PaddleOCRServerError, match="nie odpowiada"):
        PaddleOCRVLEngine()._ocr_page(str(png))


# ---------------------------------------------------------------------------
# convert — obsługa błędów
# ---------------------------------------------------------------------------


def test_convert_returns_error_result_when_server_down(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Serwer niedostępny → ConversionResult z pustym markdown i komunikatem w warnings."""
    _patch_settings(monkeypatch)
    engine = PaddleOCRVLEngine()
    monkeypatch.setattr(engine, "is_available", lambda: False)

    result = engine.convert(str(tmp_path / "doc.pdf"))

    assert result.markdown == ""
    assert result.pages == 0
    assert result.engine_used == "PaddleOCR-VL"
    assert len(result.warnings) == 1
    assert "nie odpowiada" in result.warnings[0]
    assert "http://localhost:8000/v1" in result.warnings[0]


def test_unload_model_is_noop() -> None:
    """unload_model() to no-op — nie rzuca i nie wymaga GPU."""
    PaddleOCRVLEngine().unload_model()
