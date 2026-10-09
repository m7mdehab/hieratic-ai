# W14 LING-003 — frozen *train-only* oracle-free group diagnostic

**Registration date:** 2026-10-09. This registration precedes construction/scoring of the W14 heldout group labels. The source's train file was accessed for metadata census and incidental first/last line previews; W13 had already released whole-TRAIN aggregate grammar counts. Thus this is an **internal retrospective diagnostic**, NOT a clean unseen/blind manuscript benchmark. The original W13 DEV is exposed; the UD Egyptian-PC official TEST must remain completely unopened.

## Primary source and rights
- Original publisher: UniversalDependencies/UD_Egyptian-PC, University of Jaén (Old Egyptian Pyramid Texts; Tübingen transcription), CC BY-SA 4.0. Original publisher tree `fca8538287cb69fd07b811eb55dcfd25584f3006` and TRAIN Git blob `ea262ee047943b81c0e0db8ff139ec7deb9b7b53`, 2,563,828 original bytes.
- Public original publisher repository and license: https://github.com/UniversalDependencies/UD_Egyptian-PC; attribution to Díaz Hernández, collaborators and the treebank project; derivatives retain CC BY-SA. No manuscript image data or image/text rights transferred.
- Metadata-only census before registration: 1,619 sentences, groups `Teti` (744), `Pepi` (829), `Neith` (40), `Merenre` (6). These are publisher `# king` fields, **not verified independent physical writing supports/scribes**.
- Source has prior W13 global TRAIN model exposure: this prevents claiming independent, pretraining-clean or held-out-original scientific validity.

## Frozen question, split and models
Can a *train-group-only* surface-form classifier supply non-oracle UPOS to a training-group-only dependency frequency model? Will predictions improve over a weak previous-token baseline on the heldout **Pepi** publisher metadata group, without supplying gold UPOS to inference?

- Training publisher group set: **Teti, Neith, Merenre** (790 sentences). Heldout evaluation group: **Pepi** (829 sentences). No change of holdout based on results; no dev or official test.
- Preserve all original train CoNLL-U word tokens: skip UD multiword range/empty-node rows exactly as UD word-token convention. Use original FORM, UPOS, HEAD, DEPREL and # sent_id, # king; pin original source, derived bytes and counts. Reject duplicates, malformed graphs and drifting hashes.
- Input to public inference function: only nonempty Egyptian FORM strings in original sequence. Normalize each form via Unicode casefold for lookup only; exact-form POS majority; for never-seen forms try form-final suffix of length 3 with at least 3 training token observations, length 2 with at least 5, length 1 with at least 8; else global train-majority UPOS. Tie break lexicographically. Preserve exact-known vs suffix vs fallback statuses; no secret lemma, FEATS, DEPREL, gold UPOS at inference.
- Syntax: derive W13 head-POS/child-POS/direction/DEPREL count dictionaries **solely** from the allowed W14 training groups. Use the frozen W13 `FixedOraclePosSyntax` algorithm without changing its head-score or distance penalty of 0.02 and with single-root/cycle-repair. Apply it to **predicted UPOS**.
- Comparison A: global-majority train UPOS, previous-token head + train-dependent-POS majority relation. Comparison B: predicted-form UPOS feeding *same* W13 syntax model. Comparison C (oracle diagnostic only, **not headline**): same W13 syntax model with publisher gold heldout UPOS supplied explicitly under oracle privilege.
- All three predictions occur before the scorer consults target HEAD/DEPREL. C is for error propagation only and never called nonoracle.
- Fixed metrics: all-token POS exact accuracy, macro F1 over observed tag inventory (no unspecified tag drop), model and naive baseline UAS/LAS with integer correct counts and complete denominators, oracle gap, zero/invalid tree count, unknown/backoff proportions, per-role/UPOS error, group micro and macro (one target king = macro identical to micro), exact Egyptian FORM-sequence duplicates across train/eval groups, sentence ID intersection, and SHA-256 reproducible report.
- Do not drop duplicate heldout examples opportunistically; document cross-group exact duplicates separately and mark contamination risk. No hyperparameter selection using target labels or cherry-picked examples, even when results are poor. Tests reject any gold-POS access by public inference, target injection, source drift and train/test group mixing.

## Outcome gates
- This does not demonstrate Hieratic pixel recognition, later Egyptian period transfer, fluent German translation, semantic adequacy or unseen physical manuscript generalization.
- **LING-003 0/2**, **verified goal 34.5/100**, **validated Hieratic VLM model experiments 0**, official UD TEST unopened unless separately explicitly authorized.
- If no genuinely independent text/translation witness and separately verified license is available, record an external semantic experiment blocker rather than use exposed AES cohorts.
