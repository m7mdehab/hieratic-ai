# Sign identities and palaeographic mappings

`schemas/sign_mappings.schema.json` keeps three distinct claims: observed Hieratic form, hieroglyphic correspondence, and transliteration value. Null/unresolved values are valid and preferred to fabricated equivalence. Context and historical qualifiers are attached to candidate claims. Relations are many-to-many and each mapping/variant carries provenance citations with a claim scope and optional locator; status and confidence do not replace evidence.

Run `python -m tools.sign_mappings validate FILE`, `lookup FILE ID`, or `export FILE [--format json|yaml]`. The validator checks schema, unique record/variant/relation/citation IDs, citation presence for supported claims, references, duplicate edges and cycles in `variant_of`/`subclass_of`. Citation URLs are not treated as proof: `verified_metadata` records that reference metadata was checked, while scholars still review the cited content and claim. No source metadata or historical mapping is included in the synthetic example.

To add a real mapping, cite a verifiable scholarly source and a precise locator, state which representational layer it supports, preserve competing readings as disputed candidates, and review conflicts independently. Never infer transliteration from a hieroglyphic glyph or use a hieroglyphic rendering as the observed Hieratic shape.


## W8 publisher-pinned HPDB ID concordance (real reference metadata)

The new offline lookup uses **all 937 genuine source-published cross-system concordance records**, preserved byte-for-byte in data/mappings/hpdb/id_correspondence_ccby4.json. Its Git blob SHA-1 **9de1829304fcb2c3b5ee054fd7bd0e6f1dea964b** equals the upstream public/data/id_correspondence.json blob in immutable hp-db/hp-db.github.io commit **a8cfcf52632487cf1d61a5793d84c9b2f7192d5a**. The matching source manifest pins attribution, licensing, original identity and no-training status.

**Source and licence:** https://moeller.jinsha.tsukuba.ac.jp/en/datasets/ (CC BY 4.0). **Publisher citation:** Masakatsu Nagai, Toshihito Waki, Yona Takahashi and Satoru Nakamura, *Hieratische Paläographie DB*, https://moeller.jinsha.tsukuba.ac.jp/ .

### Try it

~~~bash
python -m tools.sign_mappings hpdb-verify
python -m tools.sign_mappings hpdb-verify --disagreements
python -m tools.sign_mappings hpdb-search --field moller_no --exact 1
python -m tools.sign_mappings hpdb-search --field gardiner_no --exact A26
python -m tools.sign_mappings hpdb-search --field unicode_cp --exact U+1301E
python -m tools.sign_mappings hpdb-search --field aku_id --exact A0890
python -m tools.sign_mappings hpdb-search --field gardiner_no --exact D50 --limit 5
~~~

Supported exact-query fields: moller_no, gardiner_no, unicode_cp, unicode_char, jsesh, mdc, hieroglyphica, match_type, tsl_id, aku_id, phrp_id, isut_id, dpdp_id. No fuzzy coercion, false equivalences or implicit transliteration. Ambiguous, compound, unknown and unmatched publisher types are preserved. Multiple Möller references sharing a Gardiner or Unicode string are all returned with bounded pagination.

### Verified metadata joins and disagreement report

The bundle links publisher Möller numbers to the existing **2,065 real sign-index metadata** entries, preserving each volume/item ID. Reference correspondence census: **628 matched, 158 compound, 124 unmatched, 27 unknown**. For **2,053** sign-index records, the publisher's two datasets contain the exact same printed Gardiner notation; for **12**, the printed notations differ. Both competing source strings are retained and flagged; no historical label is auto-corrected or ranked as more authoritative.

| HPDB item | Möller | Index Gardiner | Concordance Gardiner |
| --- | --- | --- | --- |
| 122001 | 225 | G235 | G235+X1+Z4 |
| 145001 | 473 | U35/U34 | U35 |
| 163007 | 656 | Z1 | (Z1*) |
| 165017 | 683 | O39 | V2 |
| 169010 | 331+574 | N35+X1 | N35+Aa1 |
| 170006 | 91+200B | D21+Z7 | D21+Z1 |
| 174007 | 329+561 | N33+Z3 | N33+Z2 |
| 321001 | 225 | G50 | G235+X1+Z4 |
| 323008 | 251 | I31 | I31c |
| 339009 | 414 | S6=S1+S3+V30 | S5=S1+S3 |
| 339010 | 413 | S3a | S3 |
| 365004 | 331+560 | N35+I9 | N35+Z4 |

**Boundary:** These are cross-database references for printed Möller sign notations, NOT authenticated single original manuscript images, original document witnesses, independently authored diplomatic gold or measured classifier accuracy. CC BY covers HPDB project metadata; underlying Tokyo-hosted IIIF page scans and third-party Wikidata-linked image files have separate rights. No image bytes are downloaded or inferred. This cannot admit DATA-008 production training, VLM certification or HieraticBench development, and does not earn a second DATA-005 capability award.

### Integrity and regression verification

~~~bash
python -m unittest tests.data.test_sign_mappings -v
python -m unittest discover -s tests/data -v
python -m tools.sign_mappings hpdb-verify --disagreements
~~~

Tests check the real upstream Git blob identity, 937+2,065 census, all 12 divergence item IDs, deterministic exact lookup, truncation, rejection of forged source/rights manifests, changed sign-index data and no silent download. The operation is offline and requires no external subscription, GPU, Egyptologist hiring or annotation rights.
