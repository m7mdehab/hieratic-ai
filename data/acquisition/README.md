# Acquisition manifests

Acquisition manifests describe one source item and the evidence needed to reproduce its acquisition decision. The source registry remains the authority for source rights, allowed uses, quarantine, and attribution. Manifest rights fields are snapshots checked against that registry; they do not grant permission.

## Dry-run commands

From the repository root:

```bash
python -m tools.acquisition plan data/acquisition/examples/hieraticbench-evaluation.yaml
python -m tools.acquisition validate data/acquisition/examples/hpdb-reference.yaml
```

`plan` is offline and never fetches data. It prints a planning result separately from an admission result, plus missing conditions, target path, provenance requirements, and logical fingerprint. The planner never admits an asset to a corpus. A refused request returns a nonzero status. `validate` has the same checks and is suitable for automation. This task does not implement a fetch command.

## Policy and conditions

- Each item names a `source_id`; decisions are read from `data/sources/registry.yaml` at runtime. An unknown ID fails closed.
- A manifest's rights class, requested-use decision, quarantine, overlap risk, and attribution must match the registry snapshot.
- `allowed`, `prohibited`, `not_approved`, and `metadata_only` are honored directly. `conditional` use requires an explicit `review_conditions` entry for each access constraint and project review marker in the source record. Every entry must be marked satisfied and include evidence URLs and notes. Placeholder domains cannot satisfy real review evidence. Conditional redistribution uses the same condition set.
- Conditional PER-ITEM training/development plans require item URL, item-specific license, rightsholder, accountable reviewer approval, review evidence/date, and a clear benchmark-overlap assessment with reviewer, evidence, version, and date. A URL by itself never clears an item. High-risk overlap review is also required for other training/development sources marked high-risk by the registry.
- `is_synthetic_fixture: true` permits synthetic references in repository tests only. It cannot produce admission; the output explicitly reports `NOT ADMITTED — synthetic fixture only`.
- Conditional results are labeled `CONDITIONAL PLAN READY` when their review fields are complete. That label records planning metadata only and does not grant use rights or admit an asset.
- `reference` is metadata-only. It cannot declare an acquisition complete.
- A complete direct-download, IIIF, or API acquisition requires the original-byte SHA-256 and retrieval timestamp. Retrieval events preserve repeated retrieval history.
- The logical fingerprint hashes `source_id`, `source_object_id`, and `canonical_object_url` using canonical JSON. Retrieval-event details do not change logical item identity.

All examples are repository-authored metadata. They include no copied corpus records or binaries. The blocked AKU-PAL example deliberately omits item-rights and benchmark-overlap clearance; placeholder domains never count as real evidence.
