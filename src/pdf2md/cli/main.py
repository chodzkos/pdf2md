"""Interfejs wiersza poleceń pdf2md."""

from __future__ import annotations

import glob
import importlib
import importlib.metadata
import os
import platform
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from pdf2md import __version__
from pdf2md.core import config as config_module
from pdf2md.core import history as conversion_history
from pdf2md.core.config import Settings, get_settings, save_settings
from pdf2md.core.converter import ConversionError, Converter
from pdf2md.core.image_extraction import (
    append_image_references,
    extract_pdf_images,
    image_output_dir,
)
from pdf2md.core.input_types import is_image_input, is_supported_input
from pdf2md.core.registry import engine_registry, llm_registry
from pdf2md.detection.dependencies import check_all
from pdf2md.detection.hardware import HardwareInfo, detect_hardware, is_compute_cap_too_old
from pdf2md.detection.pdf_type import detect_pdf_type
from pdf2md.engines.base import ConversionEngine
from pdf2md.exporters import EPUB_BACKENDS, MarkdownExporter, build_epub_exporter
from pdf2md.llm.base import LLMProvider
from pdf2md.utils.logging import setup_logging

if TYPE_CHECKING:
    from pdf2md.scan.profiles import Profile

console = Console()

LLM_CHOICES = ("none", "ollama", "claude", "openai", "gemini")
LLM_MODES = ("none", "whole_document", "by_page", "by_chunk", "by_heading")

ENGINE_CATALOG: tuple[dict[str, object], ...] = (
    {
        "key": "pymupdf4llm",
        "name": "PyMuPDF4LLM",
        "package": "pymupdf4llm",
        "scope": "Core",
        "ocr": False,
        "llm": False,
        "license": "AGPL/kom.",
        "hint": "uv pip install pymupdf4llm",
        "min_vram_gb": 0,  # CPU — zawsze wykonalny
        "description": "Szybki ekstraktor tekstu z natywnych PDF-ów.",
    },
    {
        "key": "marker",
        "name": "Marker",
        "package": "marker-pdf",
        "scope": "Core",
        "ocr": True,
        "llm": True,
        "license": "GPL",
        "hint": "uv pip install marker-pdf",
        "min_vram_gb": 4,  # przybliżone; działa też na CPU (wolno)
        "description": "Uniwersalny konwerter z OCR i trybem LLM.",
    },
    {
        "key": "docling",
        "name": "Docling",
        "package": "docling",
        "scope": "Core",
        "ocr": True,
        "llm": False,
        "license": "MIT",
        "hint": "uv pip install docling",
        "min_vram_gb": 2,  # przybliżone; działa też na CPU (wolno)
        "description": "Enterprise parser dokumentów, tabele, RAG.",
    },
    {
        "key": "mineru",
        "name": "MinerU",
        "package": "mineru",
        "scope": "Opc.",
        "ocr": True,
        "llm": False,
        "linux_only": True,  # vLLM — tylko Linux/WSL
        "license": "AGPL",
        "hint": "uv tool install mineru --with mineru[all]",
        "min_vram_gb": 6,  # backend pipeline; backend vlm ~12 GB (cięższy)
        "description": "Dokumenty naukowe, layout, CJK. Backend pipeline (lekki) lub vlm (~12 GB).",
    },
    {
        "key": "olmocr",
        "name": "olmOCR",
        "package": "olmocr",
        "scope": "Opc.",
        "ocr": True,
        "llm": False,
        "gpu": True,
        "linux_only": True,  # vLLM — tylko Linux/WSL
        "license": "Apache-2.0",
        "hint": "pip install olmocr (osobne środowisko + CUDA)",
        "min_vram_gb": 24,  # zmierzone: 9.5 GB model + 9.3 GB KV-cache + grafy CUDA
        "description": "VLM 7B do skanów: czysty Markdown, równania, tabele.",
    },
    {
        "key": "paddleocr-vl",
        "name": "PaddleOCR-VL",
        "package": "paddleocr",
        "scope": "Opc.",
        "ocr": True,
        "llm": False,
        "gpu": True,
        "linux_only": True,  # vLLM — tylko Linux/WSL
        "license": "Apache-2.0",
        "hint": (
            "Uruchom serwer: VLLM_USE_FLASHINFER_SAMPLER=0 vllm serve "
            "PaddlePaddle/PaddleOCR-VL-1.6 --trust-remote-code --no-enable-prefix-caching "
            "(zob. INSTALL.md 7.3)"
        ),
        "min_vram_gb": 12,  # przybliżone (serwowany VLM)
        "description": "Serwer VLM (OpenAI-compatible): wielojęzyczny parser dokumentów.",
    },
    {
        "key": "surya",
        "name": "Surya",
        "package": "surya-ocr",
        "scope": "Opc.",
        "ocr": True,
        "llm": False,
        "gpu": True,
        "license": "GPL/komercyjna",
        "hint": "uv pip install surya-ocr",
        "min_vram_gb": 6,  # przybliżone
        "description": "Layout + OCR + reading order, kontrola/fallback.",
    },
    {
        "key": "scan-pipeline",
        "name": "Scan Pipeline (premium)",
        "package": "surya-ocr",
        "scope": "Opc.",
        "ocr": True,
        "llm": True,
        "gpu": True,
        "license": "różne (zależnie od silnika OCR)",
        "hint": "uv pip install surya-ocr ebooklib (+ GPU); zob. INSTALL.md",
        "min_vram_gb": 6,  # przybliżone (domyślnie Surya)
        "description": "Skan książki → VLM-OCR, korekta LLM, składanie, EPUB/Markdown.",
    },
)


