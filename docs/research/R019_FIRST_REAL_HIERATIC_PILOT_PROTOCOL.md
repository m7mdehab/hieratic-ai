# R-019 — First scientifically defensible real Hieratic reading pilot

**As of 2026-10-08. Status: protocol ready; no real-data acquisition, annotation or model experiment.**

**Evidence:** [R-017 all-266 public benchmark audit](R017_PUBLIC_BENCHMARK_LINEAGE_AUDIT.md), [R-018 institutional dataset feasibility](R018_INSTITUTIONAL_RIGHTS_GOLD_FEASIBILITY.md), [R-016 15 identified accession candidates](R016_CORPUS_GOLD_FEASIBILITY.md).

**Purpose:** convert public research to a preregistered and falsifiable pilot with explicit legal, scholarly, contamination, ML and statistical decision gates. DATA-008 and VLM-001 agent workstreams provide the software; **nothing in this plan establishes permission or scientific performance**.

## 1. Phased scientific plan and primary research questions

**Stage F — data continuity proof (not an ML experiment).** Obtain one legitimately authorized original Hieratic image-line pair with independently documented expert diplomatic reading and exact source accession. Feed source image, immutable hash, transcription, spatial alignment, uncertainty, source review and licence through accepted DATA-003–008 plumbing. If even one required field is missing, refuse admission. One line proves technical compatibility, **not corpus adequacy or reading performance**.

**Stage P — independent document-cohort feasibility.** Recruit additional original manuscript groups selected *by source/genre/media/dating/quality stratification* rather than arbitrary item counts. Annotate by qualified Egyptologists and independently adjudicate. Freeze a held-out document-group evaluation partition before inspecting model outputs. Determine practical corpus-size needs from observed legal availability, document variance, annotation reliability and a preregistered target precision—not a made-up minimum.

**Stage E — genuine zero-shot experiment.** Execute a pinned open-weight vision-conditioned model, on actually rights-cleared source-independent held-out images, preserving all raw outputs and failures. Run SCRIPT_ACC, SIGN_TOP1, TR_CER and TRANS_CHRF only for their truly gold-eligible tasks; follow native EVAL-001 contract. Keep official pinned HieraticBench results separate; no official claim unless the true official scorer is run. No training, fine-tuning or few-shot until evaluation boundaries are proven.

**Stage S — specialist improvements.** Only after adequate authorized train/dev/test data and genuine baselines exist, compare untuned VLM vs specialist sign/line reading, morphological interpretation and eventual adaptation, all on the same frozen held-out document groups.

Research questions:
- RQ1. Does image-conditioned inference identify Hieratic and distinct comparator scripts rather than answer using filename/caption/source metadata?
- RQ2. Can a model read isolated Hieratic signs on genuinely independent manuscripts, compared with rights-cleared sign-specialist reference?
- RQ3. Can a model transcribe unseen authentic manuscript **lines**, with alternatives, incompleteness and calibrated abstention, rather than merely recognize published text names?
- RQ4. What failure classes dominate: stroke segmentation, writing direction, palaeographic form, damage, period, medium, grapheme mapping or linguistic inference?
- RQ5. Only later: does trained specialization improve across independent source groups and scribes, compared with the frozen untuned condition?

## 2. Full lineage and annotation data contract

One physical manuscript/support may yield many fragments, faces, exposures, crops, signs and lines. Treat these as **linked views, not independent samples**.

**Original asset identity:** institution; collection; accession; known alternate accession IDs; physical support ID; join/fragment group; recto/verso; document/writing identity; exposure; original pixel SHA-256, file size, image dimensions and color space; institution URL; accepted image-specific permission; intended training/evaluation/redistribution/weight terms; attribution and review timestamp.

**Gold identity:** exact source image hash; line polygon in a versioned image coordinate system; orientation and line ordering; diplomatic transliteration retained separately from normalized reading; sign sequence when genuinely annotated; editorial reference and verified permissions; lacuna/damage and restoration; explicit unknown/abstention-eligible span; confidence and competing alternatives; annotator IDs and review history; reproducible hash of each layer.

**Review identity:** first reviewer independent annotation, second reviewer independent annotation where personnel permit, blinded disagreement type, adjudicating specialist identity, reason, citation, retained alternatives, date and rights. Reviewer assertions themselves do not override rights evidence.

**Unseen-source group identity:** combine all fragments and faces of same manuscript; all photos/crops/AKU sign instances of same support; same published textual witness or scanned facsimile; and linked original/normalized image variants. Require external documentation before asserting two potentially overlapping accessions are separate physical supports.

**No transcribed museum synopsis as gold.** A catalogue explanation of an ostracon mentioning workmen's names or torches is not the line-by-line transcription.

## 3. Expert annotation handbook (to be approved by actual Egyptologists)

