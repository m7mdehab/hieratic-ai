# DATA-008 corpus assembly and release

`tools.release_corpus` assembles one release from the accepted DATA-001/002/003/004/005/006/007 and EVAL-004 contracts. It reads manifests only and never downloads source objects. A bundle is validated as a whole; any broken identity, rights gate, split assignment, gold target or artifact hash refuses publication. A successful immutable output contains `release-manifest.json`, `export.jsonl`, `dataset-card.md`, `rejection-report.json`, and `audit-trail.json`. The export retains layer-specific annotation values and alternatives, alignment hypotheses, and aggregate review state; reviewer identities, individual rationales, and private reviewer evidence are redacted. The image itself stays in the DATA-003 artifact store and is referenced by SHA-256.

## Commands

```text
python -m tools.release_corpus validate data/releases/examples/synthetic-test/bundle.yaml
python -m tools.release_corpus build data/releases/examples/synthetic-test/bundle.yaml --output out/synthetic-test-v1
```

`schemas/dataset_release.schema.json` defines the input bundle and the `$defs.releaseManifest` output contract. Bundle file references are relative to the bundle directory; absolute paths, path traversal, symlinks, missing files, oversized manifests/artifacts, hash mismatches, and existing output destinations are refused. On Linux the builder opens every output-parent component without following symlinks, writes all five files in a private sibling directory, flushes them, and commits once with `renameat2(RENAME_NOREPLACE)`. The destination is therefore either absent or a complete release; an empty directory or symlink created by a competing publisher wins the name and is never replaced. If the filesystem lacks atomic no-replace rename support, publication fails closed. Windows uses its no-replace directory rename semantics. Version identifiers hash canonical JSON over sorted, hashed inputs, split identity and per-item records; generation timestamps are excluded.

`synthetic_test_release` is exclusively a structural fixture mode. It retains a synthetic flag and cannot be renamed into `corpus_v1_release`. Synthetic identifiers, clearances, rights references and readings do not constitute an independent license, scholarly mapping, review or gold score. `corpus_v1_release` additionally requires complete real DATA-002 acquisition, source-registry permission for training and redistribution, item-level annotation and mapping permissions with evidence, explicit intended use and attribution, compatible split and image hashes, reviewed benchmark overlap, resolved near-duplicate checks, and per-item reviewed scorable gold. Empty train/dev/test partitions are not a production corpus.

## W5 admission evidence and readiness

The `authorization_evidence_path` envelope follows admission schema 1.1.0 and is a structural contract for claims. Its receipt covers canonical UTF-8 JSON with the receipt omitted, so Ed25519 verifies that a private key signed those bytes. It does not prove an institutional identity, authority, reviewer role, permission, or truth of the contents. Document URIs and `sha256` values are submitter declarations: this engine does not fetch the referenced documents, verify their bytes, or make substantive rights determinations. The schema therefore fixes document state to `reference_only_unverified`, `verified_content_sha256` to null, and substantive determination to `not_assessed`.

`data/releases/trust_anchors.yaml` is repository-controlled metadata, not an independently protected trust root. A contributor can syntactically add a key or change its status; neither operation establishes authority. Production authorization is hard-disabled in code until overseer-governed onboarding provides a protected root and independently authenticated institutional and reviewer identities/roles. No repository YAML, signed receipt, environment variable, or caller argument can override this block. Structural checks for key syntax, scope, dates, receipt binding, revocation, asset claims, role conflicts, and provenance remain useful regression defenses but do not authorize production.

Run `python -m tools.release_corpus assess data/releases/examples/synthetic-test/bundle.yaml --json-out out/readiness.json --report-out out/readiness.md` to report three separate states: software integrity, evidence admission, and scientific corpus adequacy. It cross-checks the R-016 roster against the pinned R-017 266-record public metadata census and 15-entry accession crosswalk, reporting nearby institutional-family witnesses and unresolved identity/image/right gates. A literal no-match is never treated as independent clearance; every R-016 candidate remains blocked. The command makes no legal or scholarly determination and invents no minimum corpus-size threshold. `python -m tools.release_corpus audit <bundle> --release-dir <published-release>` rebuilds expected outputs from current inputs and compares the five required files byte-for-byte, rejecting extra, missing, symlinked or altered artifacts.

