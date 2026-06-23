"""Most konfiguracji motywu: kitowy ThemeManager (MutableMapping) ↔ pdf2md config.toml.

Kitowy ``chodzkos_gui_kit.qt.theme.ThemeManager`` oczekuje ``MutableMapping[str, Any]`` i
czyta/pisze pod kluczem ``"theme"`` (wartości ``auto``/``light``/``dark``). pdf2md ma własny
config (Settings/pydantic, config.toml jako jedyne źródło prawdy, atomowy zapis, ZERO QSettings).

``SettingsMapping`` jest cienkim adapterem: czyta ``get_settings().theme`` i zapisuje przez
``save_settings()``. Świadomie obsługuje WYŁĄCZNIE klucz ``"theme"`` — Settings ma sztywny
schemat, a kit dziś czyta tylko ten klucz. Inny klucz → jawny ``KeyError`` (nie cicha utrata),
żeby od razu wyłapać, gdyby kit zaczął sięgać po coś innego.
"""

from __future__ import annotations

from collections.abc import Iterator, MutableMapping
from typing import Any

from pdf2md.core.config import get_settings, save_settings

_THEME_KEY = "theme"
_ONLY_THEME_MSG = "SettingsMapping obsługuje tylko klucz 'theme'"


class SettingsMapping(MutableMapping[str, Any]):
    """Adapter MutableMapping nad pdf2md Settings, ograniczony do klucza ``theme``."""

    def __getitem__(self, key: str) -> Any:
        if key != _THEME_KEY:
            raise KeyError(f"{_ONLY_THEME_MSG}, nie {key!r}")
        return get_settings().theme

    def __setitem__(self, key: str, value: Any) -> None:
        if key != _THEME_KEY:
            raise KeyError(f"{_ONLY_THEME_MSG}, nie {key!r}")
        settings = get_settings()
        settings.theme = value
        save_settings(settings)  # atomowy zapis do config.toml + odświeżenie cache

    def __delitem__(self, key: str) -> None:
        raise KeyError(f"{_ONLY_THEME_MSG}; usuwanie nie jest wspierane")

    def __iter__(self) -> Iterator[str]:
        return iter((_THEME_KEY,))

    def __len__(self) -> int:
        return 1
