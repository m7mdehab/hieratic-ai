# LING-003 — Meaning and translation layer (Wave 8)

**Canonical task:** ready, weight 2.0 points, dependency LING-002 accepted. **Owner implementation branch:** task/LING-003-real-aes-translation-w8.

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
