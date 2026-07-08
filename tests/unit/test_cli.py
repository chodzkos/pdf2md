"""Testy CLI pdf2md."""

from __future__ import annotations

import importlib.metadata
import io
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import click
import pytest
from click.testing import CliRunner

from pdf2md.cli.main import cli
from pdf2md.core import config, history
from pdf2md.core.image_extraction import ExtractedImage
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
        "calibre": False,
        "ollama": {"available": False, "models": []},
    }


def test_list_engines_returns_zero(cli_test_env: Path) -> None:
    result = CliRunner().invoke(cli, ["list-engines"])

    assert result.exit_code == 0


def test_list_llm_returns_zero(cli_test_env: Path) -> None:
    result = CliRunner().invoke(cli, ["list-llm"])

    assert result.exit_code == 0


def test_history_command_lists_recent(cli_test_env: Path) -> None:
    history.record(
        input_path="plik.pdf",
        engine="Marker",
        output_path="plik.md",
        status="ok",
        duration_s=1.0,
    )

    result = CliRunner().invoke(cli, ["history"])

    assert result.exit_code == 0
    assert "Historia konwersji" in result.output
    assert "Marker" in result.output
    assert "plik.pdf" in result.output


def test_history_command_exports_csv(cli_test_env: Path) -> None:
    csv_path = cli_test_env / "history.csv"
    history.record(
        input_path="marker.pdf",
        engine="Marker",
        output_path="marker.md",
        status="ok",
        duration_s=1.0,
    )
    history.record(
        input_path="docling.pdf",
        engine="Docling",
        output_path="docling.md",
        status="ok",
        duration_s=1.0,
    )

    result = CliRunner().invoke(
        cli,
        ["history", "--engine", "docling", "--csv", str(csv_path)],
    )

    assert result.exit_code == 0
    exported = csv_path.read_text(encoding="utf-8")
    assert "docling.pdf" in exported
    assert "marker.pdf" not in exported


def test_history_command_clear_requires_confirmation(cli_test_env: Path) -> None:
    history.record(
        input_path="plik.pdf",
        engine="Marker",
        output_path="plik.md",
        status="ok",
        duration_s=1.0,
    )

    result = CliRunner().invoke(cli, ["history", "--clear"], input="y\n")

    assert result.exit_code == 0
    assert "Wyczyszczono historię" in result.output
    assert history.list_recent() == []


def test_doctor_returns_zero(cli_test_env: Path) -> None:
    result = CliRunner().invoke(cli, ["doctor"])

    assert result.exit_code == 0
    assert "CUDA smoke test" in result.output


def test_doctor_plain_renders_without_ansi(cli_test_env: Path) -> None:
    result = CliRunner().invoke(cli, ["doctor", "--plain"])

    assert result.exit_code == 0
    # Treść merytoryczna bez zmian wobec trybu zwykłego.
    assert "CUDA smoke test" in result.output
    # Brak sekwencji ANSI — wyjście nadaje się pod stabilne snapshoty.
    assert "\x1b[" not in result.output


def test_doctor_plain_is_stable_between_runs(cli_test_env: Path) -> None:
    first = CliRunner().invoke(cli, ["doctor", "--plain"])
    second = CliRunner().invoke(cli, ["doctor", "--plain"])

    assert first.exit_code == 0
    assert second.exit_code == 0
    assert first.output == second.output


