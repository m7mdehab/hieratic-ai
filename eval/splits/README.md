# Leakage-resistant split system

This directory defines split profiles and offline tools for future source metadata. The checked-in metadata and manifest examples are synthetic fixtures only. **No final real-corpus split exists.** DATA-008 instantiates production membership only after a rights-cleared corpus and metadata are available.

## Profiles

- `PROFILE-DOC-HOLDOUT`: primary deterministic document holdout; atomic document/page/object/hash groups; source-stratified 60/20/20 allocation when each stratum has enough independent groups. Low-sample strata produce warnings instead of relaxing isolation.
- `PROFILE-SCRIBE-HOLDOUT`: values passed with `--holdout-value` are test-only. Unknown-scribe documents follow the explicit `train_only` policy.
- `PROFILE-SOURCE-HOLDOUT`: requested source IDs are test-only; remaining groups use deterministic train/dev allocation.
- `PROFILE-PERIOD-HOLDOUT`: requested period bands are test-only; unknown period values remain a separately reported `UNKNOWN` stratum.
- `PROFILE-SEALED-TEST`: policy only. Freeze membership before final model selection and do not regenerate it after seeing results. This profile cannot generate a split.

`profiles.yaml` records the known HieraticBench source ID and sealed item IDs (`hb-0001`, `hb-0002`). Items with a quarantine flag, a known benchmark source/item/object ID, or hashes/confirmed duplicate links to quarantined items are excluded with a reason. The exact source object ID, original SHA-256, and normalized-content SHA-256 join atomic groups so duplicates cannot cross partitions.

## Input metadata and commands

Metadata YAML has `metadata_version`, a non-empty `items` list, and optional known quarantine IDs and `near_duplicate_candidates`. Each item carries stable item/source/object/document/page IDs, institution, scribe, period, support, genre, image and normalized SHA-256 values, perceptual hash when available, and an explicit quarantine boolean.

```bash
python -m tools.split_system generate --metadata eval/splits/examples/synthetic_metadata.yaml --profile PROFILE-DOC-HOLDOUT --seed 41 --output eval/splits/examples/doc-holdout.synthetic.yaml
python -m tools.split_system validate --metadata eval/splits/examples/synthetic_metadata.yaml --manifest eval/splits/examples/doc-holdout.synthetic.yaml
python -m tools.split_system generate --metadata corpus-metadata.yaml --profile PROFILE-SCRIBE-HOLDOUT --holdout-value SCRIBE-17 --seed 41 --output splits/scribe-holdout.yaml
```

The source metadata version and canonical SHA-256 are embedded in every manifest and checked against the supplied input. Membership is deterministic for the same metadata, profile, holdout values, and seed. The manifest also stores generator version, grouping keys, timestamp, partition statistics (item/document/source/institution/scribe/period/support/genre), exclusions, warnings, and a near-duplicate review queue.

Repeated perceptual hashes and explicitly supplied suspicious pairs enter the review queue. A pending pair cannot cross partitions; resolve it as `same_content` (atomic grouping) or `distinct_content` (review evidence retained) before such a split can be generated. Similarity scoring itself is a future image/embedding hook; this task does not claim it is solved. Exact and normalized hashes are enforced directly.

The tool is offline and does not read benchmark answers or source images. It refuses metadata holdout profiles without explicit held-out values and refuses a future sealed-test generation request. Input metadata, profiles, and generated memberships must be reviewed before production use.
