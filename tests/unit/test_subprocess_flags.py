"""Testy flagi `NO_WINDOW_FLAGS` tłumiącej mignięcia okna konsoli (Windows)."""

from __future__ import annotations

import subprocess
import sys
from typing import Any

import pytest

from pdf2md.utils.subprocess_flags import NO_WINDOW_FLAGS


def test_no_window_flags_zero_off_windows() -> None:
    if sys.platform == "win32":
        assert NO_WINDOW_FLAGS == subprocess.CREATE_NO_WINDOW
    else:
        assert NO_WINDOW_FLAGS == 0


def test_smi_query_passes_creationflags(monkeypatch: pytest.MonkeyPatch) -> None:
    """Wywołanie nvidia-smi przekazuje `creationflags=NO_WINDOW_FLAGS` (reprezentatywne call-site)."""
    from pdf2md.detection import hardware

    captured: dict[str, Any] = {}

    def fake_run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        captured.update(kwargs)
        return subprocess.CompletedProcess(command, 0, stdout="NVIDIA\n")

    monkeypatch.setattr(hardware.subprocess, "run", fake_run)
    hardware._smi_query(["name"])

    assert captured.get("creationflags") == NO_WINDOW_FLAGS
