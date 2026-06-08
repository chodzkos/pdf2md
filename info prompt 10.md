# Info prompt 10 - etap packaging

Stan na pauzie: 2026-06-08, galaz `etap-10-packaging`.

Uzytkownik poprosil o pauze w trakcie finalnego rebuilda PyInstaller. Aktywny proces zostal zatrzymany przez:

```bash
pkill -TERM -f "pyinstaller build.spec"
```

Potwierdzono pozniej, ze `pgrep -af pyinstaller` nic nie zwraca.

## Zakres wykonanych zmian

Zrobione pliki i zmiany:

- `build.spec` - nowy spec PyInstaller budujacy dwa one-file binary:
  - `pdf2md` CLI, bez GUI,
  - `pdf2md-gui` GUI z PySide6.
- `scripts/build_linux.sh` - nowy skrypt builda Linux.
- `scripts/build_windows.ps1` - nowy skrypt builda Windows z komentarzami o Tesseract/Poppler i `shutil.which()` dla MinerU.
- `.github/workflows/release.yml` - nowy workflow release na tagi `v*` z buildem Linux/Windows i `gh release create`.
- `docs/RELEASE.md` - nowy checklist release i opis strategii bundlowania.
- `src/pdf2md/cli/main.py` - dodano:

```python
if __name__ == "__main__":
    import multiprocessing

    multiprocessing.freeze_support()
    cli()
```

- `src/pdf2md/gui/app.py` - dodano analogiczny guard:

```python
if __name__ == "__main__":
    import multiprocessing

    multiprocessing.freeze_support()
    main()
```

- `pyproject.toml` - usunieto bezposrednia zaleznosc `pdf-craft>=1.0.13` z default dependencies. `pdf-craft` zostaje jako optional extra, zgodnie z celem: nie bundlowac ciezkich/opcjonalnych silnikow w core binary.
- `uv.lock` - zaktualizowany po usunieciu default `pdf-craft`.

Nie ruszac / nie stage'owac tych lokalnych zmian:

- `tests/fixtures/test_text.pdf`
- `tests/fixtures/test_text_1page.pdf`
- `tests/fixtures/test_text_full.pdf`

## Najwazniejsze decyzje techniczne

### 1. Nie zbierac calego Doclinga

Pierwsza wersja `build.spec` uzywala `collect_submodules("docling")`. To okazalo sie bledem, bo PyInstaller zaczal wciagac:

- `docling.experimental.*`,
- `docling.experimental.pipeline.threaded_layout_vlm_pipeline`,
- inne moduly VLM/experimental.

To narusza wymaganie prompta: bez VLM i bez ciezkich/niepotrzebnych komponentow.

Aktualny `build.spec` ma zawężone hidden imports:

```python
CORE_HIDDENIMPORTS = [
    "pymupdf4llm",
    "pymupdf",
    "docling",
    "docling.document_converter",
    "docling.datamodel.base_models",
    "docling.datamodel.pipeline_options",
    "docling.datamodel.accelerator_options",
]
```

Szerokie `collect_submodules()` zostalo tylko dla pakietow PyMuPDF:

```python
PYMUPDF_PACKAGES = (
    "pymupdf4llm",
    "pymupdf",
    "fitz",
)
```

Dodatkowe wykluczenia w spec:

```python
EXCLUDED_OPTIONAL_ENGINES = [
    "marker",
    "marker_pdf",
    "surya",
    "pdftext",
    "texify",
    "mineru",
    "magic_pdf",
    "pdf_craft",
    "olmocr",
    "vllm",
    "docling.experimental",
    "docling.experimental.datamodel.table_crops_layout_options",
    "docling.experimental.datamodel.threaded_layout_vlm_pipeline_options",
    "docling.experimental.models.table_crops_layout_model",
    "docling.experimental.pipeline.threaded_layout_vlm_pipeline",
]
```

### 2. Metadata sa potrzebne

Silniki `PyMuPDF4LLMEngine.is_available()` i `DoclingEngine.is_available()` uzywaja `importlib.metadata.version(...)`. Dlatego spec kopiuje metadata przez `copy_metadata()`, inaczej binary mogloby miec modul, ale raportowac silnik jako niedostepny.

### 3. CPU-only torch jest wymagany dla one-file

Standardowy wheel torcha z PyPI (`torch==2.10.0`) zainstalowal pakiety `nvidia-*` i `triton`.

Efekt:

- PyInstaller hook torcha wypisal `hook-torch: inferred hidden imports for CUDA libraries: [...]`.
- CArchive przekroczyl 4 GiB.
- Build CLI wywalil sie na:

```text
struct.error: 'I' format requires 0 <= number <= 4294967295
```

Rozwiazanie:

