from hashlib import sha256
from pathlib import Path

from logiclens.inventory import build_inventory, classify_file


FIXTURE = Path(__file__).parent / "fixtures" / "tiny_python"


def test_inventory_is_sorted_and_classified() -> None:
    inventory = build_inventory(FIXTURE)

    assert [record.path for record in inventory.files] == [
        "README.md",
        "pyproject.toml",
        "src/shop/__init__.py",
        "src/shop/main.py",
        "src/shop/repository.py",
        "src/shop/service.py",
    ]
    assert [record.category for record in inventory.files] == [
        "documentation",
        "manifest",
        "source",
        "source",
        "source",
        "source",
    ]


def test_inventory_hash_is_repeatable() -> None:
    first = build_inventory(FIXTURE)
    second = build_inventory(FIXTURE)

    assert first.snapshot_hash == second.snapshot_hash
    assert first.files == second.files


def test_file_hash_uses_file_bytes() -> None:
    inventory = build_inventory(FIXTURE)
    readme = inventory.files[0]

    assert readme.content_hash == sha256((FIXTURE / "README.md").read_bytes()).hexdigest()


def test_classify_unknown_file() -> None:
    assert classify_file(Path("diagram.png")) == ("other", None)
