# EVAL-003 — Untuned Frontier Multimodal Baseline Suite

**Task ID:** EVAL-003  
**Owner:** Overseer  
**Dependencies:** EVAL-001 and EVAL-002 (both validated)  
**Weight:** 1.5 points, only after accepted original baseline evidence  
**Status:** active (tooling/protocol development; actual inference not yet approved)  
**Branch:** `task/EVAL-003-frontier-baselines`  
**Write scope:** `eval/baselines/**`, `docs/evaluation/FRONTIER_BASELINES.md`, `tests/evaluation/test_frontier_baselines.py`, dedicated baseline CI workflow.

## Mission

Establish an untuned, reproducible frontier VLM comparison on a frozen, genuinely independent evaluation set with preserved exact prompts, model IDs/configs, raw outputs, scoring and coverage. EVAL-002's *published third-party leaderboard* is context, **not a newly run Hieratic AI baseline**.

## Required scientific contract

- Freeze dataset benchmark commit/version, item IDs and task/rung subset *before* model results.
- Separate script-ID and isolated-sign baselines from real sequence/transliteration/translation claims; never infer the latter from the former.
- Use official HieraticBench prompting/scoring unchanged for official scores; EVAL-001 project diagnostics are optional and separate.
- Pin actual provider model IDs, effort/config, API route, prompt bytes/hash, response status, sampling/seed handling and environment.
- Store complete raw predictions and failure/retry metadata in an external private artifact store with immutable hashes, not public Git or benchmark-development datasets.
- Preserve all attempted items, including failures/abstentions; prohibit adaptive prompt edits or cherry-picked score averaging.
- Exclude unpublished commissioned/sealed reading content from repository-based local tests, and do not read/score undisclosed answers.
- Report counts, coverage, per-layer scores and group uncertainty. Do not rank models with dissimilar test coverage as though runs were paired.
- A baseline is validated only once actual external inference occurred, score computation was reproduced, benchmark/model rights reviewed, and recorded outputs independently inspected.

## Planned outputs

1. Frozen baseline suite proposal and model-selection/cost decision gate.
2. Explicit, machine-validatable preflight and immutable run-record contract.
3. Offline verification of completed raw-response archives and no missing/duplicate item/attempt keys.
4. Synthetic negative tests and CI.
5. Actual model calls, prompt/prediction artifacts and score reconciliation **after separately approved credentials, budget and frozen item set**.
6. Canonical experiment registry and task progress update **after** final acceptance.

## Non-goals for current iteration

No provider API keys are present or supplied. This implementation must **not** claim to have rerun GPT/Claude/Gemini or reproduce sealed sentence reading, nor commit any benchmark image/gold content. The tooling/protocol PR can be merged while EVAL-003 stays active and earns zero points.
