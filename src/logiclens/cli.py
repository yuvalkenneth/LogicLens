"""Command-line interface for LogicLens."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from logiclens.database import (
    create_database,
    read_files,
    read_imports,
    read_modules,
    read_repository_brief_context,
    read_symbols,
)
from logiclens.brief import validate_repository_brief
from logiclens.inventory import build_inventory
from logiclens.python_modules import analyze_python_modules


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

    modules_parser = commands.add_parser(
        "modules", help="List saved Python modules and import relationships."
    )
    modules_parser.add_argument("--db", required=True, type=Path)

    symbols_parser = commands.add_parser(
        "symbols", help="List saved functions, classes, and methods."
    )
    symbols_parser.add_argument("--db", required=True, type=Path)

    context_parser = commands.add_parser(
        "context", help="Build bounded context from the saved mapping."
    )
    context_parser.add_argument("kind", choices=["repository-brief"])
    context_parser.add_argument("--db", required=True, type=Path)
    context_parser.add_argument("--json", action="store_true")

    validate_parser = commands.add_parser(
        "validate-brief", help="Validate an agent-produced Repository Brief."
    )
    validate_parser.add_argument("brief", type=Path)
    validate_parser.add_argument("--db", required=True, type=Path)
    validate_parser.add_argument("--expectations", type=Path)

    eval_parser = commands.add_parser(
        "eval", help="Run a paired native-versus-LogicLens Codex evaluation."
    )
    eval_parser.add_argument("case", type=Path)
    eval_parser.add_argument("--results", required=True, type=Path)
    eval_parser.add_argument("--model", default="gpt-5.6-sol")
    eval_parser.add_argument("--repetitions", type=int)
    eval_parser.add_argument("--seed", type=int, default=0)
    eval_parser.add_argument("--codex", type=Path)
    eval_parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)

    try:
        if arguments.command == "eval":
            from logiclens.evaluation import run_codex_evaluation

            session = run_codex_evaluation(
                arguments.case,
                arguments.results,
                model=arguments.model,
                repetitions=arguments.repetitions,
                seed=arguments.seed,
                codex_executable=arguments.codex,
                dry_run=arguments.dry_run,
            )
            print(f"Saved evaluation session to: {session}")
            manifest = json.loads(
                (session / "manifest.json").read_text(encoding="utf-8")
            )
            return 1 if manifest["failed_runs"] and not arguments.dry_run else 0

        if arguments.command == "map":
            inventory = build_inventory(arguments.repository)
            structure = analyze_python_modules(inventory)
            create_database(arguments.db, inventory, structure)
            print(f"Mapped {len(inventory.files)} files")
            print(
                f"Python modules: {len(structure.modules)}; "
                f"imports: {len(structure.imports)}; "
                f"symbols: {len(structure.symbols)}"
            )
            print(f"Snapshot: {inventory.snapshot_hash}")
            print(f"Saved to: {arguments.db}")
            return 0

        if arguments.command == "files":
            records = read_files(arguments.db)
            print("PATH\tTYPE\tLANGUAGE\tSIZE\tHASH")
            for record in records:
                print(
                    f"{record.path}\t{record.category}\t{record.language or '-'}\t"
                    f"{record.size_bytes}\t{record.content_hash[:12]}"
                )
            return 0

        if arguments.command == "context":
            context = read_repository_brief_context(arguments.db)
            print(json.dumps(context, indent=2, sort_keys=True))
            return 0

        if arguments.command == "validate-brief":
            brief = json.loads(arguments.brief.read_text(encoding="utf-8"))
            expectations = (
                json.loads(arguments.expectations.read_text(encoding="utf-8"))
                if arguments.expectations
                else None
            )
            errors = validate_repository_brief(brief, arguments.db, expectations)
            print(json.dumps({"valid": not errors, "errors": errors}, indent=2))
            return 1 if errors else 0

        if arguments.command == "symbols":
            print("ID\tKIND\tFILE\tLOCATION\tSIGNATURE")
            for record in read_symbols(arguments.db):
                location = (
                    f"{record.start_line}:{record.start_column}-"
                    f"{record.end_line}:{record.end_column}"
                )
                print(
                    f"{record.kind}:{record.qualified_name}\t{record.kind}\t"
                    f"{record.file_path}\t{location}\t{record.signature or '-'}"
                )
            return 0

        print("MODULE\tKIND\tFILE")
        for module in read_modules(arguments.db):
            print(f"{module.name}\t{module.kind}\t{module.file_path}")
        print("\nSOURCE\tIMPORT\tTARGET\tLOCATION")
        for record in read_imports(arguments.db):
            location = (
                f"{record.file_path}:{record.start_line}:{record.start_column}"
            )
            print(
                f"{record.source_module}\t{record.imported_name}\t"
                f"{record.target_module or 'unresolved'}\t{location}"
            )
        return 0
    except (FileExistsError, FileNotFoundError, ValueError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())
