"""Treść okna pomocy offline pdf2md — zakładki dla kitowego ``HelpWindow``.

Okno (belka DWM + re-render motywu) liczy wspólny kit
(:class:`chodzkos_gui_kit.qt.widgets.HelpWindow`). pdf2md był wzorcem ekstrakcji
tego widgetu — teraz go konsumuje. Tu zostaje WYŁĄCZNIE wiedza o pdf2md: lista
zakładek ``(tytuł, html)`` (:func:`help_tabs`) składana kitowymi helperami HTML.

Kolory w HTML idą WYŁĄCZNIE przez funkcję ``palette(...)`` Qt — tła treści na
``palette(alternate-base)`` + tekst ``palette(text)``; zero zaszytych hexów.
``QTextBrowser`` rozwiązuje ``palette(...)`` do konkretnych kolorów przy
``setHtml`` i nie aktualizuje ich przy zmianie motywu — re-render na
``PaletteChange`` (re-``setHtml`` tym samym html) robi teraz kit dla WSZYSTKICH
zakładek (``HelpWindow.changeEvent``).

Wołający::

    from chodzkos_gui_kit.qt.widgets import HelpWindow
    from pdf2md.gui.help_window import HELP_TITLE, help_tabs
    HelpWindow(parent, title=HELP_TITLE, tabs=help_tabs()).exec()
"""

from __future__ import annotations

from chodzkos_gui_kit.qt.widgets import (
    code as _code,
)
from chodzkos_gui_kit.qt.widgets import (
    paragraph as _p,
)
from chodzkos_gui_kit.qt.widgets import (
    preformatted as _pre,
)
from chodzkos_gui_kit.qt.widgets import (
    section as _section,
)
from chodzkos_gui_kit.qt.widgets import (
    table as _table,
)
from chodzkos_gui_kit.qt.widgets import (
    unordered_list as _ul,
)

HELP_TITLE = "Pomoc — pdf2md"


def help_tabs() -> list[tuple[str, str]]:
    """Zakładki pomocy jako ``(tytuł, html)`` — składane kitowymi helperami HTML."""
    return [
        ("Silniki konwersji", _engines_tab()),
        ("Instalacja silników", _install_tab()),
        ("Post-processing LLM", _llm_tab()),
        ("Profile skanowania", _profiles_tab()),
        ("CLI", _cli_tab()),
        ("Model AI / Ollama", _models_tab()),
    ]


# ── Treść zakładek (po polsku; opis realnego stanu z kodu) ─────────────────────


def _engines_tab() -> str:
    table = _table(
        ["Silnik", "Typ dokumentu", "OCR", "Grupa"],
        [
            [
                "PyMuPDF4LLM",
                "Natywne PDF z warstwą tekstową (raporty, instrukcje) — najszybszy",
                "Nie",
                "główne",
            ],
            [
                "Marker",
                "Skany, dokumenty mieszane, trudniejszy layout; opcjonalny LLM",
                "Tak (CPU)",
                "główne",
            ],
            ["Docling", "Tabele, dokumenty biznesowe, struktura, RAG", "Tak", "główne"],
            [
                "Surya",
                "Layout + OCR + reading order, GPU, in-process",
                "Tak",
                "GPU (też Windows)",
            ],
            [
                "MinerU",
                "Artykuły naukowe, CJK, wielokolumnowe układy",
                "Tak",
                "izolowany — Linux/WSL",
            ],
            ["PaddleOCR-VL", "Wielojęzyczny VLM-OCR (serwer vLLM)", "Tak", "izolowany — Linux/WSL"],
            [
                "olmOCR",
                "VLM 7B do skanów (zaparkowany, anglocentryczny)",
                "Tak",
                "izolowany — Linux/WSL",
            ],
        ],
    )
    groups = _p(
        "Silniki dzielą się na trzy grupy: <b>główne</b> (PyMuPDF4LLM / Marker / Docling — działają "
        "wszędzie), <b>Surya</b> (GPU, ale dzieli środowisko projektu — działa też pod Windows) oraz "
        "<b>izolowane usługi VLM-OCR</b> (MinerU / PaddleOCR-VL / olmOCR). Te ostatnie opierają się "
        "na vLLM i <b>działają tylko pod Linux/WSL</b> (pod natywnym Windows nie ruszą) — uruchamiasz "
        "je przez CLI. <b>olmOCR</b> jest dodatkowo <b>zaparkowany</b> (anglocentryczny, zajmuje "
        "~całą kartę); dla skanów po polsku użyj PaddleOCR-VL lub Surya."
    )
    doctor = _p(
        "Co jest zainstalowane i dostępne w <b>Twoim</b> środowisku — wraz ze statusem GPU/CUDA, "
        "Ollamy, narzędzi i kluczy API — sprawdzisz komendą " + _code("pdf2md doctor") + "."
    )
    when = _p(
        "<b>Kiedy który:</b> natywny tekst → PyMuPDF4LLM; skan / mieszane → Marker; "
        "tabele / biznes → Docling; kontrola layoutu → Surya; nauka / CJK / wielokolumnowe → MinerU; "
        "wielojęzyczny VLM → PaddleOCR-VL."
    )
    return _section("Silniki konwersji", table + groups + doctor + when)


