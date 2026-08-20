"""Language-neutral source symbol records."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SymbolRecord:
    file_path: str
    qualified_name: str
    name: str
    kind: str
    parent_qualified_name: str | None
    signature: str | None
    docstring: str | None
    start_line: int
    start_column: int
    end_line: int
    end_column: int
