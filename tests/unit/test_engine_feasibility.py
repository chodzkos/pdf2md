"""Testy wykonalności silników względem wykrytego sprzętu (VRAM + sterownik + system)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from pdf2md.cli.main import _engine_feasibility, _hardware_summary
from pdf2md.detection.hardware import HardwareInfo


def _hw(state: str, vram_gb: float | None = None, compute_cap: str = "") -> HardwareInfo:
    return HardwareInfo(
        state=state,
        name="GPU",
        vram_gb=vram_gb,
        arch="",
        driver_cuda="12.2",
        compute_cap=compute_cap,
    )


def _gpu_engine(min_vram: float) -> dict[str, object]:
    return {"name": "X", "gpu": True, "min_vram_gb": min_vram}


def test_cpu_engine_always_feasible() -> None:
    """Silnik z progiem 0 (PyMuPDF4LLM) jest zawsze ✅ CPU."""
    item = {"name": "PyMuPDF4LLM", "min_vram_gb": 0}
    assert _engine_feasibility(item, _hw("no_gpu")) == "✅ CPU"
    assert _engine_feasibility(item, _hw("ok", 8)) == "✅ CPU"


def test_vram_thresholds_fit_borderline_too_little() -> None:
    """Próg VRAM daje ✅ / ⚠️ / ❌ wokół wartości i 70% wartości."""
    item = _gpu_engine(6)  # próg 6 GB; granica = 4.2 GB
    assert _engine_feasibility(item, _hw("ok", 8)).startswith("✅")
    assert _engine_feasibility(item, _hw("ok", 5)).startswith("⚠️")
    assert _engine_feasibility(item, _hw("ok", 3)).startswith("❌ za mało VRAM")


def test_thresholds_at_8_16_24_gb() -> None:
    """Te same karty 8/16/24 GB dają różną wykonalność per silnik."""
    surya = _gpu_engine(6)
    paddle = _gpu_engine(12)
    olmocr = _gpu_engine(24)

    assert _engine_feasibility(surya, _hw("ok", 8)).startswith("✅")
    assert _engine_feasibility(paddle, _hw("ok", 8)).startswith("❌")
    assert _engine_feasibility(olmocr, _hw("ok", 8)).startswith("❌")

    assert _engine_feasibility(paddle, _hw("ok", 16)).startswith("✅")
    assert _engine_feasibility(olmocr, _hw("ok", 16)).startswith("❌")

    assert _engine_feasibility(olmocr, _hw("ok", 24)).startswith("✅")


def test_gpu_engine_hint_matches_cause() -> None:
    """Silnik wymagający GPU bez działającej CUDA → podpowiedź pasuje do PRZYCZYNY."""
    item = _gpu_engine(6)
    assert _engine_feasibility(item, _hw("no_gpu")) == "❌ wymaga CUDA (brak karty)"
    assert (
        _engine_feasibility(item, _hw("driver_too_old")) == "❌ wymaga CUDA (zaktualizuj sterownik)"
    )
    assert (
        _engine_feasibility(item, _hw("arch_too_old")) == "❌ wymaga CUDA (karta za stara na GPU)"
    )
    assert (
        _engine_feasibility(item, _hw("no_torch")) == "❌ wymaga CUDA (zainstaluj torch / zły venv)"
    )
    # Stan nietypowy → ogólny fallback.
    assert _engine_feasibility(item, _hw("cuda_unavailable")) == "❌ wymaga działającego CUDA"


def test_cpu_fallback_engine_regardless_of_state() -> None:
    """Silnik z fallbackiem CPU (Marker/Docling) działa niezależnie od stanu GPU → ✅ CPU (wolno)."""
    item = {"name": "Marker", "min_vram_gb": 4}  # bez flagi gpu
    assert _engine_feasibility(item, _hw("no_gpu")) == "✅ CPU (wolno)"
    assert _engine_feasibility(item, _hw("arch_too_old")) == "✅ CPU (wolno)"
    assert _engine_feasibility(item, _hw("no_torch")) == "✅ CPU (wolno)"


def test_linux_only_local_engine_on_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    """Lokalny proces vLLM (MinerU) pod Windows → ❌ wymaga Linux/WSL niezależnie od VRAM."""
    monkeypatch.setattr("pdf2md.cli.main.platform.system", lambda: "Windows")
    item = {"key": "mineru", "name": "MinerU", "linux_only_local": True, "min_vram_gb": 6}
    assert _engine_feasibility(item, _hw("ok", 48)) == "❌ wymaga Linux/WSL"


class _FakeEngine:
    """Minimalny silnik do testów wykonalności — steruje tylko is_available()."""

    def __init__(self, available: bool) -> None:
        self._available = available

    def is_available(self) -> bool:
        return self._available


def _paddle_item() -> dict[str, object]:
    return {
        "key": "paddleocr-vl",
        "name": "PaddleOCR-VL",
        "server_backed": True,
        "gpu": True,
        "min_vram_gb": 12,
    }


def test_server_backed_engine_reachable_on_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    """PaddleOCR-VL (klient serwera) pod Windows z osiągalnym serwerem → ✅, mimo braku GPU."""
    monkeypatch.setattr("pdf2md.cli.main.platform.system", lambda: "Windows")
    monkeypatch.setattr("pdf2md.cli.main._find_engine", lambda _key: _FakeEngine(True))
    assert _engine_feasibility(_paddle_item(), _hw("no_gpu")) == "✅ serwer osiągalny"


def test_server_backed_engine_unreachable_on_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    """PaddleOCR-VL pod Windows z serwerem down → ⚠️ z podpowiedzią o serwerze (nie ❌ CUDA)."""
    monkeypatch.setattr("pdf2md.cli.main.platform.system", lambda: "Windows")
    monkeypatch.setattr("pdf2md.cli.main._find_engine", lambda _key: _FakeEngine(False))
    result = _engine_feasibility(_paddle_item(), _hw("no_gpu"))
    assert result.startswith("⚠️")
    assert "serwer" in result
    assert "CUDA" not in result


def test_olmocr_server_backed_when_url_set(monkeypatch: pytest.MonkeyPatch) -> None:
    """olmOCR z olmocr_server_url pod Windows → silnik-usługa: ✅ gdy serwer stoi, mimo braku GPU."""
    monkeypatch.setattr("pdf2md.cli.main.platform.system", lambda: "Windows")
    monkeypatch.setattr("pdf2md.cli.main._find_engine", lambda _key: _FakeEngine(True))
    monkeypatch.setattr(
        "pdf2md.cli.main.get_settings",
        lambda: SimpleNamespace(olmocr_server_url="http://wsl:30000/v1"),
    )
    item = {
        "key": "olmocr",
        "name": "olmOCR",
        "linux_only_local": True,
        "server_url_setting": "olmocr_server_url",
        "gpu": True,
        "min_vram_gb": 24,
    }
    assert _engine_feasibility(item, _hw("no_gpu")) == "✅ serwer osiągalny"


def test_olmocr_spawn_mode_on_windows_is_linux_only(monkeypatch: pytest.MonkeyPatch) -> None:
    """olmOCR bez server_url (tryb spawn) pod Windows → ❌ wymaga Linux/WSL."""
    monkeypatch.setattr("pdf2md.cli.main.platform.system", lambda: "Windows")
    monkeypatch.setattr(
        "pdf2md.cli.main.get_settings",
        lambda: SimpleNamespace(olmocr_server_url=""),
    )
    item = {
        "key": "olmocr",
        "name": "olmOCR",
        "linux_only_local": True,
        "server_url_setting": "olmocr_server_url",
        "gpu": True,
        "min_vram_gb": 24,
    }
    assert _engine_feasibility(item, _hw("ok", 48)) == "❌ wymaga Linux/WSL"


def test_hardware_summary_driver_too_old_mentions_update() -> None:
    """Komunikat dla za starego sterownika prowadzi do aktualizacji."""
    summary = _hardware_summary(_hw("driver_too_old", 24), cuda_version="")
    assert "ktualizuj sterownik" in summary  # „Zaktualizuj sterownik"
    assert "CUDA 12.2" in summary
    assert "CUDA 13" in summary


def test_hardware_summary_arch_too_old_says_card_too_old() -> None:
    """Komunikat dla za starej karty: zbyt stara, aktualizacja sterownika NIE pomoże + minimum."""
    summary = _hardware_summary(_hw("arch_too_old", 8, compute_cap="6.1"), cuda_version="")
    assert "ZBYT STARA" in summary
    assert "compute 6.1" in summary
    assert "NIE" in summary and "pomoże" in summary
    assert "Turing" in summary  # z MIN_CARD
    assert "§12" in summary


def test_hardware_summary_no_torch_says_install_torch() -> None:
    summary = _hardware_summary(_hw("no_torch"), cuda_version="")
    assert summary.startswith("ℹ️")
    assert "PyTorch" in summary
    assert "uv sync" in summary


def test_hardware_summary_no_torch_old_card_warns_pointless() -> None:
    """no_torch + znana stara karta (compute 6.1) → dopisek, że instalacja torcha nie pomoże."""
    summary = _hardware_summary(_hw("no_torch", 8, compute_cap="6.1"), cuda_version="")
    assert "uv sync" in summary  # nadal podstawowa podpowiedź
    assert "zbyt stara na GPU" in summary
    assert "compute 6.1" in summary


def test_hardware_summary_no_torch_ok_card_no_warning() -> None:
    """no_torch + karta dość nowa (compute 8.6) → BEZ dopisku o za starej karcie."""
    summary = _hardware_summary(_hw("no_torch", 12, compute_cap="8.6"), cuda_version="")
    assert "zbyt stara na GPU" not in summary


def test_hardware_summary_no_torch_unknown_cap_no_warning() -> None:
    """no_torch + nieznana compute_cap → nie zgadujemy, BEZ dopisku."""
    summary = _hardware_summary(_hw("no_torch", 8, compute_cap=""), cuda_version="")
    assert "zbyt stara na GPU" not in summary


def test_hardware_summary_ok_lists_card() -> None:
    info = HardwareInfo("ok", "RTX 3090", 24.0, "Ampere (8.6)", "")
    summary = _hardware_summary(info, cuda_version="13.0")
    assert summary.startswith("✅ CUDA 13.0")
    assert "RTX 3090" in summary
    assert "24 GB" in summary


def test_hardware_summary_no_gpu_includes_min_card() -> None:
    summary = _hardware_summary(_hw("no_gpu"), cuda_version="")
    assert summary.startswith("ℹ️")
    assert "CPU" in summary
    assert "Turing" in summary  # tekst MIN_CARD
    assert "GTX 16" in summary
