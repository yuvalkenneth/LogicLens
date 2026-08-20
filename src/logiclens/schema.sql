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
