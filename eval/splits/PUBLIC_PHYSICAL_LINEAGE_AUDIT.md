# W28 EVAL-004 public physical-source lineage hardening

**Task:** EVAL-004 (already validated split control); independent engineering during concurrent DATA-008 and VLM-001 work. **Status:** public-source metadata match + cross-provider grouping, NOT training-data admission, benchmark-independence certification, or an unsealing exercise. **Risk addressed:** falsely treating different image sources/sign crops as independent physical manuscripts when a single museum accession recurs.

## Reproducible public-only evidence

Pinned prior public R017 metadata: `docs/research/R017_PUBLIC_BENCHMARK_SOURCE_METADATA.jsonl`, exact original Git blob `974c959651d86eaa6dda6097dc8912972cafc8d1`, 266 source-only records, original HieraticBench revision `d587dc990013f18007f1e7a8f56f96ff2f7127e2`. No benchmark item image bytes, transcript/sign gold, benchmark prompts or the two sealed item files were read by the scanner.

Run:

```bash
python -m eval.splits.public_benchmark_lineage audit-public
python -m eval.splits.public_benchmark_lineage screen --institution "Metropolitan Museum of Art" --accession "22.3.517"
python -m eval.splits.public_benchmark_lineage screen --institution "Museo Egizio" --accession "Cat.1880"
python -m unittest tests.evaluation.test_split_system
```

The entire 266-item public metadata register is ingested only after the exact hash/family/field-inventory verification. Deterministic exact-inventory diagnostic from the **actual Python scanner on GitHub Actions**, after correcting a separate JavaScript cross-check's two-scan-record undercount. All counts are pinned by hosted tests:

| Public metadata metric | Count |
|---|---:|
| Total frozen PUBLIC records (150 aku, 16 cbl, 37 met, 61 wm, 2 ypm) | **266** |
| Public records with an unambiguous currently supported institution+inventory signature | **137** |
| Distinct supported exact inventory keys, **not proof of physically unique manuscripts** | **92** |
| Exact inventory keys repeated across 2+ records | **20** |
| Public records with unsupported/ambiguous/no inventory key | **129** |
| Exact keys spanning different benchmark provider-prefix families in this supported subset | **0** |
| Official sealed records read or matched | **0** |

Census totals are *not estimates of 90 manuscript supports*; aliases, joined fragments, multiple inventories per same physical document, editorial genealogy, cross-museum transfers and unnamed support IDs remain UNKNOWN. The absence of cross-prefix exact key matches among these recognized inventory groups does **not** refute known AKU-PAL Met/Museo Egizio source mixing, because the test asks whether items with distinct provider **prefixes** use exactly the same accession and the recognized public set happened not to have one in different prefixes. The risk for future candidate acquisition providers remains genuine and is tested with synthetic split fixtures.

### Positive same-support clusters in actual public provenance metadata

- **Brooklyn Museum 47.218.84**: `aku-0006,0031,0063,0086,0130` — five isolated signs, one accession.
- **Louvre E 25416**: `aku-0017,0054,0069,0090,0116` — five public sign examples from one Louvre inventory.
- **Berlin P 3057**: `aku-0034,0047,0061,0066,0147` — one recorded manuscript/accession, five sign examples.
- **Met 22.3.517**: `aku-0013,0041,0118,0125` — four sign pages, one Met accession.
- **Turin CGT 54050**: `aku-0023,0083,0128` — three sign pages, one Turin inventory.
- **Chester Beatty Pap XXII**: `cbl-0004,0009` — one named papyrus viewed in two public items.

These are source-name identities, NOT evidence of equal original photographic pixels or equal image crop labels.

### The actual before/after safety barrier

**Before:** The accepted EVAL-004 `_atomic_components` linked `source_object_id` by a composite of `source_id + source_object_id`. For example, candidate source `SRC-HPDB` and `SRC-AKU-PAL` each referring to real Met object 22.3.517 could be split as independent if their document ID, photos and hashes differed. A metadata-only `benchmark_overlap_review.status=clear` declaration and arbitrary syntactically plausible evidence string could bypass high-risk source quarantine without an independent public physical accession cross-check.

**Now:** `eval/splits/public_benchmark_lineage.py` extracts only narrowly recognized **museum-qualified accession categories** (Met/Brooklyn dotted object numbers, Turin CGT versus Cat versus S schemes, Berlin P, Louvre E, British Museum EA, Cairo CG, Chester Beatty Pap). It never merges on an unqualified bare number, page count, catalogue title or near-similar numeric string.

`tools/split_system.py` now:
1. Adds the supported institution+inventory physical-support key to the disjoint-set grouping independently of acquisition-provider ID; cross-provider same physical object is atomic in the generated split.
2. Excludes any item/components with a **positive, exact PUBLIC benchmark source match** from train/dev/test, even if their `benchmark_quarantine` flag is false and their self-declared review state says `clear`.
3. Rechecks physical-source keys and source-overlap exclusions when validating **externally supplied manifests**. Hand-edited split assignment cannot silently put a known public benchmark support into training or send same recognized physical support to different partitions.
4. Keeps **no-match and unparsed aliases UNKNOWN**. Existing high-risk source review, immutable roster, duplicate-hash, known source identity, near-duplicate, sealed-test quarantine and independent DATA-008 permissions remain separately mandatory. A metadata-negative never grants use rights.

### Threat-model and incompleteness

The strict institution+inventory parser deliberately gives up recall rather than risking false positive merges. It cannot detect a split/renamed fragment accession, physically same manuscript moved museums, alternative numbering conventions, textual edition overlap, image perceptual similarity, or model pretraining memorization. Ambiguous fields remain unresolved and high-risk sources remain blocked unless independently authenticated under their own policy. Semantic source context such as a parent manuscript title does not itself prove identical physical material.

No source images/annotations from the protected DDD, AKU-PAL, Cat1880 or any benchmark material are downloaded, trained on, licensed or published by this improvement. **EVAL-004 was previously accepted, earns no additional weighted task points**, and does not change DATA-008/VLM-001/EVAL-003/ LING-003 status. Canonical weighted 34.5/100, qualitative research coverage 18/100 until independently accepted novel scientific evidence, not a repaired safety gate.

## Verification

`tests/evaluation/test_split_system.py` includes additional W28 adversarial tests for original 266-source identity, mutation detection, forbidden gold fields, duplicate source grouping, institutional scheme collision, synthetic fake `clear`, same-object cross-provider grouping and explicit Cat1880 no-match UNRESOLVED. Complete hosted governance and error integrity must pass **on the final exact PR commit** before merge. Do not infer legitimate physical manuscript train/test independence merely from green unit tests.
