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

from pydantic import field_validator
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
ollama_model = "qwen3:14b"
ollama_url = "http://localhost:11434"

[conversion]
default_engine = "pymupdf4llm"
default_output_dir = ""
default_language = "pol+eng"

[marker]
marker_device = "cpu"
marker_workers = 1
# 0 = cały dokument (domyślnie); wartość dodatnia ogranicza liczbę stron (debug/test)
marker_max_pages = 0
# GPU batch tuning — 0 = auto (surya dobiera samodzielnie)
# Dostrajaj empirycznie patrząc na `nvidia-smi -l 1`; podnoś aż VRAM/util sensownie rośnie.
# Batche działają niezależnie od disable_multiprocessing (który dotyczy CPU-side, nie GPU).
marker_torch_device = ""
marker_recognition_batch_size = 0
marker_detector_batch_size = 0
marker_layout_batch_size = 0
marker_table_rec_batch_size = 0

[docling]
docling_device = "auto"

[mineru]
mineru_backend = "pipeline"

[olmocr]
# Izolowany venv olmOCR (subprocess). "" = auto: ~/.venvs/olmocr/bin/python (zob. SILNIKI_INSTALACJA.md 2.7)
olmocr_python = ""
olmocr_model = "allenai/olmOCR-2-7B-1025-FP8"
# Flagi vLLM na 24 GB: bez nich olmocr spawnuje vLLM z 128k KV-cache → OOM "no memory for cache blocks"
olmocr_max_model_len = 16384
olmocr_gpu_memory_utilization = 0.90
# Tryb produkcyjny: własny serwer olmOCR (--server). "" = spawn lokalny per-plik (wolny, ~90-150 s)
olmocr_server_url = ""

[paddleocr_vl]
# Silnik-usługa: serwer OpenAI-compatible (vLLM). pdf2md jest tylko klientem HTTP.
paddleocr_vl_url = "http://localhost:8000/v1"
paddleocr_vl_model = "PaddlePaddle/PaddleOCR-VL-1.6"
paddleocr_vl_prompt = "OCR:"
paddleocr_vl_timeout = 120.0

