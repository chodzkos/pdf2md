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

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from pdf2md import __version__
from pdf2md.core import config as config_module
from pdf2md.core.config import Settings, get_settings, save_settings
from pdf2md.core.converter import ConversionError, Converter
from pdf2md.core.registry import engine_registry, llm_registry
from pdf2md.detection.dependencies import check_all
from pdf2md.detection.pdf_type import detect_pdf_type
from pdf2md.engines.base import ConversionEngine
from pdf2md.exporters import MarkdownExporter, PandocEpubExporter
from pdf2md.llm.base import LLMProvider
from pdf2md.utils.logging import setup_logging

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
        "description": "Dokumenty naukowe, layout, CJK.",
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
        "description": "Skan książki → VLM-OCR, korekta LLM, składanie, EPUB/Markdown.",
    },
)


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


def _print_engine_table() -> None:
    table = Table(title="Silniki konwersji")
    table.add_column("Nazwa")
    table.add_column("Status")
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
            str(item["scope"]),
            "tak" if item["ocr"] else "nie",
            "wymagane" if item.get("gpu") else "nie",
            "tak" if item["llm"] else "nie",
            str(item["license"]),
            description,
        )
    console.print(table)


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
        pdf_info = detect_pdf_type(str(path))
        table = Table(title=f"Plan konwersji: {path}")
        table.add_column("Pole")
        table.add_column("Wartość")
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
        table.add_row("Ollama", "tak" if deps["ollama"]["available"] else "nie")
        console.print(table)


def _export_result(markdown: str, output_path: Path) -> Path:
    if output_path.suffix.lower() == ".epub":
        return PandocEpubExporter().export(markdown, output_path)
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
    ctx.ensure_object(dict)
    ctx.obj["settings"] = _startup(verbose=False)


@cli.command()
@click.argument("files", nargs=-1, required=True)
@click.option("--engine", "-e", help="Silnik konwersji, np. pymupdf4llm albo marker.")
@click.option("--output", "-o", help="Plik wyjściowy .md/.epub albo katalog dla wielu plików.")
@click.option("--output-dir", help="Katalog dla wyników batch.")
@click.option(
    "--llm", "llm_name", type=click.Choice(LLM_CHOICES), default="none", show_default=True
)
@click.option("--llm-model", help="Model LLM nadpisujący config tylko dla tego uruchomienia.")
@click.option("--llm-mode", type=click.Choice(LLM_MODES), default="none", show_default=True)
@click.option("--lang", default="pol+eng", show_default=True, help="Język OCR.")
@click.option("--dry-run", is_flag=True, help="Pokaż plan bez konwersji.")
@click.option("--verbose", "-v", is_flag=True, help="Szczegółowy output.")
@click.pass_context
def convert(
    ctx: click.Context,
    files: tuple[str, ...],
    engine: str | None,
    output: str | None,
    output_dir: str | None,
    llm_name: str,
    llm_model: str | None,
    llm_mode: str,
    lang: str,
    dry_run: bool,
    verbose: bool,
) -> None:
    """Konwertuje jeden lub wiele plików PDF do Markdown."""
    if verbose:
        setup_logging(verbose=True)
    settings: Settings = ctx.obj["settings"]
    engine_name = engine or settings.default_engine
    selected_engine = _select_engine(engine_name)
    input_files = _expand_files(files)
    if not input_files:
        raise click.ClickException("Nie znaleziono plików wejściowych.")

    missing = [str(path) for path in input_files if not path.exists()]
    if missing:
        raise click.ClickException(f"Plik nie istnieje: {missing[0]}")

    output_paths = _resolve_output_paths(input_files, output, output_dir)
    if dry_run:
        _print_dry_run(input_files, output_paths, selected_engine, llm_name)
        return

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
            try:
                result = converter.convert(
                    str(path),
                    selected_engine,
                    llm=llm_provider,
                    llm_mode=llm_mode,
                    engine_kwargs=engine_kwargs,
                )
                exported_path = _export_result(result.markdown, output_paths[path])
                converted += 1
                if verbose:
                    console.print(f"[green]Zapisano:[/] {exported_path}")
            except (ConversionError, RuntimeError, OSError) as exc:
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
    """Wyświetla dostępne profile skanowania (wbudowane + użytkownika)."""
    from pdf2md.scan.profiles import list_profiles, load_profile

    table = Table(title="Profile skanowania")
    table.add_column("Profil")
    table.add_column("DPI")
    table.add_column("OCR")
    table.add_column("LLM cleanup")
    table.add_column("EPUB")
    for name in list_profiles():
        try:
            profile = load_profile(name)
            ocr = profile.ocr.engine or profile.ocr.primary or "—"
            llm = profile.llm_cleanup.model if profile.llm_cleanup.enabled else "—"
            table.add_row(
                name,
                str(profile.dpi),
                str(ocr),
                str(llm),
                "tak" if profile.output.epub else "nie",
            )
        except Exception as exc:
            # pokaż błędny profil w tabeli zamiast wywalać całą listę
            table.add_row(name, "—", "—", "—", f"błąd: {exc}")
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
    result = engine.convert(
        str(pdf_path),
        output_dir=output_dir,
        profile=prof.model_dump(),
        keep_work=keep_work,
    )
    elapsed = time.monotonic() - start
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
@click.pass_context
def doctor(ctx: click.Context) -> None:
    """Diagnozuje środowisko uruchomieniowe."""
    settings: Settings = ctx.obj["settings"]
    deps = check_all()

    console.print(Panel.fit("pdf2md doctor", style="bold cyan"))

    system_table = Table(title="System")
    system_table.add_column("Element")
    system_table.add_column("Status")
    system_table.add_row("OS", _detect_os_label())
    system_table.add_row("Python", sys.version.split()[0])
    system_table.add_row("Platforma", str(deps.get("system", {}).get("platform", "")))
    console.print(system_table)

    gpu = deps["gpu"]
    gpu_table = Table(title="GPU")
    gpu_table.add_column("Element")
    gpu_table.add_column("Status")
    gpu_table.add_row("PyTorch", "✅ działa" if gpu.get("torch_available") else "❌ brak")
    gpu_table.add_row("CUDA", "✅ dostępna" if gpu.get("cuda_available") else "❌ niedostępna")
    gpu_table.add_row(
        "CUDA smoke test",
        "✅ używalna" if gpu.get("cuda_usable") else "❌ nieużywalna",
    )
    gpu_table.add_row("CUDA version", str(gpu.get("cuda_version") or "brak"))
    gpu_table.add_row("Urządzenie", str(gpu.get("device_name") or "brak"))
    console.print(gpu_table)

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
    console.print(tools_table)

    ollama = deps["ollama"]
    ollama_models = ", ".join(ollama.get("models", [])) or "brak"
    console.print(
        Panel(
            f"Status: {'✅ działa' if ollama['available'] else '❌ niedostępna'}\n"
            f"Modele: {ollama_models}",
            title="Ollama",
        )
    )

    _print_engine_table()

    keys_table = Table(title="Klucze API")
    keys_table.add_column("Provider")
    keys_table.add_column("Status")
    keys_table.add_row("Anthropic", _mask_secret(settings.anthropic_api_key))
    keys_table.add_row("OpenAI", _mask_secret(settings.openai_api_key))
    keys_table.add_row("Gemini", _mask_secret(settings.gemini_api_key))
    console.print(keys_table)


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
