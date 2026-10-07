# Decision Log

Accepted decisions are append-only in substance. Later decisions may supersede earlier ones, but the historical decision remains visible.

## ADR-0001 — Repository is the canonical project memory

**Status:** Accepted  
**Date:** 2026-10-07

Long-running continuity must not depend on a single AI conversation or provider. Canonical state lives in the public repository. Chats and agent memories are transient views.

## ADR-0002 — Measure capability, not elapsed time

**Status:** Accepted  
**Date:** 2026-10-07

The primary roadmap is a 100-point capability program. Elapsed time may be logged retrospectively but does not define progress.

Only accepted weighted milestones earn goal-progress points. Research coverage is tracked separately.

## ADR-0003 — Overseer/executor separation

**Status:** Accepted  
**Date:** 2026-10-07

The overseer owns research, architecture, decomposition, acceptance criteria, review, and state transitions. Heterogeneous AI agents are primarily execution workers operating from bounded briefs.

This separation is intended to reduce duplicated reasoning, drift, and inconsistent project assumptions.

## ADR-0004 — Parallelism is default when dependency-safe

**Status:** Accepted  
**Date:** 2026-10-07

Independent tasks should run in parallel. Concurrency is restricted when tasks share mutable files, benchmark/test material, canonical schemas, or incompatible interfaces.

Branch/write-scope isolation is preferred over ad-hoc coordination.

## ADR-0005 — Control plane is mandatory but unweighted

**Status:** Accepted  
**Date:** 2026-10-07

The dashboard, context tooling, task graph, and governance automation are essential infrastructure but do not themselves improve Hieratic-reading capability. They are a mandatory Phase-0 gate worth 0 goal-progress points.

## ADR-0006 — Dashboard derives from repository state

**Status:** Accepted  
**Date:** 2026-10-07

The public website/control plane must consume canonical repository state. It must not maintain an independent manually edited project-status database.

## ADR-0007 — Code license does not relicense external research assets

**Status:** Accepted  
**Date:** 2026-10-07

Apache-2.0 covers repository-authored software/documentation unless otherwise stated. External images, datasets, editions, fonts, and model artifacts retain their own terms. Provenance and redistribution rights must be recorded separately.

## ADR-0008 — Every agent review ends with a complete status report

**Status:** Accepted  
**Date:** 2026-10-07

Whenever Mohammed brings back execution-agent feedback or implementation evidence, the overseer must review the actual work and then provide a standardized project status report.

The report must include:
- review verdict;
- verified completed items;
- pending/revision items;
- checked/unchecked acceptance checklist;
- task evidence completion;
- verified goal progress and remaining percentage;
- research coverage;
- current phase progress;
- relevant operational gate progress;
- next dependency-aware checklist;
- explicit statement of which percentages changed.

Operational/task percentages must remain distinct from the 0–100 verified capability score.

The canonical format is `docs/governance/REVIEW_REPORTING_PROTOCOL.md`.


## ADR-0009 — Third-party data is deny-by-default

**Status:** Accepted  
**Date:** 2026-10-07

Public availability is not permission to train, redistribute, or relicense.

Every third-party asset must pass the repository's data-admission gate before it enters a training/dev corpus. The project records provenance, license/rightsholder, allowed uses, redistribution status, attribution, source identity, cryptographic hash, transformation history, and benchmark-overlap status.

Unknown or ambiguous rights default to **metadata-only / do not ingest**.

Training permission, dataset redistribution permission, and model-weight release permission are treated as separate questions.

HieraticBench is quarantined for external evaluation even when an individual public benchmark image would otherwise have a permissive source license.

The canonical policy is `docs/governance/DATA_LICENSING_AND_PROVENANCE_POLICY.md`.


## ADR-0010 — Every dispatch wave includes approved overseer work when safe

**Status:** Accepted  
**Date:** 2026-10-08

The project should maximize safe parallel throughput across Luna, Sonnet, Gemini/other execution agents, and the overseer.

Whenever at least one substantial dependency-ready task is suitable for the overseer's strengths, the overseer must include that task in the same wave plan rather than waiting idly for execution agents.

Before starting, the overseer presents the complete wave assignment to Mohammed, including:
- each execution agent's task;
- the overseer's own task;
- why each task is assigned that way;
- dependencies and collision risks;
- expected capability or infrastructure effect.

Mohammed approves the wave before the overseer begins its own task.

The overseer-owned task should normally be a high-leverage research, architecture, evaluation, scientific-method, or integration task. Filler work is prohibited.

If no safe overseer task is available, the overseer must explicitly state the blocking dependency instead of inventing work.

The detailed protocol is `docs/governance/PARALLEL_WAVE_PROTOCOL.md`.


## ADR-0011 — Sonnet and Gemini share one Anti-Gravity execution lane

**Status:** Accepted  
**Date:** 2026-10-08

The normal parallel topology is three lanes:

1. Luna;
2. one Anti-Gravity lane occupied by either Sonnet or Gemini 3.8 Flash;
3. the overseer.

Sonnet and Gemini are not planned as simultaneous independent lanes. Mohammed switches the Anti-Gravity lane between them according to model limits and availability.

A provider/model switch does not create a new project or task. The incoming model resumes from canonical repository state and the relevant task brief/handoff. Repository state remains authoritative over model memory or prior chat summaries.

Wave plans must therefore assign work to the **Anti-Gravity lane**, while naming the currently active model in parentheses.


## ADR-0012 — Evaluation v1 has no primary composite score

**Status:** Accepted  
**Date:** 2026-10-08

