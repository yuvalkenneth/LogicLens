# Product vision

## Primary user

A developer encountering an unfamiliar repository who needs to become productive
quickly and safely.

## Promise

Given a repository snapshot, LogicLens should produce an evidence-backed explanation
of what the repository is, how it is organized, where execution begins, and how its
important flows work. The developer can then explore the map and ask increasingly
specific questions.

## User experience

1. The user provides a GitHub repository.
2. LogicLens analyzes one immutable snapshot.
3. The repository mapping is persisted.
4. A repository briefing explains the system at a high level.
5. Relevant structure, entry points, and flows are visualized.
6. The user can navigate evidence or ask follow-up questions.
7. Deferred sources are analyzed only when a question requires them.

## Product principle

Deterministic components extract and resolve what the repository demonstrates.
Agents decide what evidence matters, identify missing context, form explicitly
labeled interpretations, and communicate the result.

An agent conclusion must never silently become a deterministic fact.

