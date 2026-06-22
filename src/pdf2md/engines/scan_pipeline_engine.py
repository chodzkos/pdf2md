"""Silnik Scan Pipeline (premium) — pełny przepływ skanu książki do EPUB/Markdown.

Orkiestruje: preprocessing → VLM-OCR → (unload VLM) → korekta LLM → walidacja → składanie →
eksport. WYMUSZA sekwencję VRAM: cały OCR z załadowanym modelem wizyjnym, potem
``unload_model()``, dopiero potem korekta LLM (oba modele nigdy naraz — patrz Etap 12/13).

Ciężkie zależności pozostają leniwe (silniki VLM/scan importują je dopiero w metodach).
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from loguru import logger

from pdf2md.engines.base import ConversionEngine, ConversionResult

if TYPE_CHECKING:
    from pdf2md.scan.assembly import Chapter


class ScanPipelineEngine(ConversionEngine):
    """Premium pipeline dla skanowanych książek (VLM-OCR + korekta + składanie + EPUB)."""

    name = "Scan Pipeline (premium)"
    description = "Skan książki → preprocessing, VLM-OCR, korekta LLM, składanie, EPUB"
    supports_ocr = True
    supports_llm = True
    requires_gpu = True

    def is_available(self) -> bool:
        """Dostępny, gdy dostępny jest silnik VLM-OCR (domyślnie Surya: pakiet + GPU)."""
        from pdf2md.engines.surya_engine import SuryaEngine

        return SuryaEngine().is_available()

    def convert(self, pdf_path: str, **kwargs: object) -> ConversionResult:
        """Uruchamia pełny pipeline i zwraca ConversionResult (ścieżki w metadata)."""
        from pdf2md.scan.preprocessing import DPI_OLD_BOOKS, cleanup_work_dir

        start = time.monotonic()
        profile = cast("dict[str, object]", kwargs.pop("profile", None) or {})
        dpi = int(cast(Any, profile.get("dpi", DPI_OLD_BOOKS)))
        batch_size = int(cast(Any, profile.get("batch_size", 20)))
        keep_work = bool(kwargs.pop("keep_work", False))

        output_dir = kwargs.pop("output_dir", None)
        out_base = Path(str(output_dir)) if output_dir else Path.cwd()
        out_base.mkdir(parents=True, exist_ok=True)
        work_dir = Path(tempfile.mkdtemp(prefix="pdf2md_scanpipe_", dir=str(out_base)))

        ocr_engine = cast(
            ConversionEngine, kwargs.pop("ocr_engine", None) or self._default_ocr_engine()
        )
        llm_provider = self._resolve_llm_provider(kwargs.pop("llm_provider", None))

        # --- 1. OCR (VLM załadowany) → md_pages; VLMEngine.convert robi unload w finally ---
        logger.info(f"ScanPipeline: OCR silnikiem {getattr(ocr_engine, 'name', ocr_engine)}")
        ocr_result = ocr_engine.convert(
            pdf_path, output_dir=str(work_dir), dpi=dpi, batch_size=batch_size
        )
        md_pages_dir = work_dir / "md_pages"
        ocr_pages = self._read_pages(md_pages_dir)
        if not ocr_pages:
            ocr_pages = ocr_result.markdown.split("\n\n---\n\n")

        # --- 2. Guard VRAM: model wizyjny musi być już zwolniony przed korektą ---
        from pdf2md.scan.correction import log_free_vram

        log_free_vram("ScanPipeline: po unload VLM, przed korektą")

        # --- 3. Korekta LLM (opcjonalna — gdy dostawca dostępny) ---
        pages = self._correct_pages(ocr_pages, md_pages_dir, work_dir, llm_provider)

        # --- 4. Walidacja jakości ---
        validation_results = self._validate_pages(pages)

        # --- 5. Składanie ---
        chapters = self._assemble(pages)

        # --- 6. Eksport ---
        from pdf2md.scan.export import export_epub, export_markdown, export_quality_report

        metadata = self._book_metadata(pdf_path, chapters, kwargs)
        book_md = export_markdown(chapters, out_base / "book.md")
        report = export_quality_report(validation_results, out_base / "report.html")
        epub_ok = False
        epub_path = ""
        try:
            epub_path = export_epub(chapters, metadata, out_base / "book.epub")
            epub_ok = True
        except Exception as exc:
            logger.error(f"ScanPipeline: budowa EPUB nie powiodła się: {exc}")

        # --- 7. Sprzątanie work/ tylko po UDANYM EPUB (chyba że --keep-work) ---
        if epub_ok and not keep_work:
            cleanup_work_dir(str(work_dir))
        elif keep_work:
            logger.info(f"ScanPipeline: zachowuję katalog roboczy (--keep-work): {work_dir}")

        markdown = Path(book_md).read_text(encoding="utf-8")
        result = ConversionResult(
            markdown=markdown,
            engine_used=self.name,
            pages=len(pages),
            metadata={
                "source": str(pdf_path),
                "book_md_path": book_md,
                "epub_path": epub_path,
                "report_path": report,
                "chapters": len(chapters),
                "work_dir": str(work_dir) if keep_work else "",
            },
        )
        result.conversion_time = time.monotonic() - start
        return result

    # ------------------------------------------------------------------
    # Pomocnicze
    # ------------------------------------------------------------------

    def _default_ocr_engine(self) -> ConversionEngine:
        from pdf2md.engines.surya_engine import SuryaEngine

        return SuryaEngine()

    def _resolve_llm_provider(self, provider: object) -> Any:
        """Zwraca przekazanego dostawcę LLM albo pierwszego dostępnego z rejestru (lub None)."""
        if provider is not None:
            return provider
        from pdf2md.core.registry import llm_registry

        for candidate in llm_registry.get_available():
            return candidate
        return None

    def _read_pages(self, md_pages_dir: Path) -> list[str]:
        if not md_pages_dir.is_dir():
            return []
        return [p.read_text(encoding="utf-8") for p in sorted(md_pages_dir.glob("*.md"))]

    def _correct_pages(
        self,
        ocr_pages: list[str],
        md_pages_dir: Path,
        work_dir: Path,
        llm_provider: Any,
    ) -> list[str]:
        if llm_provider is None:
            logger.warning("ScanPipeline: brak dostawcy LLM — pomijam korektę (surowy OCR)")
            return ocr_pages
        from pdf2md.scan.correction import correct_pages_batch

        corrected_dir = work_dir / "corrected"
        if md_pages_dir.is_dir():
            correct_pages_batch(str(md_pages_dir), llm_provider, str(corrected_dir))
            corrected = self._read_pages(corrected_dir)
            if corrected:
                return corrected
        # awaryjnie: korekta strona po stronie w pamięci
        from pdf2md.scan.correction import correct_page

        return [correct_page(p, llm_provider) for p in ocr_pages]

    def _validate_pages(self, pages: list[str]) -> list[dict[str, object]]:
        from pdf2md.scan.validation import page_quality_score, should_rerun_page

        results: list[dict[str, object]] = []
        for i, md in enumerate(pages, 1):
            score = page_quality_score(md)
            entry: dict[str, object] = {"page": i, **score, "rerun": should_rerun_page(score)}
            results.append(entry)
        return results

    def _assemble(self, pages: list[str]) -> list[Chapter]:
        from pdf2md.scan.assembly import (
            detect_chapters,
            fix_hyphenation,
            merge_paragraphs_across_pages,
            normalize_punctuation,
            remove_repeated_headers_footers,
        )

        cleaned = remove_repeated_headers_footers(pages)
        dehyphenated = [fix_hyphenation(p) for p in cleaned]
        merged = merge_paragraphs_across_pages(dehyphenated)
        merged = normalize_punctuation(merged)
        return detect_chapters(merged)

    def _book_metadata(
        self,
        pdf_path: str,
        chapters: list[Chapter],
        kwargs: dict[str, object],
    ) -> dict[str, str]:
        title = str(kwargs.get("title") or Path(pdf_path).stem)
        return {
            "title": title,
            "author": str(kwargs.get("author", "")),
            "language": str(kwargs.get("language", "pl")),
            "identifier": f"pdf2md-{Path(pdf_path).stem}",
        }
