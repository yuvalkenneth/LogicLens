---
name: logiclens
description: Map and explain an unfamiliar repository using LogicLens's deterministic index and evidence-backed enrichment workflow. Use when a user invokes LogicLens, asks for repository onboarding, architecture or dependency explanations, reading order, entry points, business flows, or follow-up questions that should be answered from a saved repository map instead of broad raw-code exploration.
---

# LogicLens

Use the host coding agent as the runtime. Use LogicLens CLI output as the factual
substrate; do not present agent interpretation as deterministic fact.

## Initial onboarding

1. From the target repository root, use `.logiclens/index.sqlite`.
2. If the database is absent, run:

   ```text
   logiclens map . --db .logiclens/index.sqlite
   ```

3. Build the bounded input:

   ```text
   logiclens context repository-brief --db .logiclens/index.sqlite --json
   ```

4. Read `references/repository-classifier.md` and
   `references/repository-brief.schema.json` completely.
5. Produce a Repository Brief JSON file at
   `.logiclens/repository-brief.json`. Delegate the classifier role to a subagent
   when supported; otherwise perform it sequentially. Pass only the bounded context
   and role definition.
6. Validate the proposal:

   ```text
   logiclens validate-brief .logiclens/repository-brief.json --db .logiclens/index.sqlite
   ```

7. If validation fails, read `references/evidence-validator.md` completely and
   correct or remove unsupported claims. Never fabricate an evidence reference.
8. Present the accepted brief in plain language. Clearly label unknowns.

## Follow-up questions

Start from `.logiclens/repository-brief.json` and LogicLens query output. Request
the smallest relevant deterministic context. If the index lacks the facts required
to answer, state the gap; do not silently replace indexed investigation with broad
repository exploration.

## Evidence rules

- Cite only identifiers present in the context: `file:...`, `module:...`,
  `function:...`, `class:...`, `method:...`, or `import:source->target`.
- Treat documentation as evidence of documented intent, not proof of runtime behavior.
- Treat unresolved imports and missing entry points as unknowns.
- Keep confirmed facts, candidate interpretations, and unknowns distinct.
- Do not add flows until their transitions can be supported by deterministic calls.
