# W19: Original licensed Hieratic signs — exact binary gate

Aim: turn W17's eight genuine publisher original **AKU-PAL sign metadata** records on six physical manuscript supports into verifiable per-item image file digests. Original public Mainz source [image reuse FAQ](https://aku-pal.uni-mainz.de/faq) states that individual imagery may be reused under each original **record's own license**. This W19 execution is bounded to the eight item IDs already inspected in W17.

- Fetch each source-specific JSON and prove stable source ID, response status, content type and original JSON SHA256.
- Determine item-level license from license fields (never from unrelated page text, or from another record) and admit media probing ONLY when the exact item's license is **CC BY 4.0**.
- Extract actual asset links from original metadata, same publisher host HTTPS only. Fetch a maximum of five asset files per eligible item in a bounded 4MB memory-only stream, inspect content type and image magic, hash the original bytes. **Original media binaries are never written to Git or uploaded as artifacts.**
- Publish a source-hash/rights/URL-only receipt for independent retrieval. Unknown formats, absent image endpoints, asset mismatches and rights failures remain blocked.
- The source's grapheme/identifier fields are **publisher annotations** not a second independent gold review. Training and gold admission remain false. Metadata and sign fragments are not source-linked manuscript **whole lines**. Benchmark overlap, manuscript source isolation and independently authenticated reviewer authority remain mandatory.
- Any result is W19 SOURCE IMAGE EVIDENCE only; DATA-008 full `corpus_v1_release`, training, inference scores and project capability progress unchanged unless separately independently certified.

## Executed real-source evidence — exact-head hosted 2026-10-09

**VALIDATED:** [W19 original binary run 37991651242](https://github.com/m7mdehab/hieratic-ai/actions/runs/37991651242), with source-original JSON item record and binary content read from the Mainz publisher only. All **8/8** distinct original sign record responses verified, all **8/8** per-record `details[].items[].licenseTxt` values explicitly linked to [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), **15/15** sign-specific media bytes read and SHA256 hashed with original asset MIME type and file magic:
- **8** `/img/data/ht/svg/ht_{id}.svg`: publisher sign tracings;
- **5** `/img/data/ht/scan/ht_{id}_2.webp`: digitized publication scan figures;
- **2** `/api/svg/ht_{id}.svg/outline`: derived SVG outlines.

All original media were retrieved ONLY AFTER the exact item's rights label was parsed; generic `hg_*.svg` hieroglyph references were excluded from the original Hieratogram population. Individual source artwork was not committed, uploaded, used for model training or linked with any supposed full-line text. The immutable numeric/by-hash receipt is `data/releases/w19_aku_pal_original_image_receipts.json`. Every receipt includes publisher media URL, original SHA256/bytes/type, source record and physical-witness provenance, and preservation of unresolved independent science/rights-release gates.

**Important limitations:** traced SVG and Möller publication scan signs are scholarly derivative image specimens, **NOT independently acquired original papyrus photograph pixels**. Their publisher grapheme annotation is not new blind expert gold. Eight signs and six source physical witnesses cannot satisfy real corpus scientific adequacy or original full-line image/transliteration requirements. Separate rights admission, 1:1 sign-label scholarly review, independent source-object and near-duplicate benchmark segregation, larger cohort and train/dev/test readiness remain pending. DATA-008 active 0/3 and overall goal 34.5/100, historical coverage 14%; no percentage credit.
