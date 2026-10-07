# DATA-002 — Reproducible Data Acquisition Manifests

- **Task ID:** DATA-002
- **Branch:** `task/DATA-002-acquisition-manifests`
- **Owner:** execution agent
- **Depends on:** DATA-001 — validated
- **Status at dispatch:** ready
- **Primary write scope:** `data/acquisition/`, `schemas/`, `tests/data/`, minimal `tools/` acquisition helpers
- **Do not edit:** project progress/weights, benchmark gold data, source-rights conclusions, raw third-party assets

## Objective

Turn the source registry into a reproducible, rights-aware acquisition control layer.

The system must be able to describe exactly what external asset would be acquired, from where, for what permitted project purpose, under which source record and rights constraints, with enough metadata to reproduce and audit the acquisition later.

This task does **not** authorize broad downloads. Tests must use repository-authored fixtures/mocks, not live third-party bulk acquisition.

## Required capabilities

### 1. Acquisition manifest schema

Create a machine-readable manifest schema that can represent at minimum:

- manifest/version ID;
- source registry ID;
- source object/item ID;
- canonical object URL;
- exact download/access URL when applicable;
- acquisition mode: direct download / IIIF / API / manual-reference / metadata-only;
- intended project use: training / development / evaluation / reference;
- source rights class and use-decision snapshot;
- required attribution;
- benchmark quarantine/overlap status;
- expected filename/path;
- expected MIME/type where known;
- expected size if known;
- expected SHA-256 if known before acquisition;
- actual SHA-256 after acquisition;
- retrieval timestamp;
- HTTP ETag / Last-Modified where available;
- transformation status (original bytes only at acquisition stage);
- redistribution flag;
- provenance/evidence URLs;
- acquisition status and reason;
- operator/tool version.

Use controlled vocabularies where practical.

### 2. Policy-aware planner/validator

Implement a CLI/helper that reads:
- `data/sources/registry.yaml`;
- one acquisition manifest.

It must refuse or require explicit restricted-track handling for contradictory/unsafe requests.

At minimum:

- EVALUATION-ONLY source requested for training/dev -> fail;
- benchmark-quarantined source requested for training/dev -> fail;
- source use-decision `prohibited`, `not_approved`, or `metadata_only` for requested purpose -> fail;
- `conditional` use without the manifest explicitly satisfying/recording required review conditions -> fail;
- missing source_id -> fail;
- unknown source_id -> fail;
- missing provenance/evidence -> fail;
- redistribution requested when source record does not support it -> fail;
- missing/invalid hash where a downloaded artifact is declared complete -> fail.

Do not silently downgrade a request or rewrite its intended use.

### 3. Deterministic acquisition record

Define a deterministic way to compute an acquisition-record ID/fingerprint from stable manifest fields.

Repeated acquisition of the same declared asset should be traceable as the same logical source item while preserving retrieval-event history.

### 4. Dry-run first

Provide a `plan` or `validate` mode that performs no network calls and clearly reports:
- source;
- intended use;
- whether acquisition is allowed, conditional, or refused;
- missing approvals/conditions;
- target path;
- provenance requirements.

Network access is not required for acceptance of DATA-002.

If a fetch command is implemented, it must:
- default to safe behavior;
- never bypass source-registry policy;
- write only to ignored local/raw locations;
- compute SHA-256;
- never commit downloaded third-party data.

### 5. Example manifests

Provide repository-authored examples demonstrating at least:

- a metadata-only/blocked PaPYrus-style request;
- an evaluation-only HieraticBench request that passes for evaluation but fails for training;
- a conditional AKU-PAL item example requiring explicit per-item license review;
- an OPEN-BY/HPDB-style metadata or approved-item example showing attribution/provenance handling.

Examples must contain no copied third-party binary assets.

## Tests

Add deterministic tests proving at minimum:

- canonical schemas/manifests validate;
- unknown source ID fails;
- HieraticBench training request fails;
- TLA training/bulk acquisition request fails;
- PaPYrus/Isut/HieraticAI not-approved request fails;
- conditional AKU-PAL request fails without item review evidence;
- complete acquisition record requires SHA-256;
- same stable manifest fields produce the same logical fingerprint;
- policy decisions come from DATA-001 registry rather than duplicated hard-coded source policy wherever feasible;
- no network calls are needed for tests.

## Acceptance criteria

- [ ] Manifest schema exists and is documented.
- [ ] Source registry is the authority for source-level rights/use decisions.
- [ ] Unsafe/contradictory acquisition requests fail closed.
- [ ] Conditional sources require explicit satisfaction of conditions.
- [ ] Deterministic provenance/fingerprint behavior exists.
- [ ] Dry-run/validation mode exists.
- [ ] Example manifests cover allowed/conditional/refused cases.
- [ ] Tests pass without network access.
- [ ] No third-party raw assets are added.
- [ ] No progress/status is self-awarded.

## Prohibited shortcuts

- copying source-use rules into a second divergent registry;
- treating `conditional` as automatically allowed;
- downloading benchmark/training data during tests;
- using public accessibility as permission;
- storing credentials;
- writing acquired external assets into tracked Git paths;
- bypassing hash/provenance recording for convenience.

## Evidence package

Return:
- branch and commit;
- PR;
- files changed;
- manifest/schema overview;
- CLI commands/output;
- full test output;
- example plan outputs;
- acceptance checklist;
- deviations/risks;
- explicit confirmation no third-party raw assets were committed.

Do not self-mark DATA-002 validated.
