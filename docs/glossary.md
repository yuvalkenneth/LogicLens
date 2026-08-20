# Glossary

## Snapshot

The immutable repository contents associated with one commit SHA.

## Inventory

A catalog of files in the snapshot, including their path, category, language, size,
hash, safety classification, and indexing state.

## Mapping

The entities, relationships, and evidence extracted or resolved from the snapshot.

## Entity

A thing represented in the map, such as a file, module, class, function, package,
document section, API operation, or external dependency.

## Relationship

A directed connection between entities, such as `DEFINES`, `IMPORTS`, `CALLS`, or
`INHERITS`.

## Evidence

An exact source span supporting an entity, relationship, or claim.

The initial fixture represents lines as 1-based and inclusive, and columns as 1-based
with an exclusive end column. This mirrors parser-style half-open spans while keeping
displayed positions natural for developers.

## EXTRACTED

Explicitly represented in the source syntax or structured input.

## RESOLVED

Connected deterministically using imports, names, scopes, types, or other resolution
rules.

## AMBIGUOUS

More than one plausible deterministic resolution remains.

## AGENT_INFERRED

A semantic interpretation proposed by an agent and linked to supporting evidence.

## Core indexing

Analysis performed for every snapshot using the mandatory source categories.

## On-demand enrichment

Additional deterministic analysis requested to answer a question about previously
deferred files.
