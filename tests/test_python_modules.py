from pathlib import Path

from logiclens.inventory import build_inventory
from logiclens.python_modules import analyze_python_modules


FIXTURE = Path(__file__).parent / "fixtures" / "tiny_python"


def test_extracts_python_packages_and_modules() -> None:
    structure = analyze_python_modules(build_inventory(FIXTURE))

    assert [(module.name, module.kind) for module in structure.modules] == [
        ("shop", "package"),
        ("shop.main", "module"),
        ("shop.repository", "module"),
        ("shop.service", "module"),
    ]


def test_extracts_and_resolves_relative_imports() -> None:
    structure = analyze_python_modules(build_inventory(FIXTURE))

    assert [
        (
            record.source_file_path,
            record.imported_name,
            record.target_file_path,
            record.start_line,
            record.start_column,
        )
        for record in structure.imports
    ] == [
        (
            "src/shop/main.py",
            ".repository",
            "src/shop/repository.py",
            1,
            1,
        ),
        ("src/shop/main.py", ".service", "src/shop/service.py", 2, 1),
        (
            "src/shop/service.py",
            ".repository",
            "src/shop/repository.py",
            1,
            1,
        ),
    ]


def test_retains_unresolved_external_import(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    (repository / "example.py").write_text("import requests\n", encoding="utf-8")

    structure = analyze_python_modules(build_inventory(repository))

    assert len(structure.imports) == 1
    assert structure.imports[0].imported_name == "requests"
    assert structure.imports[0].target_file_path is None
