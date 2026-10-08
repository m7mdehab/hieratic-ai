# DATA-008 corpus assembly and release

`tools.release_corpus` assembles one release from the accepted DATA-001/002/003/004/005/006/007 and EVAL-004 contracts. It reads manifests only and never downloads source objects. A bundle is validated as a whole; any broken identity, rights gate, split assignment, gold target or artifact hash refuses publication. A successful immutable output contains `release-manifest.json`, `export.jsonl`, `dataset-card.md`, `rejection-report.json`, and `audit-trail.json`. The export retains layer-specific annotation values and alternatives, alignment hypotheses, reviewer decisions and review state. The image itself stays in the DATA-003 artifact store and is referenced by SHA-256.

## Commands

```text
python -m tools.release_corpus validate data/releases/examples/synthetic-test/bundle.yaml
python -m tools.release_corpus build data/releases/examples/synthetic-test/bundle.yaml --output out/synthetic-test-v1
```

`schemas/dataset_release.schema.json` defines the input bundle and the `$defs.releaseManifest` output contract. Bundle file references are relative to the bundle directory; absolute paths, path traversal, symlinks, missing files, oversized manifests/artifacts, hash mismatches, and existing output destinations are refused. Build stages output in a sibling temporary directory and atomically renames only after all output files are complete. Version identifiers hash canonical JSON over sorted, hashed inputs, split identity and per-item records; generation timestamps are excluded.

`synthetic_test_release` is exclusively a structural fixture mode. It retains a synthetic flag and cannot be renamed into `corpus_v1_release`. Synthetic identifiers, clearances, rights references and readings do not constitute an independent license, scholarly mapping, review or gold score. `corpus_v1_release` additionally requires complete real DATA-002 acquisition, source-registry permission for training and redistribution, item-level annotation and mapping permissions with evidence, explicit intended use and attribution, compatible split and image hashes, reviewed benchmark overlap, resolved near-duplicate checks, and per-item reviewed scorable gold. Empty train/dev/test partitions are not a production corpus.

The checked-in fixture and deterministic output are under `data/releases/examples/synthetic-test/`; `demo-output-v4/` is synthetic test evidence, not a corpus release or training dataset.

## Blocked production assessment

The release engine is implemented, but no production corpus is being claimed. Current repository records are metadata-only, conditional, non-commercial, per-item, restricted, unknown-rights, or evaluation-only; there is no complete set of real acquisitions, licensed annotations/mappings, reviewed alignments, and expert adjudications covering leakage-resistant train/dev/test partitions. The machine-readable [rights readiness inventory](../../data/releases/rights-readiness.yaml) and [blocked release assessment](../../data/releases/BLOCKED_RELEASE_ASSESSMENT.md) describe the missing evidence. Do not treat this tooling acceptance as DATA-008 validation or award its three capability points.

## Admission workflow for future real material

1. Identify every source object in DATA-001 and verify the exact image, annotation and mapping rightsholders, license text, permitted training/development use, redistribution terms, attribution and modifications.
2. Acquire only after authorization, through DATA-002. Preserve retrieval identity and original byte hash; complete per-item license and benchmark-overlap reviews. `conditional`, `not_approved`, `metadata_only`, and `unknown` are not permissions.
3. Produce deterministic DATA-003 artifacts linked to those exact acquisition records. Keep originals and derived assets outside Git when policy or size requires it.
4. Validate DATA-004 annotations, DATA-005 evidence-backed mappings, DATA-006 alignments and DATA-007 independent review. Uncertain alternatives, missing gold, restoration, damage and disagreement stay represented; they are never converted to certainty to increase coverage.
5. Generate and validate an EVAL-004 split. Prove source-object, document, page, original/normalized image hash and reviewed near-duplicate separation. Keep HieraticBench and all known/possible duplicates quarantined.
6. Build a fresh immutable `corpus_v1_release` from the complete manifest bundle. Obtain independent review of rights, corpus adequacy, gold eligibility and release terms before treating it as a usable training corpus.

## Scientific limits

Corpus assembly is data plumbing, not a model experiment. It computes no capability score or reading metric. The current contracts do not define a scientifically accepted minimum sample size or subgroup coverage threshold; the engine enforces item-level identities, rights, review and split gates and refuses empty partitions, but corpus adequacy remains an independent overseer acceptance decision. No restricted images or benchmark answers are included in the repository fixture.
