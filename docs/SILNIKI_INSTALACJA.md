# pdf2md — zewnętrzne silniki i zależności: sprawdzanie i instalacja

Ten dokument zbiera wszystko, co **nie jest** zwykłą zależnością pip pakietu `pdf2md`, a czego
pdf2md potrzebuje do pełnego działania: narzędzia systemowe (Tesseract, Poppler, Pandoc),
lokalny LLM (Ollama), kompilator (build-essential) oraz ciężkie, izolowane silniki OCR
(MinerU, olmOCR, PaddleOCR-VL). Pisane krok po kroku — można iść z góry na dół.

> **Dlaczego osobny dokument?** Fazę 1 robiłeś na starym komputerze, więc na nowej maszynie
> (RTX 5090, WSL) części tych rzeczy może brakować. Najpierw sprawdź, co masz (sekcja 1),
> potem dołóż brakujące (sekcje 2–3).

---

## 0. Co pdf2md w ogóle potrzebuje

| Składnik | Do czego | Faza | Jak instalowany | Gdzie żyje |
|---|---|---|---|---|
| **Tesseract** (+ `pol`) | OCR skanów w Marker/Docling | 1 | pakiet systemowy | system |
| **Poppler** (`pdftoppm`) | PDF → obrazy (preprocessing, niektóre silniki) | 1/2 | pakiet systemowy | system |
| **Pandoc** | eksport EPUB | 2 | pakiet systemowy | system |
| **Ollama** | lokalny LLM (post-processing, korekta) | 1/2 | osobny instalator | usługa lokalna |
| **build-essential** (gcc) | kompilacja JIT kerneli (MinerU/olmOCR vLLM) | 2 | pakiet systemowy | system |
| **Sterownik NVIDIA + CUDA** | GPU dla silników VLM | 2 | sterownik Windows → WSL | system |
| **PyMuPDF4LLM, Marker, Docling, Surya** | silniki konwersji (in-process) | 1/2 | `uv`/pip w venv projektu | venv projektu |
| **MinerU** | OCR (izolowany, subprocess) | 1/2 | `uv tool install` | osobne środowisko |
| **olmOCR** | VLM-OCR do skanów (izolowany) | 2 | osobny venv | `~/.venvs/olmocr` |
| **PaddleOCR-VL** | VLM-OCR, usługa HTTP (izolowany) | 2 | osobny venv + serwer | `~/.venvs/paddleocr` |

Zasada: **silniki rdzeniowe** (PyMuPDF4LLM, Marker, Docling, Surya) idą do venv projektu.
**Ciężkie silniki** (MinerU, olmOCR, PaddleOCR-VL) są izolowane w osobnych środowiskach, bo
ich zależności (vLLM, PaddlePaddle, transformers) konfliktują ze sobą i z projektem.

---

## 1. Jak sprawdzić, co już masz

### 1a. Najpierw wbudowany doktor pdf2md

```bash
cd ~/projekty/pdf2md
uv run pdf2md doctor
```
Pokaże stan Tesseract / Pandoc / Ollama i ścieżki. To pierwszy strzał — ale doktor może nie
sprawdzać jeszcze silników Fazy 2, więc poniżej pełna lista ręczna.

### 1b. Ręczna checklista (uruchom każde; obok — co znaczy „OK")

```bash
# --- narzędzia systemowe ---
tesseract --version           # OK: wypisze wersję, np. "tesseract 5.x"
tesseract --list-langs        # OK: na liście jest "pol" (polski) i "eng"
pdftoppm -v                   # OK: "pdftoppm version x.y" (to Poppler)
pandoc --version              # OK: "pandoc x.y"
gcc --version                 # OK: "gcc (Ubuntu ...)"  — potrzebny dla MinerU/olmOCR

# --- GPU ---
nvidia-smi                    # OK: tabela z RTX 5090 i wersją CUDA
                              #     (w WSL to pochodzi ze sterownika Windows)

# --- Ollama ---
ollama --version              # OK: wersja
ollama list                   # OK: na liście jest np. qwen3:14b

# --- uv ---
uv --version                  # OK: wersja uv

# --- silniki rdzeniowe (w venv projektu) ---
cd ~/projekty/pdf2md
uv run python -c "import pymupdf4llm, marker, docling, surya; print('rdzeniowe OK')"

# --- MinerU (izolowany) ---
mineru --version              # OK: wersja 2.x  (jeśli 'command not found' → nie masz)

# --- olmOCR (izolowany) ---
ls ~/.venvs/olmocr 2>/dev/null && \
  ~/.venvs/olmocr/bin/python -c "import olmocr; print('olmOCR OK')" \
  || echo "olmOCR: brak środowiska"

# --- PaddleOCR-VL (izolowany) ---
ls ~/.venvs/paddleocr 2>/dev/null && \
  ~/.venvs/paddleocr/bin/python -c "import paddle; paddle.utils.run_check()" \
  || echo "PaddleOCR: brak środowiska"
```

