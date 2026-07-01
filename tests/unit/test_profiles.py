"""Testy systemu profili skanowania (scan/profiles)."""

from __future__ import annotations

from pathlib import Path

import pytest

from pdf2md.scan import profiles
from pdf2md.scan.profiles import (
    Profile,
    ProfileError,
    list_profiles,
    load_profile,
    save_custom_profile,
)


@pytest.mark.parametrize(
    ("name", "dpi", "ocr"),
    [
        ("fast", 300, "paddleocr"),
        ("balanced", 400, "paddleocr-vl"),
        ("premium", 400, "olmocr"),
    ],
)
def test_load_builtin_profile(name: str, dpi: int, ocr: str) -> None:
    """Każdy wbudowany profil ładuje się i waliduje, ma oczekiwane wartości."""
    profile = load_profile(name)
    assert profile.name == name
    assert profile.dpi == dpi
    assert (profile.ocr.engine or profile.ocr.primary) == ocr
    assert profile.llm_cleanup.enabled is True
    assert profile.output.epub is True


def test_list_profiles_includes_builtins() -> None:
    """list_profiles zawiera trzy wbudowane profile."""
    names = list_profiles()
    assert {"fast", "balanced", "premium"} <= set(names)


def test_balanced_dewarp_auto_and_premium_compare() -> None:
    """Wartość 'auto' (dewarp/crop) i tryb primary/secondary są poprawnie walidowane."""
    balanced = load_profile("balanced")
    assert balanced.preprocess.dewarp == "auto"
    premium = load_profile("premium")
    assert premium.ocr.primary == "olmocr"
    assert premium.ocr.secondary == "surya"
    assert premium.ocr.compare_outputs is True
    assert premium.validation is not None and premium.validation.rerun_bad_pages is True


def test_load_unknown_profile_raises() -> None:
    """Nieznana nazwa profilu → ProfileError z listą dostępnych."""
    with pytest.raises(ProfileError, match="Nieznany profil"):
        load_profile("nieistnieje")


def test_invalid_yaml_unknown_key_raises(tmp_path: Path) -> None:
    """YAML z nieznanym kluczem (literówka) jest odrzucany przy walidacji."""
    bad = tmp_path / "bad.yaml"
    bad.write_text("name: zly\ndpi: 400\nnieznany_klucz: 1\n", encoding="utf-8")
    with pytest.raises(ProfileError, match="walidacji"):
        load_profile(str(bad))


def test_invalid_yaml_wrong_type_raises(tmp_path: Path) -> None:
    """YAML niebędący mapą jest odrzucany."""
    bad = tmp_path / "list.yaml"
    bad.write_text("- a\n- b\n", encoding="utf-8")
    with pytest.raises(ProfileError, match="mapą"):
        load_profile(str(bad))


def test_load_profile_from_path(tmp_path: Path) -> None:
    """Profil można wczytać bezpośrednio ze ścieżki do pliku YAML."""
    custom = tmp_path / "moj.yaml"
    custom.write_text("name: moj\ndpi: 350\noutput: {epub_backend: Calibre}\n", encoding="utf-8")
    profile = load_profile(str(custom))
    assert profile.name == "moj"
    assert profile.dpi == 350
    assert profile.output.epub_backend == "calibre"


def test_invalid_epub_backend_in_profile_raises(tmp_path: Path) -> None:
    """Nieznany backend EPUB w profilu jest odrzucany przy walidacji."""
    bad = tmp_path / "bad-epub-backend.yaml"
    bad.write_text("name: zly\noutput: {epub_backend: mobi}\n", encoding="utf-8")
    with pytest.raises(ProfileError, match="epub_backend"):
        load_profile(str(bad))


def test_save_custom_profile_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Zapisany profil użytkownika pojawia się na liście i daje się wczytać po nazwie."""
    monkeypatch.setattr(profiles, "_USER_PROFILES_DIR", tmp_path / "profiles")
    profile = Profile(name="moj-custom", dpi=333)

    path = save_custom_profile(profile, "moj-custom")
    assert Path(path).is_file()
    assert "moj-custom" in list_profiles()
    reloaded = load_profile("moj-custom")
    assert reloaded.dpi == 333
    assert reloaded.output.epub_backend == "pandoc"


def test_epub_backend_persists_in_custom_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Backend EPUB zapisany w profilu użytkownika wraca po reloadzie."""
    monkeypatch.setattr(profiles, "_USER_PROFILES_DIR", tmp_path / "profiles")
    profile = Profile(name="epub-calibre", dpi=333)
    profile.output.epub = True
    profile.output.epub_backend = "calibre"

    path = save_custom_profile(profile, "epub-calibre")

    assert "epub_backend: calibre" in Path(path).read_text(encoding="utf-8")
    assert load_profile("epub-calibre").output.epub_backend == "calibre"


def test_user_profile_overrides_builtin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Profil użytkownika o nazwie wbudowanego ma pierwszeństwo."""
    monkeypatch.setattr(profiles, "_USER_PROFILES_DIR", tmp_path / "profiles")
    save_custom_profile(Profile(name="fast", dpi=111), "fast")
    assert load_profile("fast").dpi == 111
