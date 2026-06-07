"""Testy CLI pdf2md."""

from __future__ import annotations

import importlib.metadata
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import click
import pytest
from click.testing import CliRunner

from pdf2md.cli.main import cli
from pdf2md.core import config
from pdf2md.engines.base import ConversionResult


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
            "cuda_usable": False,
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
    assert "CUDA smoke test" in result.output


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


def test_config_set_accepts_docling_section_key(cli_test_env: Path) -> None:
    result = CliRunner().invoke(cli, ["config", "set", "docling.docling_device", "cuda"])

    assert result.exit_code == 0
    assert "docling_device = cuda" in result.output


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


def test_convert_rejects_output_and_output_dir(cli_test_env: Path) -> None:
    pdf = cli_test_env / "plik.pdf"
    pdf.write_bytes(b"%PDF-1.7\n%%EOF\n")

    result = CliRunner().invoke(
        cli,
        ["convert", str(pdf), "--output", "out.md", "--output-dir", "out"],
    )

    assert result.exit_code != 0
    assert "Użyj --output albo --output-dir" in result.output


def test_convert_runs_engine_and_exports_result(
    cli_test_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pdf = cli_test_env / "plik.pdf"
    pdf.write_bytes(b"%PDF-1.7\n%%EOF\n")
    output_dir = cli_test_env / "out"
    calls: dict[str, object] = {}
    fake_engine = SimpleNamespace(
        name="FakeEngine",
        supports_ocr=True,
        is_available=lambda: True,
    )

    class FakeConverter:
        def convert(self, *args: object, **kwargs: object) -> ConversionResult:
            calls["convert"] = (args, kwargs)
            return ConversionResult(markdown="# wynik", engine_used="FakeEngine", pages=1)

    def fake_export(markdown: str, output_path: Path) -> Path:
        calls["export"] = (markdown, output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown, encoding="utf-8")
        return output_path

    monkeypatch.setattr("pdf2md.cli.main._select_engine", lambda name: fake_engine)
    monkeypatch.setattr("pdf2md.cli.main.Converter", FakeConverter)
    monkeypatch.setattr("pdf2md.cli.main._export_result", fake_export)

    result = CliRunner().invoke(
        cli,
        ["convert", str(pdf), "--engine", "fake", "--output-dir", str(output_dir), "--verbose"],
    )

    assert result.exit_code == 0
    assert (output_dir / "plik.md").read_text(encoding="utf-8") == "# wynik"
    assert calls["export"] == ("# wynik", output_dir / "plik.md")
    args, kwargs = calls["convert"]
    assert args == (str(pdf), fake_engine)
    assert kwargs["engine_kwargs"] == {"lang": "pol+eng"}


def test_convert_errors_when_selected_engine_unavailable(
    cli_test_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pdf = cli_test_env / "plik.pdf"
    pdf.write_bytes(b"%PDF-1.7\n%%EOF\n")
    fake_engine = SimpleNamespace(
        name="FakeEngine",
        supports_ocr=False,
        is_available=lambda: False,
    )
    monkeypatch.setattr("pdf2md.cli.main._select_engine", lambda name: fake_engine)

    result = CliRunner().invoke(cli, ["convert", str(pdf), "--engine", "fake"])

    assert result.exit_code != 0
    assert "Silnik nie jest dostępny" in result.output


def test_config_set_rejects_unknown_key(cli_test_env: Path) -> None:
    result = CliRunner().invoke(cli, ["config", "set", "nie.ma", "wartosc"])

    assert result.exit_code != 0
    assert "Nieznany klucz" in result.output


def test_config_set_rejects_invalid_bool(cli_test_env: Path) -> None:
    result = CliRunner().invoke(cli, ["config", "set", "llm.enabled", "maybe"])

    assert result.exit_code != 0
    assert "musi być bool" in result.output


def test_config_set_rejects_invalid_int(cli_test_env: Path) -> None:
    result = CliRunner().invoke(cli, ["config", "set", "marker.marker_workers", "duzo"])

    assert result.exit_code != 0
    assert "liczbą całkowitą" in result.output


def test_config_edit_uses_editor(
    cli_test_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setenv("EDITOR", "code --wait")

    def fake_run(command: list[str], *, check: bool) -> SimpleNamespace:
        calls.append(command)
        assert check is False
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("pdf2md.cli.main.subprocess.run", fake_run)

    result = CliRunner().invoke(cli, ["config", "edit"])

    assert result.exit_code == 0
    assert calls == [["code", "--wait", str(config._CONFIG_FILE)]]


def test_cli_helper_functions(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from pdf2md.cli import main as cli_main

    first = tmp_path / "a.pdf"
    second = tmp_path / "b.pdf"
    first.write_bytes(b"pdf")
    second.write_bytes(b"pdf")

    expanded = cli_main._expand_files((str(tmp_path / "*.pdf"), str(first)))
    assert expanded == [first, second]
    assert cli_main._resolve_output_paths([first], str(tmp_path / "out.md"), None) == {
        first: tmp_path / "out.md"
    }
    assert cli_main._resolve_output_paths([first, second], str(tmp_path / "out"), None) == {
        first: tmp_path / "out" / "a.md",
        second: tmp_path / "out" / "b.md",
    }
    assert cli_main._mask_secret("") == "brak"
    assert cli_main._mask_secret("abcd") == "***"
    assert cli_main._mask_secret("abcd1234efgh") == "abcd...efgh"

    assert cli_main._provider_key(SimpleNamespace(name="My GPT Provider")) == "openai"
    assert cli_main._provider_key(SimpleNamespace(name="Local Gemini")) == "gemini"
    assert cli_main._provider_key(SimpleNamespace(name="Other Name")) == "othername"

    monkeypatch.setattr(
        cli_main.importlib.metadata,
        "version",
        lambda package: (_ for _ in ()).throw(importlib.metadata.PackageNotFoundError),
    )
    assert cli_main._package_installed("missing") is False


def test_select_llm_sets_model_and_requires_availability(
    cli_test_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pdf2md.cli import main as cli_main
    from pdf2md.core.config import Settings

    provider = SimpleNamespace(
        name="OpenAI",
        requires_api_key=True,
        default_model="gpt",
        description="",
        is_available=lambda: True,
    )
    settings = Settings()
    monkeypatch.setattr(cli_main, "_find_provider", lambda name: provider)
    selected = cli_main._select_llm("openai", "gpt-test", settings)

    assert selected is provider
    assert settings.openai_model == "gpt-test"


def test_select_llm_errors_for_unavailable_provider(
    cli_test_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pdf2md.cli import main as cli_main
    from pdf2md.core.config import Settings

    provider = SimpleNamespace(
        name="OpenAI",
        requires_api_key=True,
        default_model="gpt",
        description="",
        is_available=lambda: False,
    )
    monkeypatch.setattr(cli_main, "_find_provider", lambda name: provider)

    with pytest.raises(click.ClickException, match="Dostawca LLM nie jest gotowy"):
        cli_main._select_llm("openai", None, Settings())