The exact canonical serialization is UTF-8 JSON with sorted keys, no insignificant whitespace, `ensure_ascii=False`, and compact separators as produced by `tools.release_corpus.canonical`. Reviewer IDs, names, and role strings in a signed document are claims. Distinct names do not demonstrate that the people exist, reviewed the material, agree with one another, or hold the asserted authority. Independently authenticated reviewer attestations and conflict/disagreement review are future onboarding requirements. Catalogue records, public policy pages, and contributor assertions alone are not item-level permission.

Published artifacts omit authorization-envelope contents, permission-document paths and signatures, reviewer identities, rationales, and reviewer-level evidence. They retain canonical payload digests, an explicit unverified status, public aggregate review states, and necessary source/item lineage. A digest does not publish or validate private source documents.

The checked-in fixture and deterministic output are under `data/releases/examples/synthetic-test/`; `demo-output-v5/` is the current synthetic test evidence. The prior `demo-output-v4/` remains an immutable historical synthetic artifact. Neither is a corpus release or training dataset.

The W9 source investigation is recorded in [W9 source-pair readiness](../../data/releases/W9_SOURCE_PAIR_READINESS.md) and its [machine-readable evidence summary](../../data/releases/W9_SOURCE_PAIR_READINESS.json). It records two private image files across two physical supports but zero verified reusable line readings, zero independent line alignments, and zero admitted production items. The exact Cat.1883 + Cat.2095 RIME image is an article-hosted processed figure; its image CC BY 2.0 evidence is separate from the unverified article-text reuse terms. No source was registered and production remains hard-disabled. These W9 artifacts do not alter or supersede the canonical readiness report above.

## W20 source expansion and original-photo intake

Wave 20 adds a bounded AKU-PAL public-record census and a separate current-file Commons photo audit. The reproducible commands, exact source hashes, per-item media receipts, source identity, exclusions and benchmark-screen decisions are recorded in `data/releases/w20_aku_pal_sign_census.json` and `data/releases/w20_museum_photo_intake.json`; their shared contract is `data/releases/w20_source_evidence.schema.json`. Run the AKU-PAL scan with `python -m data.releases.w20_aku_pal_source_audit --output <path> --target-items 240 --text-groups 32`; run the fixed museum candidate audit with `python data/releases/w20_museum_photo_intake.py --output <path>`. Both commands validate the result schema before writing. Source-image bodies are bounded, streamed into memory, hashed and discarded; no image bytes are committed. Each receipt has an evidence digest that excludes the retrieval timestamp. Pinned R-017 and W19 provenance hashes are computed from verified Git blob bytes after checking that the working file content matches its blob, so Windows CRLF checkout conversion does not change report identities.

The completed AKU-PAL receipt screens 240 unique sign IDs across 32 source text IDs and 32 source-provided inventory labels. All 240 show item-specific CC BY 4.0 metadata; 128 report `Hieratisch` and 112 `Kursivhieroglyphen`. Sixty-three passed the more restrictive Hieratic + identity/provenance + media screen; 177 were excluded for unresolved/non-Hieratic identity or provenance. The 63 include 95 individually byte-verified source media files with 95 unique SHA-256 values (63 sign SVGs, 32 publication-scan reproductions; zero hash-duplicate groups). Their nine identity-screened inventory labels are only lower-bound publisher labels, not independent physical-witness adjudications. All 63 also matched the public R-017/W19 source registry by exact sign ID or inventory token and are confirmed benchmark-overlap quarantines; the remaining 177 have no literal match but remain unknown/quarantined. A 500-ID / 200-text-group expansion attempt was stopped after about 26 minutes without a completed receipt; partial response rows were discarded, so the verified cohort remains 240 IDs and the approximate 25-support research target is unmet.

