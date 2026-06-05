"""Testy konfiguracji aplikacji."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from pdf2md.core import config
from pdf2md.core.config import Settings, get_settings, save_settings


@pytest.fixture()
def isolated_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Przekierowuje config.toml do katalogu tymczasowego."""
    config_dir = tmp_path / "config"
    config_file = config_dir / "config.toml"
    monkeypatch.setattr(config, "_CONFIG_DIR", config_dir)
    monkeypatch.setattr(config, "_CONFIG_FILE", config_file)
    monkeypatch.setattr(config, "_settings_cache", None)
    return config_file


def test_get_settings_creates_default_config(isolated_config: Path) -> None:
    """get_settings() tworzy config.toml z domyślnymi wartościami."""
    settings = get_settings()

    assert isolated_config.exists()
    assert settings.default_engine == "pymupdf4llm"
    assert settings.default_language == "pol+eng"
    assert settings.marker_device == "cpu"
    assert settings.marker_workers == 1
    assert settings.marker_max_pages == 1
    assert settings.docling_device == "auto"
    assert settings.ollama_url == "http://localhost:11434"
    assert settings.llm_mode == "none"


def test_get_settings_loads_toml_values(isolated_config: Path) -> None:
    """Wartości z config.toml trafiają do Settings."""
    isolated_config.parent.mkdir(parents=True)
    isolated_config.write_text(
        """
[llm]
enabled = true
provider = "ollama"
mode = "by_chunk"
ollama_model = "model-testowy"
ollama_url = "http://ollama-test:11434"

[conversion]
default_engine = "marker"
default_output_dir = "/tmp/out"
default_language = "pol"

[marker]
marker_device = "cuda"
marker_workers = 2
marker_max_pages = 3

[docling]
docling_device = "cuda"

[api_keys]
openai_api_key = "dev-key"
""",
        encoding="utf-8",
    )

    settings = get_settings()

    assert settings.llm_enabled is True
    assert settings.llm_provider == "ollama"
    assert settings.llm_mode == "by_chunk"
    assert settings.ollama_model == "model-testowy"
    assert settings.ollama_url == "http://ollama-test:11434"
    assert settings.default_engine == "marker"
    assert settings.default_output_dir == "/tmp/out"
    assert settings.default_language == "pol"
    assert settings.marker_device == "cuda"
    assert settings.marker_workers == 2
    assert settings.marker_max_pages == 3
    assert settings.docling_device == "cuda"
    assert settings.openai_api_key == "dev-key"


def test_dotenv_overrides_toml_values(
    isolated_config: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """.env działa jako deweloperski override wartości z config.toml."""
    isolated_config.parent.mkdir(parents=True)
    isolated_config.write_text(
        """
[llm]
provider = "none"

[api_keys]
openai_api_key = "from-toml"
""",
        encoding="utf-8",
    )
    (tmp_path / ".env").write_text(
        """
OPENAI_API_KEY=from-dotenv
LLM_PROVIDER=ollama
""",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    settings = get_settings()

    assert settings.openai_api_key == "from-dotenv"
    assert settings.llm_provider == "ollama"


def test_save_settings_writes_config_atomically(isolated_config: Path) -> None:
    """save_settings() zapisuje poprawny TOML i nie zostawia plików tymczasowych."""
    settings = Settings(
        llm_enabled=True,
        llm_provider="ollama",
        llm_mode="by_heading",
        ollama_url="http://localhost:11434",
        default_engine="marker",
        default_output_dir="/tmp/pdf2md",
        default_language="eng",
        marker_device="cpu",
        marker_workers=1,
        marker_max_pages=1,
        docling_device="cuda",
        anthropic_api_key="ant",
        openai_api_key="open",
        gemini_api_key="gem",
    )

    save_settings(settings)

    data = tomllib.loads(isolated_config.read_text(encoding="utf-8"))
    assert data["llm"]["enabled"] is True
    assert data["llm"]["provider"] == "ollama"
    assert data["llm"]["mode"] == "by_heading"
    assert data["llm"]["ollama_url"] == "http://localhost:11434"
    assert data["conversion"]["default_engine"] == "marker"
    assert data["conversion"]["default_output_dir"] == "/tmp/pdf2md"
    assert data["conversion"]["default_language"] == "eng"
    assert data["marker"]["marker_device"] == "cpu"
    assert data["marker"]["marker_workers"] == 1
    assert data["marker"]["marker_max_pages"] == 1
    assert data["docling"]["docling_device"] == "cuda"
    assert data["api_keys"]["anthropic_api_key"] == "ant"
    assert data["api_keys"]["openai_api_key"] == "open"
    assert data["api_keys"]["gemini_api_key"] == "gem"
    assert not list(isolated_config.parent.glob("*.tmp"))


def test_get_settings_returns_cached_instance(isolated_config: Path) -> None:
    """get_settings() cache'uje instancję Settings."""
    first = get_settings()
    second = get_settings()

    assert first is second