def _install_tab() -> str:
    core = _section(
        "Silniki rdzeniowe",
        _pre("uv sync --extra engines-core")
        + _p(
            "Instaluje PyMuPDF4LLM, Marker, Docling i Surya. torch z CUDA "
            f"({_code('cu130')}) wchodzi automatycznie."
        ),
    )
    tools = _section(
        "Narzędzia systemowe",
        _ul(
            "<b>Tesseract</b> (+ język <b>pol</b>) — OCR skanów w Marker/Docling",
            f"<b>Poppler</b> ({_code('pdftoppm')}) — PDF → obraz",
        )
        + _p("Oba muszą być w PATH.")
        + _p(
            "<b>Windows:</b> Tesseract — instalator UB Mannheim (zaznacz Polish); Poppler — "
            "rozpakuj ZIP i dodaj " + _code("C:\\poppler\\Library\\bin") + " do PATH."
        )
        + _pre("# WSL / Ubuntu:\nsudo apt install tesseract-ocr tesseract-ocr-pol poppler-utils"),
    )
    gpu = _section(
        "GPU / CUDA",
        _p(
            f"torch instaluje się jako {_code('+cu130')} (CUDA 13) przy {_code('uv sync')} "
            "(Windows i WSL) — jeden, testowany toolkit. Do pracy na GPU potrzebny jest "
            "<b>aktualny sterownik NVIDIA wspierający CUDA 13</b>. Bez aktualnego sterownika "
            f"aplikacja działa na CPU (nie schodzimy z {_code('+cu130')})."
        )
        + _p(
            "<b>VRAM decyduje, które silniki ruszą:</b> skromna karta (np. 8 GB) → "
            "Marker / Surya / Docling na GPU, ale bez ciężkich serwowanych VLM-ów; "
            "pełna Faza 2 (z olmOCR) dopiero przy ~24 GB."
        )
        + _p(
            f"Sprawdź {_code('pdf2md doctor')} — pokaże, co Twój konkretny sprzęt uciągnie "
            "(✅ / ⚠️ / ❌ per silnik) i czy sterownik jest wystarczająco nowy (karta wykryta, "
            "ale za stary sterownik → komunikat o aktualizacji). Pełna tabela sprzętowa: "
            "<b>INSTALL.md</b> sekcja 12."
        )
        + _p(f"Jeśli CUDA jest niedostępna albo torch wszedł jako {_code('+cpu')}:")
        + _pre(
            "uv lock --upgrade-package torch --upgrade-package torchvision\n"
            "uv sync --extra engines-core"
        ),
    )
    services = _section(
        "Silniki-usługi (zaawansowane)",
        _p(
            "MinerU, PaddleOCR-VL i olmOCR (zaparkowany) są izolowane w osobnych środowiskach i "
            "działają <b>tylko w WSL</b> — vLLM nie wspiera natywnego Windows. Szczegóły w "
            "INSTALL.md."
        ),
    )
    footer = _p(
        "Pełna instrukcja krok po kroku: <b>INSTALL.md</b> w repozytorium (przycisk "
        "„Strona projektu” w oknie <b>O programie</b>)."
    )
    return _section("Instalacja silników", core + tools + gpu + services + footer)


def _llm_tab() -> str:
    intro = _p(
        "Po konwersji opcjonalny model LLM poprawia i porządkuje wygenerowany Markdown "
        "(operacja tekst→tekst — obraz strony NIE jest podawany do modelu)."
    )
    modes = _section(
        "Tryby chunkowania",
        _ul(
            f"{_code('whole_document')} — cały dokument naraz",
            f"{_code('by_page')} — strona po stronie",
            f"{_code('by_chunk')} — fragmenty tekstu",
            f"{_code('by_heading')} — sekcje wg nagłówków",
        ),
    )
    providers = _section(
        "Dostawcy",
        _ul(
            "Ollama — lokalny, domyślny (bez kluczy, bez wysyłania danych)",
            "Claude (Anthropic), OpenAI, Gemini — chmurowe (wymagają klucza API)",
        ),
    )
    keys = _p(
        "Klucze API ustawisz w oknie <b>Ustawienia</b> albo w pliku "
        f"{_code('~/.config/pdf2md/config.toml')}."
    )
    return _section("Post-processing LLM", intro) + modes + providers + keys