1. Lock the image and manuscript inventory IDs before annotation, and record legitimate image use and independent editorial permissions. Train annotators only on nonbenchmark licensed practice records.
2. Two qualified Egyptologists, if available, independently describe writing orientation, group segmentation, observed signs and line-level diplomatic reading before seeing each other's annotations or machine predictions.
3. Preserve differing, damaged, partially legible and restored readings. Categorize disagreements as writing-direction, stroke/segmentation, sign, morphology, text restoration, lacuna or uncertain damage.
4. Have a documented expert adjudicator review irreconcilable differences; explicitly allow unresolved, missing or ineligible gold. Never delete hard spans or force certainty to boost coverage.
5. Verify line and sign geometries against each exact source image (and that transforms preserve coordinate mapping); reject wrong-face, omitted-lines, duplicate polygon, wrong document ID and source text/pixel hash drift.
6. Separate diplomatic, normalized, lexical, hierarchical sign renderings, translations and free interpretation. An MdC/JSesh sign mapping is a scholarly convention rather than a reversible one-to-one visual mapping for all periods.
7. Record reviewer workload and annotator agreement by type, not just a single misleading raw percent; gold eligible only after source and review quality acceptances.
8. Seal external test gold against models, few-shot prompt exemplars, training, hyperparameter changes and error-guided dataset selection.

**Current limitation:** no real qualified annotators, adjudicator contract, agreements or annotation budget is established. This is a work specification, not an assurance that personnel have been recruited.

## 4. Stratified sample design and statistical reporting

**Stratify based on genuinely available evidence**, preferably by manuscript group, historical period, genre, writing medium (papyrus/limestone/pottery), image legibility, damaged/uncertain fraction, writing level and independently documented scribe/hand when known. Avoid claiming independence based on a guessed scribe.

**First genuine pair** has zero inferential representativeness. Even two independent document groups create fragile intervals. Pre-register the target precision for each metric and sample enough independent document clusters to support it—estimating needed n from pilot document-level variance, permitted source availability and a scientifically meaningful difference. Do **not** pick a threshold that happens to pass a tiny convenient sample.

Use at least **2,000 document-clustered bootstrap** replicates where applicable under EVAL-006. For zero or one independent document group, report **CI null / insufficient clusters**, never a fabricated zero-width interval. Report all abstentions, failures and timeouts in intention-to-test denominators, and report conditional success separately. For paired A/B, enforce identical complete source-item/shot/sample universe.

**Holdout partition:** physical support + joins + all image views and derived crops together. Confirm institutional aliases, text editions, exact/perceptual duplicates, cross-source signs and benchmark quarantine. Keep test gold inaccessible until the experiment design is frozen.

## 5. Gate-by-gate acceptance matrix

| Gate | What must demonstrably exist | Reviewer and failure |
|---|---|---|
| G0 Discovery | Stable catalog accession, original record, script and support identity | Overseer; remain metadata-only if incomplete |
| G1 Asset licensing | Written/official image permission, actual original pixels/hash, purpose-specific terms, attribution | Rights custodian; no corpus/image publication otherwise |
| G2 Editorial licensing | Independent right to use original transcription, transliteration, mappings, translation and annotation derivatives | Author/rightsholder; no gold admission otherwise |
| G3 Contamination | All 266 pinned public source identities, alias and perceptual/edition reviews, future benchmark version control | Independent dataset reviewer; any uncertain case stays quarantined |
| G4 Gold quality | Image-line spatial correspondence; scholarly reading, uncertainty, independent annotation and review | Qualified Egyptologist(s); no eligible gold otherwise |
| G5 Corpus release | Source-rights, preprocessing, annotation, sign mapping, alignment, review, leakage-clean document partitions; immutable release evidence | DATA-008 + independent reviewer; no ML-ready corpus label if not adequate |
| G6 Technical VLM | Image-conditioned actual multimodal inference, pinned model/processor/weights, legitimate hardware, raw attempts and failed cases | VLM-001 + independent runtime review; mock preflight isn't inference |
| G7 Valid scoring | Frozen *externally anchored* attempt universe, EVAL-001 metrics and EVAL-006 cluster uncertainty, correct official-score separation | Independent evaluation reviewer; no scientific result if missing |
| G8 Accepted milestone | Full independent review of rights, dataset and real model evidence | Overseer; agents cannot self-award roadmap points |

**Five independent truth categories:** software correctness, input rights, gold reliability, real multimodal inference, statistically defensible evaluation. A passing software test cannot establish the latter four.

## 6. Preregistered experimental sequence

**EX0 — exact-pixel original-gold integrity:** one or more actually permitted manuscript lines, typed provenance, coordinates and independent gold, no model call. Decision: true round-trip from image to reviewed release. No claim of model performance.

**EX1 — source-blind script identification:** source-disjoint genuine images, explicit Hieratic vs documented comparison classes, no source names/filenames in prompt, zero-shot pinned vision model; metric SCRIPT_ACC; negative controls for wrong/no image. No source-level metadata leakage.

