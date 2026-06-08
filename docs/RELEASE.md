# Release checklist

Przed wydaniem nowej wersji:

- [ ] Zaktualizuj `CHANGELOG.md`.
- [ ] Zaktualizuj wersje w `pyproject.toml`.
- [ ] Uruchom testy: `uv run pytest`.
- [ ] Zbuduj lokalnie binary: `uv run pyinstaller build.spec --clean`.
- [ ] Sprawdz CLI: `./dist/pdf2md --help`.
- [ ] Sprawdz katalog silnikow: `./dist/pdf2md list-engines`.
- [ ] Przetestuj realna konwersje lekkim silnikiem: `./dist/pdf2md convert tests/fixtures/test_text_1page.pdf --engine pymupdf4llm --output /tmp/pdf2md-smoke.md`.
- [ ] Tag: `git tag v1.0.0 && git push origin v1.0.0`.
- [ ] Obserwuj GitHub Actions.

## Strategia bundlowania

Build standalone jest buildem rdzeniowym. W binary sa bundlowane tylko:

- PyMuPDF4LLM,
- Docling,
- GUI PySide6 dla `pdf2md-gui`.

Marker, MinerU, pdf-craft i przyszle silniki VLM nie sa bundlowane. Powody sa dwa:
rozmiar oraz licencje copyleft/ciezkie zaleznosci. Te silniki pozostaja opcjonalne i powinny
byc instalowane osobno przez uzytkownika.

Build wymusza CPU-only torch przed PyInstallerem. Standardowy wheel torcha z PyPI instaluje
pakiety `nvidia-*`; z nimi one-file PyInstaller moze przekroczyc limit formatu CArchive
4 GiB jeszcze przed utworzeniem pliku wynikowego.

## Reczne testowanie builda

```bash
uv sync --extra pymupdf --extra docling
uv pip install pyinstaller
uv pip install --reinstall --index-url https://download.pytorch.org/whl/cpu torch==2.10.0+cpu torchvision==0.25.0+cpu
uv run pyinstaller build.spec --clean
./dist/pdf2md --help
./dist/pdf2md list-engines
./dist/pdf2md convert tests/fixtures/test_text_1page.pdf --engine pymupdf4llm --output /tmp/pdf2md-smoke.md
```
