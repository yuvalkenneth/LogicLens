# Tiny Shop Codex baseline

This is the first executable LogicLens end-to-end baseline. It compares Codex CLI
with and without LogicLens on the frozen Tiny Shop snapshot.

- LogicLens commit: `3699297`
- Model: `gpt-5.6-sol`
- Repetitions: 5 paired runs (10 total)
- Randomization seed: `20260820`
- Completion: 10/10
- Schema validation: 10/10 run records and answers
- Evidence resolution: 100% of cited source spans and LogicLens references

## Efficiency telemetry

| Condition | Wall time, mean ± SD | Input tokens, mean ± SD | Output tokens, mean ± SD | Tool calls, mean |
| --- | ---: | ---: | ---: | ---: |
| Native | 36.00s ± 2.24s | 46,777 ± 132 | 1,494 ± 82 | 2 |
| LogicLens | 39.95s ± 4.57s | 49,445 ± 64 | 1,523 ± 86 | 2 |

LogicLens indexing averaged 12.2ms ± 2.6ms. The paired mean overhead was 3.95s
and 2,668 input tokens. On this tiny repository, almost all measured overhead came
from the additional indexed context presented to the agent rather than indexing.

## Scoring status

Three context-free LLM subagents independently scored the condition-blind answers.
LogicLens improved relation recall from 0.76 to 0.96, reduced evidence precision
from 1.00 to 0.91, and produced no clear task-success improvement (0.99 versus
1.00). See `scoring/README.md` and `scoring/comparison-result.json` for the complete
results and limitations. The judgments have not received human audit.
