"""Testy porównywarki silników (F07) — metryki, orkiestracja i komenda CLI."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from pdf2md.cli.main import cli
from pdf2md.core.compare import compare_engines, compute_metrics, make_llm_scorer
from pdf2md.engines.base import ConversionEngine, ConversionResult

_TABLE_MD = "# Nagłówek\n\n## Podtytuł\n\n| a | b |\n| --- | --- |\n| 1 | 2 |\n"


@pytest.fixture()
def cli_test_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Izoluje config i wycisza logowanie dla komendy CLI compare."""
    from pdf2md.core import config

    config_dir = tmp_path / "config"
    monkeypatch.setattr(config, "_CONFIG_DIR", config_dir)
    monkeypatch.setattr(config, "_CONFIG_FILE", config_dir / "config.toml")
    monkeypatch.setattr(config, "_settings_cache", None)
    monkeypatch.setattr("pdf2md.cli.main.setup_logging", lambda verbose=False: None)
    return tmp_path


class FakeEngine(ConversionEngine):
    """Silnik-atrapa: zwraca stały Markdown albo rzuca wyjątek."""

    def __init__(
        self,
        name: str,
        *,
        markdown: str = "# Tytuł\n\ntekst\n",
        available: bool = True,
        ocr: bool = False,
        raises: Exception | None = None,
    ) -> None:
        self.name = name
        self.description = "atrapa"
        self.supports_ocr = ocr
        self.supports_llm = False
        self.requires_gpu = False
        self._markdown = markdown
        self._available = available
        self._raises = raises

    def is_available(self) -> bool:
        return self._available

    def convert(self, pdf_path: str, **kwargs: object) -> ConversionResult:
        if self._raises is not None:
            raise self._raises
        return ConversionResult(markdown=self._markdown, engine_used=self.name, pages=1)


def _make_pdf(tmp_path: Path) -> Path:
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.7\n%%EOF\n")
    return pdf


# ── metryki ──────────────────────────────────────────────────────────────────


def test_compute_metrics_counts_headings_tables_chars() -> None:
    md = "# A\n\nzwykły tekst\n\n## B\n\n| x | y |\n|---|---|\n| 1 | 2 |\n\n---\n\n#niehasztag\n"
    metrics = compute_metrics(md)

    assert metrics.headings == 2  # '# A' i '## B'; '#niehasztag' i '---' nie liczą się
    assert metrics.tables == 1  # jeden wiersz separatora = jedna tabela
    assert metrics.chars == len(md)


def test_compute_metrics_empty() -> None:
    metrics = compute_metrics("")
    assert metrics == compute_metrics("")
    assert metrics.headings == 0
    assert metrics.tables == 0
    assert metrics.chars == 0


# ── orkiestracja ─────────────────────────────────────────────────────────────


def test_compare_engines_writes_files_and_measures(tmp_path: Path) -> None:
    pdf = _make_pdf(tmp_path)
    out_dir = tmp_path / "cmp"
    ok = FakeEngine("Alpha", markdown=_TABLE_MD)
    bad = FakeEngine("Beta", raises=RuntimeError("boom"))

    results = compare_engines(pdf, [ok, bad], out_dir)

    assert [r.engine for r in results] == ["Alpha", "Beta"]
    good, failed = results

    assert good.status == "ok"
    assert good.output_path == out_dir / "doc_Alpha.md"
    assert good.output_path is not None
    assert good.output_path.read_text(encoding="utf-8") == _TABLE_MD
    assert good.metrics is not None
    assert good.metrics.headings == 2
    assert good.metrics.tables == 1
    assert good.duration_s >= 0.0

    assert failed.status == "error"
    assert failed.error is not None
    assert "boom" in failed.error
    assert not (out_dir / "doc_Beta.md").exists()


def test_compare_engines_runs_llm_scorer(tmp_path: Path) -> None:
    pdf = _make_pdf(tmp_path)
    results = compare_engines(
        pdf,
        [FakeEngine("Alpha")],
        tmp_path / "cmp",
        llm_scorer=lambda _md: 73,
    )
    assert results[0].llm_score == 73


# ── ocena LLM ────────────────────────────────────────────────────────────────


class _StubProvider:
    def __init__(self, reply: str, *, boom: bool = False) -> None:
        self._reply = reply
        self._boom = boom

    def correct(self, text: str, *, system_prompt: str, temperature: float = 0.0) -> str:
        if self._boom:
            raise RuntimeError("api down")
        return self._reply


def test_llm_scorer_parses_number() -> None:
    score = make_llm_scorer(_StubProvider("Ocena: 87/100"))  # type: ignore[arg-type]
    assert score("# doc") == 87


def test_llm_scorer_clamps_above_100() -> None:
    score = make_llm_scorer(_StubProvider("150"))  # type: ignore[arg-type]
    assert score("# doc") == 100


def test_llm_scorer_none_without_number() -> None:
    score = make_llm_scorer(_StubProvider("brak oceny"))  # type: ignore[arg-type]
    assert score("# doc") is None


def test_llm_scorer_none_on_exception() -> None:
    score = make_llm_scorer(_StubProvider("", boom=True))  # type: ignore[arg-type]
    assert score("# doc") is None


def test_llm_scorer_none_on_empty_markdown() -> None:
    score = make_llm_scorer(_StubProvider("100"))  # type: ignore[arg-type]
    assert score("   \n  ") is None


# ── komenda CLI ──────────────────────────────────────────────────────────────


def test_compare_command_renders_table_and_writes(
    cli_test_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pdf2md.cli.main import engine_registry

    pdf = _make_pdf(cli_test_env)
    out_dir = cli_test_env / "cmp"
    fakes = [
        FakeEngine("Alpha", markdown=_TABLE_MD),
        FakeEngine("Beta", raises=RuntimeError("padło")),
    ]
    monkeypatch.setattr(engine_registry, "get_all", lambda: fakes)
    monkeypatch.setattr(engine_registry, "get_available", lambda: fakes)

    result = CliRunner().invoke(cli, ["compare", str(pdf), "--output-dir", str(out_dir)])

    assert result.exit_code == 0, result.output
    assert (out_dir / "doc_Alpha.md").read_text(encoding="utf-8") == _TABLE_MD
    assert not (out_dir / "doc_Beta.md").exists()
    assert "Porównanie silników" in result.output
    assert "Alpha" in result.output
    assert "Beta" in result.output


def test_compare_command_fails_when_all_engines_fail(
    cli_test_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pdf2md.cli.main import engine_registry

    pdf = _make_pdf(cli_test_env)
    fakes = [FakeEngine("Alpha", raises=RuntimeError("padło"))]
    monkeypatch.setattr(engine_registry, "get_all", lambda: fakes)
    monkeypatch.setattr(engine_registry, "get_available", lambda: fakes)

    result = CliRunner().invoke(cli, ["compare", str(pdf), "--output-dir", str(cli_test_env / "c")])

    assert result.exit_code != 0
    assert "Żaden silnik" in result.output


def test_compare_command_errors_when_no_engines(
    cli_test_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pdf2md.cli.main import engine_registry

    pdf = _make_pdf(cli_test_env)
    monkeypatch.setattr(engine_registry, "get_all", list)
    monkeypatch.setattr(engine_registry, "get_available", list)

    result = CliRunner().invoke(cli, ["compare", str(pdf)])

    assert result.exit_code != 0
    assert "Brak dostępnych silników" in result.output
