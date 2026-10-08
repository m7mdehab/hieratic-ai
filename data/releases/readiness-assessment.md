# DATA-008 corpus readiness assessment

- Assessment: `readiness-cc2079e965e0e670c2411c6ca5b4c6fa6b91beddb3dbcd2e44ca6c7495182234`
- As of: 2026-10-08
- Software integrity: **PASS**
- Evidence admission: **BLOCKED**
- Scientific adequacy: **INDEPENDENT_REVIEW_REQUIRED**

## Cohort

- Real admitted items: 0
- Synthetic fixture items: 1
- Unique real manuscript groups: 0
- Unique real source objects: 0
- Real partition document groups: train=0, dev=0, test=0

## R-016 candidates screened against R-017

R-017 screened 266 pinned public source metadata records; sealed records excluded: 2. This is a literal metadata comparison only; zero direct matches do not establish source independence, image equivalence, or permission. Every candidate remains blocked.

| Candidate | Overlap state | Nearby collection witnesses | Exact metadata matches | Rights / image | Admission | Open gates |
|---|---|---:|---:|---|---|---|
| TPOP-1896 | potential_overlap | 18 | 0 | NOT_CLEARED / NOT_TESTED | blocked | 13 |
| TPOP-1971 | potential_overlap | 18 | 0 | NOT_CLEARED / NOT_TESTED | blocked | 13 |
| TPOP-1966 | potential_overlap | 18 | 0 | NOT_CLEARED / NOT_TESTED | blocked | 13 |
| TPOP-2021 | potential_overlap | 18 | 0 | NOT_CLEARED / NOT_TESTED | blocked | 13 |
| TPOP-NECROPOLIS-5 | potential_overlap | 18 | 0 | NOT_CLEARED / NOT_TESTED | blocked | 13 |
| TPOP-1880 | potential_overlap | 18 | 0 | NOT_CLEARED / NOT_TESTED | blocked | 13 |
| MET-561345 | potential_overlap | 12 | 0 | NOT_CLEARED / NOT_TESTED | blocked | 13 |
| MET-561392 | potential_overlap | 12 | 0 | NOT_CLEARED / NOT_TESTED | blocked | 13 |
| MET-561361 | potential_overlap | 12 | 0 | NOT_CLEARED / NOT_TESTED | blocked | 13 |
| MET-561391 | potential_overlap | 12 | 0 | NOT_CLEARED / NOT_TESTED | blocked | 13 |
| MET-561407 | potential_overlap | 12 | 0 | NOT_CLEARED / NOT_TESTED | blocked | 13 |
| MET-561409 | potential_overlap | 12 | 0 | NOT_CLEARED / NOT_TESTED | blocked | 13 |
| MET-561410 | potential_overlap | 12 | 0 | NOT_CLEARED / NOT_TESTED | blocked | 13 |
| MET-561413 | potential_overlap | 12 | 0 | NOT_CLEARED / NOT_TESTED | blocked | 13 |
| MET-561621 | potential_overlap | 12 | 0 | NOT_CLEARED / NOT_TESTED | blocked | 13 |

## Readiness dimensions

