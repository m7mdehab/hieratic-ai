# Wave 31 — independently reviewed genuine original-photo versus printed-source domain detection

**Actual experiment completed on 2026-10-12 UTC.** This is a true source-domain CPU learning study on verified real pixels, not a preparation-only packet. Main PR [#185](https://github.com/m7mdehab/hieratic-ai/pull/185) merged as `9c8aa7004dc0fef266879d5e53cdf175da7e827b`; exact original GitHub-hosted run [38317822070](https://github.com/m7mdehab/hieratic-ai/actions/runs/38317822070) SUCCESS; final PR exact-head Project Governance run [38318006799](https://github.com/m7mdehab/hieratic-ai/actions/runs/38318006799) SUCCESS. Full 74 individual original source hashes, original Met SHA, all train-only hyperparameters and exact heldout contingency are [archived as source-original numeric JSON](../research/W31_ACTUAL_ORIGINAL_PRINT_PHOTO_DOMAIN_CPU_RESULTS.json); no original publisher images or museum pixel files committed.

## Source and preregistration chain

1. The original W31 source population of **Met 555779** was prospectively frozen before API content retrieval (see [W31 original prereg](W31_PRINT_PHOTO_OOD_PREREG.md)). Real original museum API eligibility/identity requirement failed; **no heldout original pixels scored**, run [38317588714](https://github.com/m7mdehab/hieratic-ai/actions/runs/38317588714) FAILED with explicit eligibility exception. This is a fully preserved negative source-access outcome.
2. A **different public-domain Hieratic papyrus** — The Metropolitan Museum of Art [551786](https://www.metmuseum.org/art/collection/search/551786), *Book of the Dead of the Priest of Horus, Imhotep (Imuthes)*, physical accession **35.9.20a–w** — was selected from public catalogue and independently preregistered in **commit `a24c970152e2c1d7e8eef8e215c4bf257af37062` before original API original-image bytes were opened**. This is a fresh **physical museum accession from Met**, different from prior train-only Met 546511 and 554654.
3. Strict official Met Open Access museum record asserts Public Domain, exact Egyptian Art and Papyrus metadata; genuine original `CRDImages/eg/original` 4,000 × 970 JPEG, original **1,755,227 bytes**, SHA-256 `46a03fa43462372ccc7ce481f3f5b8b0627b887a97f815be10545779ec946f5e`. Original bytes used ephemerally on hosted machine and absent from repository.
4. The licensed historical Tokyo IIIF printed Möller sign scans are **NOT photographed papyrus sign ground truth**; 74 frozen published sign JPEG images across 11 Gardiner labels from prior W30, with original source hashes and printed-page identities. Training printed crop count 49 (vols I–II), prior-exposed printed vol III heldout 25. Previously seen Met original CC0 photo sources 546511 and 554654 provided deterministic 32×32 unlabeled photographic tiles, 32 per original physical accession (**64 train-side tiles**). New photo from 551786 provided **32 new heldout photographic tiles**. No overlap of museum accession between photo train and test.
5. Fit **real supervised photo-versus-print image-DOMAIN ridge classifier** on original HOG/ink density image features. Positives=publisher printed sign crops; negatives=original photo tiles from known training objects. Training-side dev alpha grid [0.01, 0.1, 1, 10], selected alpha 0.01 on 54/56 original dev examples, fixed binary domain threshold 0.5; nothing tuned on original Met 551786 heldout photo.

## Exact actual source-domain result

| Heldout source type | Correct | Incorrect | Correct-domain fraction |
|---|---:|---:|---:|
| Historical printed Hieratic sign crop, Möller vol III (**previously W30-exposed**) | 25 | 0 | 100% |
| **NEW public-domain photographed papyrus** Met object 551786 | 31 correctly rejected | 1 falsely admitted as print | 96.875% |
| Combined test, 57 original images/tiles | **56** | **1** | 98.2456% raw accuracy |
| Balanced source-domain classification | | | **98.4375%** |

[Full actual-source receipt](../research/W31_ACTUAL_ORIGINAL_PRINT_PHOTO_DOMAIN_CPU_RESULTS.json): `new_photo_false_admitted:1`, `new_photo_rejected:31`, `true_print_accepted:25`, `print_rejected:0`, `balanced_domain_accuracy:0.984375`.

The older W30 *printed-classifier-only* confidence-gating approach **rejected 0/64** tiles from different, previously observed Met papyri. That establishes a serious old source-domain rejection weakness, but **W31 versus W30 is not a direct same-test-cohort or same-model comparison**; also W31 explicitly trained on photographic-domain negative examples while W30 printed confidence gate did not. Do not claim a statistically controlled OOD improvement magnitude or generalize 31/32 photo rejection to all museum photos, to glyph detection, to sign transcription or to a Hieratic model accuracy percentage. Another papyrus source with no tuning will be necessary for stronger source transfer estimates.

### Science and provenance verdict

**ACCEPTED as a NEW, independently hosted real-original-photo/printed-image supervised DOMAIN-adaptation research axis**, source rights and actual original pixels verified on GitHub-hosted runner. Scientific strengths: actual two authentic image domains, distinct museum photo accession test, pre-frozen new source identity, exact source SHA, full train/test denominator and explicit first-candidate failure. Scientific limits: narrow two-source train photograph cohort, old printed volume III examples used in prior W30, random tiles include backgrounds not adjudicated ink/signs, simple domain classifier may learn photography/page texture rather than Hieratic script, rights on printed Tokyo source use governed separately, manuscript ancestry to sealed benchmark not cleared, no professional palaeographer original-glyph gold, no image→original Egyptian text decoding.

**Weighted reading-science gate remains 34.5/100**, active tasks DATA-008 0/3, VLM-001 0/2, LING-003 0/2, EVAL-003 0/1.5. Original trained Hieratic glyph/photo text-reading models accepted: **0**. If canonical qualitative research-space coverage separately accepts a new method, **22→23/100** is justified for first successful supervised print-versus-genuine-original-photo source-domain separation with unseen museum accession. Do not score this as an additional accepted Hieratic reading experiment: original sign accuracy on photo = **unmeasured**.

## Next actions that do not wait for expert gold

- Train a *document-local* ink-stroke segmentation/line proposal on public-domain original Met images with realistic source-independent negative controls and line consistency metrics. Preserve source-aspect and report provenance, not transcription scores.
- Treat domain detector as **routing/abstention** preflight: a visually photographed papyrus region must not be passed to a printed-glyph classifier with its confidence misinterpreted. Replicate on several **new public-domain museum physical objects**, not only Met 551786, and report sensitivity to crop location, texture, noise, and across-provider domain changes.
- Continue actual Egyptian morphology and multiword translation model fitting on licensed publisher corpora, freezing genuinely new heldout corpus families. Do not reuse previously exposed W30 Amarna or W29 Ramesside German references as blind gold.
- Expert manuscript adjudication can improve eventual reading-certification validity but **does not stop** these legal, reproducible public-data experiments. No paid inference/outreach/sealed benchmark exposure.

**Repo/CI:** W31 source code, frozen C1/C2 preregs, tests and GitHub workflow are on main via #185. The W30-named branches created before discovering W30 already complete were not merged and should not be presented as independent wave results.
