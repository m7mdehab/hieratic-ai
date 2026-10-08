# DATA-008 blocked production-release assessment

**Assessment:** `corpus_v1_release` is blocked. The release engine and synthetic structural release are available; a real ML-ready training corpus is not established by this work.

## Blocking evidence

- The canonical DATA-001 registry currently classifies candidates as evaluation-only, non-commercial, unknown, conditional, per-item, or restricted. No source has an unconditional, item-verified combination of training and redistribution permission for all needed images, annotations, mappings and derivatives.
- There are no complete real DATA-002 acquisitions with per-item clearance, hashes and benchmark-overlap decisions suitable for this release.
- There are no real DATA-003 output artifacts tied to such admitted acquisitions.
- No linked real DATA-004/005 records with separately cleared annotation/mapping rights and scholarly references are assembled with DATA-006 aligned gold and DATA-007 completed expert review.
- An EVAL-004 manifest and source roster exist, but no cleared item set has complete source-object, document, page, original/normalized-image and reviewed near-duplicate separation for train/dev/test.
- The current accepted contracts do not state a validated corpus-size or subgroup-coverage minimum. Independent scientific acceptance would still need to assess adequacy after admission checks pass.

The per-source checklist is in [`rights-readiness.yaml`](rights-readiness.yaml), which points to the canonical source records and evidence URLs. It records outstanding questions and explicitly sets `rights_granted: false`; it does not convert a registry snapshot into permission.

## Safe actions completed by the engine

- A synthetic-only fixture exercises the acquisition → preprocessing → annotation/mapping → alignment/review → split → release-manifest path.
- Production mode rejects synthetic items, unapproved or conditional source use, absent annotation/mapping permissions, missing provenance/hashes, quarantined or unresolved benchmark overlap, split leakage, incomplete gold review, and unresolved near-duplicate checks.
- The synthetic fixture contains a generated 2×2 PPM image, placeholder annotation structures, unresolved synthetic sign mapping, and synthetic review history. It contains no HieraticBench answers, copied source material, or claimed scholarly identification.
- No external assets were downloaded; no source rights were granted or inferred; no model training, performance measurement, capability-point award or real corpus release occurred.

**Disposition:** do not claim DATA-008's three points or downstream data readiness. Revisit only after the missing evidence is assembled and independently reviewed. This assessment is not legal advice.
