"""Testy ponownego przebiegu trudnych stron (scan/rerun.py) — odporność i sprzątanie.

Bez pymupdf i bez modeli: `_render_page` jest podmieniany na atrapę tworzącą pusty PNG,
a silnik fallbackowy to fake spełniający publiczny kontrakt (ocr_page/load/unload).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pdf2md.scan import rerun


class _FakeEngine:
    """Fake silnika per-strona zgodny z Protocol _PageOCREngine (publiczne ocr_page)."""

    name = "FakeVLM"

    def __init__(self, fail_pages: set[int] | None = None) -> None:
        self.loaded = False
        self.unloaded = False
        self.fail_pages = fail_pages or set()
        self.seen: list[int] = []

    def load_model(self) -> None:
        self.loaded = True

    def unload_model(self) -> None:
        self.unloaded = True

    def ocr_page(self, image_path: str) -> str:
        # Nazwa renderu: rerun_page_0002.png → strona 1-based = 2 → index 1.
        page_1based = int(Path(image_path).stem.split("_")[-1])
        index = page_1based - 1
        self.seen.append(index)
        if index in self.fail_pages:
            raise RuntimeError(f"OCR padł na stronie {page_1based}")
        return f"# strona {page_1based}"


@pytest.fixture()
def patched_render(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, Path | None]:
    """Podmienia mkdtemp (znany katalog) i _render_page (pusty PNG), by nie wołać pymupdf."""
    root = tmp_path / "workroot"
    root.mkdir()
    created: dict[str, Path | None] = {"dir": None}

    def fake_mkdtemp(prefix: str = "") -> str:
        work = root / f"{prefix}job"
        work.mkdir()
        created["dir"] = work
        return str(work)

    def fake_render(pdf_path: str, page_index: int, dpi: int, out_dir: str) -> str:
        png = Path(out_dir) / f"rerun_page_{page_index + 1:04d}.png"
        png.write_bytes(b"png")
        return str(png)

    monkeypatch.setattr(rerun.tempfile, "mkdtemp", fake_mkdtemp)
    monkeypatch.setattr(rerun, "_render_page", fake_render)
    return created


def test_happy_path_all_pages(patched_render: dict[str, Path | None]) -> None:
    """Wszystkie strony OCR-owane; model załadowany i zwolniony; katalog roboczy posprzątany."""
    engine = _FakeEngine()

    results = rerun.rerun_difficult_pages([0, 2], "doc.pdf", engine)

    assert results == {0: "# strona 1", 2: "# strona 3"}
    assert engine.loaded is True
    assert engine.unloaded is True
    work_dir = patched_render["dir"]
    assert work_dir is not None
    assert not work_dir.exists()  # shutil.rmtree posprzątał


def test_one_page_failure_does_not_stop_rest(patched_render: dict[str, Path | None]) -> None:
    """Błąd OCR jednej strony nie przerywa reszty; strona nieudana pomijana w wyniku."""
    engine = _FakeEngine(fail_pages={1})  # druga strona (index 1) rzuca

    results = rerun.rerun_difficult_pages([0, 1, 2], "doc.pdf", engine)

    assert set(results) == {0, 2}  # udane strony
    assert results[0] == "# strona 1"
    assert results[2] == "# strona 3"
    assert 1 not in results  # nieudana pominięta
    assert engine.seen == [0, 1, 2]  # próbowano każdej strony (nie zatrzymano się na błędzie)
    assert engine.unloaded is True  # model zwolniony mimo błędu
    work_dir = patched_render["dir"]
    assert work_dir is not None
    assert not work_dir.exists()  # katalog posprzątany także po błędzie


def test_empty_page_list_returns_empty() -> None:
    """Pusta lista stron → pusty wynik, bez tworzenia katalogu ani ładowania modelu."""
    engine = _FakeEngine()

    assert rerun.rerun_difficult_pages([], "doc.pdf", engine) == {}
    assert engine.loaded is False


def test_rejects_engine_without_page_contract() -> None:
    """Silnik bez ocr_page/load_model/unload_model → TypeError (kontrakt Protocol)."""

    class _Bad:
        pass

    with pytest.raises(TypeError, match="ocr_page"):
        rerun.rerun_difficult_pages([0], "doc.pdf", _Bad())