```bash
env UV_CACHE_DIR=/tmp/uv-cache uv pip install --reinstall --index-url https://download.pytorch.org/whl/cpu torch==2.10.0+cpu torchvision==0.25.0+cpu
env UV_CACHE_DIR=/tmp/uv-cache uv pip uninstall cuda-bindings cuda-pathfinder nvidia-cublas-cu12 nvidia-cuda-cupti-cu12 nvidia-cuda-nvrtc-cu12 nvidia-cuda-runtime-cu12 nvidia-cudnn-cu12 nvidia-cufft-cu12 nvidia-cufile-cu12 nvidia-curand-cu12 nvidia-cusolver-cu12 nvidia-cusparse-cu12 nvidia-cusparselt-cu12 nvidia-nccl-cu12 nvidia-nvjitlink-cu12 nvidia-nvshmem-cu12 nvidia-nvtx-cu12 triton
```

Po tym:

```text
torch                     2.10.0+cpu
torchvision               0.25.0+cpu
```

i nie ma juz `nvidia-*` / `triton` w `uv pip list`.

W skryptach i workflow dodano wymuszenie CPU-only torch przed PyInstallerem.

### 4. PySide6 nie zbierac calego drzewa

W jednej wersji spec dodal:

```python
QT_DATAS = safe_collect_data_files("PySide6")
QT_BINARIES = safe_collect_dynamic_libs("PySide6")
```

To zadzialalo, ale wciagnelo m.in. WebEngine, Multimedia, SQL drivers i powodowalo mase warningow o brakujacych bibliotekach `libpulse`, `libasound`, `libxkbfile`, `libpq`, `libmysqlclient`, itd.

Aktualna wersja `build.spec` zostala poprawiona:

- usunieto `collect_data_files("PySide6")`,
- usunieto `collect_dynamic_libs("PySide6")`,
- GUI polega na standardowych hookach PyInstaller dla importowanych modulow `PySide6.QtWidgets`, `QtGui`, `QtCore`,
- `datas=COMMON_DATAS`, czyli m.in. ikona SVG.

UWAGA: po tej ostatniej poprawce finalny rebuild zostal przerwany na prosbe uzytkownika. Trzeba go dokonczyc i zweryfikowac.

## Komendy, ktore przeszly

Statyka i testy przed buildem:

```bash
uv run ruff check .
# All checks passed!

uv run ruff format --check .
# 67 files already formatted

uv run mypy src/
# Success: no issues found in 42 source files

uv run pytest --cov=pdf2md -v
# 143 passed, 5 deselected
# TOTAL coverage: 89%
```

Instalacja PyInstaller:

```bash
uv pip install pyinstaller
```

Pierwsza proba `uv run pip install pyinstaller` byla bledna w tym srodowisku, bo trafila w PEP 668 / externally managed environment. Dlatego skrypty uzywaja `uv pip install pyinstaller`, nie `uv run pip install pyinstaller`.

## Buildy i wyniki

### Problem 1: uszkodzony stan `cv2` w venv

Po `uv sync --extra pymupdf --extra docling` venv mial `opencv-python` w metadanych, ale katalog `cv2` byl niepelny:

- `importlib.util.find_spec("cv2").origin == None`,
- brak `cv2/__init__.py`,
- brak `cv2/cv2.abi3.so`.

PyInstaller hook `hook-cv2.py` wywalil:

```text
TypeError: argument should be a str or an os.PathLike object where __fspath__ returns a str, not 'NoneType'
```

Naprawa:

```bash
env UV_CACHE_DIR=/tmp/uv-cache uv pip install --reinstall opencv-python
```

Po tym `cv2` byl normalnym modulem i build przeszedl dalej.

### Problem 2: CUDA torch >4 GiB

Build z CUDA torchem przekroczyl limit PyInstaller CArchive i zakonczyl sie bledem:

```text
struct.error: 'I' format requires 0 <= number <= 4294967295
```

Rozwiazanie: CPU-only torch, opisane wyzej.

### Udany pelny build przed ostatnia optymalizacja PySide6

Po CPU-only torch i jeszcze przed usunieciem pelnego `collect_data_files("PySide6")` udalo sie zbudowac oba binary:

```text
dist/pdf2md      454M
dist/pdf2md-gui  706M
```

Smoke testy przeszly:

```bash
./dist/pdf2md --help
./dist/pdf2md list-engines
./dist/pdf2md-gui --help
./dist/pdf2md convert tests/fixtures/test_text_1page.pdf --engine pymupdf4llm --output /tmp/pdf2md-smoke.md --verbose
./dist/pdf2md doctor
```

Wynik realnej konwersji:

```text
Pliki: 1/1
Czas: 1.33s
Silnik: PyMuPDF4LLM
```

Plik wynikowy:

