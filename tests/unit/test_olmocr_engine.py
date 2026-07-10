"""Testy dostępności silnika olmOCR — rozdział trybów external-server vs spawn lokalny.

Kluczowe (B7): tryb external-server (olmocr_server_url) NIE wymaga lokalnego GPU —
inferencja żyje na serwerze. Tryb spawn (brak server_url) wymaga GPU ORAZ bina vllm.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from pdf2md.engines import olmocr_engine
from pdf2md.engines.olmocr_engine import OlmOCREngine


def _venv_python(tmp_path: Path, *, with_vllm: bool = False) -> Path:
    """Tworzy atrapę venv (bin/python, opcjonalnie bin/vllm) i zwraca ścieżkę do pythona."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    python = bin_dir / "python"
    python.write_text("")
    if with_vllm:
        (bin_dir / "vllm").write_text("")
    return python


def test_available_in_server_mode_without_gpu(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """external-server (server_url + venv) → dostępny NAWET bez lokalnego GPU i bez bina vllm."""
    engine = OlmOCREngine()
    python = _venv_python(tmp_path, with_vllm=False)
    monkeypatch.setattr(engine, "_olmocr_python", lambda: str(python))
    monkeypatch.setattr(OlmOCREngine, "has_gpu", staticmethod(lambda: False))
    monkeypatch.setattr(
        olmocr_engine,
        "get_settings",
        lambda: SimpleNamespace(olmocr_server_url="http://wsl:30000/v1"),
    )

    assert engine.is_available() is True


def test_unavailable_in_spawn_mode_without_gpu(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """spawn lokalny (brak server_url) bez GPU → niedostępny, mimo obecnego bina vllm."""
    engine = OlmOCREngine()
    python = _venv_python(tmp_path, with_vllm=True)
    monkeypatch.setattr(engine, "_olmocr_python", lambda: str(python))
    monkeypatch.setattr(OlmOCREngine, "has_gpu", staticmethod(lambda: False))
    monkeypatch.setattr(
        olmocr_engine,
        "get_settings",
        lambda: SimpleNamespace(olmocr_server_url=""),
    )

    assert engine.is_available() is False


def test_available_in_spawn_mode_with_gpu_and_vllm(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """spawn lokalny z GPU ORAZ binem vllm → dostępny."""
    engine = OlmOCREngine()
    python = _venv_python(tmp_path, with_vllm=True)
    monkeypatch.setattr(engine, "_olmocr_python", lambda: str(python))
    monkeypatch.setattr(OlmOCREngine, "has_gpu", staticmethod(lambda: True))
    monkeypatch.setattr(
        olmocr_engine,
        "get_settings",
        lambda: SimpleNamespace(olmocr_server_url=""),
    )

    assert engine.is_available() is True


def test_unavailable_in_spawn_mode_with_gpu_without_vllm(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """spawn lokalny z GPU, ale bez bina vllm (półzłożony venv) → ❌, nie fałszywe ✅."""
    engine = OlmOCREngine()
    python = _venv_python(tmp_path, with_vllm=False)
    monkeypatch.setattr(engine, "_olmocr_python", lambda: str(python))
    monkeypatch.setattr(OlmOCREngine, "has_gpu", staticmethod(lambda: True))
    monkeypatch.setattr(
        olmocr_engine,
        "get_settings",
        lambda: SimpleNamespace(olmocr_server_url=""),
    )

    assert engine.is_available() is False


def test_unavailable_without_venv(monkeypatch: pytest.MonkeyPatch) -> None:
    """Brak venv (python None) → niedostępny nawet w trybie server (CLI odpalamy przez venv)."""
    engine = OlmOCREngine()
    monkeypatch.setattr(engine, "_olmocr_python", lambda: None)
    monkeypatch.setattr(
        olmocr_engine,
        "get_settings",
        lambda: SimpleNamespace(olmocr_server_url="http://wsl:30000/v1"),
    )

    assert engine.is_available() is False
