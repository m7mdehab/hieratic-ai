# W10 LING-003 — preregistered new AES archival-domain generalization test

**Classification:** Genuine first-use external scholarly **editorial text** evaluation; negative finding. **Not** Hieratic manuscript-image reading, independent semantic adjudication, grammatical competence proof, or a certifiable held-out gold reading benchmark.

## 1. Chronological preregistration and licensed data

1. Pre-registered before access to original archive contents: Git commit `7bd1d01c1d9d6242625a1dcd3363e6aaac15ffba`, `W10_PREREG_ARCHIVE_HOLDOUT.md`. Source and whole-group cohort rule, independent source-name blocking, 5-fold training/dev strategy, frozen algorithm thresholds and comparisons were recorded before ingesting the new external reference translations.
2. Compositional method code was then committed as `d836f7e9273859343dccdd23619e6aedd792842e`, **before** the archive first-read and evaluation. This is important because the new archive reference translations became visible after the method was frozen.
3. Publisher: Simon D. Schweitzer, contributors to AES/AED, scholarly Ancient Egyptian Sentences repository `https://github.com/simondschweitzer/aes` at `35276d2527cca1a055e31ed5f6683e777717170f`. Publisher README licenses repository files **CC BY-SA 4.0**. Original file `files/aes/_aes_bbawarchive.json` Git blob SHA1 `014cccf04235d9e093fca24ed48c62630d235852`, **5,855,067 bytes**. The original contains **3,081 published sentence objects spanning 1,163 source-text IDs**. No live TLA website content was copied (its bulk scientific-data reuse differs).
4. Deterministic predeclared selection of the 32 original text IDs with smallest SHA-256(`hieratic-ai-ling003-w10-archive-v1:` + text ID) gave **47 complete-source-group sentences**, all 47 carrying publisher German sentences. Their allowed CC BY-SA text fields are stored at `ling/translation/data/w10_archive_32groups_ccby_sa.json`, pinned Git blob SHA1 `d3d7b57aef7bd10a48df6b1be340be8ff5b36e32`. Each token includes only Egyptian `written_form`, not hidden test cotext or lemma labels; references are separately held in `sentence_translation`.
5. Prior corpus overlap: **0 matching text IDs** between the 32 new source groups and all **418** text IDs in the four earlier AES corpora, including the *now exposed* Tübingen-stelae reserved set. This is source-ID-level separation, **not** independently verified distinct physical papyri, editorial schools, works or language-family independence. AES archives and the earlier AED/AES samples share contributor/scholarly lineage.

## 2. Models and immutable evaluation

Only the three W9 internal training/dev subcorpora (904 sentences with German translations) can supply parameters, cotext alternatives or sentence memories. Five fixed `SHA256(text_id)` source-group-blocked folds are internal development sanity, **not** the new external evaluation. The previously exposed Tübingen set is excluded from new training, cotext lookup, evaluation selection and threshold fitting.

- **Gloss control:** most-supported German publisher cotext gloss for the same Egyptian written form from other training text IDs; `[?]` for unobserved forms.
- **W9 retrieval:** original, unchanged `TranslationMemory.predict` with its previously chosen threshold **0.0**. Copies a real training text's whole German editorial sentence where Egyptian word-form overlap triggers retrieval, even for nonidentical original source sequences.
- **W10 constrained composition:** builds German lexical units **only** from other-training-text word glosses. A neighboring Egyptian-form contextual choice requires at least **two independent source-text IDs**; otherwise deterministic global train-form backoff. Local adjacent-unit inversions require two training-source witnesses and more than twice the normal-order witnesses. No target reference/German words, whole translated training sentence, unearned German function words, invented personal names or grammatical role labels are injected. It keeps alternatives, explicit abstentions, source-ID support and exact source-slot order.

A real grammatical/semantic sentence decoder was **not** established. The W10 composition is a conservative source-attributed German lexical-unit composer with occasional possible train-supported local reorderings; the new external test will show whether any reordering activates at all.

## 3. Full first-use archive external results (all 47 publisher references)

Results were printed by hosted Linux Project Governance on the first external execution for the frozen method. Initial CI had **one test-assertion error-message mismatch**, unrelated to reference scoring or implementation; the later repair changed **only** the expected substring of that negative test, leaving source population, model, algorithm, frozen thresholds and scoring unchanged.