Hieratic AI evaluation v1 reports layer-specific metrics rather than one primary composite score.

Reason:
- script identification, visual recognition, transliteration, linguistic analysis, translation, and uncertainty are different capabilities;
- a single weighted average can hide catastrophic failure at an earlier reading layer;
- fluent translation must not compensate for incorrect visual reading.

A future public composite may be introduced only through a versioned decision with fixed predeclared weights, visible component metrics, and hard capability floors.

The canonical metric contract is `docs/evaluation/METRICS_SPEC.md` plus `eval/metric_contract.yaml`.


## ADR-0013 — Luna receives larger independent-task work packages

**Status:** Accepted  
**Date:** 2026-10-08

Luna completes bounded engineering tasks faster than the overseer lane, so one-small-task-per-wave creates avoidable idle time.

When several tasks are independently ready, the default Luna assignment is therefore a **2–3 task work package**.

Constraints:
- all package tasks must already have validated dependencies at dispatch;
- each task keeps separate acceptance criteria, evidence, and progress accounting;
- preferably one branch/PR per canonical task;
- write scopes must be disjoint or explicitly partitioned;
- Luna may return only after completing the full package;
- no dependent task may start solely because its prerequisite was locally completed inside the package; overseer validation is still required.

This changes throughput, not scientific or quality standards.


## ADR-0014 — Pin external HieraticBench; preserve its official scoring and quarantine

**Status:** Accepted  
**Date:** 2026-10-08

HieraticBench reproduction is pinned to upstream commit
`d587dc990013f18007f1e7a8f56f96ff2f7127e2`
and harness `0.1.0`.

- Reproduce item inventory and public numeric score aggregation with a read-only external adapter.
- Use the benchmark's own TypeScript scoring implementation/tests as the authoritative raw-answer scorer.
- Never silently substitute Hieratic AI's different normalization or metrics for official benchmark scores.
- Do not claim fresh model-inference reproduction merely because historical numeric aggregates were reproduced.
- Never fabricate gold labels/scores for the undisclosed sentence.
- Keep images, crops, exact/near-duplicate source items, benchmark answer gold, and model outputs out of the training/development pipeline.
- Any future upstream benchmark version requires a new reviewed manifest, scorer comparison and benchmark-integrity decision.

References: `docs/evaluation/HIERATICBENCH_REPRODUCTION.md` and `eval/benchmarks/hieraticbench/manifest.yaml`.


## ADR-0015 — Error-review events are not performance denominators

**Status:** Accepted  
**Date:** 2026-10-08

EVAL-005 formalizes an evidence-linked taxonomy with one primary failure code, optional secondary codes, adjudication status, gold eligibility, contamination status, causal references, and subgroup metadata.

Error-review counts must **not** be interpreted as rates, model accuracy or reading proficiency without a separately frozen EVAL-001 scored-item universe and documented sampling design. Public summaries exclude sealed-aggregate records before computing any statistics. Disputed/uncertain/contaminated events may be logged diagnostically but do not enter confirmed clean-error distributions.

See `docs/evaluation/ERROR_TAXONOMY_AND_ANALYSIS.md` and `eval/analysis/error_taxonomy.yaml`.


## ADR-0016 — Evidence validity and capability acceptance are separate gates

**Status:** Accepted  
**Date:** 2026-10-08

FND-006 made project governance executable via evidence/experiment schemas, task write-scope registration, CI checking of actual PR file diffs, full cross-domain tests, and operational reproducibility documentation.

- A syntactically valid agent evidence bundle or experiment record is not proof that its underlying commands/results/rights were independently verified.
- Only the overseer, after inspecting actual PR/CI/evaluation evidence, may mark weighted tasks validated.
- An experiment may be labeled `validated` only after frozen data/splits, code/config/model/run outputs and actual reviewed metrics exist; schema completeness alone is insufficient.
- Unregistered execution-agent task branches fail CI write-scope checks; novel tasks must register a reviewed allowed scope.
- FND-006 closes foundation P1 at 5/5; CTRL-003 remains an independent, unresolved control-plane gate item.

Reference: `docs/governance/REPRODUCIBILITY_GATES.md`.


## ADR-0017 — Reviewable acquisition and split plans do not constitute dataset clearance

**Status:** Accepted  
**Date:** 2026-10-08

DATA-002, DATA-004 and EVAL-004 infrastructure was accepted after code, CI and negative-test review, but **only the mechanisms** have been validated:

- Acquisition manifests plan source handling without downloading, licensing, granting rights or admitting assets into a training/dev corpus; real per-item license/rightsholder/reviewer and independent overlap evidence must exist.
- A syntactically reviewed `benchmark_overlap_review.status: clear` is an attestation that must be independently checked; it does not prove the item was compared with all 268 pinned HieraticBench examples. The aggregate-only roster is explicitly insufficient to automate exhaustive overlap clearance.
- Any real/production split must pass item-level provenance and exact/near-duplicate comparison before downstream training or blind-evaluation claims; unreviewed high-risk items remain excluded.
- Annotation examples are synthetic. EVAL-001 scoring against actual expert gold still needs reviewed real annotations with permission.
- Downstream tasks `EVAL-006`, `DATA-003`, `DATA-005`, `DATA-006`, `DATA-007` become **dependency-ready only**; ready is not automatically active or validated.

The accepted implementation PRs are #20, #23 and #24, with W1 acceptance recorded in canonical state. The limitation protects the difference between validated engineering guardrails and scientific or licensing evidence.