def _is_windows_platform() -> bool:
    return sys.platform == "win32"


def _reconfigure_windows_stdio() -> None:
    """Force UTF-8 stdio on Windows so Rich can print emoji under redirected output."""
    if not _is_windows_platform():
        return

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")


def _startup(verbose: bool = False) -> Settings:
    setup_logging(verbose=verbose)
    settings = get_settings()
    importlib.import_module("pdf2md.engines")
    importlib.import_module("pdf2md.llm")
    return settings


def _normalize_name(name: str) -> str:
    return name.lower().replace(" ", "").replace("-", "").replace("_", "")


def _find_engine(name: str) -> ConversionEngine | None:
    wanted = _normalize_name(name)
    for engine in engine_registry.get_all():
        if _normalize_name(engine.name) == wanted:
            return engine
    for engine in engine_registry.get_all():
        if _normalize_name(engine.name).startswith(wanted):
            return engine
    return None


def _provider_key(provider: LLMProvider) -> str:
    name = provider.name.lower()
    if "ollama" in name:
        return "ollama"
    if "claude" in name or "anthropic" in name:
        return "claude"
    if "openai" in name or "gpt" in name:
        return "openai"
    if "gemini" in name or "google" in name:
        return "gemini"
    return _normalize_name(provider.name)


def _find_provider(name: str) -> LLMProvider | None:
    if name == "none":
        return None
    for provider in llm_registry.get_all():
        if _provider_key(provider) == name:
            return provider
    return None


def _package_installed(package_name: str) -> bool:
    try:
        importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return False
    return True


def _record_history_safely(
    *,
    input_path: str | Path,
    engine: str,
    llm_provider: LLMProvider | None,
    llm_mode: str,
    output_path: str | Path | None,
    status: conversion_history.HistoryStatus,
    duration_s: float,
    error_msg: str | None = None,
) -> None:
    conversion_history.record_safely(
        input_path=input_path,
        engine=engine,
        llm_provider=llm_provider.name if llm_provider is not None else "none",
        llm_mode=llm_mode,
        output_path=output_path,
        status=status,
        duration_s=duration_s,
        error_msg=error_msg,
    )


def _catalog_entry_for_engine(engine_name: str) -> dict[str, object] | None:
    normalized = _normalize_name(engine_name)
    for item in ENGINE_CATALOG:
        if _normalize_name(str(item["name"])) == normalized or str(item["key"]) == normalized:
            return item
    return None


def _engine_available(item: dict[str, object]) -> bool:
    engine = _find_engine(str(item["key"]))
    if engine is not None:
        return bool(engine.is_available())
    return _package_installed(str(item["package"]))


def _expand_files(patterns: tuple[str, ...]) -> list[Path]:
    files: list[Path] = []
    seen: set[Path] = set()
    for pattern in patterns:
        matches = sorted(glob.glob(pattern)) if glob.has_magic(pattern) else [pattern]
        for match in matches:
            path = Path(match)
            if path not in seen:
                seen.add(path)
                files.append(path)
    return files


def _resolve_output_paths(
    files: list[Path],
    output: str | None,
    output_dir: str | None,
) -> dict[Path, Path]:
    if output and output_dir:
        raise click.ClickException("Użyj --output albo --output-dir, nie obu naraz.")

    if output_dir:
        out_dir = Path(output_dir)
        return {path: out_dir / f"{path.stem}.md" for path in files}

    if output:
        out = Path(output)
        if len(files) == 1 and out.suffix.lower() in {".md", ".epub"}:
            return {files[0]: out}
        return {path: out / f"{path.stem}.md" for path in files}

    return {path: path.with_suffix(".md") for path in files}


def _select_engine(engine_name: str) -> ConversionEngine:
    engine = _find_engine(engine_name)
    if engine is None:
        available = ", ".join(engine.name for engine in engine_registry.get_all()) or "brak"
        raise click.ClickException(
            f"Nieznany silnik: {engine_name}. Zarejestrowane silniki: {available}"
        )
    return engine


def _load_conversion_profile(profile_name: str) -> Profile:
    from pdf2md.scan.profiles import ProfileError, load_profile

    try:
        return load_profile(profile_name)
    except ProfileError as exc:
        raise click.ClickException(str(exc)) from exc


def _profile_value(profile: Profile | None, field_name: str) -> str | None:
    if profile is None:
        return None
    value = getattr(profile.conversion, field_name)
    return value if value not in (None, "") else None


def _validate_input_formats(paths: list[Path]) -> None:
    for path in paths:
        if not is_supported_input(path):
            raise click.ClickException(
                f"Nieobsługiwany format wejściowy: {path}. Obsługiwane: PDF, JPG, PNG, TIFF."
            )


def _image_page_count(path: Path) -> int:
    from PIL import Image, ImageSequence

    with Image.open(path) as image:
        return sum(1 for _ in ImageSequence.Iterator(image))