| Metric | Train-only gloss | W9 sentence memory | W10 composition |
| --- | ---: | ---: | ---: |
| New published German sentences scored | 47 | 47 | 47 |
| Independent original AES text IDs (not independently verified physical supports) | 32 | 32 | 32 |
| Publisher reference German words | 199 | 199 | 199 |
| German words emitted | 147 | 269 | 151 |
| Matching German multiset word occurrences | 4 | 5 | 4 |
| **Micro German word multiset F1** | **0.02312139** | **0.02136752** | **0.02285714** |
| Macro sentence word F1 | 0.01885420 | 0.02736483 | 0.01885420 |
| Macro in-house character ngram F2 | 0.10104778 | 0.06863804 | 0.10098361 |
| Whole-sentence copying from nonidentical Egyptian source forms | 0 | **5** | 0 via retrieval |

**W10 composition-specific controls, 162 original Egyptian source word-form tokens:**
- **107** unavailable lexical glosses yielded explicit unknown abstentions; all 47 targets were still included in the denominator.
- **5** unit hypotheses used training-source-supported Egyptian neighboring-form contextual selection.
- **0** eligible adjacent German gloss swaps satisfied the fixed 2-text and >2× training-evidence criterion on the novel archive corpus.
- **0** accidental exact training German sentences with nonidentical source forms were generated by the compositional method.

The five original source-text-group internal development fold compositional micro F1 results were **0.15342087, 0.17804428, 0.13868178, 0.15609175, 0.17232598**, dramatically above the observed new archival-domain ~0.023 range. Those are NOT new held-out results.

**Deterministic full W10 report SHA-256:** `da1d4275c9f78e4ad229ab1681de58a3374497df6a150e78cffc03c8f3c1b04c`. All raw derived text and scoring denominators are in the checked-in CC BY-SA cohort and code; reproduce with:

```bash
python -m ling.translation.w10_evaluation verify
python -m ling.translation.w10_evaluation internal
python -m ling.translation.w10_evaluation external
python -m unittest tests.linguistics.test_translation_layer -v
```

## 4. Interpretation and next scientific blocker

**The frozen W10 model did not generalize to this independent editorial domain.** It is *slightly worse* than the simple gloss control by micro overlap (0.02285714 vs 0.02312139). Its optional syntactic local-swap rule never activated, so there is no evidence of learned German word-order generalization in this cohort. W9 nearest-neighbor memory also underperformed the gloss baseline and copied five whole sentences from different Egyptian input sequences, preserving a named-entity/role hallucination risk.

The dominant observed bottleneck is domain lexical coverage (**107/162 unknown source-token glosses**), not an externally established syntactic improvement. Even identical publisher German words would not demonstrate correct agent/patient role, negation, gender, syntax or historical meaning; these in-house F1/F2 overlap metrics do not score semantic adequacy. No selective scoring of favorable examples or retrospective archive threshold fitting is allowed. **This archive corpus is now exposed** after first-use evaluation; a future revised model must use a separately preregistered previously unseen source, not relabel this one as untouched.

Open gates: richer legal and independent genre/witness training, defensible grammatical composition, independent professional semantic adjudication, licensable photographed source-line alignment, physically disjoint edition genealogy, and original image-to-reading-to-translation linkage. W10 provides a real runnable constrained compositional *diagnostic* and new genuine negative external evaluation, **not completion of the LING-003 2.0-point milestone**. Canonical **34.5/100**, zero independently validated real manuscript model experiments, zero trained neural models, LING-003 active.


**Per-item attribution and release gate:** `ling/translation/data/w10_archive_rights_manifest.json` captures all **47** publisher original sentence IDs, original source text IDs, original AES `owner` editor attribution, original pinned Git blob, derived cohort Git blob, `CC-BY-SA-4.0`/`OPEN-SA`, and explicit nonadmission to production training or DATA-008. The original full source's independently computed SHA-256 and source-to-photographic-physical identity are not available in this artifact; they are transparently marked unverified. This test-only licensed editorial data is not represented as a fully item-audited public training corpus.
