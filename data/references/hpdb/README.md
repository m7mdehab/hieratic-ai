# HPDB published metadata — real 2,065-row reference intake (R-023)

**Source:** [Tsukuba/Tokyo Hieratische Paläographie DB](https://moeller.jinsha.tsukuba.ac.jp/en/datasets/) official published CC BY 4.0 sign-index datasets. This folder contains **actual upstream-derived sign-index metadata**, not synthetic fixtures and not downloaded image bytes.

**Source revision:** `hp-db/hp-db.github.io@a8cfcf52632487cf1d61a5793d84c9b2f7192d5a`, original `public/data/index.json` Git blob SHA-1 `6efc36471b47255cfc03f6ba8cf9c887a293bb89`. It was fetched through GitHub repository files, parsed against the real published field schema, and normalized into three **volume-partitioned** JSONL files on 2026-10-09. Manifest contains the complete population and component rights.

**Publisher citation:** Masakatsu Nagai, Toshihito Waki, Yona Takahashi and Satoru Nakamura, *Hieratische Paläographie DB*, <https://moeller.jinsha.tsukuba.ac.jp/>. The dataset licence is **Creative Commons Attribution 4.0**. Preserve attribution, changes and citation in derived metadata.

## Actual ingested records

| Printed Möller volume | Unique metadata entries |
|---|---:|
| 1 | 738 |
| 2 | 670 |
| 3 | 657 |
| **Total** | **2,065** |

Across all volumes: **214 distinct printed-page groups**; **1,626** main sign items, **251** number items, and **188** ligature items. **1,439** printed Gardiner labels fit one parsable token; the remaining **626** are compound, uncertain or non-single and remain `single_sign: null`, never coerced into a false single-sign class.

### Format

Each JSONL line has source `id`, printed `vol` and `page`, category `kind`, original `hieratic` and `gardiner_printed` notation, optional `single_sign`, linked printed-page IIIF **reference URL** (`iiif_ref`), and stable `item_url`. Printed page group = `MOLLER-V{vol}-P{page}`. Every record is a published palaeography *facsimile* sign reference, **not** a source manuscript/expert diplomatic text. A printed-page group is necessary but **not sufficient** to prove original manuscript source independence.

### Licensing boundaries and scientific honesty

The HPDB project licenses its own metadata/curation data CC BY 4.0. The scanned Möller printed-page images are supplied by University of Tokyo's IIIF and **underlying image reuse rights have not been independently verified**. Those image URLs are source pointers, not downloaded files or model-usable pixels. No source photo, editor text, original manuscript source identity, peer-review gold, legal corpus admission or measured VLM accuracy is inferred from this bundle.

**Allowed now:** reproducible palaeographic lookup, label vocabulary/concordance analysis, source bibliography, disambiguation, lexicon metadata retrieval and machine-readable database engineering with attribution. **Not allowed automatically:** pull Tokyo scans into model training; call this a 2,065-image corpus; treat these 2,065 sign records as independent original handwritten papyri; merge source aliases into official `HieraticBench` development; use noncommercial/editor-restricted reading material without correct permission.

### Validate
```bash
python -m unittest tests.research.test_hpdb_reference -v
python -m tools.hpdb_reference --index /path/to/actual/publisher/index.json --output /path/to/new-independent-output.json
```

The importer consumes complete **locally supplied** official-shaped original index files; the checked-in data is a normalized publisher-derived metadata snapshot. Optional checking against upstream full JSON is independent of CI, to avoid third-party network dependency and unbounded original-image downloads. **No current dataset release or image/gold experiment** is claimed.
