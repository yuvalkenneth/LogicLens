PRAGMA foreign_keys = ON;

CREATE TABLE metadata (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    source_path TEXT NOT NULL,
    snapshot_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE files (
    id INTEGER PRIMARY KEY,
    path TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL CHECK (
        category IN ('source', 'manifest', 'documentation', 'other')
    ),
    language TEXT,
    content_hash TEXT NOT NULL,
    size_bytes INTEGER NOT NULL CHECK (size_bytes >= 0)
);

CREATE INDEX files_category_index ON files (category);

CREATE TABLE modules (
    id INTEGER PRIMARY KEY,
    file_id INTEGER NOT NULL UNIQUE REFERENCES files (id),
    name TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('package', 'module'))
);

CREATE INDEX modules_name_index ON modules (name);

CREATE TABLE imports (
    id INTEGER PRIMARY KEY,
    source_module_id INTEGER NOT NULL REFERENCES modules (id),
    imported_name TEXT NOT NULL,
    target_module_id INTEGER REFERENCES modules (id),
    start_line INTEGER NOT NULL,
    start_column INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    end_column INTEGER NOT NULL
);

CREATE INDEX imports_source_index ON imports (source_module_id);
CREATE INDEX imports_target_index ON imports (target_module_id);
