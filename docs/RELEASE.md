# Release checklist

Checklist przed wydaniem nowej wersji pakietu `pdf2md`.

- [ ] `CHANGELOG.md` zaktualizowany.
- [ ] Wersja w `pyproject.toml` podbita.
- [ ] Wersja w `src/pdf2md/__init__.py` podbita.
- [ ] `uv run pytest` zielone.
- [ ] `uv build` tworzy wheel i sdist w `dist/`.
- [ ] Tag wypchniety: `git tag vX.Y.Z && git push origin vX.Y.Z`.
- [ ] GitHub Release zawiera wheel i sdist.
- [ ] Opcjonalnie: publikacja na PyPI przez trusted publishing.

## Lokalny smoke test pakietu

```bash
uv build
uv tool install dist/pdf2md-*.whl
pdf2md doctor
uv pip install pymupdf4llm
pdf2md convert tests/fixtures/test_text_1page.pdf
```

Frozen binary/PyInstaller nie jest czescia tego etapu. Ten temat wraca dopiero w Etapie 10b.
