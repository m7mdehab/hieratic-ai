# EVAL-004 — Leakage-Resistant Development and Test Splits

- **Task ID:** EVAL-004
- **Branch:** `task/EVAL-004-leakage-splits`
- **Owner:** execution agent
- **Depends on:** FND-003, FND-004 — validated
- **Status at dispatch:** ready
- **Primary write scope:** `eval/splits/`, `schemas/`, `tests/evaluation/`, minimal split tooling
- **Do not edit:** benchmark gold answers, project progress/weights, source-rights decisions, external raw assets

## Objective

Create the deterministic split-policy and tooling needed to prevent document, page, scribe, source, and near-duplicate leakage across development and test evaluation.

The project does not yet have the final ML-ready corpus. Therefore EVAL-004 must build and validate the split **system** using repository-authored synthetic metadata fixtures, and define the production split profiles that DATA-008 will later instantiate on the real corpus.

Do not claim a final production corpus split exists when it does not.

## Required split dimensions

Support, where metadata exists:

- document/object ID;
- page/surface ID;
- source/institution;
- scribe/writer group;
- period/date band;
- material/support;
- genre/register;
- image/content fingerprint;
- benchmark overlap/quarantine state.

At minimum, same document/page may never cross train/dev/test.

## Required split profiles

Define at least:

### PROFILE-DOC-HOLDOUT
Primary generalization split:
- no document overlap;
- no page overlap;
- deterministic;
- stratification where feasible without violating group isolation.

### PROFILE-SCRIBE-HOLDOUT
When scribe metadata exists:
- held-out scribes entirely absent from train;
- unknown-scribe records handled by an explicit policy, not randomly mixed without documentation.

### PROFILE-SOURCE-HOLDOUT
Diagnostic:
- hold out one or more source/institution groups when sample size permits.

### PROFILE-PERIOD-HOLDOUT
Diagnostic:
- hold out a chronological band/period where metadata/sample size permits.

### PROFILE-SEALED-TEST
Rules for a future sealed test set:
- split manifest frozen before final model selection;
- test IDs/hashes may be public or private according to source policy, but labels/answers follow sealed protocol;
- no adaptive regeneration after seeing results.

Profiles that cannot be instantiated on current data should be defined as policies, not fabricated outputs.

## Benchmark quarantine

The split system must treat:
- `benchmark_quarantine: true`;
- known HieraticBench source IDs/object IDs;
- exact file hashes;
- normalized/perceptual hashes when available

as hard exclusion signals from train/dev.

HieraticBench benchmark items must never be placed in train/dev merely to balance strata.

## Near-duplicate / overlap model

Design a layered overlap check:

1. exact source/object ID;
2. exact original SHA-256;
3. normalized-content SHA-256 where deterministic normalization exists;
4. perceptual image hash or embedding similarity hook for later use;
5. document/page lineage;
6. manual-review queue for suspicious pairs.

EVAL-004 need not solve image-near-duplicate detection perfectly without real assets, but the interface and failure policy must exist.

## Deterministic split manifest

Create a schema/manifest format containing at least:

- split version;
- generator version;
- seed;
- profile ID;
- source metadata version/hash;
- item IDs;
- grouping keys used;
- train/dev/test membership;
- quarantine/exclusion reasons;
- overlap-check version;
- statistics by source/document/scribe/period/material/genre when available;
- generation timestamp;
- code commit or tool version.

Given the same input metadata, profile, and seed, output membership must be reproducible.

## Split validator

Validator must detect at minimum:

- duplicate item IDs;
- same document across train/dev/test;
- same page across train/dev/test;
- held-out scribe appearing in train for scribe profile;
- quarantined benchmark item in train/dev;
- exact hash overlap across partitions;
- source/object lineage overlap where prohibited;
- manifest input-version mismatch where represented;
- missing reason for excluded/quarantined items.

## Synthetic fixtures/tests

Build repository-authored synthetic metadata to prove:

- deterministic repeatability;
- document leakage detection;
- page leakage detection;
- scribe-holdout behavior;
- benchmark quarantine;
- exact-hash duplicate rejection;
- group-stratification behavior;
- safe handling of missing scribe/period metadata;
- validator failure on intentionally contaminated fixtures.

Do not use copied manuscript images or sealed benchmark answers.

## Reporting

Generate or document split statistics including:
- item counts;
- document counts;
- source counts;
- known-scribe counts;
- period/material/genre coverage;
- excluded/quarantined counts;
- warnings for low-sample strata.

The tool should prefer a clear warning or refusal over silently violating a holdout rule to hit a target percentage.

## Acceptance criteria

- [ ] Deterministic split schema/tool exists.
- [ ] Document/page isolation is hard-enforced.
- [ ] Scribe/source/period holdout profiles are represented.
- [ ] Benchmark quarantine is hard-enforced.
- [ ] Exact-hash overlap is hard-enforced.
- [ ] Near-duplicate review hook/policy exists.
- [ ] Synthetic fixtures demonstrate valid and invalid cases.
- [ ] Reproducibility metadata is recorded.
- [ ] No final real-corpus split is falsely claimed.
- [ ] No third-party raw assets are added.
- [ ] No canonical progress/status is self-modified.

## Prohibited shortcuts

- random row-level split as the primary evaluation split;
- allowing the same document in multiple partitions;
- weakening quarantine for balance;
- silently regenerating test membership to improve metrics;
- using filenames alone as overlap identity;
- claiming perceptual de-duplication is solved without evidence;
- adding benchmark answers to fixtures.

## Evidence package

Return:
- branch/commit and PR;
- files changed;
- split profiles;
- deterministic generation example;
- validator output;
- full test output;
- one deliberate contamination failure example;
- acceptance checklist;
- limitations/open questions;
- confirmation no third-party data or benchmark answers were added.

Do not self-mark EVAL-004 validated.
