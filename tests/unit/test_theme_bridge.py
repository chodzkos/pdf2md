"""Testy mostu motywu (gui/theme_bridge.SettingsMapping) — backend, bez GUI."""

from __future__ import annotations

from pathlib import Path

import pytest

from pdf2md.core import config
from pdf2md.gui.theme_bridge import SettingsMapping

_ENV_VARS_TO_CLEAR = ("THEME",)


@pytest.fixture()
def isolated_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Izoluje config.toml do tmp i odcina env/.env (jak w test_config, wzór D6)."""
    config_dir = tmp_path / "config"
    config_file = config_dir / "config.toml"
    monkeypatch.setattr(config, "_CONFIG_DIR", config_dir)
    monkeypatch.setattr(config, "_CONFIG_FILE", config_file)
    monkeypatch.setattr(config, "_settings_cache", None)
    for var in _ENV_VARS_TO_CLEAR:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.chdir(tmp_path)
    return config_file


def test_default_theme_is_auto(isolated_config: Path) -> None:
    assert SettingsMapping()["theme"] == "auto"


def test_set_theme_persists_and_reloads(isolated_config: Path) -> None:
    """Zapis przez most trafia do config.toml i jest czytany po reloadzie cache."""
    mapping = SettingsMapping()
    mapping["theme"] = "dark"

    assert 'theme = "dark"' in isolated_config.read_text(encoding="utf-8")

    config._settings_cache = None  # reload z dysku
    assert SettingsMapping()["theme"] == "dark"


def test_get_with_default_for_theme(isolated_config: Path) -> None:
    """get('theme') zwraca wartość; bez configu — i tak tworzony jest domyślny 'auto'."""
    assert SettingsMapping().get("theme") == "auto"


def test_unknown_key_getitem_raises_keyerror(isolated_config: Path) -> None:
    with pytest.raises(KeyError, match="tylko klucz 'theme'"):
        _ = SettingsMapping()["nieznany"]


def test_unknown_key_setitem_raises_keyerror(isolated_config: Path) -> None:
    with pytest.raises(KeyError, match="tylko klucz 'theme'"):
        SettingsMapping()["nieznany"] = "x"


def test_get_unknown_key_returns_default(isolated_config: Path) -> None:
    """MutableMapping.get łapie KeyError → zwraca default (nie cicha utrata, ale nie wybucha)."""
    assert SettingsMapping().get("nieznany") is None
    assert SettingsMapping().get("nieznany", "fallback") == "fallback"


def test_iter_and_len_expose_only_theme(isolated_config: Path) -> None:
    mapping = SettingsMapping()
    assert list(mapping) == ["theme"]
    assert len(mapping) == 1


def test_delitem_raises(isolated_config: Path) -> None:
    with pytest.raises(KeyError):
        del SettingsMapping()["theme"]
