"""SQLite persistence for deterministic inventory data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from importlib.resources import files
from pathlib import Path
import sqlite3

from logiclens.inventory import FileRecord, Inventory, build_inventory
from logiclens.python_modules import (
    ImportRecord,
    ModuleRecord,
    PythonStructure,
)
from logiclens.symbols import SymbolRecord


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
    top_level_symbols = [
        record for record in structure.symbols if record.parent_qualified_name is None
    ]
    _insert_symbols(connection, module_ids, {}, top_level_symbols)
    parent_ids = dict(connection.execute("SELECT qualified_name, id FROM symbols"))
    _insert_symbols(
        connection,
        module_ids,
        parent_ids,
        [record for record in structure.symbols if record.parent_qualified_name],
    )


def _insert_symbols(
    connection: sqlite3.Connection,
    module_ids: dict[str, int],
    parent_ids: dict[str, int],
    symbols: list[SymbolRecord],
) -> None:
    connection.executemany(
        """
        INSERT INTO symbols (
            module_id, parent_symbol_id, qualified_name, name, kind,
            signature, docstring, start_line, start_column, end_line, end_column
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            (
                module_ids[record.file_path],
                parent_ids.get(record.parent_qualified_name),
                record.qualified_name,
                record.name,
                record.kind,
                record.signature,
                record.docstring,
                record.start_line,
                record.start_column,
                record.end_line,
                record.end_column,
            )
            for record in symbols
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


def read_symbols(database_path: Path) -> tuple[SymbolRecord, ...]:
    source = _existing_database(database_path)
    with sqlite3.connect(source) as connection:
        rows = connection.execute(
            """
            SELECT
                files.path,
                symbols.qualified_name,
                symbols.name,
                symbols.kind,
                parent.qualified_name,
                symbols.signature,
                symbols.docstring,
                symbols.start_line,
                symbols.start_column,
                symbols.end_line,
                symbols.end_column
            FROM symbols
            JOIN modules ON modules.id = symbols.module_id
            JOIN files ON files.id = modules.file_id
            LEFT JOIN symbols AS parent ON parent.id = symbols.parent_symbol_id
            ORDER BY files.path, symbols.start_line, symbols.start_column
            """
        ).fetchall()
    return tuple(SymbolRecord(*row) for row in rows)


def read_file_content(database_path: Path, file_path: str) -> str:
    source = _existing_database(database_path)
    with sqlite3.connect(source) as connection:
        row = connection.execute(
            """
            SELECT metadata.source_path, files.content_hash
            FROM metadata, files
            WHERE metadata.id = 1 AND files.path = ?
            """,
            (file_path,),
        ).fetchone()
    if row is None:
        raise ValueError(f"File is not present in the mapped snapshot: {file_path}")

    root = Path(row[0]).resolve()
    target = (root / file_path).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        raise ValueError(f"Mapped file is no longer available: {file_path}")

    content = target.read_bytes()
    if sha256(content).hexdigest() != row[1]:
        raise ValueError(f"Mapped file has changed: {file_path}")
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(f"Mapped file is not UTF-8 text: {file_path}") from error


def read_repository_brief_context(database_path: Path) -> dict[str, object]:
    source = _existing_database(database_path)
    with sqlite3.connect(source) as connection:
        source_path, snapshot_hash = connection.execute(
            "SELECT source_path, snapshot_hash FROM metadata WHERE id = 1"
        ).fetchone()

    current_inventory = build_inventory(Path(source_path))
    if current_inventory.snapshot_hash != snapshot_hash:
        raise ValueError("Repository no longer matches the mapped snapshot")

    file_records = read_files(source)
    modules = read_modules(source)
    imports = read_imports(source)
    symbols = read_symbols(source)
    readable_files = [
        record
        for record in file_records
        if record.category in {"documentation", "manifest"}
    ]
    return {
        "snapshot_id": snapshot_hash,
        "files": [
            {
                "path": record.path,
                "category": record.category,
                "language": record.language,
            }
            for record in file_records
        ],
        "documents": [
            {
                "path": record.path,
                "category": record.category,
                "content": read_file_content(source, record.path),
            }
            for record in readable_files
        ],
        "modules": [
            {
                "name": module.name,
                "kind": module.kind,
                "file": module.file_path,
            }
            for module in modules
        ],
        "imports": [
            {
                "source": record.source_module,
                "imported_text": record.imported_name,
                "target": record.target_module,
                "evidence": {
                    "file": record.file_path,
                    "line": record.start_line,
                    "column": record.start_column,
                },
            }
            for record in imports
        ],
        "symbols": [
            {
                "id": f"{record.kind}:{record.qualified_name}",
                "name": record.name,
                "kind": record.kind,
                "file": record.file_path,
                "parent": record.parent_qualified_name,
                "signature": record.signature,
                "docstring": record.docstring,
                "evidence": {
                    "line": record.start_line,
                    "column": record.start_column,
                    "end_line": record.end_line,
                    "end_column": record.end_column,
                },
            }
            for record in symbols
        ],
    }


def _existing_database(database_path: Path) -> Path:
    source = database_path.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Database does not exist: {source}")
    return source
