"""Filesystem wiki generated from an immutable SQLite repository map."""

from __future__ import annotations

from pathlib import Path
import sqlite3


def initialize_wiki(database_path: Path, output: Path) -> None:
    """Create a small navigable wiki without changing the mapped snapshot."""
    with sqlite3.connect(database_path) as connection:
        source_path, snapshot_hash = connection.execute(
            "SELECT source_path, snapshot_hash FROM metadata WHERE id = 1"
        ).fetchone()
        files, modules, symbols = (
            connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("files", "modules", "symbols")
        )
    output.mkdir(parents=True, exist_ok=True)
    (output / "index.md").write_text(
        "# LogicLens Wiki\n\n"
        "- [Repository overview](overview.md)\n"
        "- `SQLite map`: `../index.sqlite`\n",
        encoding="utf-8",
    )
    (output / "overview.md").write_text(
        "# Repository overview\n\n"
        f"- Source snapshot: `{snapshot_hash}`\n"
        f"- Source path: `{source_path}`\n"
        f"- Deterministic inventory: {files} files, {modules} Python modules, {symbols} symbols.\n\n"
        "This page is a starting artifact. Agent-written claims must cite source spans "
        "or deterministic IDs from the SQLite map.\n",
        encoding="utf-8",
    )
