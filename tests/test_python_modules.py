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


def test_extracts_functions_classes_and_methods() -> None:
    symbols = analyze_python_modules(build_inventory(FIXTURE)).symbols

    assert [
        (
            symbol.qualified_name,
            symbol.kind,
            symbol.parent_qualified_name,
            symbol.signature,
        )
        for symbol in symbols
    ] == [
        (
            "shop.main.build_service",
            "function",
            None,
            "build_service() -> OrderService",
        ),
        (
            "shop.main.create_order",
            "function",
            None,
            "create_order(order_id: str) -> str",
        ),
        ("shop.repository.OrderRepository", "class", None, None),
        (
            "shop.repository.OrderRepository.save",
            "method",
            "shop.repository.OrderRepository",
            "save(self, order_id: str) -> str",
        ),
        ("shop.service.OrderService", "class", None, None),
        (
            "shop.service.OrderService.__init__",
            "method",
            "shop.service.OrderService",
            "__init__(self, repository: OrderRepository) -> None",
        ),
        (
            "shop.service.OrderService.create",
            "method",
            "shop.service.OrderService",
            "create(self, order_id: str) -> str",
        ),
    ]
    assert (symbols[0].start_line, symbols[0].end_line) == (5, 7)


def test_extracts_decorated_symbol_docstrings(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    (repository / "example.py").write_text(
        "@staticmethod\n"
        "def explain(value: str) -> str:\n"
        '    """Return the value."""\n'
        "    return value\n",
        encoding="utf-8",
    )

    symbol = analyze_python_modules(build_inventory(repository)).symbols[0]

    assert symbol.qualified_name == "example.explain"
    assert symbol.signature == "explain(value: str) -> str"
    assert symbol.docstring == "Return the value."
    assert symbol.start_line == 1
