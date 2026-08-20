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

The project is in its mapping-laboratory phase. There is deliberately no mapper,
agent, database, API, or user interface yet. The first task is to define and verify
the mapping contract using a tiny repository whose correct graph can be inspected by
hand.

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

