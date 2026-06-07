"""Testy adaptera MinerU."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from pdf2md.engines import mineru_engine
from pdf2md.engines.mineru_engine import MinerUEngine


def test_is_available_uses_mineru_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    """Dostepnosc MinerU jest wykrywana po aktualnej komendzie CLI."""
    calls: list[str] = []

    def fake_which(command: str) -> str | None:
        calls.append(command)
        return "/usr/bin/mineru" if command == "mineru" else None

    monkeypatch.setattr(mineru_engine.shutil, "which", fake_which)

    assert MinerUEngine().is_available() is True
    assert calls == ["mineru"]


def test_convert_runs_mineru_cli_from_which(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Konwersja uruchamia pelna sciezke do mineru znaleziona przez shutil.which."""
    pdf_path = tmp_path / "input.pdf"
    output_dir = tmp_path / "out"
    markdown_path = output_dir / "result.md"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    calls: list[list[str]] = []

    monkeypatch.setattr(
        mineru_engine.shutil,
        "which",
        lambda command: "/opt/bin/mineru" if command == "mineru" else None,
    )
    monkeypatch.setattr(MinerUEngine, "_page_count", lambda _self, _path: 1)

    def fake_run(
        command: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        assert check is True
        assert capture_output is True
        assert text is True
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text("# wynik\n", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(mineru_engine.subprocess, "run", fake_run)

    result = MinerUEngine().convert(str(pdf_path), output_dir=str(output_dir))

    assert calls == [["/opt/bin/mineru", "-p", str(pdf_path), "-o", str(output_dir)]]
    assert result.markdown == "# wynik\n"
    assert result.pages == 1
    assert result.engine_used == "MinerU"


def test_convert_error_mentions_uv_tool_install(monkeypatch: pytest.MonkeyPatch) -> None:
    """Brak CLI pokazuje instrukcje instalacji izolowanego narzedzia uv."""
    monkeypatch.setattr(mineru_engine.shutil, "which", lambda _command: None)

    with pytest.raises(RuntimeError, match=r"uv tool install mineru --with mineru\[all\]"):
        MinerUEngine().convert("missing.pdf")