def _select_llm(llm_name: str, llm_model: str | None, settings: Settings) -> LLMProvider | None:
    provider = _find_provider(llm_name)
    if provider is None:
        if llm_name == "none":
            return None
        raise click.ClickException(f"Nieznany dostawca LLM: {llm_name}")

    if llm_model:
        model_field = {
            "ollama": "ollama_model",
            "claude": "anthropic_model",
            "openai": "openai_model",
            "gemini": "gemini_model",
        }[llm_name]
        setattr(settings, model_field, llm_model)

    if not provider.is_available():
        raise click.ClickException(f"Dostawca LLM nie jest gotowy: {provider.name}")
    return provider


def _mask_secret(secret: str) -> str:
    if not secret:
        return "brak"
    if len(secret) <= 8:
        return "***"
    return f"{secret[:4]}...{secret[-4:]}"


def _coerce_config_value(field_name: str, value: str, settings: Settings) -> object:
    current = getattr(settings, field_name)
    if isinstance(current, bool):
        lowered = value.lower()
        if lowered in {"1", "true", "yes", "tak", "on"}:
            return True
        if lowered in {"0", "false", "no", "nie", "off"}:
            return False
        raise click.ClickException(f"Wartość dla {field_name} musi być bool: true/false")
    if isinstance(current, int):
        try:
            return int(value)
        except ValueError as exc:
            raise click.ClickException(
                f"Wartość dla {field_name} musi być liczbą całkowitą"
            ) from exc
    return value


def _normalize_config_key(key: str) -> str:
    aliases = {
        "llm.enabled": "llm_enabled",
        "llm.provider": "llm_provider",
        "llm.mode": "llm_mode",
        "conversion.default_engine": "default_engine",
        "conversion.default_output_dir": "default_output_dir",
        "conversion.default_language": "default_language",
        "api_keys.anthropic_api_key": "anthropic_api_key",
        "api_keys.openai_api_key": "openai_api_key",
        "api_keys.gemini_api_key": "gemini_api_key",
        "marker.marker_device": "marker_device",
        "marker.marker_workers": "marker_workers",
        "marker.marker_max_pages": "marker_max_pages",
        "docling.docling_device": "docling_device",
    }
    normalized = key.strip().replace("-", "_")
    if normalized in aliases:
        return aliases[normalized]
    if "." in normalized:
        return normalized.split(".")[-1]
    return normalized


# Wspólny opis minimum karty — reużywany w stanach no_gpu i arch_too_old (spójność komunikatu).
MIN_CARD = (
    "Silniki wymagające CUDA potrzebują karty NVIDIA Turing (compute 7.5) lub nowszej: "
    "GTX 16-series (GTX 1650/1660), RTX 20-series (RTX 2060+), lub dowolna RTX 30/40/50-series. "
    "Starsze (GTX 10-series Pascal i wcześniejsze) nie są obsługiwane przez build cu130."
)


def _hardware_summary(hw: HardwareInfo, cuda_version: str) -> str:
    """Buduje wykonalny, gradacyjny opis sprzętu do sekcji GPU w doctorze (komunikat per stan)."""
    name = hw.name or "GPU"
    vram = f"{hw.vram_gb:.0f} GB" if hw.vram_gb is not None else "nieznany VRAM"
    if hw.state == "ok":
        version = cuda_version or "?"
        vram_ok = f"{hw.vram_gb:.0f}" if hw.vram_gb is not None else "?"
        return f"✅ CUDA {version} · {hw.name} · {vram_ok} GB · {hw.arch}"
    if hw.state == "arch_too_old":
        cap = f"compute {hw.compute_cap}" if hw.compute_cap else "architektura sprzed Turinga"
        return (
            f"⚠️ Karta {name} ({vram}, {cap}) jest ZBYT STARA na tryb GPU — build cu130 wymaga "
            "≥ sm_75 (Turing). GPU niedostępne, działa tylko CPU. Aktualizacja sterownika NIE "
            f"pomoże (architektura za stara). {MIN_CARD} (INSTALL.md §12.)"
        )
    if hw.state == "driver_too_old":
        return (
            f"⚠️ Karta {name} ({vram}) wykryta, ale sterownik wspiera tylko CUDA {hw.driver_cuda}. "
            "Zaktualizuj sterownik NVIDIA do wersji z CUDA 13 "
            "(https://www.nvidia.com/Download/index.aspx). Bez aktualizacji — tryb CPU."
        )
    if hw.state == "no_torch":
        msg = (
            "ℹ️ PyTorch nie jest zainstalowany w tym środowisku — uruchom z venv pdf2md albo "
            "zainstaluj zależności: `uv sync --extra engines-core`. (Do tego czasu tryb CPU.)"
        )
        # Gdy znamy compute_cap karty (z nvidia-smi) i jest za stara — ostrzeż, by nie tracić
        # czasu na instalację torcha „pod GPU"; silniki CUDA i tak nie ruszą na tej architekturze.
        if is_compute_cap_too_old(hw.compute_cap):
            msg += (
                f" Uwaga: wykryta karta ({name}, compute {hw.compute_cap}) i tak jest zbyt stara "
                "na GPU — silniki CUDA nie ruszą nawet po instalacji torcha; nadają się tylko "
                "silniki CPU."
            )
        return msg
    if hw.state == "no_gpu":
        return (
            "ℹ️ Brak karty NVIDIA — tryb CPU. Silniki CPU (PyMuPDF4LLM, Marker, Docling) działają; "
            f"silniki wymagające CUDA są niedostępne. {MIN_CARD}"
        )
    return f"⚠️ Karta {name} wykryta, ale CUDA niedostępna dla torcha (przyczyna nieustalona). Tryb CPU."


