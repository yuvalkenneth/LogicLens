"""Safe standard-library Python extraction for repository mapping."""

from __future__ import annotations

import ast
from collections import Counter
from dataclasses import replace


def analyze(inventory):
    from logiclens.python_modules import ImportRecord, ModuleRecord, PythonStructure
    from logiclens.symbols import SymbolRecord

    paths = {x.path for x in inventory.files if x.category == "source" and x.language == "python"}
    modules = tuple(ModuleRecord(path, *_module_name(path, paths)) for path in sorted(paths))
    duplicate_names = Counter(x.name for x in modules)
    modules = tuple(
        replace(x, name=f"{x.name}@{x.file_path.removesuffix('.py').replace('/', '.')}")
        if duplicate_names[x.name] > 1 else x
        for x in modules
    )
    by_file = {x.file_path: x for x in modules}
    by_name: dict[str, list] = {}
    for module in modules:
        by_name.setdefault(module.name, []).append(module)
    symbols, imports = [], []
    for path in sorted(paths):
        try:
            tree = ast.parse((inventory.source_path / path).read_text(encoding="utf-8"), filename=path)
        except SyntaxError as error:
            raise ValueError(f"Python parser could not parse: {path}") from error
        module = by_file[path]
        for node in tree.body:
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                record = _symbol(node, path, module.name, None, SymbolRecord)
                symbols.append(record)
                if isinstance(node, ast.ClassDef):
                    symbols.extend(_symbol(child, path, module.name, record.qualified_name, SymbolRecord) for child in node.body if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(_import(module, alias.name, _target(alias.name, (), by_name), node, ImportRecord))
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                raw = "." * node.level + node.module
                imports.append(_import(module, raw, _target(_resolve(module, raw), tuple(x.name for x in node.names), by_name), node, ImportRecord))
    duplicates = Counter((x.file_path, x.qualified_name) for x in symbols)
    symbols = [
        replace(x, qualified_name=f"{x.qualified_name}@L{x.start_line}")
        if duplicates[(x.file_path, x.qualified_name)] > 1 else x
        for x in symbols
    ]
    symbols.sort(key=lambda x: (x.file_path, x.start_line, x.start_column))
    imports.sort(key=lambda x: (x.source_file_path, x.start_line, x.start_column, x.imported_name))
    return PythonStructure(modules, tuple(imports), tuple(symbols))


def _module_name(path, paths):
    from pathlib import PurePosixPath
    item = PurePosixPath(path); parents = item.parent.parts; start = len(parents)
    for i in range(len(parents) - 1, -1, -1):
        if PurePosixPath(*parents[:i + 1], "__init__.py").as_posix() not in paths: break
        start = i
    parts = list(parents[start:])
    return ((".".join(parts) or item.parent.name), "package") if item.name == "__init__.py" else (".".join([*parts, item.stem]), "module")


def _symbol(node, path, module, parent, SymbolRecord):
    decorators = getattr(node, "decorator_list", [])
    first = min(decorators, key=lambda x: (x.lineno, x.col_offset), default=node)
    signature = None if isinstance(node, ast.ClassDef) else f"{node.name}({ast.unparse(node.args)})" + (f" -> {ast.unparse(node.returns)}" if node.returns else "")
    return SymbolRecord(path, ".".join(x for x in (parent or module, node.name) if x), node.name, "class" if isinstance(node, ast.ClassDef) else "method" if parent else "function", parent, signature, ast.get_docstring(node, clean=False), first.lineno, first.col_offset + 1, node.end_lineno or node.lineno, (node.end_col_offset or node.col_offset) + 1)


def _resolve(module, name):
    if not name.startswith("."): return name
    count = len(name) - len(name.lstrip(".")); rest = name[count:]
    parts = module.name.split(".") if module.kind == "package" else module.name.split(".")[:-1]
    parts = parts[:max(0, len(parts) - (count - 1))]
    return ".".join([*parts, *rest.split(".")] if rest else parts)


def _target(base, names, by_name):
    for candidate in [*(f"{base}.{x}" for x in names if base), base]:
        found = by_name.get(candidate, [])
        if len(found) == 1: return found[0].file_path
    return None


def _import(module, name, target, node, ImportRecord):
    return ImportRecord(module.file_path, name, target, node.lineno, node.col_offset + 1, node.end_lineno or node.lineno, (node.end_col_offset or node.col_offset) + 1)
