# Graphify research plan

Reference: <https://github.com/Graphify-Labs/graphify>

## Purpose

Understand Graphify's actual mapping behavior before deciding whether LogicLens
should consume it, extend it, or recreate a narrow subset for learning.

## Current understanding

Graphify separates file detection, per-file extraction, graph construction,
clustering, analysis, reporting, and export. Code extraction uses Tree-sitter and
produces node-and-edge fragments. Cross-file resolution occurs after local syntax
extraction. The graph is represented with NetworkX and exported as node-link JSON.

## Experiment corpora

1. `tests/fixtures/tiny_python`: completely hand-labeled control corpus.
2. Pallets ItsDangerous at a recorded commit: small real-world corpus.

The external corpus itself should not be committed into LogicLens. Record its URL and
commit SHA so the experiment is reproducible.

## Questions

- Which files does Graphify detect or ignore?
- Which node kinds does it emit for Python?
- How are stable identifiers constructed?
- Which relationships are extracted locally?
- How are imported and member calls resolved across files?
- How is ambiguity represented?
- Are edges directional in the exported graph?
- Are source locations precise enough for evidence-backed explanations?
- How are duplicate entities merged?
- What does it learn from `pyproject.toml`?
- What deterministic knowledge does it extract from documentation?
- Which expected facts are missing or incorrect?
- How much smaller is a relevant subgraph than the source context it replaces?

## Outputs to preserve

- Exact Graphify version.
- Command and options used.
- Repository URL and commit SHA.
- Node, edge, and confidence counts.
- Selected correct, missing, incorrect, and ambiguous relationships.
- Notes about concepts LogicLens should reuse or model differently.

