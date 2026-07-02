"""Testy eksporterow plikow wynikowych."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from pdf2md.exporters import build_epub_exporter
from pdf2md.exporters.calibre_epub_exporter import CalibreEpubExporter
from pdf2md.exporters.markdown_exporter import MarkdownExporter
from pdf2md.exporters.pandoc_epub_exporter import PandocEpubExporter


def test_markdown_exporter_writes_file(tmp_path: Path) -> None:
    output = tmp_path / "nested" / "doc.md"

    result = MarkdownExporter().export("# Tytul\n", output)

    assert result == output
    assert output.read_text(encoding="utf-8") == "# Tytul\n"


def test_pandoc_epub_exporter_raises_when_pandoc_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("pdf2md.exporters.pandoc_epub_exporter.check_pandoc", lambda: False)

    with pytest.raises(RuntimeError, match="Pandoc nie jest dostępny"):
        PandocEpubExporter().export("# Tytul", tmp_path / "book.epub")


def test_pandoc_epub_exporter_runs_pandoc_and_removes_temp_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output = tmp_path / "out" / "book.epub"
    calls: list[list[str]] = []
    temp_paths: list[Path] = []
    monkeypatch.setattr("pdf2md.exporters.pandoc_epub_exporter.check_pandoc", lambda: True)

    def fake_run(
        command: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        temp_paths.append(Path(command[1]))
        assert check is True
        assert capture_output is True
        assert text is True
        output.write_bytes(b"epub")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("pdf2md.exporters.pandoc_epub_exporter.subprocess.run", fake_run)

    result = PandocEpubExporter().export("# Tytul", output)

    assert result == output
    # Bez source_dir temp .md ląduje obok wyniku (nie w /tmp) i tam wskazuje --resource-path.
    assert temp_paths[0].parent == output.parent
    assert calls == [
        ["pandoc", str(temp_paths[0]), "-o", str(output), f"--resource-path={output.parent}"]
    ]
    assert output.read_bytes() == b"epub"
    assert not temp_paths[0].exists()


def test_pandoc_epub_exporter_puts_temp_in_source_dir(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "images"
    source_dir.mkdir()
    output = tmp_path / "out" / "book.epub"
    calls: list[list[str]] = []
    temp_paths: list[Path] = []
    monkeypatch.setattr("pdf2md.exporters.pandoc_epub_exporter.check_pandoc", lambda: True)

    def fake_run(
        command: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        temp_paths.append(Path(command[1]))
        # Temp musi istnieć w source_dir w trakcie wywołania Pandoca (obok obrazów).
        assert temp_paths[0].parent == source_dir
        assert temp_paths[0].is_file()
        output.write_bytes(b"epub")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("pdf2md.exporters.pandoc_epub_exporter.subprocess.run", fake_run)

    PandocEpubExporter().export("![](fig.png)", output, source_dir=source_dir)

    assert calls == [
        ["pandoc", str(temp_paths[0]), "-o", str(output), f"--resource-path={source_dir}"]
    ]
    assert not temp_paths[0].exists()


def test_calibre_epub_exporter_raises_when_calibre_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("pdf2md.exporters.calibre_epub_exporter.check_calibre", lambda: False)

    with pytest.raises(RuntimeError, match=r"Calibre .* nie jest dostępny"):
        CalibreEpubExporter().export("# Tytul", tmp_path / "book.epub")


def test_calibre_epub_exporter_runs_ebook_convert_and_removes_temp_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "images"
    source_dir.mkdir()
    output = tmp_path / "out" / "book.epub"
    calls: list[list[str]] = []
    temp_paths: list[Path] = []
    monkeypatch.setattr("pdf2md.exporters.calibre_epub_exporter.check_calibre", lambda: True)

    def fake_run(
        command: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        temp_paths.append(Path(command[1]))
        assert check is True
        assert capture_output is True
        assert text is True
        # Temp .md leży obok obrazów (source_dir), nie w /tmp — Calibre rozwiąże ![](fig.png).
        assert temp_paths[0].parent == source_dir
        assert temp_paths[0].is_file()
        output.write_bytes(b"epub")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("pdf2md.exporters.calibre_epub_exporter.subprocess.run", fake_run)

    result = CalibreEpubExporter().export("![](fig.png)", output, source_dir=source_dir)

    assert result == output
    assert calls == [["ebook-convert", str(temp_paths[0]), str(output)]]
    assert output.read_bytes() == b"epub"
    assert not temp_paths[0].exists()


def test_build_epub_exporter_defaults_to_pandoc() -> None:
    assert isinstance(build_epub_exporter(), PandocEpubExporter)
    assert isinstance(build_epub_exporter("pandoc"), PandocEpubExporter)


def test_build_epub_exporter_returns_calibre_when_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("pdf2md.exporters.check_calibre", lambda: True)

    assert isinstance(build_epub_exporter("calibre"), CalibreEpubExporter)


def test_build_epub_exporter_falls_back_to_pandoc_when_calibre_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("pdf2md.exporters.check_calibre", lambda: False)

    assert isinstance(build_epub_exporter("calibre"), PandocEpubExporter)
