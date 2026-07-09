"""Testy konfiguracji logowania."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from pdf2md.utils import logging as logging_module


class _FakeLogger:
    def __init__(self) -> None:
        self.removed = False
        self.add_calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def remove(self) -> None:
        self.removed = True

    def add(self, *args: Any, **kwargs: Any) -> int:
        self.add_calls.append((args, kwargs))
        return len(self.add_calls)


def test_setup_logging_configures_console_and_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fake_logger = _FakeLogger()
    monkeypatch.setattr(logging_module, "logger", fake_logger)

    logging_module.setup_logging(log_dir=tmp_path, level="WARNING", verbose=True)

    assert fake_logger.removed is True
    assert len(fake_logger.add_calls) == 2
    assert fake_logger.add_calls[0][1]["level"] == "DEBUG"
    assert fake_logger.add_calls[1][0][0] == tmp_path / "pdf2md.log"
    assert fake_logger.add_calls[1][1]["level"] == "DEBUG"
    assert tmp_path.exists()


def test_setup_logging_to_file_adds_gui_log(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Tryb GUI (`to_file=True`) dodaje sink do ~/.config/pdf2md/logs/gui.log (rotacja 5 MB)."""
    fake_logger = _FakeLogger()
    monkeypatch.setattr(logging_module, "logger", fake_logger)
    monkeypatch.setattr(logging_module.Path, "home", lambda: tmp_path)

    logging_module.setup_logging(log_dir=tmp_path, to_file=True)

    gui_log = tmp_path / ".config" / "pdf2md" / "logs" / "gui.log"
    gui_call = next(
        (c for c in fake_logger.add_calls if c[0] and c[0][0] == gui_log),
        None,
    )
    assert gui_call is not None
    assert gui_log.parent.exists()
    assert gui_call[1]["rotation"] == "5 MB"
    assert gui_call[1]["level"] == "INFO"


def test_setup_logging_survives_missing_stderr(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """gui-script/pythonw: sys.stderr==None nie może wywalić setup_logging (brak sinku stderr)."""
    fake_logger = _FakeLogger()
    monkeypatch.setattr(logging_module, "logger", fake_logger)
    monkeypatch.setattr(logging_module.sys, "stderr", None)

    logging_module.setup_logging(log_dir=tmp_path)  # nie rzuca

    # Żaden add nie dostał None jako celu (sink stderr pominięty); plikowy sink jest.
    assert all(not (c[0] and c[0][0] is None) for c in fake_logger.add_calls)
    assert any(c[0] and c[0][0] == tmp_path / "pdf2md.log" for c in fake_logger.add_calls)
