# Evaluation contract 0.1

## Goal

LogicLens must be evaluated as a reliability intervention, not as a demo. The
benchmark compares the same coding harness with and without LogicLens and also tests
each LogicLens agent role independently.

The primary question is:

> Does LogicLens improve factual correctness, evidence quality, abstention, and
> consistency without unacceptable cost?

## Contract artifacts

Every artifact uses `contract_version: "0.1"` and validates against one schema in
`evals/schemas`.

| Artifact | Purpose |
| --- | --- |
| `eval-case` | Immutable task, agent-visible input, withheld oracle, and protocol |
| `answer` | Harness-neutral end-to-end answer made of claims and relations |
| `run-result` | One execution, its exact environment, output, usage, and timing |
| `score-result` | Auditable claim, relation, decision, and metric judgments |
| `comparison-result` | Paired native-versus-LogicLens aggregate |
| `harness-adapter` | Capabilities and identity of one harness integration |

Role evaluations may name their own output schema. End-to-end repository tasks use
`answer.schema.json`.

## Case isolation

An evaluation case has four sections:

- `target`: an individual role or the end-to-end workflow.
- `repository`: the immutable local fixture and its LogicLens snapshot ID.
- `agent_input`: the only case data an adapter may reveal to the agent.
- `oracle`: gold facts, expected unknowns or decisions, and graph references.

Adapters MUST NOT expose `oracle` or protocol metadata to the agent. A runner should
materialize only `agent_input` in the agent workspace. Gold artifacts must live
outside that workspace or be access-controlled by the runner.

## Evaluation targets

`target.kind: "role"` evaluates one frozen role definition with frozen input. Each
role case declares the role file and its output schema. Initial roles are:

- `repository_classifier`: fact coverage and unsupported-claim rate.
- `evidence_validator`: false-accept and false-reject rates on seeded claims.
- `flow_mapper`: relation precision and recall once deterministic calls exist.
- `question_answerer`: correctness, evidence, and abstention for bounded questions.
- `orchestrator`: stage selection, recovery from rejected output, and stopping.

`target.kind: "end_to_end"` evaluates the user experience through a coding harness.

## Paired protocol

Each end-to-end case runs both required conditions:

- `native`: LogicLens is unavailable; the harness uses its normal repository tools.
- `logiclens`: the LogicLens skill and CLI are available to the harness. The user
  question and answer schema remain identical; the harness chooses whether to invoke
  LogicLens. Targeted source reads are allowed and counted.

A valid pair holds these values constant:

- Repository snapshot and task turns.
- Harness and harness version.
- Model and model configuration, for the controlled-model track.
- Time and token budgets.
- Network and repository-history access.
- Repetition number.

Each run starts in a clean copy of the same snapshot. Condition order should be
randomized. Report at least three repetitions; five is the default. Never reuse
conversation state between conditions.

Each run records `sequence_index`, so condition randomization can be audited rather
than merely asserted.

Two reporting tracks are valid:

1. `controlled_model`: the same model and model configuration across conditions and,
   where supported, across harnesses.
2. `native_default`: each harness uses its recommended default setup.

Never merge these tracks into one unexplained score.

## Harness adapter boundary

An adapter translates the shared case into a harness invocation and emits a standard
run result. It may add only formatting needed to request the declared output schema.
Any added prompt text must be captured in `environment.prompt_wrapper`.

Adapters for Codex, Claude Code, Pi, or another harness must:

1. Prepare a clean repository snapshot.
2. Apply the selected condition without changing the task.
3. Invoke the requested model/configuration when supported.
4. Capture the raw answer, structured output, tool trace, timing, and available usage.
5. Record missing telemetry as `null`, never as zero.

The contract does not prescribe a specific agent framework or harness CLI.

## Answer contract

End-to-end answers contain one result per task turn. Each result separates:

- `confirmed` claims supported directly by repository evidence.
- `inferred` interpretations with supporting evidence and lower certainty.
- `unknown` statements where the available snapshot cannot support an answer.
- Directed relations used to describe dependencies or flows.

Evidence may be an exact repository span or a LogicLens evidence reference. Before
scoring, LogicLens references must resolve back to the evaluated snapshot.

## Scoring

Scoring happens after schema and snapshot validation. Semantic scorers must be blind
to harness and condition. Every claim judgment records matched oracle facts, a
verdict, an evidence verdict, and a rationale. LLM judgments are allowed only through
this structured rubric and should receive human audit during benchmark development.
The scorer records whether it is deterministic, LLM-based, human, or hybrid, plus
its complete model/configuration metadata. Oracle graph edges use the canonical
identifier `<source>|<kind>|<target>` when referenced by a score.

Primary metrics:

- `claim_precision = correct confirmed/inferred claims / scored confirmed/inferred claims`
- `required_fact_recall = covered required gold facts / required gold facts`
- `evidence_precision = claims with valid supporting evidence / claims citing evidence`
- `unsupported_claim_rate = unsupported claims / scored confirmed/inferred claims`
- `correct_abstention_rate = correct unknowns / expected unknowns`
- `false_abstention_rate = answerable gold facts incorrectly labeled unknown / gold facts`
- `relation_precision` and `relation_recall` for dependency or flow edges.
- `decision_precision` and `decision_recall` for verifier/orchestrator role cases.
- `task_success`, the weighted sum of the case's explicit success criteria.

For claim, evidence, and relation calculations, `correct`/`valid` contributes 1,
`partial` contributes 0.5, and `incorrect`/`unsupported`/`invalid`/`missing`
contributes 0. Each score result records one criterion judgment per case criterion;
the criterion weights must sum to 1.

Efficiency telemetry is secondary: input/output tokens, cost, wall time, tool calls,
raw files read, and LogicLens indexing time. Missing telemetry stays `null`.

Run-to-run reliability is reported in the paired aggregate using the mean, standard
deviation, paired delta, and confidence interval for every metric. Do not hide a
regression inside a single combined score. Wrong confident claims and wrongly
resolved relations are more harmful than honest abstentions.

## Session cost

For a one-turn case, LogicLens indexing time is included in the condition wall time.
If the harness cannot isolate that timing from an agent tool trace, it records
`index_wall_ms: null`; it must not record a fabricated zero. A future multi-turn
case reuses one index within that case and reports both total and per-turn cost. It
must never reuse the index across repetitions or conditions.

## First benchmark

`evals/benchmarks/tiny_python/repository-understanding.case.json` is the first paired
case. It asks for repository purpose, entry-point status, the order-creation path,
and a reading order. Its oracle reuses the hand-labeled Tiny Shop graph.

This case is intentionally useful before call resolution: LogicLens should abstain
where its current deterministic evidence is insufficient. Future changes should
improve coverage without increasing unsupported claims.

Run the paired Codex case with:

```console
logiclens eval evals/benchmarks/tiny_python/repository-understanding.case.json \
  --results evals/results --model gpt-5.6-sol
```

The runner creates a fresh, history-free fixture copy for every condition and
repetition. In the LogicLens condition it exposes the repository-local skill and
CLI, but does not pre-index the repository or alter the user prompt. Each session
contains raw Codex events, structured run results, a condition-blind scoring packet,
and a separate private key.

## Versioning

Case, schema, prompt, role, adapter, harness, model, and LogicLens versions are part
of the evidence. Any semantic contract change increments `contract_version`. Gold
changes require review and invalidate comparisons against older case revisions.
