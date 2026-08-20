# Blind scoring results — same-prompt skill-available baseline

Three context-free LLM subagents independently scored all ten answers. They received
only the blind packet, frozen case and source, oracle graph, score schema, and metric
definitions. They did not receive the condition key, run artifacts, repository
history, or conversation context.

All 30 score results validate against `score-result.schema.json`. The comparison uses
the median of the three scorer values for each answer and metric, then paired
aggregation across five repetitions. Confidence intervals are paired t intervals
with four degrees of freedom.

## Quality

| Metric | Native | LogicLens skill available | Paired delta | 95% CI |
| --- | ---: | ---: | ---: | ---: |
| Task success | 0.980 | 1.000 | +0.020 | -0.036 to +0.076 |
| Claim precision | 0.971 | 1.000 | +0.029 | -0.051 to +0.108 |
| Required-fact recall | 1.000 | 1.000 | 0.000 | 0.000 to 0.000 |
| Evidence precision | 0.986 | 1.000 | +0.014 | -0.025 to +0.054 |
| Unsupported-claim rate | 0.000 | 0.000 | 0.000 | 0.000 to 0.000 |
| Correct-abstention rate | 1.000 | 1.000 | 0.000 | 0.000 to 0.000 |
| False-abstention rate | 0.000 | 0.000 | 0.000 | 0.000 to 0.000 |
| Relation precision | 0.955 | 1.000 | +0.045 | -0.032 to +0.122 |
| Relation recall | 0.660 | 0.920 | +0.260 | +0.018 to +0.502 |

The scorers agreed on the practical interpretation of relation recall: the five
task-relevant `CALLS` edges, not every graph edge including `DEFINES`. One native
answer mistakenly identified `OrderService.create` as the business entry point;
LogicLens answers did not make that error.

## Efficiency and adoption

| Metric | Native | LogicLens skill available | Paired delta | 95% CI |
| --- | ---: | ---: | ---: | ---: |
| Wall time | 37.42s | 55.09s | +17.66s | +12.72s to +22.60s |
| Input tokens | 47,417 | 96,998 | +49,581 | +37,390 to +61,773 |
| Output tokens | 1,568 | 2,229 | +661 | +470 to +852 |
| Tool calls | 2.0 | 4.6 | +2.6 | +1.9 to +3.3 |

LogicLens was actually invoked in 4 of 5 treatment runs. One treatment run discovered
the skill but did not execute its CLI; it remains included, as it should in an
availability-only evaluation. Isolated indexing duration is unavailable from the
Codex event trace, so it is recorded as `null` rather than inferred from total time.

## Interpretation

This is a fairer product-shaped comparison than the earlier injected-context
experiment: the user task, required source-span answer format, model, sandbox, and
repository snapshot are identical. Only the treatment workspace contains the local
LogicLens skill and CLI. On this small repository, skill availability improved
business-flow relation recall, but added substantial model-context and tool-use cost.
The judgments are exploratory until a human audits them.
