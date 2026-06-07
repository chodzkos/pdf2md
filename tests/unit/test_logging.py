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