def _min_vram_gb(item: dict[str, object]) -> float:
    """Orientacyjny próg VRAM silnika w GiB (0 = silnik działa na CPU)."""
    value = item.get("min_vram_gb", 0)
    return float(value) if isinstance(value, (int, float)) else 0.0


def _engine_feasibility(item: dict[str, object], hw: HardwareInfo) -> str:
    """Wykonalność silnika względem wykrytego sprzętu (✅ / ⚠️ / ❌).

    Progi VRAM (poza olmOCR) są SZACUNKAMI — stąd pas „⚠️ na granicy" zamiast twardego „nie"
    tam, gdzie da się docisnąć dostrajaniem. Wymiar Linux/WSL łączy się z VRAM-em: silnik na
    vLLM pod Windows jest niewykonalny niezależnie od pamięci karty.
    """
    # Wymiar systemu: vLLM-owe silniki pod natywnym Windows nie ruszą, choćby VRAM starczał.
    if item.get("linux_only") and platform.system() != "Linux":
        return "❌ wymaga Linux/WSL"

    min_vram = _min_vram_gb(item)
    requires_gpu = bool(item.get("gpu"))

    if min_vram == 0:
        return "✅ CPU"

    if hw.state == "ok" and hw.vram_gb is not None:
        vram = hw.vram_gb
        if vram >= min_vram:
            return "✅ zmieści się"
        if vram >= min_vram * 0.7:
            return "⚠️ na granicy (dostraja --gpu_memory_utilization / --max_model_len)"
        return f"❌ za mało VRAM (~{min_vram:.0f} GB, masz {vram:.0f})"

    # Brak działającego GPU — podpowiedź MUSI pasować do przyczyny (ta sama co „Ocena sprzętu").
    if requires_gpu:
        reason = {
            "arch_too_old": "karta za stara na GPU",
            "driver_too_old": "zaktualizuj sterownik",
            "no_torch": "zainstaluj torch / zły venv",
            "no_gpu": "brak karty",
        }.get(hw.state)
        if reason is not None:
            return f"❌ wymaga CUDA ({reason})"
        return "❌ wymaga działającego CUDA"
    # Silnik z fallbackiem CPU (Marker/Docling/MinerU-pipeline) — działa, tylko wolno.
    return "✅ CPU (wolno)"


def _env_flag(name: str) -> bool:
    """Czyta flagę bool ze zmiennej środowiskowej (1/true/yes/on = włączona)."""
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _plain_console() -> Console:
    """Konsola pod stabilne snapshoty: bez ANSI/kolorów i ze stałą szerokością.

    Treść (statusy, wersje, emoji) bez zmian — deterministyczna jest tylko prezentacja:
    brak kolorów eliminuje sekwencje ANSI, a stała szerokość usuwa zależność od terminala.
    """
    return Console(no_color=True, highlight=False, force_terminal=False, width=100)


def _print_engine_table(hw: HardwareInfo | None = None, out: Console | None = None) -> None:
    out = out or console
    if hw is None:
        hw = detect_hardware()
    table = Table(title="Silniki konwersji")
    table.add_column("Nazwa")
    table.add_column("Status")
    table.add_column("Wykonalność")
    table.add_column("Core/Opc.")
    table.add_column("OCR")
    table.add_column("GPU")
    table.add_column("LLM")
    table.add_column("Licencja")
    table.add_column("Opis")

    for item in ENGINE_CATALOG:
        available = _engine_available(item)
        description = str(item["description"])
        if available:
            status = "✅ Dostępny"
        elif item.get("linux_only") and platform.system() != "Linux":
            # Silnik na vLLM — pod natywnym Windows nie ruszy; hint instalacji mylił.
            status = "❌ Niedostępny (wymaga Linux/WSL)"
            description = (
                f"{description}\nUWAGA: silnik opiera się na vLLM — działa tylko pod "
                "Linux/WSL, nie pod natywnym Windows."
            )
        else:
            status = "❌ Niezainstalowany"
            description = f"{description}\nHint: {item['hint']}"
        table.add_row(
            str(item["name"]),
            status,
            _engine_feasibility(item, hw),
            str(item["scope"]),
            "tak" if item["ocr"] else "nie",
            "wymagane" if item.get("gpu") else "nie",
            "tak" if item["llm"] else "nie",
            str(item["license"]),
            description,
        )
    out.print(table)


def _llm_status(provider: LLMProvider, settings: Settings) -> str:
    key = _provider_key(provider)
    api_key = {
        "claude": settings.anthropic_api_key,
        "openai": settings.openai_api_key,
        "gemini": settings.gemini_api_key,
    }.get(key, "")
    if provider.requires_api_key and not api_key:
        return "⚠️ Brak klucza API"
    return "✅ Gotowy" if provider.is_available() else "❌ Niedostępny"


def _print_llm_table(settings: Settings) -> None:
    table = Table(title="Dostawcy LLM")
    table.add_column("Nazwa")
    table.add_column("Status")
    table.add_column("Model")
    table.add_column("API key")
    table.add_column("Opis")

    model_by_key = {
        "ollama": settings.ollama_model,
        "claude": settings.anthropic_model,
        "openai": settings.openai_model,
        "gemini": settings.gemini_model,
    }
    for provider in llm_registry.get_all():
        key = _provider_key(provider)
        model = model_by_key.get(key) or provider.default_model
        api_key = "wymagany" if provider.requires_api_key else "nie"
        table.add_row(
            provider.name, _llm_status(provider, settings), model, api_key, provider.description
        )
    console.print(table)


