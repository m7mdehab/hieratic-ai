# DATA-001 — Machine-Readable Training-Data Source Registry

- **Task ID:** DATA-001
- **Branch:** `task/DATA-001-source-registry`
- **Owner:** execution agent
- **Depends on:** FND-004, FND-005 — validated
- **Status at dispatch:** ready
- **Primary write scope:** `data/sources/`, `schemas/`, `tests/data/`, minimal `tools/` helpers if needed
- **Do not edit:** capability weights, project progress, research conclusions, benchmark gold data, raw third-party assets

## Context

FND-004 established the verified prior-art/data registry. FND-005 established the deny-by-default data licensing and provenance policy.

DATA-001 converts those human-readable findings into the machine-readable source registry that all later acquisition, preprocessing, annotation, split, and release tooling will depend on.

This task is **metadata and governance infrastructure only**. Do not download or commit manuscript images, corpora, benchmark assets, or model weights.

## Objective

Create a deterministic, schema-validated source registry covering the currently verified candidate resources and encoding enough provenance/licensing information for downstream automation to decide whether a source is eligible for:

- training;
- development;
- evaluation;
- redistribution;
- commercial-compatible use;
- model-weight release review.

## Required source coverage

At minimum, include registry records for:

- HieraticBench
- DDD
- PaPYrus
- Isut
- HieraticAI
- HPDB
- AKU-PAL
- TLA

The registry may include additional verified sources only if they are already supported by canonical project research. Do not invent new sources in this task.

## Required schema

Create an inspectable schema for source records, preferably JSON Schema.

Each source record must support at least:

- `source_id`
- `name`
- `source_type`
- `responsible_party`
- `canonical_url`
- `access_url` when different
- `accessed_at`
- `granularity`
- `verified_status`
- `rights_text_verbatim`
- `rights_class`
- `license_url`
- `rightsholder`
- `attribution_requirements`
- `training_use`
- `evaluation_use`
- `redistribution_use`
- `commercial_use`
- `model_release_review`
- `automated_access_constraints`
- `benchmark_quarantine`
- `benchmark_overlap_risk`
- `evidence_urls`
- `provenance_notes`
- `open_questions`
- `recommended_project_role`

Use enums/controlled vocabularies where appropriate.

## Canonical rights classes

Use the policy classes from `docs/governance/DATA_LICENSING_AND_PROVENANCE_POLICY.md` rather than inventing a second taxonomy:

- OPEN-PD
- OPEN-BY
- OPEN-SA
- NONCOMMERCIAL
- PER-ITEM
- EVALUATION-ONLY
- RESTRICTED
- UNKNOWN

Where the source needs a temporary project-specific review marker, represent that explicitly without replacing the canonical rights class.

## Registry behavior

The registry must make the following current project decisions machine-visible:

### HieraticBench
- evaluation-only;
- training/dev prohibited;
- exact/near-duplicate overlap risk high;
- source-specific image licenses remain separate from project quarantine.

### DDD
- non-commercial/restricted research track;
- per-image complexity recorded;
- not approved for default commercial-compatible training.

### HPDB
- CC BY 4.0 dataset status recorded;
- attribution required;
- image/IIIF provenance preserved.

### AKU-PAL
- per-item rights;
- no blanket database-wide image license assumption;
- benchmark overlap risk recorded.

### PaPYrus / Isut / HieraticAI
- code/software license must not be treated as automatic clearance for all underlying images/data;
- rights-review/open-question state visible.

### TLA
- live-site bulk extraction restricted;
- no bulk scraping for training;
- separately licensed raw release or permission required for large-scale ingestion.

## Machine validation

Provide a small validator or reuse existing project tooling where sensible.

Validation must detect at minimum:

- duplicate `source_id`;
- missing required fields;
- invalid rights class;
- malformed URLs where practical;
- contradictory states such as `training_use: allowed` with `rights_class: EVALUATION-ONLY`;
- HieraticBench not marked evaluation-only;
- source marked redistributable while required rights evidence is absent;
- empty evidence list for VERIFIED-PRIMARY sources.

Do not silently repair invalid records.

## Tests

Add tests proving:

- the canonical registry validates;
- duplicate IDs fail;
- invalid rights classes fail;
- contradictory benchmark/training flags fail;
- a VERIFIED-PRIMARY source without evidence fails;
- HieraticBench quarantine is enforced;
- no raw asset directory or external binary is added by this task.

## Deliverables

Expected outputs:

- `data/sources/registry.yaml` or equivalent canonical machine-readable registry;
- `schemas/data_sources.schema.json` or equivalent;
- validator/helper code if needed;
- tests under `tests/data/`;
- concise `data/sources/README.md` explaining semantics and update procedure.

## Acceptance criteria

- [ ] All required verified sources are represented.
- [ ] Schema captures provenance, access, rights, and project-use decisions.
- [ ] Rights classes match the canonical policy.
- [ ] HieraticBench is machine-enforced as evaluation-only.
- [ ] TLA live-site bulk scraping prohibition is encoded.
- [ ] DDD's non-commercial/per-image complexity is encoded.
- [ ] Source records cite authoritative evidence URLs already supported by project research.
- [ ] Registry validation and negative tests pass.
- [ ] No third-party raw assets are downloaded or committed.
- [ ] No canonical progress/weights/status are self-modified.

## Prohibited shortcuts

- copying prose from FND-004 without producing a machine-usable schema;
- treating GitHub/software licenses as image/data licenses;
- marking UNKNOWN/RIGHTS-REVIEW material as training-cleared for convenience;
- weakening HieraticBench quarantine;
- downloading data "just to inspect it" inside this task;
- inventing legal permissions not supported by the canonical policy;
- maintaining a second rights taxonomy that can drift from FND-005.

## Evidence package on return

Return:

- task ID;
- branch and commit SHA;
- exact files changed;
- registry validation command/output;
- test command/output;
- count/list of source records;
- acceptance checklist;
- deviations/open questions;
- licensing/provenance impact;
- explicit confirmation that no third-party raw assets were added.

Do **not** self-mark DATA-001 validated.