def _profiles_tab() -> str:
    table = _table(
        ["Profil", "Co robi / kiedy"],
        [
            ["fast", "Niższy DPI, lekki tryb — szybki podgląd, gdy jakość mniej istotna"],
            ["balanced", "Kompromis jakość/czas — domyślny, dobry do większości skanów"],
            [
                "premium",
                "Najwyższy DPI + pełny tryb (VLM-OCR, korekta LLM, raport) — książki, materiał docelowy",
            ],
        ],
    )
    intro = _p(
        "Profile sterują skanowaniem książek (silnik <b>Scan Pipeline</b>): DPI, korekta LLM, "
        "wyjścia. Wbudowane: <b>fast</b> / <b>balanced</b> / <b>premium</b> (domyślny "
        "<b>balanced</b>)."
    )
    editor = _p(
        "Własny profil zapiszesz przez <b>Edytuj profil</b> (DPI, wyjścia EPUB / raport jakości); "
        f"trafia do {_code('~/.config/pdf2md/profiles/')}."
    )
    return _section("Profile skanowania", intro + table + editor)


def _cli_tab() -> str:
    commands = _pre(
        "pdf2md convert dokument.pdf --engine pymupdf4llm\n"
        'pdf2md convert "pdfy/*.pdf" --engine docling --output-dir ./markdown\n'
        "pdf2md convert dokument.pdf --engine marker --llm ollama --llm-mode by_heading\n"
        "pdf2md convert dokument.pdf --dry-run        # plan bez konwersji\n"
        "pdf2md scan skan.pdf --profile premium       # pipeline skanu książki\n"
        "\n"
        "pdf2md list-engines          # silniki + wymóg GPU\n"
        "pdf2md list-llm              # dostawcy LLM\n"
        "pdf2md list-profiles         # profile skanowania\n"
        "pdf2md doctor                # diagnostyka środowiska\n"
        "\n"
        "pdf2md config show                  # pokaż konfigurację\n"
        "pdf2md config set KLUCZ WARTOŚĆ     # ustaw wartość\n"
        "pdf2md config edit                  # otwórz config.toml w edytorze"
    )
    intro = _p("Te same konwersje co w GUI wykonasz z linii poleceń:")
    return _section("CLI", intro + commands)


def _models_tab() -> str:
    intro = _p(
        "Post-processing LLM działa lokalnie przez <b>Ollama</b> — bez kluczy i bez wysyłania "
        "danych. Rekomendowany model korekty: " + _code("qwen3:14b") + "."
    )
    vram = _p(
        "<b>VRAM:</b> model 14B mieści się swobodnie na 24 GB. Większe modele (np. 27B/30B) dają "
        "lepszą jakość korekty, jeśli starcza pamięci. Na mniejszej karcie wybierz mniejszy model "
        "(np. 7B/8B) — inaczej Ollama zejdzie na CPU i korekta będzie wolna."
    )
    howto = _p(
        "Model korekty wskażesz w <b>Ustawieniach</b> albo komendą "
        + _code("pdf2md config set ollama_model qwen3:14b")
        + "."
    )
    vision = _p(
        "<b>Wskazówka:</b> do obróbki tekstu lepszy jest <b>zwykły</b> "
        + _code("qwen3:14b")
        + f" niż wariant vision ({_code('qwen3-vl')}) — na etapie korekty (tekst→tekst) zdolności "
        "wizyjne nie są używane, a VL oddaje część parametrów na vision. VL ma sens osobno "
        "(np. opis wyciąganych obrazów), nie jako model korekty."
    )
    installed = _p(
        "<b>Modele dostępne w Twoim środowisku</b> (i status serwera Ollama) zobaczysz w "
        + _code("pdf2md doctor")
        + " — listy modeli nie wpisujemy tu na sztywno, bo zmienia się z instalacją."
    )
    keys = _p(
        "Klucze API dostawców chmurowych (Anthropic / OpenAI / Gemini) sprawdzisz w "
        + _code("pdf2md doctor")
        + " (sekcja Klucze API), a ustawisz w <b>Ustawieniach</b> lub przez "
        + _code("pdf2md config set")
        + "."
    )
    return _section("Model AI / Ollama", intro + vram + howto + vision + installed + keys)
