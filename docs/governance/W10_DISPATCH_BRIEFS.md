# Hieratic-AI — Wave 10 execution briefs (reconciled 2026-10-09)

**Authority:** Canonical `PROJECT_STATE.yaml`, `TASKS.yaml`, `AGENTS.md`, `DECISIONS.md`, `docs/governance/TASK_WRITE_SCOPES.yaml`. Dispatch is immediate authorization for *in-scope work*, never for spending, restricted data, institutional contact, model API credentials, self-issued rights or milestone points.

**Base:** Pull current `main` after W9 merges #96–#100; the final W9 VLM correction is `c6f59103b7168b7b26ede0e696fa356e01ea5b29` before the present governance refresh. Never resurrect the original W9 VLM image-substitution path.

**Shared baseline:** 34.5/100 verified capability, 14% historically uncalibrated research coverage, P2 8.5/10, P3 17/20, P6 4/10, zero validated model experiments, zero trained models. Last weighted acceptance: LING-002. W8 Cat.2044 and W9 Cat.1883+2095 are two private image files over **two** physical supports, with zero independently verified reusable image/text line pairs and zero admitted corpus items. W9 LING-003 heldout contextual translation result is negative. Keep DATA-008 production authorization hard-disabled.

## Lane 1 — Luna / DATA-006: first lawful source-exact image↔edition line-pair pilot

**Agent dispatch prompt (copy as written):**

> You are the DATA-006 execution agent for Hieratic-AI Wave 10. Start immediately from latest `main`. Your substantial deliverable is to investigate and implement a source-exact, rights-conservative manuscript image-to-scholarly-edition *line reference* pilot, not merely reformat W9's three column boxes. Work exclusively in `data/alignment/**`, `tools/alignment.py`, `tests/data/test_alignment.py`, `docs/data/IMAGE_TEXT_ALIGNMENT.md` and your authorized DATA-006 brief/schema paths. Create `task/DATA-006-w10-lawful-image-edition-pair`, one PR, no cross-task changes.
>
> Work online-first using legitimate free primary publishers and recorded evidence, prioritizing Turin Cat.1883+2095 RIME Fig. 6 and Cat.2044/013, then independently assess alternate CC0 + separately reusable edition pairs if blocked. The RIME Fig. 6 photograph is CC BY 2.0 but article text rights have **not** been established; TPOP image CC0 is not a license for partner PDFs or written transcriptions. Never copy an unlicensed transcription, infer commercial/training permission, scrape a restricted source or admit a dataset on your own. No external correspondence or paid access.
>
> Independently record exact image/face/physical-support identity, article-to-figure relation, edition/writing-unit attribution, published line numbering, alternative and damaged readings, apparent benchmark/edition collisions, and source-specific text permissions. Test each available lawful route, not merely list websites. The pilot must distinguish reference pointers, approximate region proposals, human/editorial line identifiers, truly source-exact cross-linked line hypotheses and qualified score-eligible gold; preserve all unknowns. Where text reuse lacks an actual verified license, keep pointers only and produce zero copied line readings. Validate coordinates and geometry by independent visual checks where feasible; do not silently promote a column envelope into a line box.
>
> Implement concrete machine-readable provenance/line-pair dossier and negative validators for identity mismatch, wrong support/side, nonidentical image derivative, missing rights, absent review, approximate-only geometry, split contamination and missing text lineage. Preserve W9 source hash locks. If a genuine fully licensed pair exists, demonstrate reproducible exact line link on **one or more** verified examples, without claiming DATA-008 admission or independent second-reader gold. If no such pair exists, return a complete evidence-backed failure matrix (candidate routes tried, publisher terms, why blocked) and a validated fail-closed pilot—not invented labels.
>
> Run focused and full feasible test suites, exact-head hosted GitHub Actions and write-scope checks. Return PR, head SHA, changed files, tests, source links, hashes, exact right-component breakdown, independently counted supports/lines, linked line evidence, admission status and next gate. Do not edit `PROJECT_STATE.yaml`, `TASKS.yaml`, sealed benchmarks, or award points. This is a substantial pending DATA-006 scientific-research task, not an extension of already-completed W9 geometry.

**Acceptance gate:** Verified concrete source-pair and rights dispositions; meaningful exact-line identity where lawful; adversarial invariants; no gold leakage; reproducible evidence; green exact-head CI. Science weight unchanged pending independent admissibility and review.

## Lane 2 — Gemini 3.8 Flash / VLM-001: fresh post-remediation genuine CPU evidence and controlled negative comparisons

**Agent dispatch prompt (copy as written):**

