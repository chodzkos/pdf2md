"""Skrypt testowy preprocessingu obrazów PDF.

Użycie:
    python scripts/preprocess_test.py input.pdf [--dpi DPI] [--deskew] [--crop] [--denoise] [--normalize] [--dewarp]

Zapisuje obrazy przed i po do work/pages_png/ i work/preprocessed/.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Dodaj src/ do PYTHONPATH przy uruchomieniu bezpośrednim
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import cv2

from pdf2md.scan.preprocessing import (
    DPI_DIFFICULT,
    DPI_OLD_BOOKS,
    DPI_STANDARD,
    iter_page_batches,
    preprocess_page,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Testowy preprocessing stron PDF.")
    parser.add_argument("pdf", help="Ścieżka do pliku PDF")
    parser.add_argument(
        "--dpi",
        type=int,
        default=DPI_STANDARD,
        help=f"Rozdzielczość renderowania (domyślnie {DPI_STANDARD}; "
             f"stare książki: {DPI_OLD_BOOKS}; trudne skany: {DPI_DIFFICULT})",
    )
    parser.add_argument("--deskew", action="store_true", help="Wyrównaj pochylenie")
    parser.add_argument("--crop", action="store_true", help="Przytnij marginesy")
    parser.add_argument("--denoise", action="store_true", help="Redukuj szum")
    parser.add_argument("--normalize", action="store_true", help="Normalizuj kontrast (CLAHE)")
    parser.add_argument("--dewarp", action="store_true", help="Korekta wygięcia strony")
    parser.add_argument(
        "--batch-size", type=int, default=20, help="Rozmiar paczki stron (domyślnie 20)"
    )
    args = parser.parse_args()

    ops: list[str] = []
    if args.deskew:
        ops.append("deskew")
    if args.denoise:
        ops.append("denoise")
    if args.dewarp:
        ops.append("dewarp")
    if args.crop:
        ops.append("crop")
    if args.normalize:
        ops.append("normalize")

    pdf_path = Path(args.pdf).resolve()
    if not pdf_path.exists():
        print(f"Błąd: plik {pdf_path} nie istnieje", file=sys.stderr)
        sys.exit(1)

    work_dir = Path("work")
    raw_dir = work_dir / "pages_png"
    pre_dir = work_dir / "preprocessed"
    raw_dir.mkdir(parents=True, exist_ok=True)
    pre_dir.mkdir(parents=True, exist_ok=True)

    print(f"PDF:        {pdf_path}")
    print(f"DPI:        {args.dpi}")
    print(f"Operacje:   {ops if ops else ['(brak)']}")
    print(f"Paczka:     {args.batch_size} stron")
    print(f"Raw →       {raw_dir}")
    print(f"Pre →       {pre_dir}")
    print()

    t0 = time.monotonic()
    total_pages = 0

    for batch in iter_page_batches(str(pdf_path), dpi=args.dpi,
                                   batch_size=args.batch_size,
                                   work_dir=str(raw_dir)):
        for raw_path in batch:
            name = Path(raw_path).name
            img = cv2.imread(raw_path)
            if img is None:
                print(f"  UWAGA: nie można wczytać {raw_path}", file=sys.stderr)
                continue

            total_pages += 1
            h, w = img.shape[:2]

            out = preprocess_page(img, ops) if ops else img
            out_path = pre_dir / name
            cv2.imwrite(str(out_path), out)
            print(f"  {name}  {w}x{h}px -> {out.shape[1]}x{out.shape[0]}px")
        # NIE usuwamy plików raw — zostają w work/pages_png/ do wizualnej inspekcji

    elapsed = time.monotonic() - t0
    print()
    print(f"Gotowe: {total_pages} stron w {elapsed:.1f}s")
    if ops:
        print(f"Preprocessowane obrazy: {pre_dir}/")
    print(f"Surowe obrazy:           {raw_dir}/")


if __name__ == "__main__":
    main()
