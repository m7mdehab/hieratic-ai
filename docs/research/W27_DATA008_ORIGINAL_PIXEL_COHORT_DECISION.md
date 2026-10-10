# W27 DATA-008 — original-pixel cohort decision and experiment ledger

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