**EX2 — isolated-sign capability:** independently licensed Hieratic sign images/labels only, not AKU benchmark 150 image items. Use sign correspondence only if rights and image-to-label relation independently reviewed; primary SIGN_TOP1 plus confusion by period/medium.

**EX3 — diplomatic line recognition:** authentic lines on previously unseen physical supports, fixed transliteration conventions, alternative readings and damage; TR_CER primary (lower better) plus coverage/abstention/failure and expert error taxonomy. Compare model against appropriate no-image/text-prior control to detect text/title memorization.

**EX4 — translation and morphological interpretation:** only documents with independently licensed translation and lexical annotations; TRANS_CHRF for translation, separately scholarly-validated LING-002 morphology. Do not score translation on museum synopsis or translation of another edition.

**EX5 — real paired comparison:** compare actually executed untuned model conditions with a specialist baseline on frozen identical independent cohorts and clear failures, using document-clustered CIs. Future few-shot requires real authorized exemplar pixels and approved multimodal template; all live few-shot presently blocked.

### Explicit experiment stop conditions

Unverified image/text rights; missing actual source image; ambiguous source accession or benchmark near-duplicate; no independently reviewed line gold; all model attempts failed; ambiguous shot-mode pairing; uncertified external dataset; absent weights/hardware; incomplete denominator; sample too small for meaningful confidence; leaked held-out material. Stop and report the failure; never substitute fake data for a real scientific success.

## 7. Reproducibility packet required for each experiment

- Canonical task and version, objective hypothesis and prespecified primary endpoint.
- Original museum source and all aliases, document and photo exposure IDs, actual pixel hash and geometry.
- Source layer and rights receipts independently reviewable, allowed intended uses and model-weight/output implications.
- Distinct gold/adjudication receipts, uncertainty and alternate readings.
- Source/benchmark quarantine report, whole-document split proof, true independent document-cluster count.
- Frozen cohort anchored outside editable generated run results, model+processor+weights hashes, prompts and decoding parameters.
- Full raw model responses, errors, timeouts, abstentions and retries, exact image-conditioning evidence.
- Native and official scoring explicitly separated, bootstrap seed/scheme, subgroup denominators and interpretable uncertainty.
- Independent reviewer signoff, scientific limitations, permissible release status and reproduction instructions.

Sensitive permitted original data should be stored with access control outside the public Git repository where terms demand. Public research metadata cannot substitute for source permissions.

## 8. Cross-agent integration scenarios

**Luna DATA-008:** refuse TPOP image-only CC0 without separately cleared scholarly transcription; reject R-016's all 15 metadata-only candidates; detect image/transcription mismatch, false reviewed flags, source aliases and fragment split leakage; report exact missing approvals.

**Gemini VLM-001:** accept independently licensed item-and-image evidence only if supplied by an external admission authority; never allow self-relabelled synthetic results to count as certified; require externally pinned item universe, actual image conditioning and full failure records. The current scientific certification gate must fail closed.

**Overseer:** compare both independent agent PRs with source rights and gold evidence, exact-head CI, signed-off scopes and scientific outcomes. Research findings alone are not eligible for weighted project progress.

**Integration-specific red team:** AKU-PAL sign from a known benchmark support reintroduced as museum photo; TPOP edited text not licensed even when photo CC0; Met image lacks expert gold; source filename leaks target script; test examples reused in a few-shot demonstration; removed difficult attempts and rewritten manifest; one document yields artificial confidence interval. All should be refused or accurately labelled non-scientific.

## 9. Decision and owner dependencies (no outreach sent)

1. Confirm whether intended eventual corpus and model weights must be commercially compatible and redistributable, versus separated noncommercial academic research. Default: no permission assumptions.
2. Designate legitimate institutional inquiry identity and explicitly authorize contact. Drafts exist in R-016/R-018; none sent.
3. Find authorized Egyptologist reviewers and an adjudicator, including time/cost permissions if needed. No staffing inferred.
4. Confirm future secure image storage for legitimately licensed raw files, with immutable hashes and access controls; do not fabricate connection or credentials.
5. Establish actually available zero-cost local hardware/model weights and real eligibility before any VLM science experiment.

**Milestones with no invented timeline:** M1 institution-specific image and text rights; M2 first real original image/expert-approved line pair; M3 independently grouped rights-and-gold corpus plus a genuine held-out evaluation set; M4 actual pinned multimodal model evaluation with auditable native metrics; M5 paired generalization and specialist model study.

## 10. Integrity summary

As of this publication, **0 new museum images or transcripts acquired**, **0 expert-adjudicated real lines**, **0 eligible real corpus releases**, **0 valid VLM experiments**, **0 trained models**, **0 outbound museum contacts**, **0 sealed benchmark artifacts inspected**. R-017 reviewed **266 public source metadata records**, not their raw image bytes or gold. Research does not establish the pilot's legal or scientific preconditions. Verified goal progress remains **32.5/100** and research coverage remains **14%** pending independent reassessment.
