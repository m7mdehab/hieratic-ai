# R033 / W26 — Original DDD per-image visual research admission preflight

**Status:** Accepted as a verified original-publisher rights/lineage **research preflight**, not recognition science. [Original publisher-source and 16-test CI run](https://github.com/m7mdehab/hieratic-ai/actions/runs/38049276587) **SUCCESS**, [independent governance CI](https://github.com/m7mdehab/hieratic-ai/actions/runs/38049276610) **SUCCESS**; [implementation PR #143](https://github.com/m7mdehab/hieratic-ai/pull/143) merged `6f277e48d0bc9aed066bc8396f334da1d5648b64`. **This is not a Hieratic reader or model.**

## Scientific gap

W23–W24 verified 17,885 real scholarly sign/group annotation records, 159 source images and 50 physical manuscripts. The frozen 35/7/8 **project-specific** manuscript-group split produced a nonvisual majority-label negative baseline of **81/1,566 (5.172414%)**; this is not image-recognition accuracy. W25 verified five genuine source-scan image pixels over four physical witnesses with descriptive image metrics; no learned visual classifier was run. The next actual capability target is a real image-conditioned sign recognizer tested on physically independent witnesses, with clean rights and non-overlapping source lineage.

DDD original publisher: https://zenodo.org/records/20553713, noncommercial **CC BY-NC-SA 4.0** plus exact copyright metadata varying by individual papyrus. Source copyright strings and free online access do not establish model-training or derivative-image permissions for each included image. Cat.1880 original/rotated IDs 003 and 004 are **one physical support**, and public benchmark/HieraticBench overlap is **UNKNOWN_QUARANTINED**.

## Delivered W26 executable

Run:

    python -m tools.research_ddd_visual_gate --output /tmp/r033-full.json --summary-output /tmp/r033-summary.json

1. Bounded-access retrieves only three exact publisher **metadata** originals via W23's preexisting publisher MD5 verifier. An additional SHA256 lock authenticates those 2026 revisions: papyri.json, samples.json, classes.json. No ~2 GB source image archive, large publisher split ZIP, derived copyrighted photos, source crop bytes or private annotation images are downloaded.
2. Validates all 159 source image records, 17,885 annotation records, 504 classes and 50 physical witness groups. Every source sample must join to its publisher image/actual class. Rejects changed counts, unknown image IDs, missing item-level copyright text and divergence between Cat.1880 source siblings.
3. Preserves W24's exact SHA-seeded physical-witness diagnostic split (35 training, 7 development, 8 test), explicitly **not** claiming the publisher's published C-B split. The original C-B split ZIP needs separate verification. Do not use random-sample C-C/C-D to claim unseen-manuscript generalization.
4. Emits a deterministic per-image research ledger with publisher image ID, witness group, sample count, original copyright claim and unresolved admission gates. Every image remains **blocked** for training and heldout visual evaluation without independent image/crop byte provenance, item-specific research permission, benchmark/near-duplicate exclusion and adjudicated label appropriateness.
5. Inspects later individual permission/source-clearance *reference packets* without self-authenticating a reviewer. Even a syntactically complete packet remains **provisional** and cannot authorize model training, a scientific accuracy claim, benchmark contamination or DATA-008 release.
6. Outputs a **private** complete ledger and a **shareable aggregate-only** source-authenticated receipt with the ledger SHA256 digest; no original images, raw image archives, source annotations or license-holder letters are added to the public repository.

## Acceptance and conservative reporting

16 synthetic/adversarial regression tests passed both locally and on the exact hosted PR head. Exact hosted source replay verified all **159 original publisher images, 17,885 original annotation rows, 504 classes and 50 manuscript groups** against original Zenodo MD5 and SHA256. **38 of 159 images had placeholder copyright claims**, and all 159 had TPOP document metadata; there were **48 distinct copyright strings**. The immutable-order private ledger SHA256 is `7bcb4dc2ccdb6acb4322b3bc81ec7c8b4845e05f6056b64d37510b59e2ea4664`. Only the **aggregate-only** 14-day artifact (ID `11668687638`) was uploaded. Future source refusal or drift must fail rather than substitute fixtures. The metadata-source preflight establishes blockers and their witness-group scope; it does not resolve them. **No visual model, heldout sign accuracy, admitted DDD images, new blind expert gold, or capability points.** Do not inflate current 34.5/100 weighted goal, 17/100 internal research breadth, DATA-008 0/3 or VLM-001 0/2 for this gate alone.

## Next scientifically consequential execution

First, independently match each shortlisted DDD photo to exact museum/TPOP source exposure, original revision and independently documented per-image reuse rights; record annotation rights separately. Verify image bytes, cropped sample/source relationship and legal noncommercial research training/evaluation reuse. Then independently exclude HieraticBench/public benchmark source, accession and near-duplicate aliases while preserving **all** views of one physical support together. A missing match is unknown, never automatic clearance.

Freeze and check actual publisher **C-B** document-aware labels and partitions (or openly call W24's fixed 35/7/8 a separate diagnostic). Only after a genuinely approved cohort exists, fit and evaluate a reproducible CPU pixel-feature/1-NN learned baseline with an immutable heldout denominator, negative no-image/class-prior controls, per-document results, abstentions/failures, unseen classes and witness-cluster uncertainty. Keep noncommercial research outputs separate from unrestricted DATA-008 corpus and withhold model-weight release pending NC/SA review. Cat.1880 independently reviewed physical line/plate mapping remains separate issue #136; never wait for that email before exploring independently permissible source routes.

## Original-source integrity

- papyri.json SHA256 33265df94656e79a27c1c158756f0a2479173d00184c5212159ec1bb8414eb62
- samples.json SHA256 763944b29e06643131fa9fdbd14a2b169afe5961df80394fecfd152203584e46
- classes.json SHA256 5ff0181de57e1018058ba53e8e436e6e67a19fca290568ed0f9ea341af7afe18

Prior primary evidence: [R028](R028_DDD_PUBLISHER_RESEARCH_ROUTE.md), [R029](R029_DDD_REAL_ANNOTATION_HOLDOUT.md), [R032](R032_PIXEL_RESEARCH_ACCEPTANCE.md); binding [data-rights policy](../governance/DATA_LICENSING_AND_PROVENANCE_POLICY.md).