```json
{
  "ambiguity": {
    "items_with_uncertain_gold": 0
  },
  "annotation_granularity": {
    "line_level_items": 0,
    "sign_level_items": 0
  },
  "benchmark_source_metadata_screen": {
    "excluded_sealed_files_count": 2,
    "gold_or_images_copied": false,
    "public_metadata_records": 266,
    "records_admitted_for_training": 0,
    "source_family_counts": {
      "aku": 150,
      "cbl": 16,
      "met": 37,
      "wm": 61,
      "ypm": 2
    },
    "unique_public_source_ids": 266,
    "upstream_revision": "alymoursy/hieraticbench@d587dc990013f18007f1e7a8f56f96ff2f7127e2"
  },
  "cross_partition_source_or_group_overlap": {
    "items": 0,
    "validation_errors": []
  },
  "disagreement": {
    "review_cases_with_disagreement": 0
  },
  "genres": {},
  "incomplete_rights": {
    "items": 0
  },
  "missing_or_illegible_gold": {
    "items": 0,
    "observed_statuses": []
  },
  "missing_provenance": {
    "items": 0
  },
  "period": {},
  "reviewer_coverage": {
    "items": 0,
    "reviewed_items": 0,
    "reviewer_identity_visibility": "redacted_from_public_release",
    "unique_reviewers": null
  },
  "rights_readiness_inventory": {
    "assets_downloaded": false,
    "global_missing_evidence": [
      "real completed DATA-002 acquisitions with original hashes",
      "matching DATA-003 artifacts for each admitted page",
      "item-level annotation and mapping rights, with training and redistribution permissions",
      "DATA-004 annotations and DATA-005 mappings with auditable scholarly provenance",
      "DATA-006 reviewed, unambiguous alignment coverage and DATA-007 expert review/adjudication",
      "EVAL-004 train/dev/test manifest whose source-object, document, page, image hashes, normalized hashes and reviewed near-duplicate identities do not leak across partitions",
      "independent review of corpus adequacy, subgroup coverage, terms, attribution and final release"
    ],
    "production_corpus_exists": false,
    "production_corpus_status": "blocked_no_real_items_admitted",
    "rights_granted": false
  },
  "source_registry_rights": [
    {
      "benchmark_quarantine": true,
      "development_use": "prohibited",
      "name": "HieraticBench",
      "redistribution_use": "conditional",
      "rights_class": "EVALUATION-ONLY",
      "rights_evidence_urls": [
        "https://github.com/alymoursy/hieraticbench"
      ],
      "source_id": "SRC-HIERATICBENCH",
      "training_use": "prohibited"
    },
    {
      "benchmark_quarantine": false,
      "development_use": "conditional",
      "name": "Diagnostic Deir el-Medina Dataset (DDD)",
      "redistribution_use": "conditional",
      "rights_class": "NONCOMMERCIAL",
      "rights_evidence_urls": [
        "https://zenodo.org/records/20553713"
      ],
      "source_id": "SRC-DDD",
      "training_use": "conditional"
    },
    {
      "benchmark_quarantine": false,
      "development_use": "not_approved",
      "name": "Tabin / PaPYrus sign corpus",
      "redistribution_use": "not_approved",
      "rights_class": "UNKNOWN",
      "rights_evidence_urls": [
        "https://github.com/jtabin/PaPYrus",
        "https://openscience.ub.uni-mainz.de/items/7aef8525-734c-4ab5-a5c3-4fbf312e1397"
      ],
      "source_id": "SRC-PAPYRUS",
      "training_use": "not_approved"
    },
    {
      "benchmark_quarantine": false,
      "development_use": "not_approved",
      "name": "Isut annotated Hieratic texts",
      "redistribution_use": "not_approved",
      "rights_class": "UNKNOWN",
      "rights_evidence_urls": [
        "https://isut.uliege.be/admin/about",
        "https://github.com/nederhof/isut"
      ],
      "source_id": "SRC-ISUT",
      "training_use": "not_approved"
    },
    {
      "benchmark_quarantine": false,
      "development_use": "not_approved",
      "name": "HieraticAI Westcar annotations and model",
      "redistribution_use": "not_approved",
      "rights_class": "UNKNOWN",
      "rights_evidence_urls": [
        "https://github.com/MargotBelot/HieraticAI"
      ],
      "source_id": "SRC-HIERATICAI",
      "training_use": "not_approved"
    },
    {
      "benchmark_quarantine": false,
      "development_use": "conditional",
      "name": "Hieratische Paläographie Database (HPDB) datasets",
      "redistribution_use": "conditional",
      "rights_class": "OPEN-BY",
      "rights_evidence_urls": [
        "https://moeller.jinsha.tsukuba.ac.jp/en/datasets/"
      ],
      "source_id": "SRC-HPDB",
      "training_use": "conditional"
    },
    {
      "benchmark_quarantine": false,
      "development_use": "conditional",
      "name": "AKU-PAL",
      "redistribution_use": "conditional",
      "rights_class": "PER-ITEM",
      "rights_evidence_urls": [
        "https://aku-pal.uni-mainz.de/faq"
      ],
      "source_id": "SRC-AKU-PAL",
      "training_use": "conditional"
    },
    {
      "benchmark_quarantine": false,
      "development_use": "prohibited",
      "name": "Thesaurus Linguae Aegyptiae (TLA) live website",
      "redistribution_use": "conditional",
      "rights_class": "RESTRICTED",
      "rights_evidence_urls": [
        "https://thesaurus-linguae-aegyptiae.de/info/licenses"
      ],
      "source_id": "SRC-TLA",
      "training_use": "prohibited"
    }
  ],
  "unresolved_overlap": {
    "items": 0
  },
  "writing_media": {}
}
```

## Blockers

- 15 R-016 discovery candidates remain blocked
- no real items passed corpus admission; the accepted example is synthetic infrastructure evidence only
- no signing-key metadata is configured; repository metadata cannot establish an external trust root
- production authorization is hard-disabled pending overseer-governed, independently protected trust-root and reviewer/document verification onboarding

No minimum sample-size threshold was invented. Software integrity, evidence admission, and scientific adequacy are separate decisions. This report is not a rights determination or corpus release.
