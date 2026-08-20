"""SQLite persistence for deterministic inventory data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path
import sqlite3

from logiclens.inventory import FileRecord, Inventory
from logiclens.python_modules import ImportRecord, ModuleRecord, PythonStructure


@dataclass(frozen=True)
class ModuleImportView:
    source_module: str
    imported_name: str
    target_module: str | None
    file_path: str
    start_line: int
    start_column: int


def create_database(
    database_path: Path,
    inventory: Inventory,
    python_structure: PythonStructure | None = None,
) -> None:
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
        if python_structure is not None:
            _write_python_structure(connection, python_structure)


def _write_python_structure(
    connection: sqlite3.Connection, structure: PythonStructure
) -> None:
    file_ids = dict(connection.execute("SELECT path, id FROM files"))
    connection.executemany(
        "INSERT INTO modules (file_id, name, kind) VALUES (?, ?, ?)",
        (
            (file_ids[module.file_path], module.name, module.kind)
            for module in structure.modules
        ),
    )
    module_ids = dict(
        connection.execute(
            """
            SELECT files.path, modules.id
            FROM modules
            JOIN files ON files.id = modules.file_id
            """
        )
    )
    connection.executemany(
        """
        INSERT INTO imports (
            source_module_id, imported_name, target_module_id,
            start_line, start_column, end_line, end_column
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            (
                module_ids[record.source_file_path],
                record.imported_name,
                module_ids.get(record.target_file_path),
                record.start_line,
                record.start_column,
                record.end_line,
                record.end_column,
            )
            for record in structure.imports
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


def read_modules(database_path: Path) -> tuple[ModuleRecord, ...]:
    source = _existing_database(database_path)
    with sqlite3.connect(source) as connection:
        rows = connection.execute(
            """
            SELECT files.path, modules.name, modules.kind
            FROM modules
            JOIN files ON files.id = modules.file_id
            ORDER BY modules.name, files.path
            """
        ).fetchall()
    return tuple(ModuleRecord(*row) for row in rows)


def read_imports(database_path: Path) -> tuple[ModuleImportView, ...]:
    source = _existing_database(database_path)
    with sqlite3.connect(source) as connection:
        rows = connection.execute(
            """
            SELECT
                source.name,
                imports.imported_name,
                target.name,
                files.path,
                imports.start_line,
                imports.start_column
            FROM imports
            JOIN modules AS source ON source.id = imports.source_module_id
            JOIN files ON files.id = source.file_id
            LEFT JOIN modules AS target ON target.id = imports.target_module_id
            ORDER BY files.path, imports.start_line, imports.start_column
            """
        ).fetchall()
    return tuple(ModuleImportView(*row) for row in rows)


def _existing_database(database_path: Path) -> Path:
    source = database_path.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Database does not exist: {source}")
    return source