Czego brakuje — instalujesz z sekcji niżej. Jeśli wszystko zwróciło „OK", masz komplet.

---

## 2. Instalacja — WSL / Ubuntu (główne środowisko na RTX 5090)

> Wykonuj po kolei. Linijki z `sudo` poproszą o hasło. To jest środowisko, w którym
> realnie liczą się silniki GPU.

### Krok 2.1 — narzędzia systemowe (jednym poleceniem)

```bash
sudo apt update
sudo apt install -y tesseract-ocr tesseract-ocr-pol tesseract-ocr-eng \
                    poppler-utils pandoc build-essential
```
- `tesseract-ocr` + `-pol` + `-eng` — OCR i polski słownik.
- `poppler-utils` — `pdftoppm`/`pdfinfo` (PDF→obraz).
- `pandoc` — eksport EPUB (Faza 2).
- `build-essential` — gcc; **konieczny** dla MinerU/olmOCR (kompilacja kerneli vLLM/Triton).

### Krok 2.2 — sprawdź GPU w WSL

```bash
nvidia-smi
```
Powinieneś zobaczyć RTX 5090. Jeśli nie:
- upewnij się, że masz **WSL2** (nie WSL1) i **aktualny sterownik NVIDIA zainstalowany w Windows**
  (sterownik z Windows „przechodzi" do WSL — NIE instaluj osobnego sterownika w Ubuntu).

### Krok 2.3 — Ollama (lokalny LLM)

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen3:14b          # model do post-processingu/korekty
ollama list                    # potwierdź
```
(Na 24 GB VRAM możesz później sięgnąć po `qwen3:27b`/`30b` dla lepszej jakości.)

### Krok 2.4 — uv (menedżer pakietów projektu)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# przeładuj powłokę albo: source ~/.bashrc
uv --version
```

### Krok 2.5 — silniki rdzeniowe projektu (w venv projektu)

```bash
cd ~/projekty/pdf2md
uv sync                                  # jeśli masz lock/pyproject z zależnościami
# albo jawnie z extra:
uv pip install -e ".[engines-core]"      # PyMuPDF4LLM + Marker + Docling + transformers>=4.48,<5
```
> Surya (silnik Etapu 12) jedzie w tym samym venv — to ten sam `surya-ocr`, którego używa Marker.

### Krok 2.6 — MinerU (izolowany, subprocess)

```bash
uv tool install mineru --with mineru[all]
mineru --version                         # potwierdź
```
Pierwsze uruchomienie pobierze modele. Tryb domyślny w pdf2md to `pipeline` (pewny). Tryb `vlm`
wymaga, by przy uruchomieniu było ustawione `VLLM_USE_FLASHINFER_SAMPLER=0` (adapter robi to sam).

### Krok 2.7 — olmOCR (izolowany venv, Faza 2)

```bash
uv venv ~/.venvs/olmocr --python 3.12
source ~/.venvs/olmocr/bin/activate
uv pip install olmocr
# test (model 7B pobierze się przy 1. uruchomieniu):
VLLM_USE_FLASHINFER_SAMPLER=0 python -m olmocr.pipeline --help
deactivate
```
> `VLLM_USE_FLASHINFER_SAMPLER=0` omija problem „Could not find nvcc" na Blackwellu (flashinfer
> JIT-uje sampler przez nvcc, którego nie masz). Dokładną komendę pipeline'u sprawdź w docs olmOCR.

### Krok 2.8 — PaddleOCR-VL (izolowany venv + usługa HTTP, Faza 2)

