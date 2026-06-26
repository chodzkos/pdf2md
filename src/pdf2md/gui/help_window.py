"""Okno pomocy offline pdf2md — szkielet (treść w kolejnym kroku).

Zakładki są **wstrzykiwane w pętli** z :meth:`HelpWindow._tabs` (lista
``(tytuł, html)``), nie sztywnymi metodami ``_make_X_tab`` — pod przyszłą
ekstrakcję wspólnego okna pomocy do gui-kit.

Kolory w HTML idą WYŁĄCZNIE przez funkcję ``palette(...)`` Qt — tła treści na
``palette(alternate-base)`` + tekst ``palette(text)`` (para trzymająca kontrast
w obu motywach; ``mid``/``dark``/``shadow`` to role ramek/cieni, nie powierzchni).
Qt podstawia kolor z palety ``QTextBrowser``, więc działa w obu motywach bez
re-renderu. Zero zaszytych hexów.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QScrollArea,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from pdf2md.gui.theming import follow_app_titlebar


def _scroll(widget: QWidget) -> QScrollArea:
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setWidget(widget)
    return area


def _section(title: str, body: str) -> str:
    return f"<h3>{title}</h3>{body}"


def _p(text: str) -> str:
    return f"<p>{text}</p>"


def _ul(*items: str) -> str:
    rows = "".join(f"<li>{i}</li>" for i in items)
    return f"<ul>{rows}</ul>"


def _table(headers: list[str], rows: list[list[str]]) -> str:
    th = "".join(f"<th style='padding:4px 8px;text-align:left'>{h}</th>" for h in headers)
    trs = ""
    for row in rows:
        tds = "".join(f"<td style='padding:4px 8px'>{c}</td>" for c in row)
        trs += f"<tr>{tds}</tr>"
    return (
        "<table border='1' cellspacing='0' cellpadding='0' "
        "style='border-collapse:collapse;margin:4px 0'>"
        f"<tr style='background:palette(alternate-base);color:palette(text)'>{th}</tr>{trs}</table>"
    )


def _code(text: str) -> str:
    return (
        "<code style='background:palette(alternate-base);color:palette(text);"
        f"padding:1px 4px;border-radius:2px'>{text}</code>"
    )


def _pre(text: str) -> str:
    return (
        f"<pre style='background:palette(alternate-base);color:palette(text);"
        f"padding:8px;border-radius:4px;white-space:pre-wrap'>{text}</pre>"
    )


class HelpWindow(QDialog):
    """Okno pomocy z zakładkami (szkielet — jedna placeholder-zakładka)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Pomoc — pdf2md")
        # Tylko rozmiar startowy — geometrii NIE persystujemy (żadne okno pdf2md
        # tego nie robi; dodatkowe pole w typowanym Settings = narzut bez wartości).
        self.resize(720, 560)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        tabs = QTabWidget()
        for title, html in self._tabs():
            browser = QTextBrowser()
            browser.setHtml(html)
            tabs.addTab(_scroll(browser), title)
        layout.addWidget(tabs)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Ciemna belka tytułu podążająca za motywem aplikacji (jak settings_dialog).
        self._titlebar = follow_app_titlebar(self)

    def _tabs(self) -> list[tuple[str, str]]:
        """Zakładki pomocy jako ``(tytuł, html)`` — składane helperami HTML."""
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
        ["Silnik", "Typ dokumentu", "OCR"],
        [
            [
                "PyMuPDF4LLM",
                "Natywne PDF z warstwą tekstową (raporty, instrukcje) — najszybszy",
                "Nie",
            ],
            ["Marker", "Skany, dokumenty mieszane, trudniejszy layout; opcjonalny LLM", "Tak"],
            ["Docling", "Tabele, dokumenty biznesowe, struktura, RAG", "Tak"],
            ["MinerU", "Artykuły naukowe, CJK, wielokolumnowe układy (izolowany)", "Tak"],
            ["Surya", "Layout + OCR + reading order, GPU, in-process", "Tak"],
            ["PaddleOCR-VL", "Wielojęzyczny VLM-OCR (serwer vLLM, izolowany)", "Tak"],
        ],
    )
    when = _p(
        "<b>Kiedy który:</b> natywny tekst → PyMuPDF4LLM; skan / mieszane → Marker; "
        "tabele / biznes → Docling; nauka / wielokolumnowe → MinerU; kontrola layoutu → Surya; "
        "wielojęzyczny VLM → PaddleOCR-VL."
    )
    parked = _p(
        "<b>olmOCR</b> (VLM 7B do skanów) jest <b>zaparkowany</b> — zajmuje ~całą kartę i jest "
        "anglocentryczny. Dla skanów po polsku użyj <b>PaddleOCR-VL</b> lub <b>Surya</b>."
    )
    return _section("Silniki konwersji", table + when + parked)


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
            f"torch instaluje się jako {_code('+cu130')} przy {_code('uv sync')} (Windows i WSL). "
            f"Sprawdź sekcję GPU w {_code('pdf2md doctor')}."
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
            "działają <b>tylko w WSL</b> — vLLM nie wspiera natywnego Windows. Szczegóły w INSTALL.md."
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
        "lepszą jakość korekty, jeśli starcza pamięci."
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
    return _section("Model AI / Ollama", intro + vram + howto + vision)
