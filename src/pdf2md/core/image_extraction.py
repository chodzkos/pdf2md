"""Ekstrakcja obrazów osadzonych w PDF i dopinanie referencji Markdown."""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

_IMAGES_EXTRA_HINT = "Ekstrakcja obrazów wymaga: pip install 'pdf2md[images]'"


@dataclass(frozen=True)
class ExtractedImage:
    """Obraz wyciągnięty z PDF."""

    path: Path
    page: int
    index: int
    width: int
    height: int


def image_output_dir(output_path: str | Path) -> Path:
    """Zwraca katalog `<output>_images` dla pliku wyjściowego Markdown/EPUB."""
    path = Path(output_path)
    return path.parent / f"{path.stem}_images"


def extract_pdf_images(
    pdf_path: str | Path,
    output_dir: str | Path,
    *,
    min_size: int = 100,
) -> list[ExtractedImage]:
    """Wyciąga obrazy z PDF do PNG, pomijając elementy mniejsze niż `min_size` x `min_size`.

    Importy PyMuPDF i Pillow są leniwe, żeby moduł CLI/core nadal importował się bez ciężkich
    zależności zainstalowanych w środowisku.
    """
    if min_size < 1:
        raise ValueError("min_size musi być większe od zera")

    try:
        pymupdf: Any = importlib.import_module("pymupdf")
    except ModuleNotFoundError as exc:
        raise RuntimeError(_IMAGES_EXTRA_HINT) from exc

    try:
        pil_image: Any = importlib.import_module("PIL.Image")
    except ModuleNotFoundError as exc:
        raise RuntimeError(_IMAGES_EXTRA_HINT) from exc

    destination = Path(output_dir)
    extracted_images: list[ExtractedImage] = []
    doc = pymupdf.open(str(pdf_path))
    try:
        for page_number, page in enumerate(doc, start=1):
            saved_on_page = 0
            for image in page.get_images(full=True):
                xref = int(image[0])
                info = doc.extract_image(xref)
                width = int(info.get("width") or image[2])
                height = int(info.get("height") or image[3])
                if width < min_size or height < min_size:
                    continue

                image_bytes = info.get("image")
                if not isinstance(image_bytes, bytes):
                    continue

                saved_on_page += 1
                destination.mkdir(parents=True, exist_ok=True)
                image_path = destination / f"page{page_number}_img{saved_on_page}.png"
                _save_png(pil_image, image_bytes, image_path)
                extracted_images.append(
                    ExtractedImage(
                        path=image_path,
                        page=page_number,
                        index=saved_on_page,
                        width=width,
                        height=height,
                    )
                )
    finally:
        doc.close()

    return extracted_images


def append_image_references(
    markdown: str,
    images: list[ExtractedImage],
    output_path: str | Path,
) -> str:
    """Dopisuje na końcu Markdown referencje do wyciągniętych obrazów."""
    if not images:
        return markdown

    refs = [
        f"![](<{_markdown_image_path(image.path, output_path)}>)"
        for image in sorted(images, key=lambda item: (item.page, item.index))
    ]
    body = markdown.rstrip()
    image_section = "## Obrazy z PDF\n\n" + "\n\n".join(refs)
    if body:
        return f"{body}\n\n{image_section}\n"
    return f"{image_section}\n"


def _save_png(pil_image: Any, image_bytes: bytes, image_path: Path) -> None:
    with pil_image.open(BytesIO(image_bytes)) as image:
        mode = "RGBA" if image.mode in {"RGBA", "LA"} or "transparency" in image.info else "RGB"
        converted = image.convert(mode)
        try:
            converted.save(image_path, format="PNG")
        finally:
            converted.close()


def _markdown_image_path(image_path: Path, output_path: str | Path) -> str:
    output_parent = Path(output_path).parent
    try:
        rel_path = os.path.relpath(image_path, start=output_parent)
    except ValueError:
        rel_path = str(image_path)
    return rel_path.replace(os.sep, "/")
