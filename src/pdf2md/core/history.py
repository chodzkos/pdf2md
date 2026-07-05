"""Historia konwersji zapisywana w lokalnej bazie SQLite."""

from __future__ import annotations

import csv
import os
import sqlite3
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from loguru import logger

from pdf2md.core import config as config_module

HistoryStatus = Literal["ok", "error"]

_HISTORY_DB_ENV = "PDF2MD_HISTORY_DB"
_FIELDNAMES = (
    "id",
    "ts",
    "input_path",
    "engine",
    "llm_provider",
    "llm_mode",
    "output_path",
    "status",
    "duration_s",
    "error_msg",
)


@dataclass(frozen=True)
class ConversionHistoryEntry:
    """Pojedynczy wpis historii konwersji."""

    id: int
    ts: str
    input_path: str
    engine: str
    llm_provider: str
    llm_mode: str
    output_path: str
    status: HistoryStatus
    duration_s: float
    error_msg: str


def history_db_path() -> Path:
    """Zwraca ścieżkę do bazy historii."""
    override = os.environ.get(_HISTORY_DB_ENV)
    if override:
        return Path(override).expanduser()
    return config_module._CONFIG_FILE.parent / "history.db"


def record(
    *,
    input_path: str | Path,
    engine: str,
    llm_provider: str | None = None,
    llm_mode: str | None = None,
    output_path: str | Path | None = None,
    status: HistoryStatus,
    duration_s: float,
    error_msg: str | None = None,
) -> int:
    """Zapisuje wpis historii i zwraca jego `id`."""
    if status not in {"ok", "error"}:
        raise ValueError("status musi mieć wartość: ok albo error")

    ts = datetime.now(UTC).isoformat(timespec="seconds")
    with _connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO conversions (
                ts, input_path, engine, llm_provider, llm_mode, output_path,
                status, duration_s, error_msg
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ts,
                str(input_path),
                engine,
                llm_provider or "none",
                llm_mode or "none",
                str(output_path) if output_path else "",
                status,
                float(duration_s),
                error_msg or "",
            ),
        )
        row_id = cursor.lastrowid
        if row_id is None:  # pragma: no cover - INSERT do tabeli z AUTOINCREMENT zawsze zwraca id
            raise RuntimeError("SQLite nie zwrócił id wpisu historii")
        return int(row_id)


def record_safely(**kwargs: object) -> int | None:
    """Zapisuje historię bez ryzyka przerwania konwersji."""
    try:
        return record(**kwargs)  # type: ignore[arg-type]
    except Exception as exc:  # pragma: no cover - defensywna osłona produkcyjna
        logger.warning(f"Nie udało się zapisać historii konwersji: {exc}")
        return None


def list_recent(limit: int = 20, engine: str | None = None) -> list[ConversionHistoryEntry]:
    """Zwraca najnowsze wpisy historii, opcjonalnie filtrowane po silniku."""
    return _fetch_entries(limit=limit, engine=engine)


def clear() -> int:
    """Czyści historię i zwraca liczbę usuniętych wpisów."""
    with _connect() as connection:
        count = connection.execute("SELECT COUNT(*) FROM conversions").fetchone()[0]
        connection.execute("DELETE FROM conversions")
        return int(count)


def export_csv(
    path: str | Path,
    *,
    limit: int | None = None,
    engine: str | None = None,
) -> Path:
    """Eksportuje historię do CSV i zwraca ścieżkę pliku."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    entries = _fetch_entries(limit=limit, engine=engine)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=_FIELDNAMES)
        writer.writeheader()
        for entry in entries:
            writer.writerow(asdict(entry))
    return destination


def _connect() -> sqlite3.Connection:
    db_path = history_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    _ensure_schema(connection)
    return connection


def _ensure_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS conversions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            input_path TEXT NOT NULL,
            engine TEXT NOT NULL,
            llm_provider TEXT NOT NULL,
            llm_mode TEXT NOT NULL,
            output_path TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('ok', 'error')),
            duration_s REAL NOT NULL,
            error_msg TEXT NOT NULL
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_conversions_engine_id ON conversions(engine, id)"
    )


def _fetch_entries(
    *,
    limit: int | None,
    engine: str | None,
) -> list[ConversionHistoryEntry]:
    if limit is not None and limit < 1:
        raise ValueError("limit musi być większy od zera")

    query = "SELECT * FROM conversions"
    params: list[object] = []
    if engine:
        query += " WHERE lower(engine) = lower(?)"
        params.append(engine)
    query += " ORDER BY id DESC"
    if limit is not None:
        query += " LIMIT ?"
        params.append(limit)

    with _connect() as connection:
        rows = connection.execute(query, params).fetchall()
    return [_entry_from_row(row) for row in rows]


def _entry_from_row(row: sqlite3.Row) -> ConversionHistoryEntry:
    status = str(row["status"])
    if status not in {"ok", "error"}:  # pragma: no cover - constraint pilnuje tego w DB
        raise ValueError(f"Nieznany status historii: {status}")
    return ConversionHistoryEntry(
        id=int(row["id"]),
        ts=str(row["ts"]),
        input_path=str(row["input_path"]),
        engine=str(row["engine"]),
        llm_provider=str(row["llm_provider"]),
        llm_mode=str(row["llm_mode"]),
        output_path=str(row["output_path"]),
        status=status,  # type: ignore[arg-type]
        duration_s=float(row["duration_s"]),
        error_msg=str(row["error_msg"]),
    )
