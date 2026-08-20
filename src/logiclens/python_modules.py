"""Python module and import extraction backed by Tree-sitter."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from tree_sitter import Language, Node, Parser
import tree_sitter_python

from logiclens.inventory import Inventory


PYTHON_LANGUAGE = Language(tree_sitter_python.language())


@dataclass(frozen=True)
class ModuleRecord:
    file_path: str
    name: str
    kind: str


@dataclass(frozen=True)
class ImportRecord:
    source_file_path: str
    imported_name: str
    target_file_path: str | None
    start_line: int
    start_column: int
    end_line: int
    end_column: int


@dataclass(frozen=True)
class PythonStructure:
    modules: tuple[ModuleRecord, ...]
    imports: tuple[ImportRecord, ...]


def _module_name(file_path: str, python_paths: set[str]) -> tuple[str, str]:
    path = PurePosixPath(file_path)
    parent_parts = path.parent.parts
    package_start = len(parent_parts)

    for index in range(len(parent_parts) - 1, -1, -1):
        package_init = PurePosixPath(*parent_parts[: index + 1], "__init__.py")
        if package_init.as_posix() not in python_paths:
            break
        package_start = index

    package_parts = list(parent_parts[package_start:])
    if path.name == "__init__.py":
        if package_parts:
            return ".".join(package_parts), "package"
        return path.parent.name, "package"

    return ".".join([*package_parts, path.stem]), "module"


def _node_text(node: Node, source: bytes) -> str:
    return source[node.start_byte : node.end_byte].decode("utf-8")


def _walk(node: Node):
    yield node
    for child in node.children:
        yield from _walk(child)


def _imported_modules(node: Node, source: bytes) -> tuple[str, ...]:
    modules: list[str] = []
    for child in node.named_children:
        if child.type == "dotted_name":
            modules.append(_node_text(child, source))
        elif child.type == "aliased_import" and child.named_children:
            modules.append(_node_text(child.named_children[0], source))
    return tuple(modules)


def _from_import_names(node: Node, source: bytes) -> tuple[str, ...]:
    names: list[str] = []
    module_node = node.child_by_field_name("module_name")
    for child in node.named_children:
        if child == module_node:
            continue
        if child.type == "dotted_name":
            names.append(_node_text(child, source))
        elif child.type == "aliased_import" and child.named_children:
            names.append(_node_text(child.named_children[0], source))
    return tuple(names)


def _resolve_from_module(source_module: ModuleRecord, imported_name: str) -> str:
    if not imported_name.startswith("."):
        return imported_name

    dot_count = len(imported_name) - len(imported_name.lstrip("."))
    remainder = imported_name[dot_count:]
    source_parts = source_module.name.split(".")
    package_parts = (
        source_parts if source_module.kind == "package" else source_parts[:-1]
    )
    keep = max(0, len(package_parts) - (dot_count - 1))
    resolved_parts = package_parts[:keep]
    if remainder:
        resolved_parts.extend(remainder.split("."))
    return ".".join(resolved_parts)


def _target_file(
    base_name: str,
    imported_names: tuple[str, ...],
    modules_by_name: dict[str, list[ModuleRecord]],
) -> str | None:
    candidates = [f"{base_name}.{name}" for name in imported_names if base_name]
    candidates.append(base_name)
    for candidate in candidates:
        matches = modules_by_name.get(candidate, [])
        if len(matches) == 1:
            return matches[0].file_path
    return None


def analyze_python_modules(inventory: Inventory) -> PythonStructure:
    python_paths = {
        record.path
        for record in inventory.files
        if record.category == "source" and record.language == "python"
    }
    modules = tuple(
        ModuleRecord(path, *_module_name(path, python_paths))
        for path in sorted(python_paths)
    )
    modules_by_file = {module.file_path: module for module in modules}
    modules_by_name: dict[str, list[ModuleRecord]] = {}
    for module in modules:
        modules_by_name.setdefault(module.name, []).append(module)

    parser = Parser(PYTHON_LANGUAGE)
    imports: list[ImportRecord] = []
    for file_path in sorted(python_paths):
        source = (inventory.source_path / file_path).read_bytes()
        tree = parser.parse(source)
        if tree.root_node.has_error:
            raise ValueError(f"Tree-sitter could not parse Python file: {file_path}")

        source_module = modules_by_file[file_path]
        for node in _walk(tree.root_node):
            imported_name: str | None = None
            target_file_path: str | None = None

            if node.type == "import_statement":
                imported_modules = _imported_modules(node, source)
                for module_name in imported_modules:
                    target_file_path = _target_file(
                        module_name, (), modules_by_name
                    )
                    imports.append(
                        _record_import(
                            source_module,
                            module_name,
                            target_file_path,
                            node,
                        )
                    )
                continue

            if node.type == "import_from_statement":
                module_node = node.child_by_field_name("module_name")
                if module_node is None:
                    continue
                imported_name = _node_text(module_node, source)
                resolved_name = _resolve_from_module(source_module, imported_name)
                imported_names = _from_import_names(node, source)
                target_file_path = _target_file(
                    resolved_name, imported_names, modules_by_name
                )

            if imported_name is not None:
                imports.append(
                    _record_import(
                        source_module,
                        imported_name,
                        target_file_path,
                        node,
                    )
                )

    imports.sort(
        key=lambda record: (
            record.source_file_path,
            record.start_line,
            record.start_column,
            record.imported_name,
        )
    )
    return PythonStructure(modules, tuple(imports))


def _record_import(
    source_module: ModuleRecord,
    imported_name: str,
    target_file_path: str | None,
    node: Node,
) -> ImportRecord:
    return ImportRecord(
        source_file_path=source_module.file_path,
        imported_name=imported_name,
        target_file_path=target_file_path,
        start_line=node.start_point.row + 1,
        start_column=node.start_point.column + 1,
        end_line=node.end_point.row + 1,
        end_column=node.end_point.column + 1,
    )