def _print_dry_run(
    files: list[Path],
    output_paths: dict[Path, Path],
    engine: ConversionEngine,
    llm_name: str,
) -> None:
    deps = check_all()
    for path in files:
        table = Table(title=f"Plan konwersji: {path}")
        table.add_column("Pole")
        table.add_column("Wartość")
        if is_image_input(path):
            table.add_row("Typ wejścia", "obraz")
            table.add_row("Strony/klatki", str(_image_page_count(path)))
        else:
            pdf_info = detect_pdf_type(str(path))
            table.add_row("Typ PDF", str(pdf_info["type"]))
            table.add_row("Strony", str(pdf_info["pages"]))
        table.add_row("Silnik", engine.name)
        table.add_row("Silnik dostępny", "tak" if engine.is_available() else "nie")
        table.add_row("LLM", llm_name)
        table.add_row("Wyjście", str(output_paths[path]))
        table.add_row(
            "Tesseract",
            "tak" if deps["tesseract"]["available"] else "nie",
        )
        table.add_row("Pandoc", "tak" if deps["pandoc"] else "nie")
        table.add_row("Calibre", "tak" if deps["calibre"] else "nie")
        table.add_row("Ollama", "tak" if deps["ollama"]["available"] else "nie")
        console.print(table)


def _export_result(markdown: str, output_path: Path, epub_backend: str = "pandoc") -> Path:
    if output_path.suffix.lower() == ".epub":
        # Obrazy inline leżą obok wyniku — wskaż katalog źródłowy, żeby temp .md
        # nie trafił do /tmp i względne referencje ![](obraz.png) się rozwiązały.
        return build_epub_exporter(epub_backend).export(
            markdown, output_path, source_dir=output_path.parent
        )
    return MarkdownExporter().export(markdown, output_path)


def _detect_os_label() -> str:
    system = platform.system()
    if system == "Linux":
        try:
            version = Path("/proc/version").read_text(encoding="utf-8").lower()
            if "microsoft" in version or "wsl" in version:
                return "WSL/Linux"
        except OSError:
            pass
    return system