PaddleOCR-VL działa jako **serwer**, a pdf2md gada z nim po HTTP (jak z Ollamą). To
**najtrudniejszy** z silników Fazy 2 na Blackwellu — zrób go na końcu (po Surya i olmOCR).

> 🛑 **Kiedy odpuścić (czytaj przed instalacją).** PaddleOCR-VL **dubluje** MinerU/vlm, który
> już działa na tym GPU. Na premierowym Blackwellu z CUDA 13 jego stos vLLM nightly potrafi
> sypać się ścianą po ścianie (libcudart, flashinfer JIT, frankenstein cu12/cu13). **Nie blokuj
> nim Etapu 12** — minimum etapu („≥1 silnik VLM działa") spełnia **Surya** (in-process, główny
> venv, zero tego stosu). Próbuj PaddleOCR-VL **raz**; jeśli nie wejdzie gładko — zaparkuj go,
> zrób Surya/olmOCR, a do Paddle wróć ewentualnie przez Docker (ramka w sekcji a).

> ⚠️ **KLUCZOWE: wszystkie poniższe komendy uruchamiaj w AKTYWNYM venv `~/.venvs/paddleocr`.**
> W prompcie musisz widzieć `(paddleocr)`. Jeśli go nie ma — komendy trafią w złe miejsce
> (python projektu / przypadkowa instalacja). **Nie wklejaj `deactivate` przed końcem.**
> Pułapka nazw: `paddleocr` (toolkit/CLI) i `paddle` (framework, `import paddle`) to DWA różne
> pakiety. Do samego serwera VLM `paddle` NIE jest potrzebny (patrz niżej).

```bash
uv venv ~/.venvs/paddleocr --python 3.12
source ~/.venvs/paddleocr/bin/activate     # prompt MUSI pokazać (paddleocr)

# SZYBKI TEST: czy jestem w dobrym środowisku?
which python      # → /home/<user>/.venvs/paddleocr/bin/python
which vllm        # → /home/<user>/.venvs/paddleocr/bin/vllm  (po instalacji niżej)
```

#### a) Stos VLM pod Blackwella — vLLM nightly z `--torch-backend=auto`

To jest właściwa ścieżka dla RTX 5090. **Nie wymuszaj ręcznie indeksu cu129** — w połączeniu
z `--index-strategy unsafe-best-match` miesza to pakiety CUDA 12 i CUDA 13 i kończy się błędem
`ImportError: libcudart.so.13: cannot open shared object file` (znany bug vLLM nightly —
vLLM chce runtime CUDA 13, a wymuszony torch jest cu12.9). Zamiast tego niech uv sam dobierze
zgodny backend:

```bash
uv self update                       # --torch-backend wymaga świeżego uv
uv pip install -U vllm --pre --torch-backend=auto \
  --extra-index-url https://wheels.vllm.ai/nightly
```
`--torch-backend=auto` inspekcjonuje sterownik i dobiera właściwy indeks PyTorch (cu130 dla
CUDA 13 na Blackwellu), więc nie powstaje rozjazd cu12/cu13. Nightly ściąga też komplet pod
sm_120 — `flashinfer-cubin` (PREKOMPILOWANE kernele), `cuda-toolkit`, `nvidia-cuda-nvcc` — co
załatwia import vLLM i ładowanie modelu. **Uwaga:** sam sampler flashinfera i tak próbuje JIT i
wykłada się na nvcc — dlatego serwer w kroku b uruchamiasz z `VLLM_USE_FLASHINFER_SAMPLER=0`.

> Jeśli środowisko jest już zepsute mieszanką cu12/cu13 (jak po wcześniejszym `--extra-index-url
> cu129 --index-strategy unsafe-best-match`), **odtwórz venv od zera** zamiast łatać:
> `deactivate; rm -rf ~/.venvs/paddleocr; uv venv ~/.venvs/paddleocr --python 3.12; source ...`.

