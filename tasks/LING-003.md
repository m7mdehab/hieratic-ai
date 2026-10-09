# LING-003 — Meaning and translation layer (Wave 8)

**Canonical task:** active, weight 2.0 points (not yet earned), dependency LING-002 accepted. **W8 implementation branch:** task/LING-003-real-aes-translation-w8. **W9 research branch:** task/LING-003-w9-contextual-translation-heldout.

## Objective

Implement a meaning/translation layer downstream from recognized and linguistically interpreted ancient Egyptian, measured independently of the image recognition and transliteration layers. Preserve word alternatives, missing glosses and source provenance; do not fabricate fluent sentence translation from a dictionary string.

## W8 first genuine translation baseline

Uses **actual AES publisher German sentence translation fields**, CC BY-SA 4.0, immutable published source blob pinned in the already accepted LING-002 corpus. All 445 available source sentences, 311 source-text IDs and 444 actually present editorial sentence translations are processed. A deterministic word-gloss sequence is built from **other** AES source texts' contextual German glosses for exactly matching source Egyptian word forms. It deliberately does **not** use source sentence gold, target word glosses, target lemma ID, reference German sentence or unlicensed images. Cross-text homograph gloss alternatives and unknown abstentions are retained. No heuristics silently infer Egyptological roots, grammatical roles or fluent syntax.

The evaluation compares generated gloss strings to published complete German sentence translations with source-text-ID exclusion, reporting number of available/scoreable items, gloss coverage, per-sentence bag-of-word F1 and corpus micro precision/recall/F1. The reference translation is consulted only **after** generation. The metric is explicitly a diagnostic of lexical coverage and partial translation recall, **not BLEU**, fluency, semantic adequacy, an image-conditioned OCR score, source-witness-level generalization, unseen pretraining performance or blinded expert evaluation. Data are not admitted to DATA-008 and the result is not a certification of scientific model performance.

## Core acceptance criteria

- [x] Versioned real publisher source provenance and CC BY-SA rights evidence inherited without creating extra source rights.
- [x] Publisher 445-sentence/311-group corpus, 444 real German sentence labels, original byte identity and no mutated target labels.
- [x] Deterministic reproducible Egyptian-to-German *lexical gloss sequence* predictions with alternative glosses and explicit unknowns.
- [x] Actual genuine German sentence-level publisher comparison under held-out source text group labels; independent reporting from visual recognition.
- [x] Adversarial tests for deliberate reference contamination, target word gloss and lemma leakage, missing gloss abstentions, alternative meaning, source bytes and reproducibility.
- [ ] **Full fluent semantic/syntactic translation and evaluation:** a gloss sequence is not a grammatical sentence; requires a separately implemented contextual translation model or grammar mechanism.
- [ ] **Independent held-out manuscript-level blind gold:** different AES text IDs are not necessarily physically distinct witnesses, and publisher's AED/AES source genealogy and model pretraining may overlap.
- [ ] **Downstream exact annotated manuscript recognition-to-translation integration:** cannot yet score end-to-end on eligible original image + diplomatic gold + licensed target reference.

## Completion decision rule

The implemented software and source-translation diagnostic is **substantial and real**, but do not automatically mark the 2-point LING-003 milestone `validated` unless overseer independently determines the missing fluent/semantically adequate translation acceptance requirement is satisfied. No automatic task or canonical metric changes within this PR. Preserve 34.5/100, zero real validated image/Hieratic experiments and zero trained models until independently earned.

## Reproduce

~~~bash
python -m tools.translation_layer verify
python -m tools.translation_layer evaluate
python -m tools.translation_layer evaluate --examples
python -m tools.translation_layer predict --sentence-id SOURCE_AES_SENTENCE_ID
python -m unittest tests.linguistics.test_translation_layer -v
~~~

**Attribution:** Simon D. Schweitzer and AES/AED text editors, https://github.com/simondschweitzer/aes, licensed CC BY-SA 4.0. Raw corpus source SHA-1 `7bfcba9678b64c3526a1123996a0714b5f76812f`, revision `35276d2527cca1a055e31ed5f6683e777717170f`. Different physical supports, provenance and image release are separately governed.

## Authentic sentence-level parallel extension