> You are Hieratic-AI's Wave 10 VLM-001 execution agent. Start immediately on latest `main` (which includes the independent PR #100 remediation). Branch `task/VLM-001-w10-live-original-controls`. Read `AGENTS.md`, `tasks/VLM-001.md`, `docs/evaluation/VLM_BASELINES.md`, `eval/vlm/hieratic.py` and your pinned W8/W9 source evidence. Work solely in VLM-001 scope. **Do not restore the W9 image-resize fallback, fabricated grade flags or unverified source/crop intake.**
>
> Carry out a substantial, genuine CPU-only, $0-paid-spend experimental execution on the private original Cat.2044 CC0 JPEG using exact SHA `569e8e5bb446588481481bfea823fc95383bb7076270363c666f868b7fa5b912`, pinned SmolVLM-256M checkpoint `7e3e67edbbed1bf9888184d9df282b700a323964` and weight SHA `74dea5904032e5ae99a2e0eef5179e6ac0f1dedc3ab0c7c2a5d4d387c843203e`. Confirm actual original/crop bytes and post-remediation hashes in a private execution receipt, exact code commit, dependency versions, CPU/RAM limits, image transforms, run statuses, actual latency and complete failure/abstention outputs.
>
> Investigate meaningful *pre-specified* control conditions on actual pixels: neutral blank, inverted original, controlled source crop and a no-script/scrambled-text condition where source rights and transforms permit. Keep the same model, image input policy and prompt across matched controls, and explicitly quantify where prompts disclose Egyptian or Hieratic priors. Record status-aware raw completions, response hashes and paired differences; a response string mismatch or `Hieratic` supplied by the prompt is **not** independent script classification or accuracy. Count all attempted passes including errors, timeout, repetition and hallucination.
>
> Independently check the alternate 500M SmolVLM CPU path if free available RAM/weights permit and if it materially improves a *matched* diagnostic. Do not download more than host limits, trigger paid GPU/API services, use sealed test data or assert model progress from anecdotal examples. Record unexecuted comparisons as unavailable, not passed. If a new real scientific cohort is absent, keep Grade F STRICTLY NO and VLM-001 0/2 points.
>
> Extend VLM-001 software only as required for correct run receipts and controls, with negative regression tests proving source/weight tampering, missing decoder, blank-pixel substitution, mock promotions, corrupted crops, bad statuses, and incorrect control classifications all fail safely. Keep raw third-party images, weights and protected receipts out of Git and CI uploads. Commit only redacted hashes, reproducible procedures, honest aggregate diagnostic findings and tests. Return exact PR SHA, attempted/valid inference counts, chosen control matrix, full environment and cost, source/weight checksums, hosted CI and independent scientific limitations.

**Acceptance gate:** Fresh genuine corrected-head CPU run and verified source/weight image chain; no false Grade C/D/E; honest negative controls; complete disclosure of failed passes; repeatable private evidence. No VLM scientific points until legitimate independently held-out gold and acceptance.

## Lane 3 — Overseer / LING-003: real compositional translation and new independent-source generalization

**Overseer ownership brief:**

> Own a complete substantial pending LING-003 task concurrently with Luna and Gemini, without touching their write scopes or halting for their results. Begin from accepted W8 LING-002 and merged W9 LING-003 authentic AES data and negative external result. Use only authorized `ling/translation/**`, `tools/translation_layer.py`, `tests/linguistics/test_translation_layer.py`, `docs/linguistics/TRANSLATION_PROTOCOL.md` and the LING-003 task brief.
>
> Objective: replace word-bag retrieval and nearest-neighbor German sentence copying with a genuinely compositional, provenance-aware Egyptian source representation and generation mechanism. Preserve morphology, grammatical roles, alternatives, segmentation uncertainty, abstention and named entities. Investigate lawful, source-original additional external translation corpora *not already used for development or the revealed Tübingen test*; account for source-work genealogy, scribes/supports and edition duplication when feasible. If an independently suitable new corpus is unavailable, implement the method and report a bounded failure to certify rather than using contaminated test material.
>
> Fix a complete evaluation protocol **before** inspecting new held-out references: true source-group-level dev separation, untouched alternate edition/source, independent evaluator, grammar/semantic adequacy checks and hallucination/copy detection; compare against the accepted original gloss baseline and W9 contextual model fairly. Report denominators, uncertainty, coverage versus abstention, error categories and exact source/revision hashes. Never turn a drop in test metrics into progress by changing weights or redefining scoring. Do not describe published-source word F1 as semantic adequacy.
>
> Add adversarial leakage and formula-copy tests, publish reproducible code and a genuinely negative or positive measured outcome, secure hosted exact-head CI and review the resulting PR. No LING-003 2-point acceptance without demonstrably adequate translation under independent evaluation. Do not change canonical state until scientific acceptance.

**Acceptance gate:** Mechanistic nonmemorization evidence plus a genuinely new held-out source and defensible semantic evaluation; if not met, an honestly blocked LING-003 scientific milestone with a comprehensive reusable experimental package.

## Cross-lane review, work order and dispatch rules

1. Agents work on independent fresh branches from current main; exactly one primary task ID each. Do not share mutable directories or update canonical progress.
2. Each agent executes when dispatched; no planning-only answer, artificial waiting, or invented future completion estimate. All spending, contact, private evaluation and protected-data approval gates remain separate.
3. Overseer actively executes LING-003 while both agents work; it does not merely write statuses or embellish completed tasks.
4. Inspect returned code, exact changed paths, source provenance/rights, full test logs, private evidence digests, relevant scientific denominators and exact-head CI. Independently patch bounded defects, leaving explicit unverified barriers open.
5. Merge only reviewed safe implementations, then update `PROJECT_STATE.yaml`, `TASKS.yaml`, `DECISIONS.md`, `EXPERIMENTS.md` and handoff as justified. Report the mandatory acceptance checklist/phase points; never award fractional capability points for partial evidence.
6. Unseen or sealed data, third-party asset bytes, partner PDF transcriptions and private reviewer information are not eligible for convenience-based admission.
