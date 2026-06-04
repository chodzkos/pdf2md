"""Konfiguracja aplikacji — źródłem prawdy jest ~/.config/pdf2md/config.toml.

Plik .env służy wyłącznie jako override deweloperski i nadpisuje wartości z TOML.
Kolejność ładowania: config.toml → .env (jeśli istnieje) → cache.
"""

from __future__ import annotations

import os
import tempfile
import tomllib
from contextlib import suppress
from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

_CONFIG_DIR = Path.home() / ".config" / "pdf2md"
_CONFIG_FILE = _CONFIG_DIR / "config.toml"

_DEFAULT_TOML = """\
# Konfiguracja pdf2md
# Edytuj ten plik lub używaj komendy: pdf2md config set <klucz> <wartość>

[llm]
enabled = false
provider = "none"
mode = "none"
anthropic_model = ""
openai_model = ""
gemini_model = ""
ollama_model = "qwen2.5:14b"

[conversion]
default_engine = "pymupdf4llm"
default_output_dir = ""
default_language = "pol+eng"

[api_keys]
# Klucze API — bezpieczniej trzymać w .env, tu tylko fallback
anthropic_api_key = ""
openai_api_key = ""
gemini_api_key = ""
"""


def _ensure_config_file() -> dict[str, Any]:
    """Tworzy plik config.toml z domyślnymi wartościami jeśli nie istnieje."""
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not _CONFIG_FILE.exists():
        _CONFIG_FILE.write_text(_DEFAULT_TOML, encoding="utf-8")
    with open(_CONFIG_FILE, "rb") as f:
        return tomllib.load(f)


def _load_toml_flat() -> dict[str, Any]:
    """Wczytuje TOML i spłaszcza sekcje do płaskiego słownika dla pydantic-settings."""
    data = _ensure_config_file()
    flat: dict[str, Any] = {}
    for section_name, section in data.items():
        if isinstance(section, dict):
            if section_name == "llm":
                section = {
                    ("llm_enabled" if key == "enabled" else key): value
                    for key, value in section.items()
                }
                section = {
                    ("llm_provider" if key == "provider" else key): value
                    for key, value in section.items()
                }
                section = {
                    ("llm_mode" if key == "mode" else key): value for key, value in section.items()
                }
            flat.update(section)
    return flat


class Settings(BaseSettings):
    """Ustawienia aplikacji — wspólne dla CLI i GUI (żadnego osobnego QSettings)."""

    model_config = SettingsConfigDict(
        # .env nadpisuje wartości z TOML (tylko do developmentu)
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Ustawia priorytet: zmienne środowiskowe/.env nadpisują config.toml."""
        return env_settings, dotenv_settings, init_settings, file_secret_settings

    # Klucze API
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    gemini_api_key: str = ""

    # Modele (puste = fallback z providera)
    anthropic_model: str = ""
    openai_model: str = ""
    gemini_model: str = ""
    ollama_model: str = "qwen2.5:14b"

    # Konwersja
    default_engine: str = "pymupdf4llm"
    default_output_dir: str = ""
    default_language: str = "pol+eng"

    # LLM
    llm_enabled: bool = False
    llm_provider: str = "none"
    llm_mode: str = "none"


_settings_cache: Settings | None = None


def get_settings() -> Settings:
    """Zwraca singleton ustawień (TOML → .env override → cache)."""
    global _settings_cache
    if _settings_cache is None:
        toml_values = _load_toml_flat()
        _settings_cache = Settings(**toml_values)
    return _settings_cache


def save_settings(settings: Settings) -> None:
    """Zapisuje ustawienia atomowo do ~/.config/pdf2md/config.toml."""
    global _settings_cache
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Konfiguracja pdf2md\n",
        "\n[llm]\n",
        f"enabled = {str(settings.llm_enabled).lower()}\n",
        f'provider = "{settings.llm_provider}"\n',
        f'mode = "{settings.llm_mode}"\n',
        f'anthropic_model = "{settings.anthropic_model}"\n',
        f'openai_model = "{settings.openai_model}"\n',
        f'gemini_model = "{settings.gemini_model}"\n',
        f'ollama_model = "{settings.ollama_model}"\n',
        "\n[conversion]\n",
        f'default_engine = "{settings.default_engine}"\n',
        f'default_output_dir = "{settings.default_output_dir}"\n',
        f'default_language = "{settings.default_language}"\n',
        "\n[api_keys]\n",
        f'anthropic_api_key = "{settings.anthropic_api_key}"\n',
        f'openai_api_key = "{settings.openai_api_key}"\n',
        f'gemini_api_key = "{settings.gemini_api_key}"\n',
    ]
    fd, tmp_path = tempfile.mkstemp(
        prefix=f"{_CONFIG_FILE.name}.",
        suffix=".tmp",
        dir=_CONFIG_DIR,
        text=True,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
            tmp_file.write("".join(lines))
        os.replace(tmp_path, _CONFIG_FILE)
    except Exception:
        with suppress(FileNotFoundError):
            os.unlink(tmp_path)
        raise
    _settings_cache = settings