```bash
wc -c /tmp/pdf2md-smoke.md
# 5469 /tmp/pdf2md-smoke.md
```

`doctor` z binary pokazal:

- PyTorch dziala,
- CUDA niedostepna,
- CUDA smoke test nieuzywalna,
- PyMuPDF4LLM dostepny,
- Docling dostepny,
- Marker i pdf-craft niedostepne,
- MinerU dostepny, ale dlatego, ze wykrywa zewnetrzny `mineru` w PATH przez `shutil.which()`; to nie znaczy, ze jest zbundlowany.

### Ostatni build przerwany

Po poprawce speca, ktora usuwa pelne zbieranie PySide6, uruchomiono finalny rebuild:

```bash
uv run pyinstaller build.spec --clean --noconfirm
```

Zostal przerwany na prosbe uzytkownika. Ostatnie logi byly na etapie analizy CLI:

```text
Analyzing hidden import 'docling.document_converter'
Processing hook-pypdfium2
Processing hook-pptx
Processing hook-docx
Processing hook-rtree
Analyzing hidden import 'fitz'
```

Proces zostal zatrzymany. Ten finalny rebuild trzeba powtorzyc od poczatku.

## Aktualny stan srodowiska

Branch:

```text
etap-10-packaging
```

Venv:

```text
docling                   2.97.0
docling-core              2.78.0
docling-ibm-models        3.13.2
docling-parse             6.2.0
docling-slim              2.97.0
pyinstaller               6.20.0
pyinstaller-hooks-contrib 2026.5
torch                     2.10.0+cpu
torchvision               0.25.0+cpu
```

Brak aktywnego procesu PyInstaller po pauzie.

`dist/` zawiera artefakty z poprzedniego udanego builda, niekoniecznie z najnowszej wersji `build.spec`:

```text
dist/pdf2md      454M
dist/pdf2md-gui  706M
```

Po wznowieniu trzeba wykonac rebuild, bo aktualny `build.spec` zostal odchudzony po tamtym sukcesie.

## Co zrobic po wznowieniu

1. Upewnic sie, ze nie ma procesu builda:

```bash
pgrep -af pyinstaller
```

2. Sprawdzic venv:

```bash
env UV_CACHE_DIR=/tmp/uv-cache uv pip list | rg -i "torch|nvidia|triton|cuda|docling|pyinstaller"
```

Oczekiwane:

- `torch==2.10.0+cpu`,
- `torchvision==0.25.0+cpu`,
- brak `nvidia-*`,
- brak `triton`.

3. Uruchomic finalny build:

```bash
uv run pyinstaller build.spec --clean --noconfirm
```

4. Po buildzie smoke testy:

```bash
ls -lh dist
./dist/pdf2md --help
./dist/pdf2md list-engines
./dist/pdf2md-gui --help
./dist/pdf2md convert tests/fixtures/test_text_1page.pdf --engine pymupdf4llm --output /tmp/pdf2md-smoke.md --verbose
./dist/pdf2md doctor
```

5. Jesli GUI nie startuje na Linuxie przez brak X/Wayland, najpierw wystarczy `./dist/pdf2md-gui --help`, bo GUI uruchamiane bez `--help` wymaga sesji graficznej.

6. Po finalnym buildzie ponowic:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src/
uv run pytest --cov=pdf2md -v
```

7. Sprawdzic status:

```bash
git status --short --branch
```

Uwaga: fixtures pozostawic poza stagingiem.

## Ryzyka / uwagi

- `build.spec` bundluje PyMuPDF4LLM i Docling. Nie bundluje Marker/MinerU/pdf-craft/VLM.
- PyMuPDF4LLM ma licencje AGPL/komercyjna wedlug obecnego README/katalogu. Prompt nazwal go lekkim core engine, ale licencyjnie warto to jeszcze potwierdzic przed publicznym release binary MIT.
- MinerU moze pokazywac sie jako dostepny w binary, jesli uzytkownik ma `mineru` w PATH. To jest zgodne z zalozeniem: zewnetrzna opcjonalna instalacja przez `shutil.which()`, nie bundlowanie.
- Workflow release wymusza CPU-only torch po `uv sync`. To nie jest zapisane w `uv.lock`; to swiadomy krok buildowy, bo lock/Docling moga wciagac standardowy torch z PyPI.
- Ostrzezenia PyInstaller o `torch.utils.tensorboard` sa nieblokujace.
- Ostrzezenia o `libSM/libICE` z `cv2` i o brakach linuxowych bibliotek GUI moga jeszcze wymagac oceny po finalnym, odchudzonym buildzie PySide6.
- `build/` i `dist/` sa artefaktami roboczymi. Nie commitowac ich, chyba ze repo ma inna polityke. Najpewniej zostawic poza stagingiem.
