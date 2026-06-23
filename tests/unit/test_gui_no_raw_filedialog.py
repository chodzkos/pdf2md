"""Strażnik: żaden moduł GUI nie sięga po surowy ``QFileDialog``.

File-dialogi przechodzą przez kitowe helpery (``chodzkos_gui_kit.qt.dialogs``:
``open_files``/``pick_dir``/``save_file``), które same wybierają natywny dialog
albo skonfigurowany fallback wg reguły rozjazdu motywu. Bezpośredni ``QFileDialog``
omija tę regułę (ciemny motyw + jasny natywny Explorer = rozjazd), więc pilnujemy
tego w CI — wzorzec strażnika z IcoForge.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pdf2md.gui

_GUI_ROOT = Path(pdf2md.gui.__file__).parent


def _gui_modules() -> list[Path]:
    return sorted(_GUI_ROOT.rglob("*.py"))


def test_gui_modules_exist() -> None:
    """Sanity: strażnik faktycznie ma co skanować."""
    assert _gui_modules(), f"brak modułów GUI w {_GUI_ROOT}"


def test_no_raw_qfiledialog_in_gui() -> None:
    """Nazwa ``QFileDialog`` nie pojawia się w żadnym module GUI (import ani użycie)."""
    offenders: list[str] = []
    for module in _gui_modules():
        tree = ast.parse(module.read_text(encoding="utf-8"), filename=str(module))
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id == "QFileDialog":
                offenders.append(f"{module.relative_to(_GUI_ROOT)}:{node.lineno}")
            elif isinstance(node, ast.alias) and node.name == "QFileDialog":
                offenders.append(f"{module.relative_to(_GUI_ROOT)} (import)")
    assert not offenders, (
        "Surowy QFileDialog w GUI — użyj chodzkos_gui_kit.qt.dialogs "
        f"(open_files/pick_dir/save_file). Miejsca: {offenders}"
    )
