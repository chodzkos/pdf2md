"""Testy jednostkowe modułu scan/preprocessing — bez ML, bez LLM."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import cv2
import numpy as np
import pymupdf
import pytest

from pdf2md.scan.preprocessing import (
    cleanup_work_dir,
    crop_margins,
    denoise,
    deskew,
    detect_double_page,
    dewarp,
    iter_page_batches,
    normalize_contrast,
    pdf_to_images,
    preprocess_page,
    split_double_page,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SCAN_FIXTURE = Path(__file__).parent.parent / "fixtures" / "test_scan.pdf"


def _white_page(h: int = 400, w: int = 300, channels: int = 3) -> np.ndarray:
    """Biała strona — minimalistyczny obraz do testów."""
    return np.full((h, w, channels), 255, dtype=np.uint8) if channels == 3 else np.full((h, w), 255, dtype=np.uint8)


def _noisy_page(h: int = 400, w: int = 300) -> np.ndarray:
    """Strona z szumem sól-pieprz."""
    img = _white_page(h, w)
    rng = np.random.default_rng(42)
    noise_mask = rng.random((h, w)) < 0.05
    img[noise_mask] = [0, 0, 0]
    return img


def _create_simple_pdf(path: str, pages: int = 3) -> None:
    """Utwórz prosty wielostronicowy PDF do testów (bez prawdziwej treści)."""
    doc = pymupdf.open()
    for _ in range(pages):
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 72), "Test page", fontsize=12)
    doc.save(path)
    doc.close()


# ---------------------------------------------------------------------------
# pdf_to_images
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not SCAN_FIXTURE.exists(), reason="brak tests/fixtures/test_scan.pdf")
def test_pdf_to_images_on_fixture() -> None:
    """pdf_to_images tworzy pliki page_000N.png dla każdej strony."""
    with tempfile.TemporaryDirectory() as out_dir:
        paths = pdf_to_images(str(SCAN_FIXTURE), dpi=72, output_dir=out_dir)
        assert len(paths) > 0
        for p in paths:
            assert Path(p).exists(), f"Plik {p} nie istnieje"
            assert Path(p).name.startswith("page_")
            assert Path(p).suffix == ".png"
        # Nazwy stron posortowane rosnąco
        names = [Path(p).name for p in paths]
        assert names == sorted(names)


def test_pdf_to_images_creates_directory() -> None:
    """pdf_to_images tworzy katalog wyjściowy jeśli nie istnieje."""
    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = str(Path(tmp) / "test.pdf")
        out_dir = str(Path(tmp) / "new_subdir" / "output")
        _create_simple_pdf(pdf_path, pages=1)
        paths = pdf_to_images(pdf_path, dpi=72, output_dir=out_dir)
        assert len(paths) == 1
        assert Path(paths[0]).exists()


# ---------------------------------------------------------------------------
# iter_page_batches
# ---------------------------------------------------------------------------


def test_iter_page_batches_yields_correct_batches() -> None:
    """iter_page_batches oddaje paczki właściwej wielkości."""
    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = str(Path(tmp) / "book.pdf")
        _create_simple_pdf(pdf_path, pages=5)
        work_dir = str(Path(tmp) / "work")
        os.makedirs(work_dir)

        batches = list(iter_page_batches(pdf_path, dpi=72, batch_size=2, work_dir=work_dir))

        # 5 stron z batch_size=2 → 3 paczki: [2, 2, 1]
        assert len(batches) == 3
        assert len(batches[0]) == 2
        assert len(batches[1]) == 2
        assert len(batches[2]) == 1


def test_iter_page_batches_does_not_hold_all_pages() -> None:
    """iter_page_batches nie renderuje następnej paczki dopóki caller nie pobierze."""
    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = str(Path(tmp) / "book.pdf")
        _create_simple_pdf(pdf_path, pages=4)
        work_dir = str(Path(tmp) / "work")
        os.makedirs(work_dir)

        gen = iter_page_batches(pdf_path, dpi=72, batch_size=2, work_dir=work_dir)
        batch1 = next(gen)
        assert len(batch1) == 2

        # Caller usuwa pliki pierwszej paczki (symulacja zwolnienia dysku)
        for p in batch1:
            os.remove(p)

        batch2 = next(gen)
        assert len(batch2) == 2

        # Pliki pierwszej paczki są usunięte, drugiej istnieją
        for p in batch1:
            assert not Path(p).exists(), "Plik pierwszej paczki powinien być usunięty"
        for p in batch2:
            assert Path(p).exists(), "Plik drugiej paczki powinien istnieć"

        gen.close()


def test_iter_page_batches_single_page_pdf() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = str(Path(tmp) / "one.pdf")
        _create_simple_pdf(pdf_path, pages=1)
        batches = list(iter_page_batches(pdf_path, dpi=72, batch_size=20))
        assert len(batches) == 1
        assert len(batches[0]) == 1


# ---------------------------------------------------------------------------
# cleanup_work_dir
# ---------------------------------------------------------------------------


def test_cleanup_work_dir_removes_directory() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "work"
        work.mkdir()
        (work / "test.txt").write_text("x")
        cleanup_work_dir(str(work))
        assert not work.exists()


def test_cleanup_work_dir_nonexistent_is_noop() -> None:
    cleanup_work_dir("/tmp/pdf2md_nonexistent_xyz_12345")  # nie rzuca wyjątku


# ---------------------------------------------------------------------------
# deskew
# ---------------------------------------------------------------------------


def test_deskew_returns_same_shape() -> None:
    """deskew zwraca obraz o tych samych wymiarach co wejście."""
    img = _white_page(600, 400)
    result = deskew(img)
    assert result.shape == img.shape


def test_deskew_empty_image_returns_unchanged() -> None:
    """Biały obraz (brak treści) jest zwracany bez obrotu."""
    img = _white_page(300, 200)
    result = deskew(img)
    assert result.shape == img.shape


# ---------------------------------------------------------------------------
# denoise
# ---------------------------------------------------------------------------


def test_denoise_returns_same_shape() -> None:
    img = _noisy_page()
    result = denoise(img)
    assert result.shape == img.shape
    assert result.dtype == img.dtype


def test_denoise_grayscale_returns_same_shape() -> None:
    img = _white_page(200, 150, channels=1)
    result = denoise(img)
    assert result.shape == img.shape


# ---------------------------------------------------------------------------
# crop_margins
# ---------------------------------------------------------------------------


def test_crop_margins_returns_ndarray() -> None:
    img = _white_page(400, 300)
    # Wstaw trochę czarnych pikseli wewnątrz
    img[100:200, 80:220] = [0, 0, 0]
    result = crop_margins(img)
    assert isinstance(result, np.ndarray)
    assert result.size > 0


def test_crop_margins_all_white_returns_unchanged() -> None:
    img = _white_page(300, 200)
    result = crop_margins(img)
    assert result.shape == img.shape


# ---------------------------------------------------------------------------
# normalize_contrast
# ---------------------------------------------------------------------------


def test_normalize_contrast_returns_same_shape() -> None:
    img = _white_page(200, 150)
    result = normalize_contrast(img)
    assert result.shape == img.shape
    assert result.dtype == np.uint8


def test_normalize_contrast_grayscale() -> None:
    img = _white_page(200, 150, channels=1)
    result = normalize_contrast(img)
    assert result.shape == img.shape


# ---------------------------------------------------------------------------
# detect_double_page / split_double_page
# ---------------------------------------------------------------------------


def test_detect_double_page_wide_image() -> None:
    """Szeroki obraz (dwie strony) jest poprawnie wykrywany."""
    wide = np.full((400, 800, 3), 255, dtype=np.uint8)
    assert detect_double_page(wide) is True


def test_detect_double_page_portrait_image() -> None:
    """Typowa strona portretowa nie jest wykrywana jako podwójna."""
    portrait = _white_page(600, 420)
    assert detect_double_page(portrait) is False


def test_split_double_page_returns_two_parts() -> None:
    wide = np.zeros((400, 800, 3), dtype=np.uint8)
    parts = split_double_page(wide)
    assert len(parts) == 2
    # Łączna szerokość po splitcie równa szerokości oryginału
    total_w = parts[0].shape[1] + parts[1].shape[1]
    assert total_w == 800
    # Obie części mają tę samą wysokość
    assert parts[0].shape[0] == parts[1].shape[0] == 400


# ---------------------------------------------------------------------------
# preprocess_page
# ---------------------------------------------------------------------------


def test_preprocess_page_empty_ops_returns_unchanged() -> None:
    img = _white_page(300, 200)
    result = preprocess_page(img, [])
    np.testing.assert_array_equal(result, img)


def test_preprocess_page_deskew_and_crop() -> None:
    img = _white_page(400, 300)
    img[50:350, 30:270] = [128, 128, 128]
    result = preprocess_page(img, ["deskew", "crop"])
    assert result.ndim == 3
    assert result.size > 0


def test_preprocess_page_unknown_op_is_ignored() -> None:
    img = _white_page(200, 150)
    result = preprocess_page(img, ["deskew", "nonexistent_op", "crop"])
    assert isinstance(result, np.ndarray)


def test_preprocess_page_all_ops() -> None:
    img = _noisy_page(400, 300)
    result = preprocess_page(img, ["deskew", "denoise", "crop", "normalize"])
    assert result.ndim == 3
    assert result.size > 0