def test_doctor_plain_via_env(cli_test_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCTOR_PLAIN", "1")
    result = CliRunner().invoke(cli, ["doctor"])

    assert result.exit_code == 0
    assert "\x1b[" not in result.output


def test_windows_stdio_reconfigure_handles_cp1250_streams(
    cli_test_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pdf2md.cli import main as cli_main

    stdout = io.TextIOWrapper(io.BytesIO(), encoding="cp1250")
    stderr = io.TextIOWrapper(io.BytesIO(), encoding="cp1250")
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(sys, "stdout", stdout)
    monkeypatch.setattr(sys, "stderr", stderr)

    cli_main._reconfigure_windows_stdio()

    assert sys.stdout.encoding is not None
    assert sys.stderr.encoding is not None
    assert sys.stdout.encoding.lower().replace("-", "") == "utf8"
    assert sys.stderr.encoding.lower().replace("-", "") == "utf8"
    assert sys.stdout.errors == "replace"
    assert sys.stderr.errors == "replace"


def test_doctor_plain_sorts_ollama_models(
    cli_test_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    deps = _fake_dependencies()
    deps["ollama"] = {"available": True, "models": ["qwen3:14b", "llama3", "gemma"]}
    monkeypatch.setattr("pdf2md.cli.main.check_all", lambda: deps)

    result = CliRunner().invoke(cli, ["doctor", "--plain"])

    assert result.exit_code == 0
    # Kolejność modeli z API Ollamy bywa niestabilna — w trybie plain sortujemy.
    models_line = next(line for line in result.output.splitlines() if "gemma" in line)
    assert models_line.index("gemma") < models_line.index("llama3") < models_line.index("qwen3")


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

    def fake_export(markdown: str, output_path: Path, epub_backend: str = "pandoc") -> Path:
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


def test_convert_profile_applies_conversion_preset(
    cli_test_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pdf = cli_test_env / "plik.pdf"
    pdf.write_bytes(b"%PDF-1.7\n%%EOF\n")
    profile = cli_test_env / "preset.yaml"
    profile.write_text(
        "name: preset\n"
        "conversion: {engine: fake, lang: eng, llm: claude, "
        "llm_model: sonnet, llm_mode: by_page}\n",
        encoding="utf-8",
    )
    output_dir = cli_test_env / "out"
    calls: dict[str, object] = {}
    fake_engine = SimpleNamespace(
        name="FakeEngine",
        supports_ocr=True,
        is_available=lambda: True,
    )
    fake_llm = SimpleNamespace(name="Claude")

    class FakeConverter:
        def convert(self, *args: object, **kwargs: object) -> ConversionResult:
            calls["convert"] = (args, kwargs)
            return ConversionResult(markdown="# wynik", engine_used="FakeEngine", pages=1)

    def fake_export(markdown: str, output_path: Path, epub_backend: str = "pandoc") -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown, encoding="utf-8")
        return output_path

    def fake_select_llm(name: str, model: str | None) -> object:
        calls["llm"] = (name, model)
        return fake_llm

    monkeypatch.setattr(
        "pdf2md.cli.main._select_engine",
        lambda name: calls.setdefault("engine", name) and fake_engine,
    )
    monkeypatch.setattr("pdf2md.cli.main._select_llm", fake_select_llm)
    monkeypatch.setattr("pdf2md.cli.main.Converter", FakeConverter)
    monkeypatch.setattr("pdf2md.cli.main._export_result", fake_export)

    result = CliRunner().invoke(
        cli,
        ["convert", str(pdf), "--profile", str(profile), "--output-dir", str(output_dir)],
    )

    assert result.exit_code == 0
    assert calls["engine"] == "fake"
    assert calls["llm"] == ("claude", "sonnet")
    args, kwargs = calls["convert"]
    assert args == (str(pdf), fake_engine)
    assert kwargs["llm"] is fake_llm
    assert kwargs["llm_mode"] == "by_page"
    assert kwargs["engine_kwargs"] == {"lang": "eng"}


def test_convert_explicit_options_override_profile(
    cli_test_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pdf = cli_test_env / "plik.pdf"
    pdf.write_bytes(b"%PDF-1.7\n%%EOF\n")
    profile = cli_test_env / "preset.yaml"
    profile.write_text(
        "name: preset\nconversion: {engine: fake, lang: eng, llm: none}\n",
        encoding="utf-8",
    )
    output_dir = cli_test_env / "out"
    calls: dict[str, object] = {}
    fake_engine = SimpleNamespace(
        name="OverrideEngine",
        supports_ocr=True,
        is_available=lambda: True,
    )

    class FakeConverter:
        def convert(self, *args: object, **kwargs: object) -> ConversionResult:
            calls["convert"] = (args, kwargs)
            return ConversionResult(markdown="# wynik", engine_used="OverrideEngine", pages=1)

    def fake_export(markdown: str, output_path: Path, epub_backend: str = "pandoc") -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown, encoding="utf-8")
        return output_path

    monkeypatch.setattr(
        "pdf2md.cli.main._select_engine",
        lambda name: calls.setdefault("engine", name) and fake_engine,
    )
    monkeypatch.setattr("pdf2md.cli.main.Converter", FakeConverter)
    monkeypatch.setattr("pdf2md.cli.main._export_result", fake_export)

    result = CliRunner().invoke(
        cli,
        [
            "convert",
            str(pdf),
            "--profile",
            str(profile),
            "--engine",
            "override",
            "--lang",
            "pol",
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    assert calls["engine"] == "override"
    _args, kwargs = calls["convert"]
    assert kwargs["engine_kwargs"] == {"lang": "pol"}


def test_convert_accepts_image_input(
    cli_test_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pil_image = pytest.importorskip("PIL.Image")
    image = cli_test_env / "skan.png"
    pil_image.new("RGB", (400, 160), "white").save(image, format="PNG")
    output_dir = cli_test_env / "out"
    fake_engine = SimpleNamespace(
        name="FakeOCR",
        supports_ocr=True,
        is_available=lambda: True,
    )

    class FakeConverter:
        def convert(self, *args: object, **kwargs: object) -> ConversionResult:
            return ConversionResult(markdown="tekst z obrazu", engine_used="FakeOCR", pages=1)

    def fake_export(markdown: str, output_path: Path, epub_backend: str = "pandoc") -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown, encoding="utf-8")
        return output_path

    monkeypatch.setattr("pdf2md.cli.main._select_engine", lambda name: fake_engine)
    monkeypatch.setattr("pdf2md.cli.main.Converter", FakeConverter)
    monkeypatch.setattr("pdf2md.cli.main._export_result", fake_export)

    result = CliRunner().invoke(
        cli,
        ["convert", str(image), "--engine", "fake", "--output-dir", str(output_dir)],
    )

    assert result.exit_code == 0
    assert (output_dir / "skan.md").read_text(encoding="utf-8") == "tekst z obrazu"


def test_convert_rejects_unsupported_input(cli_test_env: Path) -> None:
    text = cli_test_env / "notatka.txt"
    text.write_text("tekst", encoding="utf-8")

    result = CliRunner().invoke(cli, ["convert", str(text)])

    assert result.exit_code != 0
    assert "Nieobsługiwany format wejściowy" in result.output


def test_convert_extract_images_adds_markdown_references(
    cli_test_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pdf = cli_test_env / "plik.pdf"
    pdf.write_bytes(b"%PDF-1.7\n%%EOF\n")
    output_dir = cli_test_env / "out"
    calls: dict[str, object] = {}
    fake_engine = SimpleNamespace(
        name="FakeEngine",
        supports_ocr=False,
        is_available=lambda: True,
    )

    class FakeConverter:
        def convert(self, *args: object, **kwargs: object) -> ConversionResult:
            return ConversionResult(markdown="# wynik", engine_used="FakeEngine", pages=1)

    def fake_extract(pdf_path: Path, images_dir: Path, *, min_size: int) -> list[ExtractedImage]:
        calls["extract"] = (pdf_path, images_dir, min_size)
        images_dir.mkdir(parents=True, exist_ok=True)
        image_path = images_dir / "page1_img1.png"
        image_path.write_bytes(b"png")
        return [ExtractedImage(path=image_path, page=1, index=1, width=120, height=100)]

    def fake_export(markdown: str, output_path: Path, epub_backend: str = "pandoc") -> Path:
        calls["export"] = (markdown, output_path, epub_backend)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown, encoding="utf-8")
        return output_path

    monkeypatch.setattr("pdf2md.cli.main._select_engine", lambda name: fake_engine)
    monkeypatch.setattr("pdf2md.cli.main.Converter", FakeConverter)
    monkeypatch.setattr("pdf2md.cli.main.extract_pdf_images", fake_extract)
    monkeypatch.setattr("pdf2md.cli.main._export_result", fake_export)

    result = CliRunner().invoke(
        cli,
        [
            "convert",
            str(pdf),
            "--engine",
            "fake",
            "--output-dir",
            str(output_dir),
            "--extract-images",
            "--image-min-size",
            "90",
        ],
    )

    assert result.exit_code == 0
    output_path = output_dir / "plik.md"
    assert "![](<plik_images/page1_img1.png>)" in output_path.read_text(encoding="utf-8")
    assert calls["extract"] == (pdf, output_dir / "plik_images", 90)


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


def test_select_llm_errors_for_unavailable_provider(
    cli_test_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pdf2md.cli import main as cli_main

    provider = SimpleNamespace(
        name="OpenAI",
        requires_api_key=True,
        default_model="gpt",
        description="",
        is_available=lambda: False,
    )
    monkeypatch.setattr(cli_main, "_find_provider", lambda name: provider)

    with pytest.raises(click.ClickException, match="Dostawca LLM nie jest gotowy"):
        cli_main._select_llm("openai", None)


def test_select_llm_override_sets_run_model_without_persisting(
    cli_test_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """--llm-model nadpisuje model TYLKO dla tego uruchomienia (bind_model, nie utrwala configu)."""
    from pdf2md.cli import main as cli_main
    from pdf2md.core.config import get_settings
    from pdf2md.llm.ollama_provider import OllamaProvider

    provider = OllamaProvider()
    monkeypatch.setattr(cli_main, "_find_provider", lambda name: provider)
    monkeypatch.setattr(provider, "is_available", lambda: True)
    saved: list[object] = []
    monkeypatch.setattr(cli_main, "save_settings", lambda s: saved.append(s), raising=False)

    before = get_settings().ollama_model
    result = cli_main._select_llm("ollama", "override-na-run")

    assert result is not None
    assert result.model_override == "override-na-run"  # override wygrywa dla tego uruchomienia
    assert provider.model_override is None  # singleton z rejestru nietknięty
    assert get_settings().ollama_model == before  # config bez zmian
    assert saved == []  # nic nie utrwalono na stałe
