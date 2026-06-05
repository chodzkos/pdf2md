"""Mixin z logiką chunkowania i strażnikiem rozmiaru dla dostawców LLM."""

from __future__ import annotations

from abc import abstractmethod

from loguru import logger

from pdf2md.utils import chunking

# Bezpieczny limit tokenów dla pojedynczego chunka (przed wywołaniem API)
_SAFE_TOKEN_LIMIT = 8000


class PostprocessMixin:
    """Logika podziału Markdown na chunki i wywołania LLM per chunk."""

    @abstractmethod
    def _call_llm(self, text: str, instructions: str) -> str:
        """Pojedyncze wywołanie LLM — implementowane przez każdego dostawcę."""

    def _apply_size_guard(self, chunks: list[str]) -> list[str]:
        """Rozbija chunki przekraczające limit tokenów na mniejsze fragmenty."""
        safe: list[str] = []
        for chunk in chunks:
            if chunking.estimate_tokens(chunk) > _SAFE_TOKEN_LIMIT:
                logger.warning(
                    f"Chunk {chunking.estimate_tokens(chunk)} tokenów > {_SAFE_TOKEN_LIMIT} — "
                    "dzielę dodatkowo przez by_chunk."
                )
                safe.extend(chunking.by_chunk(chunk, max_tokens=_SAFE_TOKEN_LIMIT))
            else:
                safe.append(chunk)
        return safe

    def _split(self, markdown: str, mode: str) -> list[str]:
        """Dzieli Markdown na fragmenty zgodnie z trybem, z strażnikiem rozmiaru."""
        if mode == "by_chunk":
            return chunking.by_chunk(markdown, max_tokens=_SAFE_TOKEN_LIMIT)
        if mode == "by_heading":
            return self._apply_size_guard(chunking.by_heading(markdown))
        if mode == "by_page":
            pages = markdown.split("\f")
            return self._apply_size_guard(chunking.by_page(pages))
        # whole_document / none / nieznany — jeden call, ale z kontrolą rozmiaru
        if chunking.estimate_tokens(markdown) > _SAFE_TOKEN_LIMIT:
            logger.warning(
                f"Dokument {chunking.estimate_tokens(markdown)} tokenów > {_SAFE_TOKEN_LIMIT} — "
                "automatycznie przełączam na by_chunk."
            )
            return chunking.by_chunk(markdown, max_tokens=_SAFE_TOKEN_LIMIT)
        return [markdown]

    def _postprocess_chunks(self, markdown: str, mode: str, instructions: str) -> str:
        """Przetwarza Markdown chunkami i skleja wynik."""
        chunks = self._split(markdown, mode)
        if not chunks:
            return markdown
        processed = [self._call_llm(chunk, instructions) for chunk in chunks]
        return "\n\n".join(processed)
