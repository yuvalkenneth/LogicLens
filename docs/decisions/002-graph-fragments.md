# ADR 002: Use validated per-file graph fragments

- Status: proposed

## Context

Repository analysis must support multiple languages and source categories while
preserving exact provenance.

## Decision

Each analyzer should emit a validated fragment containing typed entities, directed
relationships, and evidence. Graph construction and cross-file resolution remain
separate stages.

Initial provenance classes are `EXTRACTED`, `RESOLVED`, and `AMBIGUOUS`.
`AGENT_INFERRED` knowledge will use a separate future claim model.

## Consequences

Analyzers can be tested independently, Graphify output can be adapted into the same
contract, and invalid fragments can fail before corrupting the canonical map.

