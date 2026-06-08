"""Preprocessing obrazów stron PDF przed OCR — klasyczna obróbka obrazu, bez ML."""

from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING

import cv2
import numpy as np
import pymupdf
from loguru import logger

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# Stałe DPI
# ---------------------------------------------------------------------------

DPI_STANDARD = 300
DPI_OLD_BOOKS = 400
DPI_DIFFICULT = 600

# ---------------------------------------------------------------------------
# Konwersja PDF → obrazy
# ---------------------------------------------------------------------------


def pdf_to_images(pdf_path: str, dpi: int, output_dir: str) -> list[str]:
    """Rozbij PDF na obrazy PNG — page_0001.png, page_0002.png, ...

    Każda strona jest renderowana do pliku PNG w *output_dir*. Zwraca listę
    ścieżek do wygenerowanych plików w kolejności stron.
    """
    os.makedirs(output_dir, exist_ok=True)
    mat = pymupdf.Matrix(dpi / 72, dpi / 72)
    doc = pymupdf.open(pdf_path)
    paths: list[str] = []
    try:
        total = len(doc)
        for i in range(total):
            pix = doc[i].get_pixmap(matrix=mat)
            out_path = str(Path(output_dir) / f"page_{i + 1:04d}.png")
            pix.save(out_path)
            paths.append(out_path)
            logger.debug(f"Wyrenderowano stronę {i + 1}/{total}: {out_path}")
    finally:
        doc.close()
    return paths


def iter_page_batches(
    pdf_path: str,
    dpi: int,
    batch_size: int = 20,
    work_dir: str | None = None,
) -> Generator[list[str], None, None]:
    """Generator renderujący strony PDF paczkami (batch_size stron naraz).

    Renderuje kolejne paczki stron do PNG i zwraca listy ścieżek przez ``yield``.
    Po odebraniu paczki wywołujący powinien przetworzyć i USUNĄĆ pliki PNG przed
    pobraniem kolejnej paczki — to ogranicza zużycie dysku do ~jednej paczki naraz
    zamiast całej książki.

    Przykład użycia::

        for batch_paths in iter_page_batches(pdf, dpi=400, batch_size=20):
            process(batch_paths)
            for p in batch_paths:
                os.remove(p)  # zwolnij dysk przed następną paczką
    """
    tmp_dir_obj: tempfile.TemporaryDirectory[str] | None = None
    if work_dir is None:
        tmp_dir_obj = tempfile.TemporaryDirectory(prefix="pdf2md_batch_")
        work_dir = tmp_dir_obj.name

    mat = pymupdf.Matrix(dpi / 72, dpi / 72)
    doc = pymupdf.open(pdf_path)
    try:
        total = len(doc)
        logger.info(f"iter_page_batches: {total} stron, batch_size={batch_size}, dpi={dpi}")
        for batch_start in range(0, total, batch_size):
            batch_end = min(batch_start + batch_size, total)
            batch_paths: list[str] = []
            for i in range(batch_start, batch_end):
                pix = doc[i].get_pixmap(matrix=mat)
                path = str(Path(work_dir) / f"page_{i + 1:04d}.png")
                pix.save(path)
                batch_paths.append(path)
            logger.debug(
                f"Paczka stron {batch_start + 1}-{batch_end}/{total}: {len(batch_paths)} plików"
            )
            yield batch_paths
    finally:
        doc.close()
        if tmp_dir_obj is not None:
            tmp_dir_obj.cleanup()


def cleanup_work_dir(work_dir: str) -> None:
    """Usuń cały katalog roboczy po udanym buildzie."""
    if os.path.isdir(work_dir):
        shutil.rmtree(work_dir)
        logger.info(f"Wyczyszczono katalog roboczy: {work_dir}")


# ---------------------------------------------------------------------------
# Operacje OpenCV na obrazach
# ---------------------------------------------------------------------------


