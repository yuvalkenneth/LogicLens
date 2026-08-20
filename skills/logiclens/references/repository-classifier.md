# Repository Classifier

## Purpose

Convert one bounded `repository-brief` context into a proposed Repository Brief.
Return JSON conforming to the adjacent `repository-brief.schema.json`; return no
prose outside it.

## Allowed input

- Snapshot ID and file inventory.
- Hash-verified documentation and manifests.
- Module/package inventory.
- Import relationships and their evidence.

Do not read arbitrary repository files. Do not infer function behavior from module
names alone.

## Required work

1. Describe repository purpose using documentation evidence.
2. Identify technologies using manifests and indexed languages.
3. Propose only components supported by module membership and imports.
4. Recommend a short reading order using known files/modules.
5. Record missing entry-point and function-flow evidence as unknowns.

## Output constraints

- Use `brief_version: "0.1"` and copy the input snapshot ID exactly.
- Use evidence IDs shaped as `file:<path>`, `module:<name>`, and
  `import:<source>-><target>`.
- Leave `entry_points` and `flows` empty unless deterministic evidence supports them.
- Keep confidence between 0 and 1.
- Prefer a supported unknown over an attractive guess.
