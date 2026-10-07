# Overseer Handoff

Updated: 2026-10-08

## Current verified state

- Goal progress: **8.0 / 100**
- Goal remaining: **92.0**
- Research coverage: **~14%**
- Current capability phase: **P1 — Research Foundation**
- Phase 1 progress: **4.5 / 5 (90%)**
- Control-plane wave: **W0**
- Validated experiments: **0**
- Trained models: **0**
- Last accepted task: **CTRL-002**

## Latest accepted execution work

**CTRL-002 — validated and merged via PR #5.**

Verified capabilities:
- JSON Schema-backed canonical-state validation;
- duplicate/status/dependency/cycle checks;
- phase/task weight and goal-progress reconciliation;
- state-array consistency checks;
- compact overseer context packet generation;
- task-specific context packet generation;
- provider-neutral Python CLI;
- 15 governance tests reported passing after remediation;
- progress/coverage assertions derive from canonical state rather than historical literals.

CTRL-002 is unweighted infrastructure, so verified Hieratic capability remains 4.5/100.

## Work currently happening in parallel

- **CTRL-003 — active with Sonnet**: live dashboard/control-plane shell.
- **CTRL-004 — validated and merged via PR #10**: CI governance checks and PR guardrails.
- **DATA-001 — ready**: machine-readable training-data source registry.
- **EVAL-001 — ready**: evaluation metric specification.
- **EVAL-002 — ready**: external benchmark reproduction.
- **EVAL-004 — ready**: leakage-resistant split design.

## Foundation work already validated

- FND-003 — writing-system/task-decomposition problem map.
- FND-004 — verified prior-art/data registry.
- FND-005 — licensing/provenance policy.

Only **FND-006 (0.5 points)** remains in Phase 1. Its dependency CTRL-004 is now validated, so FND-006 is ready but has not been started.

## Control-plane gate

Validated:
- CTRL-001
- CTRL-002
- CTRL-004

Remaining:
- CTRL-003
- FND-006

Operational gate completion: **3/5 = 60%**.

## Next overseer action

1. Review CTRL-003 as soon as Sonnet returns.
2. Present the next three-lane wave for approval: Luna -> DATA-001; Anti-Gravity (Sonnet) -> continue CTRL-003; Overseer -> EVAL-001.
3. Keep FND-006 ready but unstarted until an overseer-wave approval covers it or the overseer deliberately schedules it.
4. Continue DATA/EVAL work without violating benchmark quarantine or data-rights policy.

## Mandatory review-response rule

Every returned agent task receives:
- verdict;
- checked/unchecked completed and pending items;
- task evidence completion;
- verified goal progress and remaining;
- research coverage;
- phase/gate progress;
- next dependency-aware checklist;
- exact percentage changes.


## Parallel-wave rule

Future waves must include an overseer assignment whenever a high-value dependency-ready task is safe to run alongside the execution agents.

The overseer presents the whole wave first, including its own task, and waits for Mohammed's approval before starting that task.

The preferred overseer work is scientific evaluation design, architecture, source-grounded research, synthesis, or another reasoning-heavy task.

For the next wave, the proposed overseer assignment is EVAL-001: specify evaluation metrics across the reading stack.


## Execution-lane topology

Default parallel work uses three lanes:

- **Luna** — persistent execution lane.
- **Anti-Gravity** — one shared lane using Sonnet or Gemini 3.8 Flash, as Mohammed directs based on limits/availability.
- **Overseer** — heavy-lifting research, architecture, evaluation, synthesis, and review.

Do not schedule Sonnet and Gemini as separate simultaneous lanes unless Mohammed explicitly changes this rule.

A Sonnet ↔ Gemini switch should resume from repository state and the task brief, not from provider memory.


## CTRL-004 acceptance evidence

PR #10 was reviewed against the actual diff and GitHub Actions run 37687240616.

Verified:
- PR and main-push governance workflow;
- read-only contents permission;
- Python 3.12;
- canonical projectctl validation;
- 18 governance tests;
- nonzero failure behavior on invalid fixture;
- evidence-oriented PR template;
- successful GitHub Actions job.

CTRL-004 is unweighted infrastructure, so capability remains 4.5/100.


## Latest accepted overseer work

**EVAL-001 — validated and merged via PR #16.**

The project now has a canonical evaluation contract spanning:
- script/domain ID;
- layout and reading order;
- sign detection/classification and palaeographic retrieval;
- line/sequence HTR;
- standardized hieroglyphic rendering;
- Egyptological transliteration;
- normalization/tokenization;
- lemma and morphology;
- translation/source faithfulness;
- calibration, abstention, and alternative sets;
- generalization strata;
- blind expert evaluation.

Important decisions:
- no primary composite score in v1;
- translation cannot compensate for failed visual reading;
- multiple scholarly readings and illegible spans are first-class;
- document-macro reporting is required for heterogeneous sequence tasks;
- benchmark-specific scores remain separate from project success.

Evidence:
- `docs/evaluation/METRICS_SPEC.md`
- `docs/evaluation/NORMALIZATION_PROFILES.md`
- `docs/evaluation/SCORING_EXAMPLES.md`
- `eval/metric_contract.yaml`

EVAL-001 earns **1.5 capability points**, moving verified goal progress from 4.5 to 6.0.

EVAL-005 is newly ready.


## DATA-001 acceptance

**DATA-001 — validated and merged via PR #15.**

Verified:
- 8-source machine-readable registry;
- canonical rights classes and project review markers;
- explicit training/development/evaluation/redistribution decisions;
- HieraticBench evaluation quarantine;
- DDD non-commercial and per-item constraints;
- AKU-PAL per-item and benchmark-overlap controls;
- TLA no-bulk-scraping restriction;
- unresolved PaPYrus/Isut/HieraticAI image/data rights remain non-approved;
- JSON Schema plus deterministic validator;
- 13 data tests and 18 governance tests reported passing;
- no third-party raw assets were added.

DATA-001 earns **2.0 capability points**, moving verified progress from 6.0 to 8.0.

Newly ready:
- DATA-002
- DATA-004

A minor post-review metadata correction aligns TLA `accessed_at` with the registry's own 2026-10-08 spot-check note.

## Luna work-package sizing

Luna is substantially faster than the overseer lane on bounded engineering tasks. Future Luna dispatches should therefore be **multi-task work packages** when several independent tasks are simultaneously ready.

Rules:
- batch only tasks whose dependencies are already validated at dispatch time;
- preserve one task ID, branch, PR, and evidence package per canonical task unless the overseer explicitly approves another structure;
- Luna may complete all independent tasks in the package before returning;
- no task may start merely because another task in the same package finished if it depends on overseer acceptance of that earlier task;
- avoid overlapping write scopes across the package;
- quality/acceptance criteria remain unchanged.

This is intended to reduce idle time, not relax review.