def deskew(image: np.ndarray) -> np.ndarray:
    """Wyrównaj pochylenie strony przez obrót do kąta prostego.

    Wykrywa kąt pochylenia za pomocą ``cv2.minAreaRect`` na binaryzowanym obrazie.
    Dla dobrze zorientowanych stron (kąt < 0.5°) obraz jest zwracany bez zmian.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image.copy()
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)

    coords = np.column_stack(np.where(thresh > 0))
    if len(coords) < 20:
        return image

    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = 90 + angle
    elif angle > 45:
        angle = angle - 90

    if abs(angle) < 0.5:
        return image

    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    rot_mat = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(
        image, rot_mat, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
    )


def denoise(image: np.ndarray) -> np.ndarray:
    """Redukuj szum przez filtrowanie nielokalne (Non-Local Means)."""
    if image.ndim == 3:
        return cv2.fastNlMeansDenoisingColored(image, None, h=10, hColor=10,
                                               templateWindowSize=7, searchWindowSize=21)
    return cv2.fastNlMeansDenoising(image, None, h=10,
                                    templateWindowSize=7, searchWindowSize=21)


def dewarp(image: np.ndarray) -> np.ndarray:
    """Uproszczona korekta wygięcia strony przez wykrycie konturów i transform perspektywy.

    Jeśli cztery rogi strony nie dają się wiarygodnie wykryć, obraz jest zwracany
    bez zmian — nie rzucamy wyjątku.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image.copy()
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return image

    largest = max(contours, key=cv2.contourArea)
    page_area = image.shape[0] * image.shape[1]
    if cv2.contourArea(largest) < page_area * 0.3:
        return image

    peri = cv2.arcLength(largest, True)
    approx = cv2.approxPolyDP(largest, 0.02 * peri, True)
    if len(approx) != 4:
        return image

    pts_src = np.array(approx.reshape(4, 2), dtype=np.float32)
    # Sortuj punkty: TL, TR, BR, BL
    s = pts_src.sum(axis=1)
    diff = np.diff(pts_src, axis=1)
    ordered = np.array(
        [
            pts_src[np.argmin(s)],
            pts_src[np.argmin(diff)],
            pts_src[np.argmax(s)],
            pts_src[np.argmax(diff)],
        ],
        dtype=np.float32,
    )
    h, w = image.shape[:2]
    pts_dst = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], dtype=np.float32)
    persp_mat = cv2.getPerspectiveTransform(ordered, pts_dst)
    return cv2.warpPerspective(image, persp_mat, (w, h))


def crop_margins(image: np.ndarray) -> np.ndarray:
    """Przytnij puste marginesy — zostaw tylko obszar z treścią z małym paddingiem."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image.copy()
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    coords = np.column_stack(np.where(thresh > 0))

    if len(coords) == 0:
        return image

    y_min, x_min = coords.min(axis=0)
    y_max, x_max = coords.max(axis=0)

    pad = 20
    h, w = image.shape[:2]
    y_min = max(0, y_min - pad)
    x_min = max(0, x_min - pad)
    y_max = min(h, y_max + pad)
    x_max = min(w, x_max + pad)

    return image[y_min:y_max, x_min:x_max]


def normalize_contrast(image: np.ndarray) -> np.ndarray:
    """Popraw kontrast metodą CLAHE na kanale L (LAB) lub na szarym obrazie."""
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    if image.ndim == 3:
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l_ch, a_ch, b_ch = cv2.split(lab)
        l_eq = clahe.apply(l_ch)
        lab_eq = cv2.merge([l_eq, a_ch, b_ch])
        return cv2.cvtColor(lab_eq, cv2.COLOR_LAB2BGR)
    return clahe.apply(image)


def detect_double_page(image: np.ndarray) -> bool:
    """Wykryj czy obraz zawiera dwie strony (szerokość >> wysokość).

    Heurystyka: stosunek szerokości do wysokości > 1.5 sugeruje skan dwustronicowy.
    """
    _h, w = image.shape[:2]
    return bool(w / _h > 1.5)


def split_double_page(image: np.ndarray) -> list[np.ndarray]:
    """Podziel obraz dwie strony — prosta metoda: cięcie w połowie szerokości.

    Próbuje znaleźć pionową linię podziału jako lokalne minimum gęstości treści
    w środkowym 20% szerokości. Jeśli nie znajdzie — tnie dokładnie w połowie.
    """
    _h, w = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image.copy()
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)

    # Szukaj pionowej linii podziału w środkowym 20% szerokości
    center_start = int(w * 0.4)
    center_end = int(w * 0.6)
    col_density = thresh[:, center_start:center_end].sum(axis=0)
    split_local = int(np.argmin(col_density))
    split_x = center_start + split_local

    left = image[:, :split_x]
    right = image[:, split_x:]
    return [left, right]


def preprocess_page(image: np.ndarray, operations: list[str]) -> np.ndarray:
    """Uruchom konfigurowalny pipeline operacji na stronie.

    Obsługiwane operacje (w kolejności z listy):
    ``"deskew"``, ``"denoise"``, ``"dewarp"``, ``"crop"``, ``"normalize"``.
    Nieznane nazwy są logowane jako ostrzeżenie i pomijane.
    """
    _ops = {
        "deskew": deskew,
        "denoise": denoise,
        "dewarp": dewarp,
        "crop": crop_margins,
        "normalize": normalize_contrast,
    }
    result = image
    for op in operations:
        fn = _ops.get(op)
        if fn is None:
            logger.warning(f"Nieznana operacja preprocessingu: '{op}' — pomijam")
            continue
        result = fn(result)
    return result
