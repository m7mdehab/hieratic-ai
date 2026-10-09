# W20 DATA-008 source expansion — blocked-readiness assessment

**Disposition:** source research and release-readiness infrastructure are recorded; a real `corpus_v1_release` is not available. No capability points, training items, benchmark gold, or expert-reviewed readings are claimed. Canonical task state was not edited.

## Verified cohort counts

The complete AKU-PAL receipt covers 240 distinct public sign IDs across 32 source text IDs. It records 240 per-item CC BY 4.0 statements. Of those, 63 Hieratic records passed the source-identity/provenance and original-media screen; 112 records identify as `Kursivhieroglyphen`, and 65 more Hieratic records lacked enough identity/provenance/media evidence for that screen. The report hashes 95 source media files (63 sign SVGs and 32 publication-scan reproductions), with 95 distinct SHA-256 values and no duplicate-byte groups. The 63 screened sign records yield only nine publisher inventory labels; these are a lower bound, not independent physical-support adjudications.

The exact-match public benchmark screen uses 266 R-017 metadata entries plus the W19 verified source receipt. It reads no sealed records. Sixty-three sign records match by exact publisher ID or inventory token and are positive overlaps. The remaining 177 lack a literal hit in this metadata snapshot but remain unknown and quarantined. All records remain training-ineligible.

The separate photo intake screens seven current Commons file revisions across three physical accession groups: Cat.1880, Cat.2169, and S.6759. All seven bounded original-byte responses produced SHA-256 hashes without writing source bytes to disk. The Cat.1880 p01 digest, SHA-1 claim and byte count match the independently accepted R-026 original-source receipt. Five images decoded; both Cat.1880 photographs exceeded the 100-megapixel safe-decode ceiling and are recorded as hash-only. The other six publisher SHA-1 values are retained as file-page claims but were not independently compared against bytes in this W20 receipt. The museum cohort has zero literal accession matches in the R-017 snapshot; all seven stay unknown/quarantined.

The accepted R-025/R-026 research documents a Cat.1880-to-Pleyte/Rossi historical-edition bibliographic relationship and one original photo/PDF byte receipt. It does not identify a precise photograph side, PDF page/plate index, physical line, aligned stroke sequence, or modern transcript reuse right. Cat.2169 is retained as a monogram/inventory visual control, not as ordinary continuous text gold.

## Seven work-package verdicts

| Package | Verdict | Evidence and boundary |
|---|---|---|
| A — deterministic census | Completed with target gap | 240 completed IDs and their response hashes are enumerated. A 500-ID/200-text-group expansion attempt ran for about 26 minutes without producing a complete receipt; partial rows were discarded. The approximate 25-support research target was not met. |
| B — item rights and identity | Screened, fail-closed | All 240 records expose per-item CC BY 4.0 metadata; only 63 pass the Hieratic identity/provenance/media screen. Publisher labels are not independent scholarly verification or production authority. |
| C — original sign media | Completed for screened cohort | 95 media files were hashed and signature/content checked in bounded memory; no bytes were committed. SVG active/external-content checks and exact sign-ID URL binding are implemented. |
| D — manuscript photos | Completed as research intake | Seven current files across three physical supports were screened and SHA-256 hashed in memory. Photo terms do not license editions/transcriptions. R-026 independently matches Cat.1880 p01. No photo-to-line pair or DATA-002 acquisition is claimed. |
| E — benchmark leakage | Screened, all quarantined | Positive literal overlaps and no-literal-match results are reported separately. Every negative string result remains unknown; no sealed benchmark files or labels were read. W19 media hashes are included in the cross-cohort duplicate screen. |
| F — release readiness | Blocked | Production stays hard-disabled pending an independently protected trust root, independent institutional/reviewer authentication, substantive rights decisions, expert-reviewed gold, text permissions, and leakage-safe train/dev/test evidence. |
| G — tests and repeatability | Local focused and most full QA passed; hosted exact-head pending | Focused corpus release tests: 41 run, 35 passed and six Linux-only race/symlink tests skipped on Windows. Governance: 34 passed; data: 221 run, 206 passed and 15 skipped; evaluation: 311 passed; state and source registry validation passed; synthetic validate/build/audit/readiness CLI passed. Full suites used a clean detached test worktree with `core.autocrlf=false` to preserve upstream byte-pinned sources. Linguistics ran 110 tests: 109 passed and one errored because this Windows account cannot create a symlink (WinError 1314); the hosted Linux Project Governance workflow is the final exact-head check. |

## Evidence files and digests

- Per-sign source identities, individual response hashes, 95 media hashes, exclusions, source strata, and benchmark decisions: [W20 AKU-PAL census JSON](w20_aku_pal_sign_census.json), evidence digest `26516fa4701a050aada1bbb044383035c44afd6496e7acf04cbc2504ac3e48a2`.
- Seven per-file museum photo records, current revision IDs, licenses, byte sizes, dimensions/decode state and hashes: [W20 museum photo intake JSON](w20_museum_photo_intake.json), evidence digest `e531f25fcf114059b920db3199c397555521bd65ce35a0257356b770f2f1d871`.
- Combined item-by-item manifest, including W19 media-hash cross-check and R-026 Cat.1880 p01 corroboration: [W20 receipt manifest JSON](w20_item_receipt_manifest.json), evidence digest `9db85fc1f1c688adbb60905e3b7c8c7d1b7e5ee3f10eac634eb2eefdc983468c`.
- Shared contract: [W20 evidence JSON Schema](w20_source_evidence.schema.json).
- Machine-readable blocked readiness matrix: [W20 readiness assessment JSON](W20_READINESS_ASSESSMENT.json).

Source API and license guidance: [AKU-PAL reuse FAQ](https://aku-pal.uni-mainz.de/faq). Exact photographed-object records: [Cat.1880](https://collezionepapiri.museoegizio.it/en-GB/material/Cat_1880), [S.6759](https://collezionepapiri.museoegizio.it/en-GB/material/S_6759), and [Cat.2169](https://collezionepapiri.museoegizio.it/en-GB/material/Cat_2169). Detailed same-support and historical-edition evidence is in [R-025](../../docs/research/R025_CC0_PHOTO_EDITION_AUDIT.md) and [R-026](../../docs/research/R026_CAT1880_ORIGINAL_MEDIA_PREFLIGHT.md).

## Blockers and next work

The main blocker is the lack of a genuinely reviewable, benchmark-independent, rights-cleared image/line/gold cohort. The best next source experiment is one R-026-backed Cat.1880 p01 photograph and one exact Pleyte/Rossi plate: establish face/side and plate index, register a visible stroke sequence to a physical line, obtain independent Egyptologist adjudication for a reuse-authorized reading, and then test object/image/edition lineage against the public benchmark roster. Production admission still requires governance-protected authority onboarding and a separate adequacy review; the sign census itself is evaluation-overlapping and cannot supply training data.
