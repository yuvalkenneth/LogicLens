"""Command-line interface for LogicLens."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from logiclens.database import create_database, read_files
from logiclens.inventory import build_inventory


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="logiclens")
    commands = parser.add_subparsers(dest="command", required=True)

    map_parser = commands.add_parser(
        "map", help="Inventory a repository into a new SQLite database."
    )
    map_parser.add_argument("repository", type=Path)
    map_parser.add_argument("--db", required=True, type=Path)

    files_parser = commands.add_parser(
        "files", help="List the files saved in an inventory database."
    )
    files_parser.add_argument("--db", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)

    try:
        if arguments.command == "map":
            inventory = build_inventory(arguments.repository)
            create_database(arguments.db, inventory)
            print(f"Mapped {len(inventory.files)} files")
            print(f"Snapshot: {inventory.snapshot_hash}")
            print(f"Saved to: {arguments.db}")
            return 0

        records = read_files(arguments.db)
        print("PATH\tTYPE\tLANGUAGE\tSIZE\tHASH")
        for record in records:
            print(
                f"{record.path}\t{record.category}\t{record.language or '-'}\t"
                f"{record.size_bytes}\t{record.content_hash[:12]}"
            )
        return 0
    except (FileExistsError, FileNotFoundError, ValueError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())
