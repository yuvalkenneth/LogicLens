from pathlib import Path
import sqlite3

import pytest

from logiclens.database import create_database, read_files, read_imports, read_modules
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
