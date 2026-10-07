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
