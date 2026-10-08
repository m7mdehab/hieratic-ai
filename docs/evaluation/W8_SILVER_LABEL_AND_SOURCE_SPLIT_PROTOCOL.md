# Wave 8 — Independent silver-label diagnostic and source-split protocol

**Status:** proposal ready for implementation only when source rights and actual image/line identity are verified. **Owner:** overseer. **Date:** 2026-10-09. This is **not** a certified benchmark, production-data authorization, or expert-gold acceptance.

## Fundamental distinctions

1. **U: unlabelled original-image processing.** Verified licensable original pixels with their image SHA, no editorial text copied. May produce segmentation proposals and visualization diagnostics even while annotations remain unknown.
2. **S0: bibliographically cited edition.** Published reading exists, but matching exact view/line, full rights or machine encoding remain unverified. Bibliography and citations only; no line text imported.
3. **S1: lawful line-matched silver diagnostic.** Publisher/author *text* rights checked at figure/line scope. Original image SHA, side, writing unit, line region and edition identity match, verified visually. Scholarly editorial reading is an **existing publication**, not an independent second expert or fresh gold.
4. **F: independent held-out scientific evaluation.** Separate independently accepted original evidence, source-group independence, task-specific approved license/gold/authority, preregistration, model-blind execution and full reporting. **No W8 source is currently F.** A model's self-correction or consensus among AIs never upgrades S1 to F.

The research pipeline progresses **U → S0 → S1** wherever lawful. An S1 fail does not disable productive U-image experiments; an S1 success does not confer F.

## Exact matching before comparison

An S1 proposal must contain: museum+support_group+all joined accessions; recto/verso and physical orientation; exact photo URL and original bytes SHA-256; figure edition URL/DOI/revision; specific writing ID, column, line(s); image-to-original affine transform; pixel ROI polygon; manual review of face+line geometry; editorial text author/edition/license evidence; extent of restoration, damage, lacunae, alternative candidates and editorial intervention; overlap status with **all known benchmark public+sealed source aliases** (without opening sealed materials).

No exact match → record `NO_LINE_ALIGNMENT`, fall back to U/S0, investigate variants. Never auto-join material solely because two sources share Cat.2044 or a Pharaoh's name. Cat.1883 and Cat.2095 belong to a single joined physical text; Cat.1880 and Cat.2044 are separate support groups, but same support's multiple views are not separate test subjects.

## Frozen model-blind run

- Before accessing editorial target text, define corpus/model checkpoint revision, input pixel hash, original whole-image or defined ROI, prompts, decoding, seed, output format, segment order and unknown conventions. Save a preregistration digest.
- Process only one **permitted** source image and its predeclared ROI; retain original and every deterministic derived-image hash in private custody.
- Emit raw visual output and normalized predicted transliteration separately; record actual model architecture and whether real weights were loaded. Preserve alternatives, uncertainty, abstentions and hallucinated text.
- Save immutable raw response, timestamp, seed and model snapshot digests. **Then** consult the published licensed edition for comparison.
- Gold/silver target text must never appear in prompts, few-shot exemplars, retrieval context, human feedback on that same evaluation item, or evaluation-development sweeps.
- One descriptive diagnostic result can be reported under S1 with edition citation and publisher rights; it is not evidence of statistically valid held-out generalized Hieratic competence. Famous publications may be in foundational VLM pretraining. Record unknown pretraining exposure and publication-date cutoff.

## Scoring (silver diagnostic only)

Evaluate at explicitly declared levels:
- **Region detection:** source-coordinate IoU or coverage **only when** verified reference ROI polygons exist; a visualization alone earns no F1/IoU.
- **Line ordering/association:** report manually checked alignment count and abstained/unmapped count separately.
- **Glyph/sign hypothesis:** require aligned independent sign annotation to compute sign error; Gardiner sign metadata without verified manuscript sign regions is not gold.
- **Text:** compute CER on predeclared normalized character forms and WER/token error on fixed segmentation. Disclose when Egyptian scholarly transliteration and editorial conventions make raw character edit distance inappropriate. Report raw diplomatic form plus all transformations, not only a cleaned low-error score.
- **Uncertainty and restoration:** mark lacunae, editor reconstructions and damaged spans; calculate both literal-inclusive and uncertainty-masked diagnostics with clear denominator. Do not drop difficult spans silently.
- **Generalization:** **no claim** without multiple genuinely independent physical supports and scribal/period/source controls, cross-validation and a sealed external test.

Always report `n_sources`, `n_support_groups`, `n_images`, `n_verified_line_regions`, `n_scoreable_lines`, per-item exclusions, availability/rights, and a versioned scoring script. A one-photo multi-view collection is **one** support.

## Leakage gates

- HieraticBench evaluation-only universe (public 266 and sealed 2 metadata where safely available) never used for training, prompt choice or demo-driven tuning; keep R-021 Abbott/Hearst collisions grouped.
- Edition/scribe/manuscript aliases are transitive: one source group covers joined fragments, all views, crops, resized files, presentation scans, photographed reproductions, trace drawings and same-witness printed transcriptions.
- Same group cannot be train/dev/test across any split; not even different recto/verso or printed/institutional copies.
- Unknown overlap = `QUARANTINE_FOR_TRAINING_AND_CERTIFICATION`, but still consider permitted nontraining unlabelled image-only demonstration.
- Reject conflicting or incomplete rights as proof of scholarly gold; do not suppress differences between museum/TPOP catalogue dating (e.g., Cat.2044).
- Published edition visibility is recorded as *possible pretraining contamination*, not asserted definitive leakage without evidence.

## Free-first blocker exhaustion

Before declaring any lane blocked, test independently: alternate original CC0 file/revision/view, museum public download, relevant TPOP writing-level record and site permissions, another independently CC-licensed historical edition, published scholarly line screenshots used as bibliographic metadata only where text reuse is unclear, public-domain historic scholarship with independently audited rights, local OCR-free manual geometry, small CPU/ONNX VLM, and a nontraining unlabelled fallback.

For each attempted route record `available`, `legally_eligible`, `technically_accessible`, `experimentally_executed`, failure reason, and source URL. An unfinished attempt is **not** a terminal blocker. Explicit owner consent is required for spend, restricted media, contacts and changes to trust-controlled production/certification.

## Reporting required

A report must give exact dataset/image/model provenance and evidence grade, model prompt/hyperparams, raw output SHA, image-to-line pairing, rights statements, alignment failures, true n values, observed errors, and reproducible no-cost commands. **S1 remains silver; F remains false** until separate independent validation. There must be no update to `PROJECT_STATE.yaml` / `TASKS.yaml` for this research task alone.

Research registry: [R-024](../research/R024_W8_TURIN_CANDIDATES.json), [dossier](../research/R024_W8_TURIN_IMAGE_READING_DOSSIER.md).
