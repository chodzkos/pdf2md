"""Testy CLI pdf2md."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from pdf2md.cli.main import cli
from pdf2md.core import config


@pytest.fixture()
def cli_test_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Izoluje config i kosztowne sprawdzenia środowiska dla CLI."""
    config_dir = tmp_path / "config"
    config_file = config_dir / "config.toml"
    monkeypatch.setattr(config, "_CONFIG_DIR", config_dir)
    monkeypatch.setattr(config, "_CONFIG_FILE", config_file)
    monkeypatch.setattr(config, "_settings_cache", None)
    monkeypatch.setattr("pdf2md.cli.main.setup_logging", lambda verbose=False: None)
    monkeypatch.setattr(
        "pdf2md.llm.ollama_provider.OllamaProvider.is_available", lambda self: False
    )
    monkeypatch.setattr(
        "pdf2md.cli.main.detect_pdf_type",
        lambda path: {
            "type": "native",
            "pages": 1,
            "text_pages": 1,
            "scan_pages": 0,
            "reason": "",
        },
    )
    monkeypatch.setattr("pdf2md.cli.main.check_all", lambda: _fake_dependencies())
    return tmp_path


def _fake_dependencies() -> dict[str, Any]:
    return {
        "system": {"os": "Linux", "platform": "Linux-test", "python": "3.13"},
        "gpu": {
            "torch_available": False,
            "cuda_available": False,
            "device_name": "",
            "cuda_version": "",
        },
        "tesseract": {"available": False, "version": "", "languages": []},
        "poppler": False,
        "pandoc": False,
        "ollama": {"available": False, "models": []},
    }


def test_list_engines_returns_zero(cli_test_env: Path) -> None:
    result = CliRunner().invoke(cli, ["list-engines"])

    assert result.exit_code == 0


def test_list_llm_returns_zero(cli_test_env: Path) -> None:
    result = CliRunner().invoke(cli, ["list-llm"])

    assert result.exit_code == 0


def test_doctor_returns_zero(cli_test_env: Path) -> None:
    result = CliRunner().invoke(cli, ["doctor"])

    assert result.exit_code == 0


def test_convert_dry_run_does_not_create_markdown(cli_test_env: Path) -> None:
    pdf = cli_test_env / "plik.pdf"
    pdf.write_bytes(b"%PDF-1.7\n%%EOF\n")
    expected_output = pdf.with_suffix(".md")

    result = CliRunner().invoke(cli, ["convert", str(pdf), "--dry-run"])

    assert result.exit_code == 0
    assert not expected_output.exists()


def test_config_show_returns_zero(cli_test_env: Path) -> None:
    result = CliRunner().invoke(cli, ["config", "show"])

    assert result.exit_code == 0


def test_convert_missing_file_returns_error(cli_test_env: Path) -> None:
    missing = cli_test_env / "nieistniejacy.pdf"

    result = CliRunner().invoke(cli, ["convert", str(missing)])

    assert result.exit_code != 0
    assert "Plik nie istnieje" in result.output


def test_convert_unknown_engine_returns_error(cli_test_env: Path) -> None:
    pdf = cli_test_env / "plik.pdf"
    pdf.write_bytes(b"%PDF-1.7\n%%EOF\n")

    result = CliRunner().invoke(cli, ["convert", str(pdf), "--engine", "nieznany"])

    assert result.exit_code != 0
    assert "Nieznany silnik" in result.output
