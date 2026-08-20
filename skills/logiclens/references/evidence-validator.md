# Evidence Validator

## Purpose

Review a proposed Repository Brief against its bounded context and LogicLens
validation output. Return a corrected brief or a concise rejection reason.

## Checks

1. Every evidence ID exists in the bounded context.
2. Every component member and reading target exists.
3. Candidate entry points identify known symbols; confirmed entry points have
   deterministic execution evidence.
4. Reject flows until LogicLens exposes deterministic call evidence.
5. Documentation claims are described as documented intent when code does not prove them.
6. Unsupported claims are removed or converted into explicit unknowns.
7. Snapshot and brief versions are unchanged.

Do not approve a claim because it sounds plausible. Do not invent replacement evidence.
