"""Profile pipeline'u skanowania — walidacja YAML (pydantic) i ładowanie wbudowanych/własnych.

Profile wbudowane (fast/balanced/premium) są dostarczane jako dane pakietu w
``pdf2md/scan/profiles/*.yaml``. Profile użytkownika żyją w ``~/.config/pdf2md/profiles/``.
"""

from __future__ import annotations

import importlib.resources
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, field_validator

_USER_PROFILES_DIR = Path.home() / ".config" / "pdf2md" / "profiles"

#: Pole bool albo wartość "auto" (np. dewarp/crop dobierane heurystycznie).
BoolOrAuto = bool | Literal["auto"]


class _Strict(BaseModel):
    """Bazowy model z zakazem nieznanych kluczy (łapie literówki w YAML)."""

    model_config = ConfigDict(extra="forbid")


class Preprocess(_Strict):
    deskew: bool = False
    denoise: bool = False
    dewarp: BoolOrAuto = False
    crop: BoolOrAuto = False


class Layout(_Strict):
    engine: str


class Ocr(_Strict):
    # warianty: pojedynczy silnik (engine) albo primary/secondary z porównaniem
    engine: str | None = None
    primary: str | None = None
    secondary: str | None = None
    compare_outputs: bool = False
    gpu: bool = True


class LlmCleanup(_Strict):
    enabled: bool = False
    provider: str = "ollama"
    model: str = ""
    chunk: str | None = None
    mode: str | None = None


class Postprocess(_Strict):
    remove_headers_footers: bool = False
    merge_paragraphs: bool = False
    fix_hyphenation: bool = False
    footnotes: bool = False
    toc_detection: bool = False


class Validation(_Strict):
    detect_low_confidence_pages: bool = False
    rerun_bad_pages: bool = False


class Output(_Strict):
    markdown: bool = True
    epub: bool = False
    epub_backend: str = "pandoc"
    quality_report: bool = False
    html_report: bool = False

    @field_validator("epub_backend")
    @classmethod
    def validate_epub_backend(cls, value: str) -> str:
        """Dopuszcza tylko wspierane backendy eksportu EPUB."""
        normalized = value.lower().strip()
        if normalized not in {"pandoc", "calibre"}:
            raise ValueError("epub_backend musi mieć wartość: pandoc albo calibre")
        return normalized


class Profile(_Strict):
    """Pełna konfiguracja przebiegu skanowania."""

    name: str
    dpi: int = 400
    preprocess: Preprocess = Preprocess()
    layout: Layout | None = None
    ocr: Ocr = Ocr()
    llm_cleanup: LlmCleanup = LlmCleanup()
    postprocess: Postprocess | None = None
    validation: Validation | None = None
    output: Output = Output()


class ProfileError(Exception):
    """Profil nie istnieje albo jego YAML jest niepoprawny."""


def _builtin_dir() -> Path:
    """Katalog z wbudowanymi profilami (dane pakietu)."""
    return Path(str(importlib.resources.files("pdf2md.scan") / "profiles"))


def _builtin_names() -> list[str]:
    builtin = _builtin_dir()
    if not builtin.is_dir():
        return []
    return sorted(p.stem for p in builtin.glob("*.yaml"))


def list_profiles() -> list[str]:
    """Zwraca nazwy dostępnych profili: wbudowane + użytkownika (posortowane, bez duplikatów)."""
    names = set(_builtin_names())
    if _USER_PROFILES_DIR.is_dir():
        names.update(p.stem for p in _USER_PROFILES_DIR.glob("*.yaml"))
    return sorted(names)


def _parse_profile_file(path: Path) -> Profile:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ProfileError(f"Niepoprawny YAML profilu {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ProfileError(f"Profil {path} musi być mapą kluczy YAML, jest: {type(data).__name__}")
    try:
        return Profile(**data)
    except Exception as exc:
        raise ProfileError(f"Profil {path} nie przeszedł walidacji: {exc}") from exc


def load_profile(name_or_path: str) -> Profile:
    """Ładuje profil po nazwie (wbudowany/użytkownika) albo ze ścieżki do pliku YAML."""
    candidate = Path(name_or_path)
    if candidate.suffix in {".yaml", ".yml"} and candidate.is_file():
        return _parse_profile_file(candidate)

    user_path = _USER_PROFILES_DIR / f"{name_or_path}.yaml"
    if user_path.is_file():
        return _parse_profile_file(user_path)

    builtin_path = _builtin_dir() / f"{name_or_path}.yaml"
    if builtin_path.is_file():
        return _parse_profile_file(builtin_path)

    available = ", ".join(list_profiles()) or "(brak)"
    raise ProfileError(f"Nieznany profil '{name_or_path}'. Dostępne: {available}")


def save_custom_profile(profile: Profile, name: str) -> str:
    """Zapisuje profil użytkownika do ~/.config/pdf2md/profiles/{name}.yaml. Zwraca ścieżkę."""
    _USER_PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    path = _USER_PROFILES_DIR / f"{name}.yaml"
    data = profile.model_dump(exclude_none=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return str(path)
