# W17 DATA-008 evidence acquisition — AKU-PAL sign-image candidates

## Evidence-first discovery
AKU-PAL Mainz is a high-potential, **real sign-level Hieratic image + original manuscript provenance** candidate. Exact publicly cited per-item records supply named creator, licence, physical witness, recto/verso, line/column and dating; compare the [publisher per-item image FAQ](https://aku-pal.uni-mainz.de/faq) and individual pages:
https://aku-pal.uni-mainz.de/signs/6036 ;
https://aku-pal.uni-mainz.de/signs/2448 ;
https://aku-pal.uni-mainz.de/signs/23466 ;
https://aku-pal.uni-mainz.de/signs/6066 ;
https://aku-pal.uni-mainz.de/signs/32833 ;
https://aku-pal.uni-mainz.de/signs/56377 ;
https://aku-pal.uni-mainz.de/signs/5862 ;
https://aku-pal.uni-mainz.de/signs/5447 .

All 8 displayed records explicitly say **CC BY 4.0**, show named creators and actual physical line positions. They represent **six original physical witness identifiers**, NOT eight independent papyri (UC32782 repeated twice, Louvre E3226 A+B repeated twice). The publisher FAQ says **individual images may be used and redistributed under the license stated on each item**; screenshots of mixed views have different limitations and are NOT treated as freely reusable original image bytes.

## What this definitely does not prove
A record webpage and its per-item CC BY text do not establish:
- exact URL/byte hash/decoded dimensions for the separately delivered sign-image file,
- original publisher's interpretation of sign ID/class independently reviewed against image pixels,
- a full physical manuscript line-to-transliteration target,
- absence of physical witness/near-duplicate overlap with sealed HieraticBench,
- institutional/reviewer authority and signed release rights evidence,
- adequate cohort coverage across real physically distinct documents,
- any DATA-008 corpus_v1_release or specialist/VLM accuracy.

The W17 probe only accesses **8 exact sign-record HTML pages**, plus 3 sample metadata API paths, with bounded reads and SHA-256 receipts. It **does not download images or modern editorial transcriptions**. It records missing API access truthfully as unavailable; it cannot turn an accessible page into gold. Original page hashes are ephemeral metadata-only artifacts. Synthetic regression tests enforce origin refusal and bounded responses.

## Decision
Most promising copyright-compatible lead for future **sign recognition and visual retrieval**: use individually licensed AKU-PAL sign images **only after actual image URL/bytes, exact image-specific license, provenance and independent reviewer/overlap verification**. This improves DATA-008 source triage but does **not** meet the separate corpus v1 scientific admission gate, especially because sign specimens do not supply complete line transliterations.

DDD is rich in 159 images and 50 papyri, but CC BY-NC-SA 4.0 and per-image copyright preclude silent addition to the default permissive release. HPDB's 2,065 metadata sign items are CC BY 4.0, but underlying University of Tokyo digitized book image layers have independently listed rights.

**Current project:** DATA-008 active 0/3; verified capability 34.5/100, research coverage 14%. No production admissions; no model trained, no new percentage claim.