The publisher's 445 original AES sentences include **14 cases with an identical full Egyptian source token sequence in a different source-text ID**. The implemented pipeline can retrieve a genuine **other-text, publisher-authored German whole-sentence translation** for those cases (and preserves all alternate translation strings). The reference translation from the target text ID remains excluded, including any within-text duplicates; this is not self-leakage or a model hallucination. For the rest it abstains from claiming fluent translation and explicitly falls back to gloss sequences. Count of actual cross-source published full-sentence parallels is fixed in source-verified tests. This is real and substantial coverage of a limited domain, not general compositional translation competence.


## Wave 9 — contextual method + genuine adverse external result (scientific status unchanged)

W9 was a substantial new run, not an extension to the existing 445-sentence glossary: pinned CC BY-SA texts from three additional real AES subcorpora made **1,156 authentic sentences, 1,151 publisher German translations, 418 AES text IDs**. The source-text-blocked training/dev collection has 904 translated sentences; the entire Tübingen-stelae edition subcorpus (247 sentences / 21 text IDs) was locked out of training, word-gloss access and threshold selection. A deterministic five-fold internal training-only contextual/TF-IDF German sentence memory was tested against train-only gloss control. It was scored separately from image recognition and independently checked by exact-head CI.

Development source-text-grouped micro German-word F1 increased **0.15368591 → 0.24261684**, but on the reserved, harder different subcorpus performance **fell 0.15275625 → 0.14259102**; macro word F1 and character F2 also fell. **40 of the 247** external outputs copied whole German sentences from *non-identical* Egyptian source sequences. This demonstrates a serious formula, grammatical structure and personal-name hallucination risk. The context model is therefore **not shown to generalize** and must not be claimed as a semantically adequate translation system.

Full details, checksums, denominators and negative results: ling/translation/experiments/W9_CONTEXTUAL_TRANSLATION_EXTERNAL_TEST.md . The pinned AES publisher sources are open scholarly text only, not admissible source-aligned original Hieratic manuscript gold, so DATA-008/VLM certification remains blocked. This text experiment neither trains a neural translation model nor evaluates a bona fide Hieratic photographic reading.

**W9 output was a completed experimental work package with a clear negative finding, not completion of the full LING-003 weighted scientific milestone.** Remain **active** at 0/2 LING-003 points and canonical 34.5/100. A second untouched external source corpus, genuinely compositional grammatical translation and independently adjudicated semantic adequacy remain required before re-review. Never retune on the now-revealed Tübingen references and present such performance as unseen.


## Wave 10 — original-source blocked archive validation and real compositional lexical unit mechanism

Implementation owner: overseer. Preregistered W10 archive selection `ling/translation/experiments/W10_PREREG_ARCHIVE_HOLDOUT.md` was committed BEFORE inspection; Simon D. Schweitzer AES `bbawarchive` publisher source CC BY-SA 4.0 exact blob `014cccf04235d9e093fca24ed48c62630d235852` was then filtered by predeclared hash selection into **32 disjoint text IDs and 47 new archival sentence translations** with zero overlap against all 418 W9 source IDs, including the now-exposed Tübingen external test. Derived original-text-only edition cohort Git blob `d3d7b57aef7bd10a48df6b1be340be8ff5b36e32`.

New `ling/translation/compositional.py` implements source-text-exclusive lexical sense selection with independent neighbor-context support and limited adjacent German unit reversal only where at least two independent *training* text sources provide genuine unambiguous word-order evidence. It cannot copy whole training German publisher sentences by retrieval, never uses target reference to generate, abstains unknown tokens, and records alternatives and conditional supports. `ling/translation/w10_evaluation.py` compares train-only gloss, original W9 sentence memory frozen at threshold 0.0 and this compositional method on five original grouped development folds plus a NEW distinct archive editorial-source cohort. Tests cover tampered sources, different text IDs, secret target labels, names, independent reorder votes and deterministic original-publisher scoring.

**Boundary:** Egyptian inputs remain editor-curated text, not actual Hieratic pixels; lexical composition is not proof of fluent grammatical or semantically correct translation. The new source ID separation does not independently prove physical manuscript or scholarly genealogy separation. Exact manuscript-aligned blind gold and expert semantic adjudication remain unavailable; task **active, 0/2 LING-003 points**, canonical **34.5/100**, validated real Hieratic model experiments **0**. Results and any negative findings are documented separately without post-hoc external test tuning.
