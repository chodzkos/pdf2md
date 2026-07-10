"""Testy adaptera MinerU."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

from pdf2md.engines import mineru_engine
from pdf2md.engines.mineru_engine import MinerUEngine


class _FakeSettings:
    def __init__(self, backend: str = "pipeline") -> None:
        self.mineru_backend = backend


def _patch_env(monkeypatch: pytest.MonkeyPatch, backend: str = "pipeline") -> None:
    monkeypatch.setattr(mineru_engine, "get_settings", lambda: _FakeSettings(backend))


def _make_fake_run(
    calls: list[Any],
    markdown_path: Path,
    envs: list[Any] | None = None,
) -> Any:
    def fake_run(
        command: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        env: dict[str, str] | None = None,
        creationflags: int = 0,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        if envs is not None:
            envs.append(env)
        assert check is True
        assert capture_output is True
        assert text is True
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text("# wynik\n", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0)

    return fake_run


def test_is_available_uses_mineru_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    """Dostepnosc MinerU jest wykrywana po aktualnej komendzie CLI."""
    calls: list[str] = []

    def fake_which(command: str) -> str | None:
        calls.append(command)
        return "/usr/bin/mineru" if command == "mineru" else None

    monkeypatch.setattr(mineru_engine.shutil, "which", fake_which)

    assert MinerUEngine().is_available() is True
    assert calls == ["mineru"]


def test_convert_runs_mineru_cli_with_pipeline_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Domyślny backend pipeline: komenda zawiera -b pipeline, env nie ustawia flashinfer."""
    pdf_path = tmp_path / "input.pdf"
    output_dir = tmp_path / "out"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    calls: list[list[str]] = []
    envs: list[Any] = []

    _patch_env(monkeypatch, "pipeline")
    monkeypatch.setattr(
        mineru_engine.shutil,
        "which",
        lambda command: "/opt/bin/mineru" if command == "mineru" else None,
    )
    monkeypatch.setattr(MinerUEngine, "_page_count", lambda _self, _path: 1)
    monkeypatch.setattr(
        mineru_engine.subprocess, "run", _make_fake_run(calls, output_dir / "result.md", envs)
    )

    result = MinerUEngine().convert(str(pdf_path), output_dir=str(output_dir))

    assert calls == [
        ["/opt/bin/mineru", "-p", str(pdf_path), "-o", str(output_dir), "-b", "pipeline"]
    ]
    assert envs == [None]
    assert result.markdown == "# wynik\n"
    assert result.pages == 1
    assert result.engine_used == "MinerU"


def test_convert_vlm_backend_sets_flashinfer_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Backend vlm: komenda zawiera -b vlm i env ma VLLM_USE_FLASHINFER_SAMPLER=0."""
    pdf_path = tmp_path / "input.pdf"
    output_dir = tmp_path / "out"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    calls: list[list[str]] = []
    envs: list[Any] = []

    _patch_env(monkeypatch, "vlm")
    monkeypatch.setattr(
        mineru_engine.shutil,
        "which",
        lambda command: "/opt/bin/mineru" if command == "mineru" else None,
    )
    monkeypatch.setattr(MinerUEngine, "_page_count", lambda _self, _path: 1)
    monkeypatch.setattr(
        mineru_engine.subprocess, "run", _make_fake_run(calls, output_dir / "result.md", envs)
    )

    MinerUEngine().convert(str(pdf_path), output_dir=str(output_dir))

    assert calls == [["/opt/bin/mineru", "-p", str(pdf_path), "-o", str(output_dir), "-b", "vlm"]]
    assert len(envs) == 1
    assert envs[0] is not None
    assert envs[0]["VLLM_USE_FLASHINFER_SAMPLER"] == "0"


def test_convert_logs_stderr_on_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """CalledProcessError: loguje stderr/stdout i podnosi RuntimeError z końcówką stderr."""
    pdf_path = tmp_path / "input.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    _patch_env(monkeypatch, "pipeline")
    monkeypatch.setattr(
        mineru_engine.shutil,
        "which",
        lambda command: "/opt/bin/mineru" if command == "mineru" else None,
    )

    def fake_run_fail(command: list[str], **kwargs: Any) -> None:
        raise subprocess.CalledProcessError(
            returncode=1,
            cmd=command,
            output="some stdout",
            stderr="fatal: something went wrong at the end",
        )

    monkeypatch.setattr(mineru_engine.subprocess, "run", fake_run_fail)

    with pytest.raises(RuntimeError, match="something went wrong at the end"):
        MinerUEngine().convert(str(pdf_path), output_dir=str(tmp_path / "out"))


def test_convert_error_mentions_uv_tool_install(monkeypatch: pytest.MonkeyPatch) -> None:
    """Brak CLI pokazuje instrukcje instalacji izolowanego narzedzia uv."""
    monkeypatch.setattr(mineru_engine.shutil, "which", lambda _command: None)

    with pytest.raises(RuntimeError, match=r"uv tool install mineru --with mineru\[all\]"):
        MinerUEngine().convert("missing.pdf")