> ⚠️ **To jest udokumentowane bagno** na premierowym Blackwellu (zob. vLLM issue „SM120 + CUDA 13:
> 5 sequential failures"). Jeśli `--torch-backend=auto` nie wejdzie gładko za pierwszym razem —
> **nie drąż**. Patrz ramka „kiedy odpuścić" niżej. Najodporniejsza alternatywa to oficjalny
> obraz Docker `paddleocr-genai-vllm-server` (zamknięty, spójny stos CUDA), kosztem
> nvidia-container-toolkit w WSL.

#### b) Uruchom serwer VLM — wprost przez vLLM (paddle niepotrzebny)

`VLLM_USE_FLASHINFER_SAMPLER=0` jest na tym GPU **wymagane** — bez niego flashinfer próbuje
zJIT-ować kernel samplera (`top_k_mask_logits`) i wykłada się na braku nvcc (ten sam błąd co
przy MinerU/vlm; prekompilowany `flashinfer-cubin` nie pokrywa tej operacji). Z env serwer
przechodzi warmup i wstaje:

```bash
VLLM_USE_FLASHINFER_SAMPLER=0 vllm serve PaddlePaddle/PaddleOCR-VL-1.6 \
  --trust-remote-code --no-enable-prefix-caching
```
Pierwszy start łapie grafy CUDA (`Profiling CUDA graph memory ...`) — to trwa kilkadziesiąt
sekund. Serwer jest gotowy, gdy zobaczysz `Uvicorn running on http://0.0.0.0:8000` /
`Application startup complete`. API zgodne z OpenAI na `http://localhost:8000/v1` — i z tym gada
adapter `paddleocr_vl_engine.py`. (Warning `_POSIX_C_SOURCE redefined` z triton/gcc jest
nieszkodliwy.)

Szybki test z drugiego terminala na realnej stronie skanu (sam VLM-OCR, bez layoutu):
```bash
pdftoppm -png -r 200 -f 1 -l 1 test_scan.pdf /tmp/page    # → /tmp/page-1.png
PNG=$(ls /tmp/page*.png | head -1)
IMG=$(base64 -w0 "$PNG")
curl -s http://localhost:8000/v1/chat/completions -H "Content-Type: application/json" -d @- <<EOF | python3 -c "import sys,json;print(json.load(sys.stdin)['choices'][0]['message']['content'])"
{ "model":"PaddlePaddle/PaddleOCR-VL-1.6",
  "messages":[{"role":"user","content":[
    {"type":"image_url","image_url":{"url":"data:image/png;base64,$IMG"}},
    {"type":"text","text":"OCR:"}]}],
  "temperature":0.0 }
EOF
```

#### c) (Opcjonalnie, później) Pełny pipeline z warstwą layoutu — OSOBNY venv

Pełny PaddleOCR-VL = layout (PP-DocLayoutV2 na PaddlePaddle) + VLM. Dokumentacja wprost mówi
trzymać layout i VLM w **osobnych środowiskach** (konflikt o `transformers`). Więc `paddle`
instaluj **nie tutaj**, tylko w osobnym venv-kliencie:

```bash
uv venv ~/.venvs/paddleocr-client --python 3.12
source ~/.venvs/paddleocr-client/bin/activate
uv pip install paddlepaddle-gpu==3.2.1 \
  --index-url https://www.paddlepaddle.org.cn/packages/stable/cu126/ \
  --extra-index-url https://pypi.org/simple/
uv pip install -U "paddleocr[doc-parser]>=3.4.0"
python -c "import paddle; print(paddle.__version__)"   # potwierdź w TYM venv
# klient woła usługę VLM (serwer z kroku b):
paddleocr doc_parser --vl_rec_backend vllm-server --vl_rec_server_url http://127.0.0.1:8000/v1 \
  -i <plik_lub_obraz>
deactivate
```
> Layout na paddle (cu126) jest lekki — gdyby nie ruszył na sm_120, może zjechać na CPU bez
> wielkiej straty; ciężar (VLM) i tak idzie przez vLLM nightly w pierwszym venv. Pełny pipeline
> rób dopiero, gdy sam VLM (krok b) daje dobre wyniki na Twoich skanach.

Gdy skończysz: `deactivate`.

---

## 3. Instalacja — Windows (natywnie)

Na Windowsie **natywnie** trzymaj GUI i lekki stack Fazy 1. **Ciężkie silniki GPU
(MinerU/olmOCR/PaddleOCR-VL) uruchamiaj w WSL** — bo vLLM nie wspiera natywnego Windows.
Innymi słowy: GUI może być na Windows, ale „premium scan pipeline" Fazy 2 i tak działa w WSL.

### Krok 3.1 — narzędzia (najprościej przez winget w PowerShell)

```powershell
winget install pandoc
winget install astral-sh.uv
winget install Python.Python.3.12
winget install Ollama.Ollama
```

### Krok 3.2 — Tesseract (instalator UB Mannheim)

- Pobierz instalator z UB Mannheim (najczęściej polecana wersja Tesseract dla Windows).
- W instalatorze **zaznacz polski język** (Polish) i ewentualnie inne.
- Po instalacji dodaj folder Tesseract do PATH (instalator zwykle proponuje).
- Sprawdź w nowym oknie: `tesseract --version` i `tesseract --list-langs` (ma być `pol`).

### Krok 3.3 — Poppler (binarka + PATH)

- Pobierz binarkę Poppler dla Windows (paczka zip z `pdftoppm.exe`, `pdfinfo.exe`).
- Rozpakuj np. do `C:\poppler` i dodaj `C:\poppler\Library\bin` do PATH.
- Sprawdź: `pdftoppm -v`.

### Krok 3.4 — Ollama

- Zainstalowane przez winget (krok 3.1) albo instalatorem z ollama.com.
- `ollama pull qwen3:14b`, potem `ollama list`.

### Krok 3.5 — projekt + silniki rdzeniowe

```powershell
cd G:\projekty\pdf2md
uv sync
# albo:
uv pip install -e ".[engines-core]"
uv run pdf2md-gui          # GUI działa natywnie na Windows
```
> NIE uruchamiaj GUI „jako administrator" — Windows (UIPI) zablokuje wtedy przeciąganie plików.

### Krok 3.6 — ciężkie silniki (MinerU/olmOCR/PaddleOCR-VL) → w WSL

Tych nie instaluj natywnie na Windows. Wejdź do WSL (`wsl` w PowerShell) i zrób sekcje
2.6–2.8. GUI na Windows + silniki w WSL to normalny, działający układ na tej maszynie.

---

## 4. Weryfikacja końcowa

```bash
cd ~/projekty/pdf2md
uv run pdf2md doctor          # Tesseract / Pandoc / Ollama
uv run pdf2md list-engines    # które silniki widziane jako dostępne (+ wymóg GPU)
```
Dobry stan na RTX 5090 (WSL): widoczne PyMuPDF4LLM, Marker, Docling, Surya, MinerU; a olmOCR
i PaddleOCR-VL dostępne, gdy ich środowiska/usługa są gotowe.

---

## Szybka ściąga „czego mi brakuje?"

- `tesseract: command not found` → krok 2.1 (lub 3.2 na Windows)
- `pdftoppm: not found` → Poppler: krok 2.1 / 3.3
- `pandoc: not found` → krok 2.1 / 3.1
- `gcc: not found` → `sudo apt install build-essential` (krok 2.1)
- `mineru: command not found` → krok 2.6
- MinerU/olmOCR: „Failed to find C compiler" → brak `build-essential` (krok 2.1)
- MinerU/olmOCR: „Could not find nvcc" → uruchom z `VLLM_USE_FLASHINFER_SAMPLER=0`
- `nvidia-smi` nic nie pokazuje w WSL → WSL2 + aktualny sterownik NVIDIA w Windows
- PaddleOCR-VL `ModuleNotFoundError: paddle` → do samego serwera VLM paddle NIE jest potrzebny; serwuj `vllm serve PaddlePaddle/PaddleOCR-VL-1.6`. Paddle tylko w osobnym venv-kliencie (krok 2.8c)
- PaddleOCR-VL `invalid choice: 'genai_server'` → użyj `vllm serve` zamiast `genai_server`; ewentualnie `paddleocr install_genai_server_deps vllm` najpierw
- PaddleOCR-VL na Blackwellu → vLLM nightly cu129 (ściąga nvcc + flashinfer-cubin, więc sm_120/nvcc załatwione)
- PaddleOCR-VL `libcudart.so.13: cannot open` → rozjazd cu12/cu13; instaluj vLLM z `--torch-backend=auto` (NIE ręczny `--extra-index-url cu129 --index-strategy unsafe-best-match`); jak venv zepsuty — odtwórz od zera
- PaddleOCR-VL sypie się ścianą po ścianie na Blackwellu → to udokumentowane bagno; odpuść i użyj MinerU/vlm (już działa) albo oficjalnego Dockera; nie blokuj nim Etapu 12 (minimum = Surya)
