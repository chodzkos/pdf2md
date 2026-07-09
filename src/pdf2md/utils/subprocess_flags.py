"""Flaga `creationflags` tłumiąca mignięcia okna konsoli na Windows.

Każde wywołanie `subprocess.run`/`Popen` do zewnętrznego narzędzia (nvidia-smi,
pandoc, ebook-convert, MinerU, olmOCR) domyślnie miga oknem konsoli na Windows —
szczególnie widoczne, gdy GUI jest gui-scriptem (bez własnej konsoli). Przekazanie
`creationflags=NO_WINDOW_FLAGS` uruchamia proces bez okna. Poza Windows flaga = 0
(bez efektu), więc można ją przekazywać bezwarunkowo.
"""

from __future__ import annotations

import subprocess
import sys

#: `CREATE_NO_WINDOW` na Windows, 0 na innych platformach (no-op).
#: `if`-instrukcja (nie wyrażenie warunkowe) — tak mypy zawęża `sys.platform`
#: i sprawdza `subprocess.CREATE_NO_WINDOW` tylko pod win32, gdzie atrybut istnieje.
if sys.platform == "win32":
    NO_WINDOW_FLAGS = subprocess.CREATE_NO_WINDOW
else:
    NO_WINDOW_FLAGS = 0
