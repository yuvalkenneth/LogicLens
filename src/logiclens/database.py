"""SQLite persistence for deterministic inventory data."""

from __future__ import annotations

from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path
import sqlite3

from logiclens.inventory import FileRecord, Inventory


def create_database(database_path: Path, inventory: Inventory) -> None:
    destination = database_path.expanduser().resolve()
    if destination.exists():
        raise FileExistsError(f"Database already exists: {destination}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    schema = files("logiclens").joinpath("schema.sql").read_text(encoding="utf-8")

    with sqlite3.connect(destination) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(schema)
        connection.execute(
            """
            INSERT INTO metadata (
                id, source_path, snapshot_hash, created_at
            ) VALUES (1, ?, ?, ?)
            """,
            (
                str(inventory.source_path),
                inventory.snapshot_hash,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        connection.executemany(
            """
            INSERT INTO files (
                path, category, language, content_hash, size_bytes
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                (
                    record.path,
                    record.category,
                    record.language,
                    record.content_hash,
                    record.size_bytes,
                )
                for record in inventory.files
            ),
        )


def read_files(database_path: Path) -> tuple[FileRecord, ...]:
    source = database_path.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Database does not exist: {source}")

    with sqlite3.connect(source) as connection:
        rows = connection.execute(
            """
            SELECT path, category, language, content_hash, size_bytes
            FROM files
            ORDER BY path
            """
        ).fetchall()

    return tuple(FileRecord(*row) for row in rows)
