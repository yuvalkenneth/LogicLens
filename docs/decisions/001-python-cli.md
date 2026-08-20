# ADR 001: Start as a Python CLI

- Status: proposed

## Context

The first goal is to understand repository mapping, not web application development.
Both Graphify and CocoIndex expose Python interfaces, and Python has mature Tree-sitter
bindings and graph tooling.

## Decision

Begin with Python 3.12+, `uv`, and a local command-line workflow. Do not add a web API,
frontend, hosted database, or agent runtime during the mapping-laboratory phase.

## Consequences

The mapping pipeline remains inspectable and quick to test. A service boundary and UI
will be designed only after local graph queries are useful.

