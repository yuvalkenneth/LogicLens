from pathlib import Path
import sqlite3

import pytest

from logiclens.database import (
    create_database,
    read_file_content,
    read_files,
    read_imports,
    read_modules,
    read_repository_brief_context,
    read_symbols,
)
from logiclens.inventory import build_inventory
from logiclens.python_modules import analyze_python_modules


FIXTURE = Path(__file__).parent / "fixtures" / "tiny_python"


def test_inventory_round_trip(tmp_path: Path) -> None:
    inventory = build_inventory(FIXTURE)
    database = tmp_path / "tiny.sqlite"

    create_database(database, inventory)

    assert read_files(database) == inventory.files
    with sqlite3.connect(database) as connection:
        metadata = connection.execute(
            "SELECT source_path, snapshot_hash FROM metadata WHERE id = 1"
        ).fetchone()
    assert metadata == (str(FIXTURE.resolve()), inventory.snapshot_hash)


def test_database_is_not_overwritten(tmp_path: Path) -> None:
    inventory = build_inventory(FIXTURE)
    database = tmp_path / "tiny.sqlite"
    create_database(database, inventory)

    with pytest.raises(FileExistsError):
        create_database(database, inventory)


def test_python_structure_round_trip(tmp_path: Path) -> None:
    inventory = build_inventory(FIXTURE)
    structure = analyze_python_modules(inventory)
    database = tmp_path / "tiny.sqlite"

    create_database(database, inventory, structure)

    assert read_modules(database) == structure.modules
    imports = read_imports(database)
    assert [(record.source_module, record.target_module) for record in imports] == [
        ("shop.main", "shop.repository"),
        ("shop.main", "shop.service"),
        ("shop.service", "shop.repository"),
    ]
    assert read_symbols(database) == structure.symbols

    context = read_repository_brief_context(database)
    assert context["symbols"][0]["id"] == "function:shop.main.build_service"
    assert context["symbols"][0]["evidence"]["line"] == 5


def test_reads_hash_verified_file_content(tmp_path: Path) -> None:
    inventory = build_inventory(FIXTURE)
    database = tmp_path / "tiny.sqlite"
    create_database(database, inventory)

    assert read_file_content(database, "README.md").startswith("# Tiny Shop")


def test_rejects_context_after_repository_changes(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    readme = repository / "README.md"
    readme.write_text("original", encoding="utf-8")
    database = tmp_path / "tiny.sqlite"
    create_database(database, build_inventory(repository))
    readme.write_text("changed", encoding="utf-8")

    with pytest.raises(ValueError, match="no longer matches"):
        read_repository_brief_context(database)
