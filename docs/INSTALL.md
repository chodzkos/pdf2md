# Instalacja pdf2md

`pdf2md` to orkiestrator (MIT) z CLI i GUI. **Nie bundluje** ciężkich ani copyleftowych silników
konwersji — silniki dokładasz w swoim środowisku. Ten dokument pokrywa wszystko: od najprostszej
instalacji pakietu, przez pełne środowisko deweloperskie (Windows natywnie + WSL z GPU), po
izolowane silniki VLM-OCR Fazy 2 i przeniesienie projektu na nową maszynę.

## Spis treści

1. [Co pdf2md potrzebuje](#1-co-pdf2md-potrzebuje)
2. [Szybka instalacja — pakiet użytkownika](#2-szybka-instalacja--pakiet-użytkownika)
3. [Instalacja z repozytorium (deweloperska)](#3-instalacja-z-repozytorium-deweloperska)
4. [Sprawdzenie, co masz](#4-sprawdzenie-co-masz)
5. [Windows (natywnie)](#5-windows-natywnie)
6. [WSL / Ubuntu (środowisko GPU)](#6-wsl--ubuntu-środowisko-gpu)
7. [Silniki-usługi izolowane (Faza 2)](#7-silniki-usługi-izolowane-faza-2)
8. [LLM (Ollama + chmura)](#8-llm-ollama--chmura)
9. [Weryfikacja końcowa](#9-weryfikacja-końcowa)
10. [Przeniesienie na nową maszynę](#10-przeniesienie-na-nową-maszynę)
11. [Rozwiązywanie problemów](#11-rozwiązywanie-problemów)

---

## 1. Co pdf2md potrzebuje

| Składnik | Do czego | Jak instalowany | Gdzie żyje |
|---|---|---|---|
| **Python 3.11–3.12** | runtime (3.13+ nieobsługiwany — ekosystem ML) | system / `uv` | system |
| **uv** | instalacja i uruchamianie projektu | osobny instalator | system |
| **Tesseract** (+ `pol`) | OCR skanów w Marker/Docling | pakiet systemowy | system |
| **Poppler** (`pdftoppm`) | PDF → obrazy (preprocessing, niektóre silniki) | pakiet systemowy | system |
| **Pandoc** | eksport EPUB | pakiet systemowy | system |
| **Ollama** | lokalny LLM (post-processing, korekta) | osobny instalator | usługa lokalna |
| **build-essential** (gcc) | kompilacja JIT kerneli (MinerU/olmOCR vLLM) | pakiet systemowy | system (WSL) |
| **Sterownik NVIDIA + CUDA** | GPU dla silników VLM/Surya/Marker | sterownik Windows → WSL | system |
| **PyMuPDF4LLM, Marker, Docling, Surya** | silniki konwersji (in-process) | `uv`/pip w venv projektu | venv projektu |
| **MinerU** | OCR (izolowany, subprocess) | `uv tool install` | osobne środowisko |
| **olmOCR** *(zaparkowany)* | VLM-OCR do skanów (izolowany) | osobny venv | `~/.venvs/olmocr` |
| **PaddleOCR-VL** | VLM-OCR, usługa HTTP (izolowany) | osobny venv + serwer | `~/.venvs/paddleocr` |

Zasada: **silniki rdzeniowe** (PyMuPDF4LLM, Marker, Docling, Surya) idą do venv projektu.
**Ciężkie silniki-usługi** (MinerU, olmOCR, PaddleOCR-VL) są izolowane w osobnych środowiskach, bo
ich zależności (vLLM, PaddlePaddle, transformers) konfliktują ze sobą i z projektem. vLLM działa
tylko pod Linux/WSL — na natywnym Windows te trzy silniki nie ruszą (ale Marker/Surya na GPU tak).

---

## 2. Szybka instalacja — pakiet użytkownika

Najprościej, jako narzędzie użytkownika:

```bash
uv tool install pdf2md
pdf2md doctor
```

Albo w aktywnym virtualenv:

```bash
uv pip install pdf2md
pdf2md doctor
```

Dokładanie silników rdzeniowych do izolowanego `uv tool`:

```bash
uv tool install pdf2md --with pymupdf4llm --with docling
```

---

## 3. Instalacja z repozytorium (deweloperska)

```bash
git clone https://github.com/chodzkos/pdf2md
cd pdf2md
uv sync --extra engines-core      # PyMuPDF4LLM + Marker + Docling + Surya (+ torch CUDA)
```

`engines-core` ciągnie też `torch`/`torchvision` z indeksu `cu130` (źródło w `pyproject.toml`),
więc na maszynie z kartą NVIDIA dostajesz `torch …+cu130` (GPU), nie `+cpu`. Silniki-usługi
(MinerU/olmOCR/PaddleOCR-VL) instaluje się osobno — sekcja 7.

---

## 4. Sprawdzenie, co masz

### 4a. Wbudowany doktor

```bash
cd ~/projekty/pdf2md
uv run pdf2md doctor          # System / GPU (realny smoke test CUDA) / narzędzia / Ollama / silniki / klucze API
uv run pdf2md list-engines    # które silniki widziane jako dostępne (+ wymóg GPU)
```

### 4b. Ręczna checklista (uruchom każde; obok — co znaczy „OK")

```bash
# --- narzędzia systemowe ---
tesseract --version           # OK: wersja, np. "tesseract 5.x"
tesseract --list-langs        # OK: na liście "pol" i "eng"
pdftoppm -v                   # OK: "pdftoppm version x.y" (Poppler)
pandoc --version              # OK: "pandoc x.y"
gcc --version                 # OK (WSL): potrzebny dla MinerU/olmOCR

# --- GPU ---
nvidia-smi                    # OK: tabela z kartą i wersją CUDA (w WSL ze sterownika Windows)
uv run python -c "import torch; print(torch.__version__, torch.cuda.is_available())"  # OK: ...+cu130 True

# --- Ollama ---
ollama --version              # OK: wersja
ollama list                   # OK: np. qwen3:14b

# --- silniki rdzeniowe ---
cd ~/projekty/pdf2md
uv run python -c "import pymupdf4llm, marker, docling, surya; print('rdzeniowe OK')"

# --- silniki izolowane (jeśli zainstalowane) ---
mineru --version                                            # MinerU
~/.venvs/olmocr/bin/python -c "import olmocr; print('olmOCR OK')"   # olmOCR (zaparkowany)
~/.venvs/paddleocr/bin/python -c "import vllm; print('paddle env OK')"  # serwer PaddleOCR-VL
```

---

## 5. Windows (natywnie)

Na Windowsie **natywnie** działają: GUI, silniki Fazy 1 (PyMuPDF4LLM, Marker, Docling) **oraz
Surya — na GPU (CUDA)**. Torch z CUDA wchodzi automatycznie przy `uv sync` (źródło `cu130` w
`pyproject.toml`). **Tylko silniki-usługi przez vLLM (MinerU/olmOCR/PaddleOCR-VL) wymagają WSL** —
vLLM nie wspiera natywnego Windows.

### 5.1 — narzędzia (winget w PowerShell)

```powershell
winget install pandoc
winget install astral-sh.uv
winget install Python.Python.3.12
winget install Ollama.Ollama
```

### 5.2 — Tesseract (instalator UB Mannheim)

- Pobierz instalator UB Mannheim (polecana dystrybucja Tesseract dla Windows).
- W instalatorze **zaznacz polski** (Polish) i ewentualnie inne języki.
- Dodaj folder `C:\Program Files\Tesseract-OCR\` do PATH **systemowego**.
- Nowy terminal: `tesseract --list-langs` ma zawierać `pol` i `eng`.

### 5.3 — Poppler (binarka + PATH)

- Pobierz ZIP Poppler dla Windows (np. `oschwartz10612/poppler-windows`).
- Rozpakuj do `C:\poppler`, dodaj `C:\poppler\Library\bin` do PATH.
- Sprawdź: `pdftoppm -v`.

### 5.4 — Ollama

```powershell
ollama pull qwen3:14b
ollama list
```

### 5.5 — projekt + silniki rdzeniowe (z GPU)

```powershell
cd G:\projekty\pdf2md
uv sync --extra engines-core
# weryfikacja GPU — ma być "...+cu130 True", NIE "...+cpu False":
uv run python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
uv run pdf2md doctor       # sekcja GPU: CUDA ✅, urządzenie = Twoja karta
uv run pdf2md-gui          # GUI działa natywnie na Windows
```
> **Torch CUDA na Windows:** `pyproject.toml` ma źródło `pytorch-cu130`, więc `uv sync` ściąga
> `torch …+cu130` (z CUDA), a nie `+cpu`. Gdyby `doctor` mimo to pokazał `CUDA ❌` / `torch …+cpu`,
> lock jest nieświeży — wymuś: `uv lock --upgrade-package torch --upgrade-package torchvision`,
> potem `uv sync --extra engines-core`. Mechanika: PROJEKT.md, macierz zależności silników.
> **NIE uruchamiaj GUI „jako administrator"** — Windows (UIPI) zablokuje wtedy przeciąganie plików.

### 5.6 — ciężkie silniki → w WSL

MinerU/olmOCR/PaddleOCR-VL nie instaluj natywnie. Wejdź do WSL (`wsl` w PowerShell) i zrób
sekcje 6–7. GUI na Windows + silniki-usługi w WSL to normalny, działający układ.

---

## 6. WSL / Ubuntu (środowisko GPU)

To główne środowisko, w którym realnie liczą się silniki GPU. Wykonuj po kolei.

### 6.1 — narzędzia systemowe

```bash
sudo apt update
sudo apt install -y tesseract-ocr tesseract-ocr-pol tesseract-ocr-eng \
                    poppler-utils pandoc build-essential libgl1 libglib2.0-0
```
`build-essential` (gcc) jest **konieczny** dla MinerU/olmOCR (kompilacja kerneli vLLM/Triton).

### 6.2 — GPU w WSL

```bash
nvidia-smi
```
Jeśli nie widzisz karty: upewnij się, że masz **WSL2** (nie WSL1) i **aktualny sterownik NVIDIA
w Windows** — sterownik z Windows „przechodzi" do WSL. **NIE instaluj osobnego sterownika w Ubuntu.**

### 6.3 — Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen3:14b
ollama list
```
(Na 24 GB VRAM możesz sięgnąć po większy model dla lepszej jakości korekty.)

### 6.4 — uv + silniki rdzeniowe

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
cd ~/projekty/pdf2md
uv sync --extra engines-core      # PyMuPDF4LLM + Marker + Docling + Surya (+ torch cu130)
```
> Surya jedzie w tym samym venv — to ten sam `surya-ocr`, którego używa Marker.

---

## 7. Silniki-usługi izolowane (Faza 2)

Te silniki mają konfliktujące zależności (vLLM/PaddlePaddle/transformers), więc żyją w osobnych
środowiskach. Tylko Linux/WSL.

### 7.1 — MinerU (izolowany, subprocess)

```bash
uv tool install mineru --with mineru[all]
mineru --version
```
Pierwsze uruchomienie pobierze modele. Tryb domyślny to `pipeline` (pewny). Tryb `vlm` wymaga
`VLLM_USE_FLASHINFER_SAMPLER=0` przy uruchomieniu (adapter ustawia to sam).

### 7.2 — olmOCR (ZAPARKOWANY — adapter gotowy)

Silnik jest **zaparkowany**: serwuje na 24 GB, ale zajmuje ~całą kartę (nie współistnieje z modelem
korekty LLM), start serwera 90–150 s/wywołanie, anglocentryczny. Dla dokumentów PL używaj
PaddleOCR-VL/Surya. Instaluj tylko, jeśli naprawdę potrzebujesz — i wtedy w trybie external-server.

```bash
uv venv ~/.venvs/olmocr --python 3.12
source ~/.venvs/olmocr/bin/activate
uv pip install olmocr
# olmocr NIE ciągnie torch/vllm — dołóż nightly-vLLM jak dla Paddle (7.3a):
uv pip install -U vllm --pre --torch-backend=auto --extra-index-url https://wheels.vllm.ai/nightly
# uruchomienie (na 24 GB; przy OOM zejdź do 0.80):
VLLM_USE_FLASHINFER_SAMPLER=0 python -m olmocr.pipeline <workspace> --pdfs <plik> \
  --model allenai/olmOCR-2-7B-1025-FP8 --markdown \
  --gpu_memory_utilization 0.90 --max_model_len 16384
deactivate
```
> Gołe `vllm serve` z tymi flagami wstaje poprawnie. W trybie spawn-per-plik serwer-dziecko olmocr
> potrafi nie wstać pod nightly-vLLM/transformers 5.x — dlatego produkcyjnie używaj trybu
> `--server <url>` (pole `olmocr_server_url`): własny, raz wystartowany serwer.

### 7.3 — PaddleOCR-VL (izolowany venv + usługa HTTP)

PaddleOCR-VL działa jako **serwer**, a pdf2md gada z nim po HTTP (jak z Ollamą). To **najtrudniejszy**
z silników Fazy 2 na Blackwellu — zrób go na końcu.

> 🛑 **Kiedy odpuścić.** PaddleOCR-VL **dubluje** MinerU/vlm, który już działa na tym GPU. Na
> premierowym Blackwellu z CUDA 13 jego stos vLLM nightly potrafi sypać się ścianą po ścianie
> (libcudart, flashinfer JIT, frankenstein cu12/cu13). Próbuj **raz**; jeśli nie wejdzie gładko —
> zaparkuj go i użyj MinerU/vlm albo Surya. Minimum „≥1 silnik VLM działa" spełnia **Surya**.

> ⚠️ **Wszystkie poniższe komendy w AKTYWNYM venv `~/.venvs/paddleocr`** (prompt musi pokazać
> `(paddleocr)`). Pułapka nazw: `paddleocr` (CLI) i `paddle` (framework) to DWA różne pakiety —
> do samego serwera VLM `paddle` NIE jest potrzebny.

```bash
uv venv ~/.venvs/paddleocr --python 3.12
source ~/.venvs/paddleocr/bin/activate     # prompt MUSI pokazać (paddleocr)
which python      # → ~/.venvs/paddleocr/bin/python
```

**a) Stos VLM pod Blackwella — vLLM nightly z `--torch-backend=auto`**

**Nie wymuszaj ręcznie indeksu cu129** — w połączeniu z `--index-strategy unsafe-best-match` miesza
to CUDA 12 i 13 i kończy się `ImportError: libcudart.so.13` (vLLM chce runtime CUDA 13, a wymuszony
torch jest cu12.9). Niech uv sam dobierze backend:

```bash
uv self update
uv pip install -U vllm --pre --torch-backend=auto \
  --extra-index-url https://wheels.vllm.ai/nightly
```
`--torch-backend=auto` dobiera właściwy indeks PyTorch (cu130 dla CUDA 13 na Blackwellu), więc nie
ma rozjazdu cu12/cu13. Nightly ściąga też `flashinfer-cubin`, `cuda-toolkit`, `nvidia-cuda-nvcc`.
Sam sampler flashinfera i tak JIT-uje i wykłada się na nvcc — dlatego serwer (krok b) uruchamiasz
z `VLLM_USE_FLASHINFER_SAMPLER=0`.

> Jeśli środowisko jest już zepsute mieszanką cu12/cu13 — **odtwórz venv od zera**:
> `deactivate; rm -rf ~/.venvs/paddleocr; uv venv ~/.venvs/paddleocr --python 3.12; source ...`.
> Najodporniejsza alternatywa to oficjalny Docker `paddleocr-genai-vllm-server` (spójny stos CUDA).

**b) Uruchom serwer VLM (paddle niepotrzebny)**

```bash
VLLM_USE_FLASHINFER_SAMPLER=0 vllm serve PaddlePaddle/PaddleOCR-VL-1.6 \
  --trust-remote-code --no-enable-prefix-caching
```
Pierwszy start łapie grafy CUDA (kilkadziesiąt sekund). Gotowy, gdy widzisz `Application startup
complete` / `Uvicorn running on http://0.0.0.0:8000`. API zgodne z OpenAI na `http://localhost:8000/v1`
— z tym gada adapter `paddleocr_vl_engine.py`.

Szybki test z drugiego terminala na stronie skanu:
```bash
pdftoppm -png -r 200 -f 1 -l 1 test_scan.pdf /tmp/page
PNG=$(ls /tmp/page*.png | head -1)
IMG=$(base64 -w0 "$PNG")
curl -s http://localhost:8000/v1/chat/completions -H "Content-Type: application/json" -d @- <<JSON | python3 -c "import sys,json;print(json.load(sys.stdin)['choices'][0]['message']['content'])"
{ "model":"PaddlePaddle/PaddleOCR-VL-1.6",
  "messages":[{"role":"user","content":[
    {"type":"image_url","image_url":{"url":"data:image/png;base64,$IMG"}},
    {"type":"text","text":"OCR:"}]}],
  "temperature":0.0 }
JSON
```

**c) (Opcjonalnie, później) Pełny pipeline z warstwą layoutu — OSOBNY venv**

Pełny PaddleOCR-VL = layout (PP-DocLayoutV2 na PaddlePaddle) + VLM. Dokumentacja każe trzymać layout
i VLM w **osobnych** środowiskach (konflikt o `transformers`). `paddle` instaluj w osobnym
venv-kliencie:

```bash
uv venv ~/.venvs/paddleocr-client --python 3.12
source ~/.venvs/paddleocr-client/bin/activate
uv pip install paddlepaddle-gpu==3.2.1 \
  --index-url https://www.paddlepaddle.org.cn/packages/stable/cu126/ \
  --extra-index-url https://pypi.org/simple/
uv pip install -U "paddleocr[doc-parser]>=3.4.0"
paddleocr doc_parser --vl_rec_backend vllm-server --vl_rec_server_url http://127.0.0.1:8000/v1 -i <plik>
deactivate
```

---

## 8. LLM (Ollama + chmura)

Lokalny **Ollama** nie wymaga SDK Pythona, tylko działającej usługi (sekcje 5.4 / 6.3).

SDK dla providerów chmurowych (opcjonalnie):

```bash
uv pip install anthropic
uv pip install openai
uv pip install google-genai        # NOWE SDK; stare google-generativeai jest EOL
```

Klucze ustawiasz w `~/.config/pdf2md/config.toml` albo przez zmienne środowiskowe:

```bash
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
GEMINI_API_KEY=...
```

---

## 9. Weryfikacja końcowa

```bash
cd ~/projekty/pdf2md
uv run pdf2md doctor          # System / GPU / Tesseract / Pandoc / Ollama / silniki / klucze
uv run pdf2md list-engines    # dostępne silniki + wymóg GPU
uv run pdf2md convert tests/fixtures/test_text_1page.pdf --engine pymupdf4llm   # próbna konwersja
```
Dobry stan na RTX 5090: GPU → `CUDA ✅` (urządzenie = karta); widoczne PyMuPDF4LLM, Marker, Docling,
Surya (na Windows i WSL); MinerU/PaddleOCR-VL dostępne, gdy ich środowiska/usługa są gotowe; olmOCR
zaparkowany (czerwony, jeśli nie masz jego venv — to OK).

---

## 10. Przeniesienie na nową maszynę

**Zasada: kodu NIE kopiujesz ręcznie — projekt żyje na GitHubie.** Przeniesienie = push wszystkiego
na starym + `git clone` na nowym + `uv sync` (środowisko odtwarzasz, nie kopiujesz). Trzy rzeczy,
których w Git nie ma: **klucze API** (`.env`/`config.toml`), **modele AI** (pobiorą się same przy
1. użyciu), **`.wslconfig`** (ma być INNY na każdej maszynie — dopasowany do RAM/GPU).

### Stary komputer

```bash
cd ~/projekty/pdf2md
git status                                   # sprawdź niezapisane zmiany
git add -A && git commit -m "zapis przed przeniesieniem"
git push --all                               # wszystkie gałęzie
cat .env                                     # zapisz klucze w bezpiecznym miejscu (menedżer haseł)
cat ~/.config/pdf2md/config.toml             # jeśli istnieje
```

### Nowy komputer

```powershell
wsl --install                                # PowerShell jako admin; restart jeśli poprosi
```
Następnie ustaw `C:\Users\<user>\.wslconfig` pod mocny sprzęt (np. `memory=32GB`, `swap=16GB`,
`processors=8`), `wsl --shutdown`, otwórz WSL ponownie. Dalej w WSL:

```bash
# klucz SSH dla GitHub (każda maszyna ma własny):
ssh-keygen -t ed25519 -C "twoj@email.com"    # Enter 3x
cat ~/.ssh/id_ed25519.pub                     # wklej w github.com/settings/keys
ssh -T git@github.com

# pakiety systemowe + uv (sekcja 6.1, 6.4):
sudo apt update && sudo apt install -y poppler-utils tesseract-ocr tesseract-ocr-pol \
    tesseract-ocr-eng pandoc build-essential libgl1 libglib2.0-0
curl -LsSf https://astral.sh/uv/install.sh | sh && source ~/.bashrc

# klon + środowisko:
mkdir -p ~/projekty && cd ~/projekty
git clone git@github.com:chodzkos/pdf2md.git && cd pdf2md
git log --oneline -5                          # te same commity co na starym
uv sync --extra engines-core                  # odtwarza środowisko + torch cu130 (GPU od razu)

# odtwórz klucze API:
cat > .env << 'ENVEOF'
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AI...
ENVEOF

pdf2md doctor                                 # weryfikacja nowej maszyny
```
> **GPU od ręki:** dzięki źródłu `cu130` w `pyproject.toml` `uv sync` od razu daje `torch …+cu130`
> (nie musisz już ręcznie doinstalowywać CUDA-torcha jak na starym sprzęcie). Sprawdź:
> `uv run python -c "import torch; print(torch.cuda.is_available())"` → `True`.

**Czego NIE przenosić:** folder `.venv/` (odtwarza `uv sync`), `__pycache__/`/`dist/`/`build/`
(regenerowalne), `.wslconfig` (inny na każdej maszynie), modele AI (pobiorą się same; ewentualnie
skopiuj cache `~/.cache/huggingface/`, ale to opcjonalne).

---

## 11. Rozwiązywanie problemów

### Windows

- **Przeciąganie plików do okna nie działa** → nie uruchamiaj GUI jako administrator (UIPI blokuje
  drag-and-drop z Eksploratora). Odpalaj `pdf2md-gui` ze zwykłego terminala.
- **`command not found` przy `pdf2md`/`marker_single`** → pod `uv` programy projektu nie trafiają
  do PATH. Wołaj przez `uv run pdf2md ...` albo aktywuj venv (`.venv\Scripts\activate`).
- **GPU: `torch …+cpu` / `CUDA ❌` mimo karty** → lock nieświeży; `uv lock --upgrade-package torch
  --upgrade-package torchvision`, potem `uv sync --extra engines-core` (zob. sekcja 5.5).
- **`tesseract`/`pdftoppm` niewidoczne mimo instalacji** → nie dodane do PATH **systemowego** albo
  stary terminal; dodaj ścieżki i otwórz nowe okno. Jeśli `uv run` ich nie widzi mimo PATH —
  uruchamiaj z aktywowanego venv.

### Silniki / ML

- **Docling: `CUDA error: no kernel image is available`** → GPU zbyt stare dla aktualnego PyTorch
  (np. GTX 10xx, Pascal sm_61). Wymuś CPU: `pdf2md config set docling_device cpu`.
- **Marker/Docling bardzo wolne** → na CPU/starym GPU to normalne. Do PDF-ów z tekstem używaj
  PyMuPDF4LLM (błyskawiczny, bez GPU).
- **Konwersja skanów daje pusty/zły tekst** → brak OCR; zainstaluj Tesseract (+`pol`) i dodaj do
  PATH. `doctor` podpowie.
- **MinerU nie instaluje się na Pythonie 3.13** → zależność `ray` nie wspiera 3.13; instaluj na
  3.12: `uv tool install mineru --with mineru[all] --python 3.12`.
- **MinerU/olmOCR: „Failed to find C compiler"** → brak `build-essential` (sekcja 6.1).
- **MinerU/olmOCR: „Could not find nvcc"** → uruchom z `VLLM_USE_FLASHINFER_SAMPLER=0`.

### LLM

- **Ollama: `HTTP Error 404`** → model nie pobrany. `ollama list`, potem ustaw model, który masz,
  np. `pdf2md config set ollama_model qwen3:14b`. Duże modele (14B+) wymagają VRAM — na ≤8 GB użyj
  wariantu 7B albo LLM w chmurze.
- **Gemini: „klucz jest, ale pakiet nie zainstalowany"** → `uv pip install google-genai` (stare
  `google-generativeai` jest EOL).

### GPU / WSL / PaddleOCR-VL

- **`nvidia-smi` nic nie pokazuje w WSL** → WSL2 + aktualny sterownik NVIDIA w Windows (nie instaluj
  sterownika w Ubuntu).
- **PaddleOCR-VL `ModuleNotFoundError: paddle`** → do samego serwera VLM `paddle` nie jest potrzebny;
  serwuj `vllm serve PaddlePaddle/PaddleOCR-VL-1.6`. Paddle tylko w osobnym venv-kliencie (7.3c).
- **PaddleOCR-VL `libcudart.so.13: cannot open`** → rozjazd cu12/cu13; instaluj vLLM z
  `--torch-backend=auto` (NIE ręczny `--extra-index-url cu129 --index-strategy unsafe-best-match`);
  jak venv zepsuty — odtwórz od zera.
- **PaddleOCR-VL sypie się ścianą po ścianie na Blackwellu** → udokumentowane bagno; odpuść i użyj
  MinerU/vlm (już działa) albo oficjalnego Dockera. Nie blokuj nim Etapu 12 (minimum = Surya).
