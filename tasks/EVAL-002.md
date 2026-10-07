# EVAL-002 — Reproduce HieraticBench as an External Evaluation Adapter

- **Task ID:** EVAL-002
- **Branch:** `task/EVAL-002-hieraticbench-reproduction`
- **Owner:** overseer
- **Depends on:** FND-004 — validated
- **Status at dispatch:** ready
- **Primary write scope:** `eval/benchmarks/hieraticbench/`, `docs/evaluation/`, `tests/evaluation/`, benchmark-adapter metadata only
- **Do not edit:** HieraticBench gold answers, sealed readings, benchmark source assets, project progress/weights until acceptance

## Why this is overseer-owned

HieraticBench is the project's most visible external benchmark, and reproducing it correctly requires source-grounded methodological judgment, benchmark-quarantine discipline, result interpretation, and careful separation between official benchmark scoring and project-derived metrics.

## Objective

Verify and reproduce HieraticBench as an external evaluation target without contaminating training or redefining the benchmark.

The deliverable should let the project answer:

- exactly what the benchmark contains;
- what tasks and scoring it defines;
- which items are public vs commissioned/sealed;
- which published/current model results can be verified;
- how to run or represent the benchmark reproducibly;
- how official scores map into the Hieratic AI evaluation contract;
- which claims cannot be independently reproduced because sealed answers are unavailable.

## Required work

### 1. Primary-source verification

Verify from the official repository/site and any linked primary records:

- benchmark version/commit;
- total item count and task composition;
- item/source metadata;
- official scoring logic;
- evaluation protocol;
- sealed/commissioned item handling;
- licenses/permissions;
- published baseline/model results and dates where available.

Distinguish:
- verified fact;
- benchmark author's claim;
- project inference;
- unresolved/unknown.

### 2. Quarantine-safe adapter

Create a benchmark adapter/manifest that can represent the official benchmark inputs and scoring metadata **without copying sealed answers into the repository**.

Prefer:
- source IDs/URLs;
- item IDs;
- task categories;
- rights/provenance;
- official score definitions;
- checksums for public local fixtures only if legally/methodologically appropriate.

Do not ingest benchmark images into training/data-engine paths.

### 3. Official scoring preservation

If official scoring code exists:
- document its behavior;
- wrap/reuse it where feasible;
- test against public/non-sensitive fixtures.

If official scoring cannot be fully reproduced due sealed answers:
- reproduce all public mechanics;
- explicitly mark the sealed portion as externally adjudicated;
- do not fabricate expected scores.

### 4. Mapping to EVAL-001

Document how each HieraticBench task relates to the canonical metric contract.

Rules:
- official benchmark score remains official and unchanged;
- project-derived diagnostics are separate;
- project metric normalization may not alter official published benchmark scores;
- no benchmark-specific optimization enters training/dev.

### 5. Reproduction report

Create a source-grounded report covering:
- benchmark structure;
- methodology;
- official/public baseline results;
- reproducibility status by component;
- known limitations;
- contamination risks;
- how the benchmark complements but does not define project success.

## Expected deliverables

At minimum:

1. `docs/evaluation/HIERATICBENCH_REPRODUCTION.md`
2. `eval/benchmarks/hieraticbench/manifest.yaml` or equivalent
3. `eval/benchmarks/hieraticbench/README.md`
4. adapter/scoring wrapper only where needed
5. tests using non-sensitive/public fixtures
6. citations/URLs to official sources

## Acceptance criteria

- [ ] Benchmark composition is source-verified.
- [ ] Official scoring/protocol is documented precisely.
- [ ] Sealed-answer boundaries are explicit.
- [ ] Public vs commissioned items are distinguished.
- [ ] Rights/provenance constraints are recorded.
- [ ] Official published baseline claims are verified or marked unresolved.
- [ ] Reproduction status is stated component-by-component.
- [ ] EVAL-001 mapping exists without redefining official scores.
- [ ] No benchmark data enters training/dev paths.
- [ ] No sealed answer is exposed or guessed.
- [ ] Any adapter/tests are deterministic and CI-safe.
- [ ] No progress/status is self-awarded before acceptance.

## Prohibited shortcuts

- treating secondary reporting as equivalent to the official benchmark source;
- copying hidden/commissioned answers into the repo;
- using benchmark items for training/debugging;
- changing official scoring because a project metric is preferred;
- claiming complete reproduction when a sealed component cannot be locally verified;
- inferring unpublished model results;
- conflating script identification with sign reading.

## Evidence package

Return:
- source list and verification notes;
- files changed;
- benchmark version/commit;
- item/task counts;
- scoring/reproduction status;
- tests/commands;
- unresolved discrepancies;
- contamination/quarantine statement;
- acceptance checklist;
- exact capability-point implication if accepted.

EVAL-002 earns **2.0 capability points only after acceptance**.