[ui]
# Motyw GUI: auto (śledzi system), light, dark. Most do kitowego ThemeManager.
theme = "auto"

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
    ollama_model: str = "qwen3:14b"
    ollama_url: str = "http://localhost:11434"

    # Konwersja
    default_engine: str = "pymupdf4llm"
    default_output_dir: str = ""
    default_language: str = "pol+eng"
    marker_device: str = "cpu"
    marker_workers: int = 1
    marker_max_pages: int = 0  # 0 = cały dokument; >0 ogranicza strony tylko na jawne żądanie
    marker_torch_device: str = ""  # "" = użyj marker_device / auto-detect
    marker_recognition_batch_size: int = 0  # 0 = auto (surya default)
    marker_detector_batch_size: int = 0
    marker_layout_batch_size: int = 0
    marker_table_rec_batch_size: int = 0
    docling_device: str = "auto"

    # MinerU
    mineru_backend: str = "pipeline"

    # olmOCR (izolowany venv, subprocess) — "" = auto ~/.venvs/olmocr/bin/python
    olmocr_python: str = ""
    olmocr_model: str = "allenai/olmOCR-2-7B-1025-FP8"
    olmocr_max_model_len: int = 16384
    olmocr_gpu_memory_utilization: float = 0.90
    olmocr_server_url: str = ""  # "" = spawn lokalny; URL = własny serwer (--server)

    # PaddleOCR-VL (silnik-usługa: serwer OpenAI-compatible)
    paddleocr_vl_url: str = "http://localhost:8000/v1"
    paddleocr_vl_model: str = "PaddlePaddle/PaddleOCR-VL-1.6"
    paddleocr_vl_prompt: str = "OCR:"
    paddleocr_vl_timeout: float = 120.0

    # LLM
    llm_enabled: bool = False
    llm_provider: str = "none"
    llm_mode: str = "none"

    # GUI — most do kitowego ThemeManager (klucz "theme": auto/light/dark)
    theme: str = "auto"

    @field_validator("marker_device")
    @classmethod
    def validate_marker_device(cls, value: str) -> str:
        """Dopuszcza tylko urządzenia wspierane przez adapter Marker."""
        normalized = value.lower().strip()
        if normalized not in {"auto", "cpu", "cuda"}:
            raise ValueError("marker_device musi mieć wartość: auto, cpu albo cuda")
        return normalized

    @field_validator("marker_workers")
    @classmethod
    def validate_marker_workers(cls, value: int) -> int:
        """Marker musi mieć co najmniej jednego workera."""
        if value < 1:
            raise ValueError("marker_workers musi być większe od 0")
        return value

    @field_validator("marker_max_pages")
    @classmethod
    def validate_marker_max_pages(cls, value: int) -> int:
        """0 oznacza brak limitu stron, wartości dodatnie ograniczają konwersję."""
        if value < 0:
            raise ValueError("marker_max_pages musi być większe lub równe 0")
        return value

    @field_validator("docling_device")
    @classmethod
    def validate_docling_device(cls, value: str) -> str:
        """Dopuszcza tylko urządzenia wspierane przez GUI i adapter Docling."""
        normalized = value.lower().strip()
        if normalized not in {"auto", "cpu", "cuda"}:
            raise ValueError("docling_device musi mieć wartość: auto, cpu albo cuda")
        return normalized

    @field_validator("theme")
    @classmethod
    def validate_theme(cls, value: str) -> str:
        """Motyw GUI zgodny z kitowym ThemeManager: auto, light albo dark."""
        normalized = value.lower().strip()
        if normalized not in {"auto", "light", "dark"}:
            raise ValueError("theme musi mieć wartość: auto, light albo dark")
        return normalized


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
        f'ollama_url = "{settings.ollama_url}"\n',
        "\n[conversion]\n",
        f'default_engine = "{settings.default_engine}"\n',
        f'default_output_dir = "{settings.default_output_dir}"\n',
        f'default_language = "{settings.default_language}"\n',
        "\n[marker]\n",
        f'marker_device = "{settings.marker_device}"\n',
        f"marker_workers = {settings.marker_workers}\n",
        f"marker_max_pages = {settings.marker_max_pages}\n",
        f'marker_torch_device = "{settings.marker_torch_device}"\n',
        f"marker_recognition_batch_size = {settings.marker_recognition_batch_size}\n",
        f"marker_detector_batch_size = {settings.marker_detector_batch_size}\n",
        f"marker_layout_batch_size = {settings.marker_layout_batch_size}\n",
        f"marker_table_rec_batch_size = {settings.marker_table_rec_batch_size}\n",
        "\n[docling]\n",
        f'docling_device = "{settings.docling_device}"\n',
        "\n[mineru]\n",
        f'mineru_backend = "{settings.mineru_backend}"\n',
        "\n[olmocr]\n",
        f'olmocr_python = "{settings.olmocr_python}"\n',
        f'olmocr_model = "{settings.olmocr_model}"\n',
        f"olmocr_max_model_len = {settings.olmocr_max_model_len}\n",
        f"olmocr_gpu_memory_utilization = {settings.olmocr_gpu_memory_utilization}\n",
        f'olmocr_server_url = "{settings.olmocr_server_url}"\n',
        "\n[paddleocr_vl]\n",
        f'paddleocr_vl_url = "{settings.paddleocr_vl_url}"\n',
        f'paddleocr_vl_model = "{settings.paddleocr_vl_model}"\n',
        f'paddleocr_vl_prompt = "{settings.paddleocr_vl_prompt}"\n',
        f"paddleocr_vl_timeout = {settings.paddleocr_vl_timeout}\n",
        "\n[ui]\n",
        f'theme = "{settings.theme}"\n',
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
