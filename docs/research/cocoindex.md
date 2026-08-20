# CocoIndex research plan

Reference: <https://github.com/cocoindex-io/cocoindex>

## Purpose

Learn incremental indexing after the manual mapping pipeline is understood.

## Entry condition

Do not integrate CocoIndex until LogicLens can express and test this transformation:

```text
repository file -> validated extraction fragment -> normalized graph records
```

## Questions

- What should be the processing-component boundary: repository, file, or fragment?
- Which stable component key should own each target record?
- How does CocoIndex detect transformation-code changes?
- How are failed components isolated?
- How is lineage surfaced to the application?
- Can a single transformation populate graph and full-text projections cleanly?
- How should on-demand analyzer configuration participate in the source state?
- Which data should remain outside CocoIndex, especially agent claims and human
  decisions?

## Hypothesis

CocoIndex may eventually orchestrate deterministic extraction, memoization, lineage,
and target reconciliation. It should not be the canonical graph schema, graph query
engine, or store for interactive agent claims.

