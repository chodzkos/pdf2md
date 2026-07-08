"""Testy konfiguracji aplikacji."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from pdf2md.core import config
from pdf2md.core.config import Settings, get_settings, save_settings

_ENV_VARS_TO_CLEAR = (
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "OLLAMA_MODEL",
    "OLLAMA_URL",
    "LLM_ENABLED",
    "LLM_PROVIDER",
    "LLM_MODE",
    "MINERU_BACKEND",
    "THEME",
    "DEFAULT_OUTPUT_DIR",
    "PADDLEOCR_VL_PROMPT",
)


@pytest.fixture()
def isolated_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Przekierowuje config.toml do katalogu tymczasowego i izoluje od env/.env."""
    config_dir = tmp_path / "config"
    config_file = config_dir / "config.toml"
    monkeypatch.setattr(config, "_CONFIG_DIR", config_dir)
    monkeypatch.setattr(config, "_CONFIG_FILE", config_file)
    monkeypatch.setattr(config, "_settings_cache", None)
    for var in _ENV_VARS_TO_CLEAR:
        monkeypatch.delenv(var, raising=False)
    # pydantic-settings szuka .env względem CWD — tmp_path nie ma .env projektu
    monkeypatch.chdir(tmp_path)
    return config_file


def test_get_settings_creates_default_config(isolated_config: Path) -> None:
    """get_settings() tworzy config.toml z domyślnymi wartościami."""
    settings = get_settings()

    assert isolated_config.exists()
    assert settings.default_engine == "pymupdf4llm"
    assert settings.default_language == "pol+eng"
    assert settings.marker_device == "cpu"
    assert settings.marker_workers == 1
    assert settings.marker_max_pages == 0  # 0 = cały dokument (domyślnie)
    assert settings.docling_device == "auto"
    assert settings.ollama_url == "http://localhost:11434"
    assert settings.llm_mode == "none"
    assert settings.theme == "auto"  # domyślny motyw GUI


def test_theme_persists_through_save_and_reload(isolated_config: Path) -> None:
    """theme zapisany przez save_settings trafia do config.toml i jest czytany po reloadzie."""
    settings = get_settings()
    settings.theme = "dark"
    save_settings(settings)

    assert 'theme = "dark"' in isolated_config.read_text(encoding="utf-8")

    config._settings_cache = None  # wymuś reload z dysku
    assert get_settings().theme == "dark"


def test_invalid_theme_rejected() -> None:
    """Walidator odrzuca motyw spoza auto/light/dark."""
    with pytest.raises(ValueError, match="theme"):
        Settings(theme="neon")


def test_epub_backend_is_normalized() -> None:
    """epub_backend jest sprowadzany do małych liter i przycinany."""
    settings = Settings(epub_backend=" Calibre ")

    assert settings.epub_backend == "calibre"


def test_invalid_epub_backend_rejected() -> None:
    """Walidator odrzuca backend EPUB spoza pandoc/calibre."""
    with pytest.raises(ValueError, match="epub_backend"):
        Settings(epub_backend="mobi")


def test_epub_backend_persists_through_save_and_reload(isolated_config: Path) -> None:
    """epub_backend zapisany przez save_settings trafia do config.toml i wraca po reloadzie."""
    settings = get_settings()
    settings.epub_backend = "calibre"
    save_settings(settings)

    assert 'epub_backend = "calibre"' in isolated_config.read_text(encoding="utf-8")

    config._settings_cache = None  # wymuś reload z dysku
    assert get_settings().epub_backend == "calibre"


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


def test_save_settings_round_trips_windows_path(isolated_config: Path) -> None:
    """Ścieżka Windows z backslashami jest zapisywana jako poprawny TOML."""
    settings = get_settings()
    settings.default_output_dir = r"C:\Users\test\Documents"

    save_settings(settings)

    config._settings_cache = None
    assert get_settings().default_output_dir == r"C:\Users\test\Documents"


def test_save_settings_round_trips_prompt_with_quote_and_newline(
    isolated_config: Path,
) -> None:
    """Prompt z cudzysłowem i newline przechodzi pełny cykl save/load."""
    settings = get_settings()
    settings.paddleocr_vl_prompt = 'OCR "dokładny"\nZachowaj układ.'

    save_settings(settings)

    config._settings_cache = None
    assert get_settings().paddleocr_vl_prompt == 'OCR "dokładny"\nZachowaj układ.'


def test_get_settings_recovers_from_corrupt_config(isolated_config: Path) -> None:
    """Uszkodzony TOML jest backupowany, a config wraca do wartości domyślnych."""
    isolated_config.parent.mkdir(parents=True)
    broken_content = '[conversion]\ndefault_output_dir = "C:\\Users"\n'
    isolated_config.write_text(broken_content, encoding="utf-8")

    settings = get_settings()

    broken_files = list(isolated_config.parent.glob("config.toml.broken-*"))
    assert len(broken_files) == 1
    assert broken_files[0].read_text(encoding="utf-8") == broken_content
    assert settings.default_output_dir == ""
    assert tomllib.loads(isolated_config.read_text(encoding="utf-8"))


def test_get_settings_returns_cached_instance(isolated_config: Path) -> None:
    """get_settings() cache'uje instancję Settings."""
    first = get_settings()
    second = get_settings()

    assert first is second


def test_marker_device_is_normalized() -> None:
    """marker_device akceptuje wartości z różną wielkością liter."""
    settings = Settings(marker_device=" CUDA ")

    assert settings.marker_device == "cuda"


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("marker_device", "tpu", "marker_device"),
        ("marker_workers", 0, "marker_workers"),
        ("marker_max_pages", -1, "marker_max_pages"),
    ],
)
def test_marker_settings_are_validated(field_name: str, value: object, message: str) -> None:
    """Konfiguracja Markera odrzuca wartości, które byłyby niebezpieczne lub nieobsługiwane."""
    data = Settings().model_dump()
    data[field_name] = value

    with pytest.raises(ValueError, match=message):
        Settings(**data)


def test_per_run_model_override_does_not_mutate_settings(isolated_config: Path) -> None:
    """Przebieg z override modelu (bind_model) NIE zmienia get_settings().ollama_model.

    Regresja: dawniej worker nadpisywał <provider>_model na globalnym singletonie i
    przywracał w finally — zapis Ustawień w trakcie konwersji utrwalał tymczasowy override.
    """
    import json
    from unittest.mock import MagicMock, patch

    from pdf2md.llm.ollama_provider import OllamaProvider

    before = get_settings().ollama_model

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({"response": "ok"}).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    bound = OllamaProvider().bind_model("tymczasowy-model")
    with patch("pdf2md.llm.ollama_provider.urllib.request.urlopen", return_value=mock_resp):
        bound.postprocess("tekst", mode="whole_document")

    assert bound.model_override == "tymczasowy-model"
    assert get_settings().ollama_model == before  # override nie przeciekł do configu