The AKU-PAL API record license applies per exact sign record/image as described by its [reuse FAQ](https://aku-pal.uni-mainz.de/faq). Exact CC BY 4.0 / CC0 records with identity evidence are source-screened only; this does not independently authenticate the publisher's sign label or establish manuscript-photo lineage, expert gold, benchmark independence, or training admission. Generic hieroglyphic comparison drawings are excluded from Hieratic specimen totals. Publication scans, publisher sign drawings and derived outlines are separately typed and exact-hash deduplicated; they are not counted as independent physical witnesses. Exact matches against the pinned R-017 public metadata or W19 source receipt are positive benchmark overlaps. A no-literal-match result is not independent clearance, and all unresolved cases stay quarantined.

The separate [Museo Egizio collection records](https://collezionepapiri.museoegizio.it/) and current Commons file revisions identify the Cat.1880 pages, S.6759 ostracon, and Cat.2169 inventory/monogram views as one group per physical accession. Commons CC0 applies to those exact photo file pages only; it does not license a scholarly edition or partner transcription. Cat.2169 remains a visual control, not an ordinary line-transliteration target. Cat.1880 contains high-pixel photographs that exceed the configured safe decode ceiling: response SHA-256 and publisher SHA-1 claims are recorded, and p01 has an independent exact byte/SHA-1 confirmation in R-026; decoded dimensions are not asserted for those two W20 files. All photo candidates remain `UNKNOWN_QUARANTINED`, not DATA-002 acquisitions or train/dev/test items.

The latest accepted [R-025 document audit](../../docs/research/R025_CC0_PHOTO_EDITION_AUDIT.md) establishes a museum bibliography link between the same Cat.1880 papyrus and Pleyte/Rossi's nineteenth-century volumes, whose exact Commons edition pages carry Public Domain Mark claims. The accepted [R-026 source receipt](../../docs/research/R026_ORIGINAL_SOURCE_BYTE_RECEIPTS.json) independently verifies new Cat.1880 p01 and a volume-2 PDF byte hash. The W20 p01 photo receipt matches R-026's exact byte count, SHA-1 and SHA-256. This corroborates source bytes and a document-level bibliography only: no exact photo side, plate index, stroke/line registration, or modern TPOP transcription permission follows from it. All Cat.1880 views, the historical volume and related derivatives remain one physical support for split/leakage screening.

The photo receipt records seven current Commons files across three accession-level support groups: Cat.1880 (two views), Cat.2169 (two TIFF originals plus two JPEG views/derivatives) and S.6759 (one TIFF). All seven bounded byte streams produced SHA-256 hashes; Cat.1880 p01 additionally byte-matches R-026's source SHA-1 and file size, while the other six publisher SHA-1 claims are retained without an independent comparison in this pass. Five files decoded and yielded dimensions/dHash; the two Cat.1880 originals exceeded the 100-megapixel decode ceiling and are hash-only. The public R-017 screen found zero literal accession matches for the museum cohort, which remains unknown/quarantined.

These source receipts are research evidence, not a production release. The supported source counts, image hash verification, and metadata-only benchmark checks cannot establish a leakage-safe split, rights determination for scholarly text, actual line-transliteration alignment, blind expert review, or independent trust-root onboarding. Production stays hard-disabled and DATA-008 remains 0/3 until those separate evidence gates are satisfied.

## Blocked production assessment

The release engine is implemented for synthetic infrastructure validation, but production authorization is hard-disabled and no production corpus is claimed. Current repository records are metadata-only, conditional, non-commercial, per-item, restricted, unknown-rights, or evaluation-only. There is no independently protected trust root, authenticated reviewer authority, independently verified permission-document bytes/substantive rights determination, or complete set of real acquisitions, licensed annotations/mappings, reviewed alignments, and expert adjudications covering leakage-resistant train/dev/test partitions. The machine-readable [rights readiness inventory](../../data/releases/rights-readiness.yaml), [blocked release assessment](../../data/releases/BLOCKED_RELEASE_ASSESSMENT.md), [readiness JSON](../../data/releases/readiness-assessment.json), and [candidate-level readiness report](../../data/releases/readiness-assessment.md) describe the missing evidence. Do not treat this tooling acceptance as DATA-008 validation or award its three capability points.

## Admission workflow for future real material

1. Identify every source object in DATA-001 and verify the exact image, annotation and mapping rightsholders, license text, permitted training/development use, redistribution terms, attribution and modifications.
2. Acquire only after authorization, through DATA-002. Preserve retrieval identity and original byte hash; complete per-item license and benchmark-overlap reviews. `conditional`, `not_approved`, `metadata_only`, and `unknown` are not permissions.
3. Produce deterministic DATA-003 artifacts linked to those exact acquisition records. Keep originals and derived assets outside Git when policy or size requires it.
4. Validate DATA-004 annotations, DATA-005 evidence-backed mappings, DATA-006 alignments and DATA-007 independent review. Uncertain alternatives, missing gold, restoration, damage and disagreement stay represented; they are never converted to certainty to increase coverage.
5. Generate and validate an EVAL-004 split. Prove source-object, document, page, original/normalized image hash and reviewed near-duplicate separation. Keep HieraticBench and all known/possible duplicates quarantined.
6. Build a fresh immutable `corpus_v1_release` from the complete manifest bundle. Obtain independent review of rights, corpus adequacy, gold eligibility and release terms before treating it as a usable training corpus.

## Scientific limits

Corpus assembly is data plumbing, not a model experiment. It computes no capability score or reading metric. The current contracts do not define a scientifically accepted minimum sample size or subgroup coverage threshold; the engine enforces item-level identities, rights, review and split gates and refuses empty partitions, but corpus adequacy remains an independent overseer acceptance decision. No restricted images or benchmark answers are included in the repository fixture.


---

# W27 DATA-008 — original-manuscript-photo cohort admission decision and experiment ledger

**Branch:** `task/DATA-008-w27-original-pixel-cohort-and-specialist-baseline`
**Base verified:** `4b3cd5bc6a5807e0a2bce306920f9d51e42bce02`
**Decision:** no original-pixel image-label cohort currently meets the project's admission gates for development training or source-independent held-out visual evaluation. Do not train a classifier on the available candidate pixels. This is a positive, evidence-backed no-go decision, not a recognition experiment. DATA-008 remains active at 0/3.

## Frozen population and observed source evidence

The target population for this gate was frozen as the DDD publisher's 159 image records and the 17,885 publisher sample annotations, with all views/fragments joined by physical support before partitioning. DDD remains research-only CC BY-NC-SA content with per-image source photo rights still unresolved. The canonical W24 diagnostic split is preserved unchanged: 35 training supports, 7 development supports and 8 test supports, with 15,426 / 893 / 1,566 source-label counts and no support overlap. Those are metadata-label denominators; they are not visual-experiment counts. The C-B publisher split remains a distinct, not-yet-replayed split.

The existing DDD visual-admission executable was replayed with:

```powershell
python -m tools.research_ddd_visual_gate --output "$env:TEMP\w27-r033-ledger.json" --summary-output "$env:TEMP\w27-r033-summary.json"
```

Exact result:

- DDD universe: 159 images, 50 physical supports, 17,885 original scholarly annotation rows, 504 classes.
- Source metadata: all 159 image records link to TPOP document metadata; 38 copyright claims are placeholders; 48 distinct original copyright strings.
- Admission: **0/159** rights-approved images, **0/159** benchmark-cleared images, **0** image pixels retrieved, **0** training images, **0** held-out visual samples; no model trained and accuracy remains null.
- Cat.1880 source variants `003` and `004` remain one support.
- Exact publisher metadata locks reproduced: `papyri.json` SHA-256 `33265df94656e79a27c1c158756f0a2479173d00184c5212159ec1bb8414eb62`; `samples.json` SHA-256 `763944b29e06643131fa9fdbd14a2b169afe5961df80394fecfd152203584e46`; `classes.json` SHA-256 `5ff0181de57e1018058ba53e8e436e6e67a19fca290568ed0f9ea341af7afe18`.
- Private per-image ledger digest: `7bcb4dc2ccdb6acb4322b3bc81ec7c8b4845e05f6056b64d37510b59e2ea4664`. The ledger and aggregate run outputs remained in the local temp directory; no private or original media artifact was committed.

The 121 non-placeholder DDD copyright strings identify copyright/source claims (principally Museo Egizio scan credits, with a smaller number of named photographers). They are not training licenses. Zenodo states that the dataset is CC BY-NC-SA and that full papyrus images are courtesy of Museo Egizio with exact per-image copyright details in `papyri.json`; this does not independently establish the museum-photo reuse permission for any one image. See the [publisher record](https://zenodo.org/records/20553713).

## Alternative-source and benchmark gate

| Candidate | Positive evidence | Exclusion from this experiment |
|---|---|---|
| DDD annotations + images | Genuine publisher polygons and class labels; 50 physical supports; metadata links each sample to a known image ID and class. | Annotation-to-source-image pixel binding is not proven. No original image bytes/crop hashes were retrieved. Photo rights remain unresolved, and all 159 supports remain benchmark/alias/near-duplicate quarantined. Dataset annotations are NC-SA and cannot enter unrestricted production. |
| AKU-PAL five scan images | W19 records exact publisher file URL, bytes, SHA-256, source ID and per-entry CC BY 4.0. W25 verified the five original WebP scans across four supports. | W19 explicitly says institutional admission is unreviewed and `training_admission: false`; benchmark status is `UNRESOLVED_QUARANTINED`. Two samples, IDs 5862 and 5447, are one Louvre E3226 A+B support. No source-disjoint held-out pixel cohort or independent sign gold exists. These are historic printed publication scans, not manuscript-line photographs. |
| AKU-PAL/W20 wider source census | 240 sequentially screened records with 95 unique media hashes; 63 passed a permissive license + Hieratic identity/provenance/media screen. | The 63 have positive exact public benchmark metadata matches and are quarantined. The other 177 remain unknown/quarantined, not clean. The five W25 scan IDs are not in this 240-record subset and were not given a new independent overlap clearance here. The planned 500-ID expansion did not yield a completed receipt. |
| TPOP original photos | Museo Egizio's [published policy](https://collezionepapiri.museoegizio.it/en-GB/section/Papyrus-Database/Policy-on-access-and-publication-of-papyri/) permits use of images provided in TPOP under CC0. This is a plausible exact-photo route if the TPOP asset can be byte-matched to the DDD sample source. | No such DDD-to-TPOP byte or crop match was established in this wave. TPOP editorial text is separately authored, and benchmark lineage still needs source/alias/derivative review. Cat.1880 is a known one-support contamination risk. No registration credentials were supplied for restricted TPOP access. |

The [AKU-PAL FAQ](https://aku-pal.uni-mainz.de/faq) says individual assets may be used under each entry's stated license and distinguishes digital facsimiles, collaborator imagery and scans. An individual CC BY 4.0 label is not itself institutional source admission or benchmark clearance. The W20 public source census already has 63 positive benchmark matches and 177 unknown records. A missing literal match for the remainder is not proof of source independence.

No restricted assets were downloaded. No full DDD images archive or split ZIP was fetched before item-specific rights were settled. The five AKU-PAL originals were not fetched again because their accepted receipts expressly prohibit admission and leave overlap unresolved.

## Split and metric decision

| Split | Source supports | Publisher metadata-label count | Status |
|---|---:|---:|---|
| W24 train | 35 | 15,426 | Frozen project diagnostic only |
| W24 development | 7 | 893 | Frozen project diagnostic only |
| W24 test | 8 | 1,566 | Frozen project diagnostic only |
| DDD publisher C-B | Not independently replayed | Not verified | Publisher-described closed-set, published-documents, document-aware split; split package is a separate large archive and was not fetched before image rights clearance |

Because the admissible image denominator is zero, no fair visual train/dev/test image counts can be reported. No image-conditioned accuracy, macro-F1, per-class outcomes, per-support metrics, confusion matrix, abstention rate or uncertainty interval is defined. W24's previously reported 81/1,566 (5.172414%) majority-class value is a **nonvisual metadata-label negative control**, not a pixel-model metric. There are no image attempts, model fitting failures, inference failures, CPU model runtime, model memory use or model spend to report.

The source annotations are publisher scholarly labels for selective signs/groups, not independent blind readings. Nothing here is evidence for handwritten full-line OCR, accepted reading accuracy, specialist recognition or transcription.

## Local verification

The default system Python lacks NumPy; the workspace-bundled Python was used without changing project dependency files:

```powershell
& 'C:\Users\M7mdEhab\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest tests.research.test_ddd_visual_gate tests.research.test_aku_pixels tests.research.test_ddd_prior_baseline -v
```

Environment: Python 3.12.14, NumPy 2.3.5, Pillow 12.3.0. **29 tests passed.** They verify publisher source shape and class identity, rights/benchmark fail-closed behavior, source-group/rotation splits, W19 exact media roles and hash rejection, and metadata-only negative-control invariants. They do not manufacture source permission or authorize model training.

Prior accepted W26 exact-head hosted runs are [source gate 38049276587](https://github.com/m7mdehab/hieratic-ai/actions/runs/38049276587) and [governance 38049276610](https://github.com/m7mdehab/hieratic-ai/actions/runs/38049276610), both successful on the original W26 PR head. They are not W27 runs. This environment has no authenticated GitHub host (`gh auth status` reports no login), so a W27 PR and hosted source workflow could not be created here.

## DATA-008 release-readiness checklist

- [x] Dataset, annotation, physical-support universe and image/annotation source metadata pinned before model results.
- [x] W24 35/7/8 source-disjoint diagnostic split preserved and kept distinct from publisher C-B.
- [x] W26 bounded gate replay completed with exact publisher metadata SHA-256 locks.
- [x] Rights for dataset annotations distinguished from underlying museum photo rights; no image trained without permission.
- [x] Known and possible benchmark collisions kept quarantined; no literal no-match promoted to clearance.
- [x] Cat.1880 rotated/original views remain grouped as one physical support.
- [x] Existing DDD, AKU-PAL and physical-source-split tests pass locally (29/29 in bundled Python).
- [ ] Independently verified item-specific photo training/evaluation permission for any DDD/TPOP image used.
- [ ] Original image bytes and deterministic sample polygon/crop pixel hash for each admitted label.
- [ ] Independent benchmark ancestry/alias/derivative/near-duplicate clearance for training and held-out supports.
- [ ] Verified publisher C-B split membership or a new pre-registered admissible cohort split.
- [ ] Adequate image-admitted source supports and overlapping label classes for a meaningful source-disjoint visual benchmark.
- [ ] Independent expert review of sign-label fitness for the intended scientific claim.
- [ ] Real CPU model ledger, model metrics, failure accounting and reproducible source workflow for an admissible cohort.
- [ ] Production rights, expert gold, independent trust and source-disjoint release evidence for DATA-008 corpus v1.
- [ ] Exact-head hosted W27 source and governance workflows and a reviewable PR.

## Decision and next action

**Do not train or claim DATA-008 acceptance in this wave.** The current evidence does not show an image that simultaneously has usable item-specific photo permission, source-byte/crop linkage, a valid expert label, and independent benchmark status. The most direct next action is to obtain exact original-image byte identity for selected TPOP-linked documents and an independent per-support benchmark ancestry decision, then retrieve only those eligible images and verify each polygon/crop transform. If those gates pass, freeze the small eligible cohort and split before fitting the requested CPU baselines. Otherwise keep the DDD cohort quarantined and seek a separately licensed, expert-linked photo source.

DATA-008 remains active at 0/3. No task/progress state, production authorization, or capability claim has been changed.

## W27 parallel research distinction

The independent overseer W27 Tokyo IIIF pilot ([R034](../../docs/research/R034_W27_TOKYO_IIIF_IMAGE_RIGHTS_AND_PIXEL_RESEARCH.md), merged PR #146) ran an actual authentic-pixel 1NN on historical printed Möller publication *sign strips*: 16 training references, 8 comparison strips, 2/8 correct vs 1/8 nonvisual prior. This is **not an admissible original papyrus photograph + labeled glyph crop cohort**, and the printed-volume partition is not a physical-manuscript holdout. Thus the research diagnostic does not contradict this DATA-008 no-admission determination, and cannot support DATA-008 points, specialist reading accuracy or training on benchmark-heldout material.

---

# W28 DATA-008 — preregistered candidate census and exact-source readiness

**Branch:** `task/DATA-008-w28-original-manuscript-cohort`
**Verified base:** `9de75ffe6c323e80fca9cc062645582e92d66362`
**Status:** bounded metadata-only source study; **0 images admitted, 0 visual training/evaluation examples, DATA-008 remains 0/3**.

Before W28 source retrieval, `data/releases/w28_candidate_study_preregistration.json` froze the candidate population, inclusion rule, use boundaries, physical-source groups, benchmark quarantine rule, and no-training gate. The finite DDD population is every key in the exact publisher `papyri.json` metadata snapshot (SHA-256 `33265df94656e79a27c1c158756f0a2479173d00184c5212159ec1bb8414eb62`): 159 image records, 50 document clusters, 17,885 samples and 504 class identities. The manifest separately preserves annotation metadata digests, the publisher's C-B closed-set split target and the historical W24 35/7/8 support split with 15,426 / 893 / 1,566 metadata-label counts.

The bounded readiness command is:

```powershell
python -m data.releases.w28_candidate_readiness
```

It fetched the hash-pinned DDD image, sample and class metadata; the split-description text; and only the C-B ZIP central directory plus its 330 KB JSON membership member using strict HTTP byte ranges. It did not fetch the 416.6 MB C-B archive, image/crop members, raw LabelMe polygon archive, or any benchmark/evaluator material. The report records exact file hashes and sample/class membership joins without including raw annotation dumps or class label lists. The resulting `data/releases/w28_candidate_readiness.json` has 159 DDD image rows plus 8 receipted/new Turin photo revisions, 4 fixed publisher-route candidates, and 3 comparison-only categories (174 rows total). It records zero new image bytes, 14,755 C-B membership rows joined to the publisher sample/class metadata, zero polygon payloads loaded, zero training/evaluation admissions and no production release.

The publisher C-B document/sample membership replays by exact sample IDs against `samples.json`, image/document IDs against both `samples.json` and `papyri.json`, and all physical `doc_cluster` supports remain partition-disjoint. It resolves to 37/38/46 publisher document IDs and **9/11/12 physical support groups**, with 5,009/4,623/5,123 sample labels in train/validation/test; 32 distinct physical supports occur in C-B. The C-B class list has a real source-version discrepancy: it lists two class IDs absent from the current sample/class metadata and omits two IDs that are present there. The discrepancy is summarized by counts and digests in the machine ledger, not by copying a publisher label dump. Thus the membership partition can be reproduced, but exact C-B class-list identity is **not** verified and the split cannot be accepted as a ready visual benchmark. The W24 project split remains a separate 35/7/8 physical support diagnostic with 15,426/893/1,566 metadata annotations across the full 50-support universe. These denominators are not interchangeable or visual-example counts.

Physical-support crosswalk between the two published/source-metadata split regimes (row = C-B partition, column = W24 project diagnostic partition):

| C-B supports | W24 train | W24 development | W24 test | C-B total |
|---|---:|---:|---:|---:|
| Train | 6 | 2 | 1 | 9 |
| Validation | 9 | 0 | 2 | 11 |
| Test | 9 | 0 | 3 | 12 |

Only 32 of the 50 W24 support groups occur in C-B; 18 do not occur in the published split. The crosswalk confirms the assignments differ: for example, nine C-B test supports are in W24 train. A future experiment must choose one frozen split regime and may not combine a training partition from one with test material from the other.

| Cohort | Frozen/receipted candidates | Rights and identity result | Visual cohort |
|---|---:|---|---:|
| DDD original photographs | 159 images / 50 source clusters | Annotation dataset claim is CC BY-NC-SA; individual museum photo rights remain unresolved. No W28 image bytes or annotation polygons retrieved; all benchmark ancestry remains unknown/quarantined. | 0 |
| Museo Egizio W20 file revisions | 7 revisions / 3 physical supports | Existing exact byte receipts preserved; item-level Commons CC0 claims are not institutional/photo-and-text admission, and all three supports remain benchmark-quarantined. Cat.1880 faces and Cat.2169 views remain grouped. | 0 |
| Cat.2044/013 and fixed TPOP routes | 1 original-object candidate plus the finite R020 portal roster | No exact source byte/crop binding; text and image rights are separate; edition/benchmark review is pending. Museum catalogue and TPOP description conflict on Ramesses VI/V attribution; do not auto-resolve. | 0 |
| S.6759 | 1 photo candidate | Museum catalogue explicitly identifies “Hieratic ostracon with an oracular text” (inventory Suppl. 6759, CGT 57227). W20 has a verified photo-byte receipt, but no admitted exact line gold, text permission, benchmark clearance or production custody. | 0 |
| Cat.2169 | 1 object with 4 receipted photo/view variants | Verified Hieratic inventory ostracon; visual control only, not a line-transliteration target. All variants are one physical support and remain quarantined. | 0 |
| AKU-PAL / Tokyo Möller / historical plates | 240 AKU-PAL sign records / 32 source-text IDs; 24 Tokyo Möller printed-book crops; historical plates as a separate class | AKU-PAL has 63 positive exact public benchmark-source matches and 177 unknown/no-literal-match records, all quarantined. Printed Möller scans/facsimiles are not original manuscript photographs; W27's 1NN is a separate printed-sign diagnostic. | 0 |

The W20 item receipt preserves exact source hashes and dimensions for Cat.2169 and S.6759, and hash/byte receipts for the two high-resolution Cat.1880 JPEGs (whose previous safe decode failed). Those are historical receipts, not W28 source-byte retrievals or evidence that the current holder may store/reuse them for this task. W28 acquired **zero** new original-image bytes; its new SHA-256 receipts cover only public metadata/split-definition text. No original pixel/crop hash or image-to-label geometry has therefore been created.

The readiness tool and schema fail closed on row loss, duplicate candidate IDs, malformed source hashes, a W28 original hash asserted without W28 byte retrieval, any gate promotion, a label asserted without a pixel binding, split physical views, benchmark “clearance” states outside the quarantined vocabulary, and production/capability promotion. The evidence digest binds the complete machine-readable rejection ledger. `tests/data/test_corpus_release.py` exercises these cases alongside the release engine's existing path containment, symlink, bounded-size, synthetic-fixture and no-clobber controls.

## W28 acceptance and scientific boundary

- [x] Freeze the finite source roster and allowed uses before W28 image/annotation payload retrieval.
- [x] Expand DDD image metadata to 159 source-bound candidate rows; use sample/class metadata only for the publisher split join, without loading the polygon archive or publishing label lists.
- [x] Preserve per-item photo rights separately from dataset annotation rights.
- [x] Inspect publisher split-definition text and replay C-B sample/document membership with strict byte ranges; keep C-C/C-D as non-holdout random-sample splits.
- [x] Preserve W24 support groups/counts as a separate historical metadata baseline.
- [x] Verify S.6759's museum identity as a genuine Hieratic oracular ostracon; retain one physical support and prior exact media receipt.
- [x] Keep facsimile/plate sources and W27 Tokyo comparison strips out of an original-photo cohort.
- [x] Add executable row-level fail-closed readiness and negative/adversarial tests.
- [ ] Independent permission for a specific photo asset, exact training/evaluation use and private custody.
- [ ] Annotation/editorial-text reuse permission and exact source-photo-to-label/crop alignment.
- [ ] Independent expert review/adjudication and a qualified authority/trust root.
- [ ] Resolve the two-label C-B class-list drift; independently clear benchmark/edition/source ancestry for any physical supports.
- [ ] Non-empty adequately sized source-disjoint visual train/dev/test cohort with overlapping label coverage.
- [ ] Real visual model fit, failures ledger, held-out metrics and cluster-aware uncertainty.
- [ ] Production redistribution rights and independently authorized DATA-008 corpus v1 release.

This is a reproducible rejection result, not a visual model result. The source and split investigation stopped at the real permission, label-binding and benchmark-lineage gates; no pixels were trained or evaluated. No corpus release was created and no capability score or project state was changed. The immediate external unblocker is a separately authenticated rights decision for exact museum image revisions and their intended research custody/use, plus expert-authorized scholarly labels and benchmark/source-ancestry review. This repository cannot create those authorities itself.
