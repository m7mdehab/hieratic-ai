# Luna Work Package — W1 Large Batch

**Status:** Prepared, not started  
**Prepared:** 2026-10-08  
**Execution lane:** Luna  
**Base requirement:** start every task from the latest accepted `main`

## Purpose

Keep the fast Luna lane productive for the full overseer review cycle by assigning multiple **independent, already-ready** tasks in one package.

Luna should complete all tasks below before returning, unless a blocker requires escalation.

## Tasks

### 1. DATA-002 — Reproducible data acquisition manifests

Brief: `tasks/DATA-002.md`  
Branch: `task/DATA-002-acquisition-manifests`  
Weight: **2.0**

Primary outcome:
- rights-aware acquisition manifests/planner/validator;
- fail-closed handling of prohibited/not-approved/conditional sources;
- deterministic provenance/fingerprints;
- no third-party raw assets.

### 2. DATA-004 — Canonical annotation schema

Brief: `tasks/DATA-004.md`  
Branch: `task/DATA-004-annotation-schema`  
Weight: **3.0**

Primary outcome:
- canonical document/page/line/sign/language annotation schema;
- uncertainty and multiple valid readings;
- EVAL-001 gold-field compatibility;
- synthetic valid/invalid fixtures.

### 3. EVAL-004 — Leakage-resistant split system

Brief: `tasks/EVAL-004.md`  
Branch: `task/EVAL-004-leakage-splits`  
Weight: **2.0**

Primary outcome:
- deterministic document/page/scribe/source/period split profiles;
- benchmark quarantine;
- exact-hash leakage checks and near-duplicate review hooks;
- synthetic contamination tests;
- no false claim that a final real-corpus split already exists.

## Independence / dependency rule

All three tasks are already dependency-ready at dispatch.

None depends on another task in this package.

Therefore Luna may complete them in any order without waiting for overseer acceptance between them.

Do **not** begin DATA-003, DATA-005, DATA-006, DATA-007, EVAL-006, or any other newly unblocked task inside this package. Those require a later overseer review/state transition.

## Branch and PR discipline

Use **one branch and one PR per canonical task**.

Each branch starts from latest `main`, not from another package branch.

Do not merge the branches together locally.

Write scopes are deliberately separated:

- DATA-002: acquisition manifests/planner;
- DATA-004: annotation schema/examples;
- EVAL-004: split/evaluation tooling.

If two tasks unexpectedly need the same shared file, minimize the collision and note it explicitly in the evidence package.

## Return format

Return one combined message containing **three evidence packages**, one per task.

For each task include:
- branch;
- commit SHA;
- PR;
- exact files changed;
- commands and complete results;
- acceptance checklist;
- deviations/risks;
- licensing/provenance impact;
- explicit confirmation no canonical progress/status was self-awarded.

Also include a short package summary:
- total tests run;
- which PR CI checks passed;
- any cross-task integration issue;
- any task that should be revised before merge.

## Quality rule

Batching changes throughput only.

It does not reduce:
- test coverage;
- provenance requirements;
- benchmark quarantine;
- evidence requirements;
- task acceptance criteria.

If a task cannot be completed correctly, stop that task and continue another independent task where safe, then report the blocker precisely.
