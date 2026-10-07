# Data Directory

This directory is governed by [Data Licensing & Provenance Policy](../docs/governance/DATA_LICENSING_AND_PROVENANCE_POLICY.md).

## Default rule

**Do not place third-party raw data here merely because it is publicly downloadable.**

The project is provenance-first and deny-by-default.

Before an external asset is admitted to training/dev it must have:
- verified source and item identity;
- explicit rights classification;
- training-use approval;
- provenance manifest;
- SHA-256;
- benchmark-overlap clearance;
- redistribution/release status.

## Intended structure

Future data engineering tasks may create:

- `sources/` or manifests — tracked metadata about approved/candidate sources;
- `raw/` — local/external raw assets, normally untracked;
- `interim/` — reproducible intermediate data, normally untracked;
- `processed/` — versioned ML-ready outputs, storage policy determined per release;
- `splits/` — versioned split manifests;
- `benchmarks/` — evaluation references kept isolated from training.

The exact machine-readable layout is owned by DATA-001/DATA-004 and must remain compatible with the governance policy.

## HieraticBench

HieraticBench is **evaluation-only** for this project. Do not use its exact images, crops, labels, or derived near-duplicates in training/dev.