@click.group()
@click.version_option(__version__, prog_name="pdf2md")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Konwerter PDF do Markdown z obsługą wielu silników i modeli LLM."""
    _reconfigure_windows_stdio()
    ctx.ensure_object(dict)
    ctx.obj["settings"] = _startup(verbose=False)


@cli.command()
@click.argument("files", nargs=-1, required=True)
@click.option("--engine", "-e", help="Silnik konwersji, np. pymupdf4llm albo marker.")
@click.option("--profile", "-p", "profile_name", help="Profil/preset konwersji YAML.")
@click.option("--output", "-o", help="Plik wyjściowy .md/.epub albo katalog dla wielu plików.")
@click.option("--output-dir", help="Katalog dla wyników batch.")
@click.option(
    "--llm",
    "llm_name",
    type=click.Choice(LLM_CHOICES),
    default=None,
    help="Dostawca LLM (nadpisuje profil; domyślnie none).",
)
@click.option("--llm-model", help="Model LLM nadpisujący config tylko dla tego uruchomienia.")
@click.option(
    "--llm-mode",
    type=click.Choice(LLM_MODES),
    default=None,
    help="Tryb post-processingu LLM (nadpisuje profil; domyślnie none).",
)
@click.option("--lang", default=None, help="Język OCR (nadpisuje profil; domyślnie pol+eng).")
@click.option(
    "--epub-backend",
    type=click.Choice(EPUB_BACKENDS),
    default=None,
    help="Backend eksportu EPUB (nadpisuje config); fallback na Pandoc gdy Calibre brak.",
)
@click.option(
    "--extract-images",
    is_flag=True,
    help="Wyciągnij obrazy z PDF do <output>_images i dodaj referencje Markdown.",
)
@click.option(
    "--image-min-size",
    type=click.IntRange(min=1),
    default=100,
    show_default=True,
    help="Minimalna szerokość i wysokość obrazu do ekstrakcji, w pikselach.",
)
@click.option("--dry-run", is_flag=True, help="Pokaż plan bez konwersji.")
@click.option("--verbose", "-v", is_flag=True, help="Szczegółowy output.")
@click.pass_context
def convert(
    ctx: click.Context,
    files: tuple[str, ...],
    engine: str | None,
    profile_name: str | None,
    output: str | None,
    output_dir: str | None,
    llm_name: str | None,
    llm_model: str | None,
    llm_mode: str | None,
    lang: str | None,
    epub_backend: str | None,
    extract_images: bool,
    image_min_size: int,
    dry_run: bool,
    verbose: bool,
) -> None:
    """Konwertuje jeden lub wiele plików PDF do Markdown."""
    if verbose:
        setup_logging(verbose=True)
    settings: Settings = ctx.obj["settings"]
    conversion_profile = _load_conversion_profile(profile_name) if profile_name else None
    engine_name = engine or _profile_value(conversion_profile, "engine") or settings.default_engine
    lang = lang or _profile_value(conversion_profile, "lang") or "pol+eng"
    llm_name = llm_name or _profile_value(conversion_profile, "llm") or "none"
    llm_model = llm_model or _profile_value(conversion_profile, "llm_model")
    llm_mode = llm_mode or _profile_value(conversion_profile, "llm_mode") or "none"
    selected_epub_backend = epub_backend or settings.epub_backend
    selected_engine = _select_engine(engine_name)
    input_files = _expand_files(files)
    if not input_files:
        raise click.ClickException("Nie znaleziono plików wejściowych.")

    missing = [str(path) for path in input_files if not path.exists()]
    if missing:
        raise click.ClickException(f"Plik nie istnieje: {missing[0]}")
    _validate_input_formats(input_files)

    output_paths = _resolve_output_paths(input_files, output, output_dir)
    if dry_run:
        _print_dry_run(input_files, output_paths, selected_engine, llm_name)
        return

    if any(is_image_input(path) for path in input_files) and not selected_engine.supports_ocr:
        raise click.ClickException(
            f"Wejście obrazowe wymaga silnika OCR, a '{selected_engine.name}' go nie obsługuje."
        )

    if not selected_engine.is_available():
        raise click.ClickException(f"Silnik nie jest dostępny: {selected_engine.name}")

    llm_provider = _select_llm(llm_name, llm_model, settings)
    converter = Converter()
    total_start = time.monotonic()
    converted = 0
    failures: list[str] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        for path in input_files:
            task_id = progress.add_task(f"Konwertuję {path.name}", total=None)
            engine_kwargs: dict[str, object] = {}
            if selected_engine.supports_ocr:
                engine_kwargs["lang"] = lang
            output_path = output_paths[path]
            file_start = time.monotonic()
            try:
                engine_options: dict[str, object] = {}
                if selected_engine.name.lower() in {"docling", "marker"}:
                    engine_options["output_path"] = str(output_path)
                result = converter.convert(
                    str(path),
                    selected_engine,
                    llm=llm_provider,
                    llm_mode=llm_mode,
                    engine_kwargs=engine_kwargs,
                    engine_options=engine_options,
                    record_history=False,
                )
                if extract_images and not is_image_input(path):
                    images = extract_pdf_images(
                        path,
                        image_output_dir(output_path),
                        min_size=image_min_size,
                    )
                    result.markdown = append_image_references(
                        result.markdown,
                        images,
                        output_path,
                    )
                    if verbose:
                        console.print(f"[cyan]Obrazy:[/] wyciągnięto {len(images)}")
                exported_path = _export_result(result.markdown, output_path, selected_epub_backend)
                _record_history_safely(
                    input_path=path,
                    engine=selected_engine.name,
                    llm_provider=llm_provider,
                    llm_mode=llm_mode,
                    output_path=exported_path,
                    status="ok",
                    duration_s=time.monotonic() - file_start,
                )
                converted += 1
                if verbose:
                    console.print(f"[green]Zapisano:[/] {exported_path}")
            except (ConversionError, RuntimeError, OSError) as exc:
                _record_history_safely(
                    input_path=path,
                    engine=selected_engine.name,
                    llm_provider=llm_provider,
                    llm_mode=llm_mode,
                    output_path=output_path,
                    status="error",
                    duration_s=time.monotonic() - file_start,
                    error_msg=str(exc),
                )
                failures.append(f"{path}: {exc}")
                console.print(f"[red]Błąd:[/] {path}: {exc}")
            finally:
                progress.remove_task(task_id)

    elapsed = time.monotonic() - total_start
    console.print(
        Panel(
            f"Pliki: {converted}/{len(input_files)}\n"
            f"Czas: {elapsed:.2f}s\n"
            f"Silnik: {selected_engine.name}",
            title="Raport końcowy",
        )
    )
    if failures:
        raise click.ClickException("; ".join(failures))


@cli.command("list-engines")
def list_engines() -> None:
    """Wyświetla dostępne i znane silniki konwersji."""
    _print_engine_table()


@cli.command("list-llm")
@click.pass_context
def list_llm(ctx: click.Context) -> None:
    """Wyświetla status dostawców LLM."""
    settings: Settings = ctx.obj["settings"]
    _print_llm_table(settings)


@cli.command("list-profiles")
def list_profiles_cmd() -> None:
    """Wyświetla dostępne profile/presety (wbudowane + użytkownika)."""
    from pdf2md.scan.profiles import list_profiles, load_profile

    table = Table(title="Profile i presety")
    table.add_column("Profil")
    table.add_column("Convert")
    table.add_column("Lang")
    table.add_column("LLM")
    table.add_column("DPI")
    table.add_column("OCR")
    table.add_column("EPUB")
    for name in list_profiles():
        try:
            profile = load_profile(name)
            conversion = profile.conversion
            ocr = profile.ocr.engine or profile.ocr.primary or "—"
            llm = profile.llm_cleanup.model if profile.llm_cleanup.enabled else "—"
            table.add_row(
                name,
                conversion.engine or "—",
                conversion.lang or "—",
                conversion.llm or llm,
                str(profile.dpi),
                str(ocr),
                "tak" if profile.output.epub else "nie",
            )
        except Exception as exc:
            # pokaż błędny profil w tabeli zamiast wywalać całą listę
            table.add_row(name, "—", "—", "—", "—", "—", f"błąd: {exc}")
    console.print(table)


@cli.command("history")
@click.option("--engine", "engine_filter", help="Filtruj po nazwie silnika.")
@click.option("--limit", type=click.IntRange(min=1), default=20, show_default=True)
@click.option(
    "--csv",
    "csv_path",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Wyeksportuj historię do CSV.",
)
@click.option("--clear", "clear_history", is_flag=True, help="Wyczyść historię konwersji.")
def history_cmd(
    engine_filter: str | None,
    limit: int,
    csv_path: Path | None,
    clear_history: bool,
) -> None:
    """Wyświetla historię konwersji."""
    if clear_history:
        if not click.confirm("Wyczyścić całą historię konwersji?"):
            console.print("[yellow]Anulowano.[/]")
            return
        removed = conversion_history.clear()
        console.print(f"[green]Wyczyszczono historię:[/] {removed} wpis(ów).")
        return

    if csv_path is not None:
        exported = conversion_history.export_csv(csv_path, limit=limit, engine=engine_filter)
        console.print(f"[green]Wyeksportowano historię:[/] {exported}")
        return

    entries = conversion_history.list_recent(limit=limit, engine=engine_filter)
    table = Table(title="Historia konwersji")
    table.add_column("ID", justify="right")
    table.add_column("Czas")
    table.add_column("Status")
    table.add_column("Silnik")
    table.add_column("LLM")
    table.add_column("Tryb")
    table.add_column("s", justify="right")
    table.add_column("Wejście")
    table.add_column("Wynik / błąd")

    for entry in entries:
        status = "[green]ok[/]" if entry.status == "ok" else "[red]error[/]"
        table.add_row(
            str(entry.id),
            entry.ts,
            status,
            entry.engine,
            entry.llm_provider,
            entry.llm_mode,
            f"{entry.duration_s:.2f}",
            entry.input_path,
            entry.output_path if entry.status == "ok" else entry.error_msg,
        )
    console.print(table)


@cli.command()
@click.argument("pdf")
@click.option("--profile", "-p", default="balanced", show_default=True, help="Profil skanowania.")
@click.option(
    "--output", "-o", "output_dir", default="output", show_default=True, help="Katalog wyjściowy."
)
@click.option("--keep-work", is_flag=True, help="Zachowaj katalog roboczy work/ (debug).")
@click.option("--verbose", "-v", is_flag=True, help="Szczegółowy output.")
def scan(pdf: str, profile: str, output_dir: str, keep_work: bool, verbose: bool) -> None:
    """Składa skan książki do Markdown/EPUB wg profilu (preprocessing→OCR→korekta→eksport)."""
    if verbose:
        setup_logging(verbose=True)

    from pdf2md.scan.profiles import ProfileError, load_profile

    try:
        prof = load_profile(profile)
    except ProfileError as exc:
        raise click.ClickException(str(exc)) from exc

    pdf_path = Path(pdf)
    if not pdf_path.exists():
        raise click.ClickException(f"Plik nie istnieje: {pdf}")

    engine = _find_engine("scan-pipeline")
    if engine is None:
        raise click.ClickException("Silnik Scan Pipeline nie jest zarejestrowany.")
    if not engine.is_available():
        raise click.ClickException(
            "Silnik Scan Pipeline nie jest dostępny — wymaga GPU i silnika VLM-OCR "
            "(zob. INSTALL.md)."
        )

    start = time.monotonic()
    try:
        result = engine.convert(
            str(pdf_path),
            output_dir=output_dir,
            profile=prof.model_dump(),
            keep_work=keep_work,
        )
    except (RuntimeError, OSError, ConversionError) as exc:
        _record_history_safely(
            input_path=pdf_path,
            engine=engine.name,
            llm_provider=None,
            llm_mode=f"scan:{prof.name}",
            output_path=output_dir,
            status="error",
            duration_s=time.monotonic() - start,
            error_msg=str(exc),
        )
        raise click.ClickException(str(exc)) from exc

    elapsed = time.monotonic() - start
    _record_history_safely(
        input_path=pdf_path,
        engine=engine.name,
        llm_provider=None,
        llm_mode=f"scan:{prof.name}",
        output_path=str(result.metadata.get("book_md_path") or output_dir),
        status="ok",
        duration_s=elapsed,
    )
    console.print(
        Panel(
            f"Profil: {prof.name}\n"
            f"Strony: {result.pages} · Rozdziały: {result.metadata.get('chapters')}\n"
            f"Markdown: {result.metadata.get('book_md_path')}\n"
            f"EPUB: {result.metadata.get('epub_path') or '—'}\n"
            f"Raport: {result.metadata.get('report_path') or '—'}\n"
            f"Czas: {elapsed:.1f}s",
            title="Scan Pipeline",
        )
    )


@cli.command()
@click.option(
    "--plain",
    is_flag=True,
    help="Deterministyczne wyjście pod snapshoty: bez kolorów ANSI i ze stałą szerokością "
    "(można też ustawić zmienną środowiskową DOCTOR_PLAIN=1).",
)
@click.pass_context
def doctor(ctx: click.Context, plain: bool) -> None:
    """Diagnozuje środowisko uruchomieniowe."""
    settings: Settings = ctx.obj["settings"]
    deps = check_all()

    plain = plain or _env_flag("DOCTOR_PLAIN")
    out = _plain_console() if plain else console

    out.print(Panel.fit("pdf2md doctor", style="bold cyan"))

    system_table = Table(title="System")
    system_table.add_column("Element")
    system_table.add_column("Status")
    system_table.add_row("OS", _detect_os_label())
    system_table.add_row("Python", sys.version.split()[0])
    system_table.add_row("Platforma", str(deps.get("system", {}).get("platform", "")))
    out.print(system_table)

    gpu = deps["gpu"]
    hw = detect_hardware()
    gpu_table = Table(title="GPU")
    gpu_table.add_column("Element")
    gpu_table.add_column("Status")
    gpu_table.add_row("PyTorch", "✅ działa" if gpu.get("torch_available") else "❌ brak")
    gpu_table.add_row("CUDA", "✅ dostępna" if gpu.get("cuda_available") else "❌ niedostępna")
    gpu_table.add_row(
        "CUDA smoke test",
        "✅ używalna" if gpu.get("cuda_usable") else "❌ nieużywalna",
    )
    # CUDA version / Urządzenie: gdy torch nie widzi karty, uzupełnij z nvidia-smi (hw) —
    # żeby tabela nie pokazywała „brak", gdy karta fizycznie jest (np. za stara / stary sterownik).
    cuda_version = str(gpu.get("cuda_version") or hw.driver_cuda or "brak")
    device_name = str(gpu.get("device_name") or hw.name or "")
    if device_name and hw.vram_gb is not None:
        device_label = f"{device_name}, {hw.vram_gb:.0f} GB"
    else:
        device_label = device_name or "brak"
    gpu_table.add_row("CUDA version", cuda_version)
    gpu_table.add_row("Urządzenie", device_label)
    gpu_table.add_row("Ocena sprzętu", _hardware_summary(hw, str(gpu.get("cuda_version") or "")))
    out.print(gpu_table)

    tools_table = Table(title="Narzędzia")
    tools_table.add_column("Narzędzie")
    tools_table.add_column("Status")
    tesseract = deps["tesseract"]
    langs = set(tesseract.get("languages", []))
    tesseract_status = (
        "✅ " + str(tesseract.get("version", "")) if tesseract["available"] else "❌ brak"
    )
    tools_table.add_row("Tesseract", tesseract_status)
    tools_table.add_row("Tesseract pol/eng", "✅ tak" if {"pol", "eng"} <= langs else "⚠️ niepełne")
    tools_table.add_row("Poppler", "✅ dostępny" if deps["poppler"] else "❌ brak")
    tools_table.add_row("Pandoc", "✅ dostępny" if deps["pandoc"] else "⚠️ brak")
    tools_table.add_row(
        "Calibre (ebook-convert)", "✅ dostępny" if deps["calibre"] else "⚠️ brak (opcjonalny)"
    )
    out.print(tools_table)

    ollama = deps["ollama"]
    models = ollama.get("models", [])
    # W trybie plain sortujemy listę modeli — kolejność z API Ollamy bywa niestabilna.
    if plain:
        models = sorted(models)
    ollama_models = ", ".join(models) or "brak"
    out.print(
        Panel(
            f"Status: {'✅ działa' if ollama['available'] else '❌ niedostępna'}\n"
            f"Modele: {ollama_models}",
            title="Ollama",
        )
    )

    _print_engine_table(hw, out)

    keys_table = Table(title="Klucze API")
    keys_table.add_column("Provider")
    keys_table.add_column("Status")
    keys_table.add_row("Anthropic", _mask_secret(settings.anthropic_api_key))
    keys_table.add_row("OpenAI", _mask_secret(settings.openai_api_key))
    keys_table.add_row("Gemini", _mask_secret(settings.gemini_api_key))
    out.print(keys_table)


@cli.group("config")
def config_group() -> None:
    """Zarządza ~/.config/pdf2md/config.toml."""


@config_group.command("show")
@click.pass_context
def config_show(ctx: click.Context) -> None:
    """Wyświetla aktualną konfigurację."""
    settings: Settings = ctx.obj["settings"]
    table = Table(title="Konfiguracja pdf2md")
    table.add_column("Klucz")
    table.add_column("Wartość")

    data = settings.model_dump()
    for key in sorted(data):
        value = data[key]
        if key.endswith("_api_key"):
            value = _mask_secret(str(value))
        table.add_row(key, str(value))
    console.print(table)


@config_group.command("set")
@click.argument("key")
@click.argument("value")
@click.pass_context
def config_set(ctx: click.Context, key: str, value: str) -> None:
    """Ustawia wartość w config.toml."""
    settings: Settings = ctx.obj["settings"]
    field_name = _normalize_config_key(key)
    if field_name not in Settings.model_fields:
        valid = ", ".join(sorted(Settings.model_fields))
        raise click.ClickException(f"Nieznany klucz: {key}. Dostępne: {valid}")

    data = settings.model_dump()
    data[field_name] = _coerce_config_value(field_name, value, settings)
    updated = Settings(**data)
    save_settings(updated)
    console.print(f"[green]Zapisano:[/] {field_name} = {data[field_name]}")


@config_group.command("edit")
def config_edit() -> None:
    """Otwiera config.toml w edytorze z EDITOR albo nano."""
    get_settings()
    editor = os.environ.get("EDITOR", "nano")
    command = [*shlex.split(editor), str(config_module._CONFIG_FILE)]
    raise SystemExit(subprocess.run(command, check=False).returncode)


if __name__ == "__main__":
    cli()
