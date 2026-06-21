"""Testy heurystyk jakości OCR (scan/validation)."""

from __future__ import annotations

from pdf2md.scan.validation import (
    compare_ocr_outputs,
    detect_low_quality_pages,
    page_quality_score,
    should_rerun_page,
)

_CLEAN_PAGE = (
    "# Rozdział I\n\nWszystkie ziemie polskie znajdowały się na peryferiach państw "
    "zaborczych. Rozwój przemysłowy odbywał się z opóźnieniem.\n"
)


def test_clean_page_high_quality() -> None:
    """Czysta, długa strona bez � nie kwalifikuje się do ponownego OCR."""
    score = page_quality_score(_CLEAN_PAGE)

    assert score["replacement_char_count"] == 0
    assert score["is_empty"] is False
    assert score["is_suspiciously_short"] is False
    assert should_rerun_page(score) is False


def test_page_with_replacement_chars_is_low_quality() -> None:
    """Strona ze znakami � jest wykrywana jako niskiej jakości."""
    dirty = "Tekst z b��dami rozpoznawania zawiera�cy znaki zast�pcze i wi�cej tre�ci."
    score = page_quality_score(dirty)

    assert score["replacement_char_count"] > 0
    assert should_rerun_page(score) is True


def test_empty_page_is_detected() -> None:
    """Pusta strona jest wykrywana i kwalifikowana do ponownego przebiegu."""
    score = page_quality_score("   \n\t  ")

    assert score["is_empty"] is True
    assert should_rerun_page(score) is True


def test_short_page_is_suspicious() -> None:
    """Bardzo krótka (niepusta) strona jest podejrzana."""
    score = page_quality_score("Strona 12")

    assert score["is_empty"] is False
    assert score["is_suspiciously_short"] is True
    assert should_rerun_page(score) is True


def test_suspicious_patterns_counted() -> None:
    """Wzorce pomyłek OCR (rn, cyfra w słowie) są zliczane."""
    score = page_quality_score("modern rnodel z 0CR i s10wo")

    assert int(score["suspicious_patterns"]) >= 1


def test_detect_low_quality_pages_returns_indices() -> None:
    """detect_low_quality_pages zwraca indeksy złych stron, pomija dobre."""
    pages = [_CLEAN_PAGE, "", "Tekst z � znakiem zast�pczym i wi�cej z�ego tekstu tutaj."]

    low = detect_low_quality_pages(pages)

    assert 0 not in low
    assert 1 in low  # pusta
    assert 2 in low  # ze znakami �


def test_compare_ocr_outputs_similarity() -> None:
    """compare_ocr_outputs zwraca 1.0 dla identycznych, mniej dla różnych."""
    assert compare_ocr_outputs("ten sam tekst", "ten sam tekst") == 1.0
    assert compare_ocr_outputs("zupełnie inny", "kompletnie różny") < 1.0


def test_custom_thresholds_override() -> None:
    """Własne progi zmieniają decyzję should_rerun_page."""
    score = page_quality_score("Tekst z jednym � znakiem ale poza tym całkiem w porządku i długi.")

    assert should_rerun_page(score, {"max_replacement_chars": 0}) is True
    assert should_rerun_page(score, {"max_replacement_chars": 5}) is False
