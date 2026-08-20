# Tiny Shop same-prompt, skill-available baseline

This paired evaluation compares a native Codex run with a run where the same Codex
session can discover and invoke the local LogicLens skill. The prompt and answer
schema are byte-identical across conditions; both use a writable temporary workspace
and must not modify source files.

- LogicLens commit: `0bb156f4fd5c8ebb9fc20975bd346026274e8a45`
- Model: `gpt-5.6-sol`
- Repetitions: 5 paired runs (10 total)
- Randomization seed: `20260820`
- Completion: 10/10
- Schema validation: 10/10 run records and answers
- Evidence resolution: 100% of cited source spans

## Results

Three condition-blind LLM scorers found that LogicLens skill availability improved
relation recall from 0.66 to 0.92 (paired delta +0.26, 95% CI +0.018 to +0.502).
Both conditions recovered every required fact. LogicLens was invoked in 4/5 treatment
runs and added 17.66 seconds and 49,581 input tokens on average. See
`scoring/README.md` and `scoring/comparison-result.json` for methodology, the complete
metrics, and limitations. These judgments have not received human audit.
