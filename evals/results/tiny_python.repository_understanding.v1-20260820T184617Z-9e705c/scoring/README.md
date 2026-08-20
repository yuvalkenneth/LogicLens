# Blind scoring results

Three context-free LLM subagents independently scored all ten answers. They
received only the blind packet, frozen case and source, oracle graph, score schema,
and metric definitions. They did not receive the condition key, run artifacts,
repository history, or conversation context.

All 30 score results validate against `score-result.schema.json`. The comparison
uses the median of the three scorer values for each answer and metric, followed by
paired aggregation across the five repetitions. Confidence intervals are paired
t intervals with four degrees of freedom.

## Quality

| Metric | Native | LogicLens | Paired delta | 95% CI |
| --- | ---: | ---: | ---: | ---: |
| Task success | 0.990 | 1.000 | +0.010 | -0.018 to +0.038 |
| Claim precision | 0.986 | 1.000 | +0.014 | -0.025 to +0.054 |
| Required-fact recall | 1.000 | 1.000 | 0.000 | 0.000 to 0.000 |
| Evidence precision | 1.000 | 0.910 | -0.090 | -0.173 to -0.009 |
| Unsupported-claim rate | 0.000 | 0.000 | 0.000 | 0.000 to 0.000 |
| Correct-abstention rate | 1.000 | 1.000 | 0.000 | 0.000 to 0.000 |
| False-abstention rate | 0.000 | 0.000 | 0.000 | 0.000 to 0.000 |
| Relation precision | 1.000 | 1.000 | 0.000 | 0.000 to 0.000 |
| Relation recall | 0.760 | 0.960 | +0.200 | +0.024 to +0.376 |

The scorers agreed exactly on all claim correctness, fact recall, abstention, and
relation-precision metrics. They disagreed on whether relation recall should use
the five task-relevant `CALLS` edges or all eleven graph edges including `DEFINES`;
the median selects the five-edge interpretation used by two scorers. Evidence
precision had the largest remaining judgment spread because repository-wide
negative claims require broader evidence than a single symbol or module reference.

## Efficiency

| Metric | Native | LogicLens | Paired delta | 95% CI |
| --- | ---: | ---: | ---: | ---: |
| Wall time | 36.00s | 39.95s | +3.95s | -4.17s to +12.07s |
| Input tokens | 46,777 | 49,445 | +2,668 | +2,548 to +2,788 |
| Output tokens | 1,494 | 1,523 | +29 | -113 to +171 |
| Tool calls | 2.0 | 2.0 | 0.0 | 0.0 to 0.0 |

LogicLens indexing itself averaged 12.2ms. The extra cost came from model context,
not from creating the deterministic index.

## Interpretation

On this tiny repository, LogicLens produced more complete business-flow relations
but weaker claim-to-evidence alignment and higher input-token use. It did not show a
clear task-success improvement because native Codex already recovered every required
fact. This result is exploratory until a human audits the scorer judgments.
