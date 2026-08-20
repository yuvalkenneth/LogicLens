# Initial scope

## Repository boundary

LogicLens analyzes the contents of one repository snapshot at one commit. It does not
initially analyze issues, pull requests, releases, contributors, commit history,
runtime telemetry, or external documentation.

Support for analyzing a newer snapshot is intentionally excluded for now.

## Core sources

Always inventory and analyze:

- Authored source code.
- Package manifests.
- Repository documentation.
- API specifications.

## Deferred sources

Inventory but analyze only when a question requires them:

- Tests and fixtures.
- Infrastructure and deployment configuration.
- CI workflows.
- Database migrations and schemas not already represented in the core map.
- Build scripts, task runners, and environment templates.
- Notebooks and structured data files.

Generated code, vendored dependencies, binaries, minified bundles, caches, and build
outputs are inventory-only or excluded. Likely secret-bearing files are never read.

## First technical milestone

Given a local Python repository, map selected files, modules, classes, functions,
imports, direct calls, and resolvable cross-file calls with exact source evidence.

The first milestone does not include:

- An LLM or agent.
- A database.
- A web API or user interface.
- Multiple language adapters.
- Business-flow inference.
- CocoIndex integration.

