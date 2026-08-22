# Experiment 002: CodeGraph deterministic-backend spike

## Decision

Use CodeGraph as the first **optional deterministic backend** for LogicLens.
LogicLens will not replace or modify its graph. It will ask it for bounded,
current-snapshot evidence, then agents will produce and audit interpretations
in a separate layer.

This is a capability contract, not a permanent dependency decision. A future
backend may satisfy the same contract.

## What we tested

On 2026-08-22, CodeGraph `1.5.0` indexed a shallow checkout of Flask at
snapshot `d318b683471101618febed18996405ad26462110`.

| Observation | Result |
| --- | --- |
| Index | 91 files, 2,705 nodes, 5,171 edges in 959 ms |
| Storage | Local `.codegraph/codegraph.db`; 4.95 MB |
| Static entities | files, classes, functions/methods, imports, variables, routes |
| Source lookup | `Flask.wsgi_app` resolved to `src/flask/app.py:1569` with source and static callees |
| Call graph | `wsgi_app` had five reported direct callees; `full_dispatch_request` had `wsgi_app` as a reported caller |
| Impact | depth-2 impact for `Flask.wsgi_app` reported `wsgi_app` and its `__call__` caller |
| Routes | route nodes were queryable, including method, path, file, and line span |

The index is a snapshot of the checked-out files only. No repository history,
issues, pull requests, releases, or contributor data were included.

## Backend contract for Phase 1

The agent workflow needs a small set of evidence-producing operations:

| Operation | Required response | Intended agent use |
| --- | --- | --- |
| `search_symbols` | matching symbols with kind, qualified name, path, and line span | find candidate entry points and components |
| `get_symbol` | symbol metadata, source span, and known relations | support a specific claim |
| `get_callers` / `get_callees` | directed static relations, each resolvable to a source span | trace a flow or answer impact questions |
| `search_routes` | method/path plus linked source location when available | identify HTTP entry points |
| `get_impact` | bounded, directed graph neighborhood and traversal depth | answer change-scope questions |
| `explore` | source-backed candidates and call paths for a question | orient the guide agent; never treated as a final answer |

Every result passed to an agent must carry:

```json
{
  "snapshot_id": "content hash or VCS commit",
  "backend": "codegraph",
  "source": {"path": "src/flask/app.py", "start_line": 1569, "end_line": 1620},
  "relation": {"kind": "calls", "from": "Flask.wsgi_app", "to": "Flask.full_dispatch_request"}
}
```

Fields that do not apply are omitted. A backend must represent an unresolved
name, ambiguous match, and unavailable relation explicitly; it must not invent
a result.

## The boundary

CodeGraph can establish structural facts: a symbol exists at a source span, a
route was statically detected, or a static edge was found. It cannot by itself
establish that a component is the *main business workflow*, why a design exists,
or that a statically unresolved path is impossible.

LogicLens is responsible for those interpretations. Its agents must:

1. cite the exact evidence supporting each substantive claim;
2. say when a claim is an inference rather than a graph fact;
3. preserve uncertainty when the graph is partial or ambiguous; and
4. have an independent auditor reject unsupported claims before the user sees a
   repository brief or answer.

## Consequence for implementation

Do **not** integrate CodeGraph into the CLI yet. Phase 1 is to define the guide
and auditor contracts, their shared state, evidence rules, and test cases
against this interface. Only then build a thin CodeGraph adapter and a reference
LangGraph workflow.

## Open questions to test next

- Accuracy and coverage across a small, diverse corpus (Python, TypeScript,
  and Go), especially route-to-handler edges and dynamic dispatch.
- Whether CodeGraph's JSON output exposes all source spans needed for auditable
  citations.
- Whether installation/indexing is robust enough for the eventual local and
  hosted deployment paths.
- The measurable difference between native agent, graph-only agent, and
  LogicLens guide-plus-auditor agent under the same question.
