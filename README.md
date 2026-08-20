# LogicLens

LogicLens is a learning project about deterministic repository mapping, evidence-backed
codebase understanding, graph indexing, and bounded agent reasoning.

The intended user is a developer opening an unfamiliar repository who wants a clear
answer to:

- What is this repository?
- How is it organized?
- Where does execution begin?
- How do its important parts connect?
- Where should I start reading?

## Current status

The first deterministic vertical slice inventories a local repository into SQLite.
It records relative paths, file classifications, languages, sizes, and content hashes.
There is deliberately no AST extraction, agent, API, or user interface yet.

From the project root:

```bash
uv run logiclens map tests/fixtures/tiny_python --db .logiclens/tiny.sqlite
uv run logiclens files --db .logiclens/tiny.sqlite
uv run logiclens modules --db .logiclens/tiny.sqlite
uv run logiclens context repository-brief --db .logiclens/tiny.sqlite --json
```

`map` reads the repository once, inventories its files, and extracts Python modules
and imports with Tree-sitter. `files` and `modules` read the saved result. `context`
returns hash-verified documentation, manifests, and module structure for the first
agent enrichment. Mapping refuses to overwrite an existing database.

## First experiment

`tests/fixtures/tiny_python` is a controlled Python repository. Its selected expected
nodes, relationships, provenance classes, and source spans are recorded in
`tests/expected/tiny_python.graph.json`.

The experiment will compare that hand-labeled graph with Graphify output before we
decide what LogicLens should reuse or implement.

## Reading order

1. `docs/product-vision.md`
2. `docs/scope.md`
3. `docs/glossary.md`
4. `docs/research/graphify.md`
5. `tests/expected/tiny_python.graph.json`
