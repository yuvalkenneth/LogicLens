"""Deterministic file inventory for a repository snapshot."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import os
from pathlib import Path


IGNORED_DIRECTORIES = {
    ".git",
    ".logiclens",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "node_modules",
}

SOURCE_LANGUAGES = {
    ".c": "c",
    ".cpp": "cpp",
    ".cs": "csharp",
    ".go": "go",
    ".java": "java",
    ".js": "javascript",
    ".jsx": "javascript",
    ".kt": "kotlin",
    ".php": "php",
    ".py": "python",
    ".rb": "ruby",
    ".rs": "rust",
    ".swift": "swift",
    ".ts": "typescript",
    ".tsx": "typescript",
}

DOCUMENTATION_LANGUAGES = {
    ".adoc": "asciidoc",
    ".md": "markdown",
    ".mdx": "mdx",
    ".rst": "restructuredtext",
    ".txt": "text",
}

MANIFEST_NAMES = {
    "Cargo.toml": "toml",
    "Gemfile": "ruby",
    "go.mod": "gomod",
    "package.json": "json",
    "pom.xml": "xml",
    "pyproject.toml": "toml",
    "requirements.txt": "requirements",
}


@dataclass(frozen=True)
class FileRecord:
    path: str
    category: str
    language: str | None
    content_hash: str
    size_bytes: int


@dataclass(frozen=True)
class Inventory:
    source_path: Path
    snapshot_hash: str
    files: tuple[FileRecord, ...]


def classify_file(path: Path) -> tuple[str, str | None]:
    if path.name in MANIFEST_NAMES:
        return "manifest", MANIFEST_NAMES[path.name]

    suffix = path.suffix.lower()
    if suffix in SOURCE_LANGUAGES:
        return "source", SOURCE_LANGUAGES[suffix]
    if suffix in DOCUMENTATION_LANGUAGES:
        return "documentation", DOCUMENTATION_LANGUAGES[suffix]
    return "other", None


def build_inventory(source_path: Path) -> Inventory:
    root = source_path.expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"Repository path is not a directory: {root}")

    records: list[FileRecord] = []
    for current_directory, directory_names, file_names in os.walk(root):
        directory_names[:] = sorted(
            name for name in directory_names if name not in IGNORED_DIRECTORIES
        )

        current_path = Path(current_directory)
        for file_name in sorted(file_names):
            absolute_path = current_path / file_name
            if absolute_path.is_symlink() or not absolute_path.is_file():
                continue

            content = absolute_path.read_bytes()
            relative_path = absolute_path.relative_to(root).as_posix()
            category, language = classify_file(absolute_path)
            records.append(
                FileRecord(
                    path=relative_path,
                    category=category,
                    language=language,
                    content_hash=sha256(content).hexdigest(),
                    size_bytes=len(content),
                )
            )

    records.sort(key=lambda record: record.path)
    snapshot = sha256()
    for record in records:
        snapshot.update(record.path.encode("utf-8"))
        snapshot.update(b"\0")
        snapshot.update(record.content_hash.encode("ascii"))
        snapshot.update(b"\n")

    return Inventory(root, snapshot.hexdigest(), tuple(records))
