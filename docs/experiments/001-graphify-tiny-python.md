# Experiment 001: Graphify on the tiny Python fixture

## Question

How much of the selected LogicLens golden graph can Graphify's local, code-only
extractor recover without an LLM?

## Setup

- Graphify version: `0.9.43`
- Input: `tests/fixtures/tiny_python`
- Mode: code-only, no clustering, one AST worker
- Comparison target: `tests/expected/tiny_python.graph.json`
- Two clean runs wrote to separate temporary output directories.

The command shape was:

```text
graphify extract <fixture> --out <temporary-directory> \
  --code-only --no-cluster --max-workers 1
```

## Result

Each run produced 12 nodes and 22 edges. The two `graph.json` files had the
same SHA-256 hash, so this small extraction was byte-for-byte repeatable.

The golden file contains selected facts rather than an exhaustive graph. After
mapping equivalent vocabulary (`contains`/`method` to `DEFINES`, and class
`calls` to `CONSTRUCTS`), Graphify recovered:

- all 9 selected nodes;
- all 6 selected definition relationships;
- both selected constructor relationships;
- the direct `create_order -> build_service` call;
- 9 of the 11 selected relationships overall.

It did not resolve these attribute calls to their method declarations:

- `service.create(...)` to `OrderService.create`;
- `self.repository.save(...)` to `OrderRepository.save`.

## Important differences from the LogicLens contract

1. Graphify emits useful additional nodes and edges, including imports, an
   `__init__` method, `uses` edges, and a module-docstring rationale node.
2. Its evidence points to a source file and a single line. The LogicLens golden
   contract records exact start and end positions.
3. Graphify labels constructor calls as `calls`. LogicLens currently separates
   `CONSTRUCTS` from `CALLS`.
4. Graphify marks directly extracted call edges as `EXTRACTED`, including calls
   whose target was resolved across files. LogicLens separates the fact that a
   call expression exists from the resolution of its target by using
   `origin: RESOLVED`.
5. In code-only mode, the fixture README was intentionally skipped. The package
   manifest was scanned but produced no nodes, confirming that manifests need a
   dedicated deterministic extractor in LogicLens.

## Design lesson

Graphify is a strong reference and a possible downstream input, but its graph
should not become LogicLens's storage contract unchanged. LogicLens needs a
small canonical schema that preserves exact evidence, distinguishes syntax from
resolution, and allows each extractor to emit graph fragments. An adapter can
then translate Graphify output into that schema where useful.

The next experiment should implement only the narrowest deterministic slice:
inventory files and extract Python declarations with exact spans. It should not
attempt agents, embeddings, persistence infrastructure, or a web service yet.
