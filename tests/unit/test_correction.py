"""Testy korekty OCR (scan/correction) z mockowanym dostawcą LLM."""

from __future__ import annotations

from pathlib import Path

import pytest

from pdf2md.core.prompts import POST_PROCESSING_PROMPT, SCAN_CORRECTION_PROMPT
from pdf2md.llm.base import LLMProvider, LLMResult
from pdf2md.scan.correction import correct_page, correct_pages_batch, release_ollama_model


class _FakeProvider(LLMProvider):
    """Mock LLM: zapamiętuje argumenty correct() i zwraca ustalony tekst."""

    name = "Fake"
    description = "test"
    requires_api_key = False
    default_model = "fake-model"

    def __init__(self, output: str = "POPRAWIONE") -> None:
        self.output = output
        self.calls: list[dict[str, object]] = []

    def is_available(self) -> bool:
        return True

    def postprocess(
        self,
        markdown: str,
        mode: str = "whole_document",
        instructions: str = "",
    ) -> LLMResult:
        raise AssertionError("korekta nie powinna używać postprocess()")

    def correct(self, text: str, *, system_prompt: str, temperature: float = 0.0) -> str:
        self.calls.append(
            {"text": text, "system_prompt": system_prompt, "temperature": temperature}
        )
        return self.output


def test_correct_page_uses_correction_prompt_not_postprocessing() -> None:
    """correct() dostaje system == SCAN_CORRECTION_PROMPT, BEZ POST_PROCESSING_PROMPT, temp 0.0."""
    provider = _FakeProvider(output="czysty markdown")

    result = correct_page("Surowy 0CR tekst", provider)

    assert result == "czysty markdown"
    assert len(provider.calls) == 1
    call = provider.calls[0]
    assert call["system_prompt"] == SCAN_CORRECTION_PROMPT
    assert call["temperature"] == 0.0
    system = str(call["system_prompt"])
    assert "nie parafrazuj" in system.lower()
    assert POST_PROCESSING_PROMPT not in system
    # nie ma fragmentu ogólnego promptu czyszczenia
    assert "asystentem do czyszczenia dokumentów" not in system


def test_correct_page_empty_skips_llm() -> None:
    """Pusta strona zwracana bez wywołania LLM."""
    provider = _FakeProvider()

    assert correct_page("   \n  ", provider) == "   \n  "
    assert provider.calls == []


def test_correct_pages_batch_writes_all(tmp_path: Path) -> None:
    """correct_pages_batch koryguje każdą stronę i zapisuje do output_dir."""
    md_dir = tmp_path / "md_pages"
    md_dir.mkdir()
    (md_dir / "page_0001.md").write_text("strona jeden", encoding="utf-8")
    (md_dir / "page_0002.md").write_text("strona dwa", encoding="utf-8")
    out_dir = tmp_path / "corrected"
    provider = _FakeProvider(output="OK")

    written = correct_pages_batch(str(md_dir), provider, str(out_dir))

    assert len(written) == 2
    assert (out_dir / "page_0001.md").read_text(encoding="utf-8") == "OK"
    assert (out_dir / "page_0002.md").read_text(encoding="utf-8") == "OK"
    assert len(provider.calls) == 2


def test_release_ollama_model_noop_for_cloud_provider() -> None:
    """Dla dostawcy innego niż Ollama keep_alive=0 nie jest wysyłany."""
    provider = _FakeProvider()  # brak _base_url, nazwa != ollama

    assert release_ollama_model(provider) is False


def test_release_ollama_model_sends_keep_alive(monkeypatch: pytest.MonkeyPatch) -> None:
    """Dla Ollamy wysyłane jest żądanie keep_alive=0 (wyładowanie modelu z VRAM)."""

    class _FakeOllama(_FakeProvider):
        name = "Ollama (lokalny)"

        def _base_url(self) -> str:
            return "http://localhost:11434"

    captured: dict[str, object] = {}

    def fake_urlopen(req: object, timeout: float | None = None) -> object:
        captured["url"] = req.full_url  # type: ignore[attr-defined]
        import json

        captured["body"] = json.loads(req.data)  # type: ignore[attr-defined]

        class _Ctx:
            def __enter__(self) -> object:
                return self

            def __exit__(self, *a: object) -> None:
                return None

        return _Ctx()

    import pdf2md.core.config as config_mod

    monkeypatch.setattr(
        config_mod,
        "get_settings",
        lambda: type("S", (), {"ollama_model": "qwen3:14b"})(),
    )
    import urllib.request

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    assert release_ollama_model(_FakeOllama()) is True
    assert captured["url"] == "http://localhost:11434/api/generate"
    assert captured["body"] == {"model": "qwen3:14b", "keep_alive": 0}
