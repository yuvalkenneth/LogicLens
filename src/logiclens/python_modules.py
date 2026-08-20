"""Python module and import extraction backed by Tree-sitter."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from tree_sitter import Language, Node, Parser
import tree_sitter_python

from logiclens.inventory import Inventory
from logiclens.symbols import SymbolRecord


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
    symbols: tuple[SymbolRecord, ...]


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


def _definition(node: Node) -> tuple[Node, Node] | None:
    if node.type in {"class_definition", "function_definition"}:
        return node, node
    if node.type == "decorated_definition":
        for child in node.named_children:
            if child.type in {"class_definition", "function_definition"}:
                return child, node
    return None


def _docstring(definition: Node, source: bytes) -> str | None:
    body = definition.child_by_field_name("body")
    if body is None or not body.named_children:
        return None
    statement = body.named_children[0]
    if statement.type != "expression_statement" or not statement.named_children:
        return None
    value = statement.named_children[0]
    if value.type not in {"string", "concatenated_string"}:
        return None
    try:
        parsed = ast.literal_eval(_node_text(value, source))
    except (SyntaxError, ValueError):
        return None
    return parsed if isinstance(parsed, str) else None


def _signature(definition: Node, source: bytes) -> str | None:
    if definition.type != "function_definition":
        return None
    name = definition.child_by_field_name("name")
    parameters = definition.child_by_field_name("parameters")
    if name is None or parameters is None:
        return None
    signature = f"{_node_text(name, source)}{_node_text(parameters, source)}"
    return_type = definition.child_by_field_name("return_type")
    if return_type is not None:
        signature += f" -> {_node_text(return_type, source)}"
    return signature


def _symbol_record(
    node: Node,
    definition: Node,
    source: bytes,
    file_path: str,
    module_name: str,
    parent_qualified_name: str | None = None,
) -> SymbolRecord:
    name_node = definition.child_by_field_name("name")
    if name_node is None:
        raise ValueError(f"Unnamed Python definition in: {file_path}")
    name = _node_text(name_node, source)
    qualified_name = ".".join(
        part for part in (parent_qualified_name or module_name, name) if part
    )
    kind = (
        "class"
        if definition.type == "class_definition"
        else "method" if parent_qualified_name else "function"
    )
    return SymbolRecord(
        file_path=file_path,
        qualified_name=qualified_name,
        name=name,
        kind=kind,
        parent_qualified_name=parent_qualified_name,
        signature=_signature(definition, source),
        docstring=_docstring(definition, source),
        start_line=node.start_point.row + 1,
        start_column=node.start_point.column + 1,
        end_line=node.end_point.row + 1,
        end_column=node.end_point.column + 1,
    )


def _extract_symbols(
    root: Node, source: bytes, file_path: str, module_name: str
) -> list[SymbolRecord]:
    symbols: list[SymbolRecord] = []
    for node in root.named_children:
        match = _definition(node)
        if match is None:
            continue
        definition, evidence_node = match
        symbol = _symbol_record(
            evidence_node, definition, source, file_path, module_name
        )
        symbols.append(symbol)
        if definition.type != "class_definition":
            continue
        body = definition.child_by_field_name("body")
        if body is None:
            continue
        for member in body.named_children:
            member_match = _definition(member)
            if member_match is None or member_match[0].type != "function_definition":
                continue
            member_definition, member_evidence_node = member_match
            symbols.append(
                _symbol_record(
                    member_evidence_node,
                    member_definition,
                    source,
                    file_path,
                    module_name,
                    symbol.qualified_name,
                )
            )
    return symbols


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
    symbols: list[SymbolRecord] = []
    for file_path in sorted(python_paths):
        source = (inventory.source_path / file_path).read_bytes()
        tree = parser.parse(source)
        if tree.root_node.has_error:
            raise ValueError(f"Tree-sitter could not parse Python file: {file_path}")

        source_module = modules_by_file[file_path]
        symbols.extend(
            _extract_symbols(tree.root_node, source, file_path, source_module.name)
        )
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
    symbols.sort(
        key=lambda record: (
            record.file_path,
            record.start_line,
            record.start_column,
        )
    )
    return PythonStructure(modules, tuple(imports), tuple(symbols))


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
