# Wave 12 LING-003 — original AES editor-annotated Egyptian grammar evidence

**Independent result and methodological verdict:** First preregistered W12 temple target was legally accessible but **BLOCKED** by frozen cohort size (11 available original text IDs instead of the required 24). In a separately registered, untouched W12B Amarna experiment, the train-only source-supported Egyptian part-of-speech (POS) model achieves **780/1649 = 47.301395%** complete-denominator POS accuracy versus **773/1649 = 46.876895%** for its form-majority baseline. This is a **small 7-token / 0.4245 percentage point net improvement**, NOT a demonstrated compositional grammar or sentence meaning capability. No weighted LING-003 points.

## Chronology, data and rights

1. W12 temple preregistered *before inspection* in `W12_PREREG_TEMPLE_GRAMMAR.md`, commit `b872644a040c6cc9784573695c5c58f5eded9356`. The original AES temple publisher source `_aes_bbawtempelbib.json` has 1,879 sentences but just 11 source-text IDs, violating the explicit minimum of 24 independent text IDs. **W12 blocked** with no model test and no source annotations admitted to training: `W12_TEMPLE_COHORT_BLOCKED.md`. Do not retrospectively reduce sample size or quietly reuse this source as unseen.
2. **Separate W12B** Amarna source/method/cohort preregistered at Git commit `d9e7bcb6b51742f527ae60830143b31cc67d6cde`, `W12B_PREREG_AMARNA_GRAMMAR.md`, before access to its original source records or scores. Original publisher AES CC BY-SA 4.0 Amarna `files/aes/_aes_bbawamarna.json`, upstream revision `35276d2527cca1a055e31ed5f6683e777717170f`, Git blob `5e512681dc0d1ac7177a62531582b3473a0a11f2`, **14,683,204 bytes**. Original population: **2,634 sentences / 399 distinct original source-text IDs**.
3. The frozen salt `hieratic-ai-ling003-w12b-amarna-grammar-v1:` with SHA-256(original source-text ID) chose the first **24 entire groups**, totaling **163 real AES sentences / 1,691 Egyptian editorial written-form tokens**, of which **1,649 have original publisher POS tags** and 42 lack them. The original whole source-ID universe is independently pinned and ranked, not just a convenient last hash cutoff; source-text overlap with prior W9 Tübingen, W10 archive, W11 biography, W11 training donor or exposed W12 temple is zero.
4. Training restricted to **3,925 exact original AES train-side sentences over 1,526 source-text IDs**, from W9 three original publisher developer subcorpora and the W11 archive donor with 32 former W10 archive external text groups permanently removed. The donor's word forms were rechecked against the original AES archive Git blob before extracting original `pos` and known morphological features. The training and new evaluation source bytes remain separately pinned by immutable Git blob identities.
5. Versioned source output files under `ling/translation/data/`: `w12_grammar_train_publisher_ccby_sa.json` (source-attributed train grammar rows), `w12b_amarna_inputs.json` (target written form IDs only), `w12b_amarna_reference_annotations.json` (separate original publisher POS/morphology scoring labels), `w12b_amarna_source_universe.json` (full source rank) and `w12b_amarna_rights_manifest.json` (all 163 original sentence ID, editor attribution, OPEN-SA CC BY-SA and explicit test-only/nonadmission rights flags). Publisher editors in selected rows: Gunnar Sperveslage 148 and Ingelore Hafemann 15. **Neither raw publisher photos nor rights for photographed Hieratic pixels are asserted.**
6. W9 Tübingen, W10 archive, W11 biographies and W12 temple were already exposed and did not become hidden new tests, training data or model-selection material for this experiment. This W12B Amarna cohort is **now exposed after first-use scoring** and must likewise never be called untouched after changing hyperparameters.

## Models fixed before target inspection

- **A — form-majority baseline:** exact Egyptian `written_form` → the POS tag most attested in other original source-text IDs, one vote per source-text ID for each tag; deterministic alphabetic tie. Unknown form → null abstention.
- **B — contextual original-token evidence:** same exact-form candidate inventory, optionally choose a tag when immediate left/right Egyptian word-form context provides at least two *different training text IDs*, testing both neighbors first then left/right, otherwise fall back to A. A context can never introduce a new tag unattested for that exact written form.
- **C — morphology candidate lattice:** train-original `genus`, `numerus`, `status`, `inflection`, `voice`, `verbalClass` values associated with the same exact original form and chosen POS, retaining all alternatives and distinct training-source evidence. Missing target field remains missing and is not treated as a guessed negative.
- **D — original token adjacency evidence:** count source-supported adjacent POS pairs. A POS bigram is **not** a syntactic dependency or a subject/object relation. No German-word insertion, grammatical-role construction, translation, lemma restoration or morphological inference from letters.

Prediction takes only `forms` and `text_id`. It does not receive the target original German reference, POS, lemma, morphology or cotext annotations. The target gold file is opened **only after** all frozen predictions have been calculated. All publisher labels belong to real scholarly editorial data, but **not** independently blind expert adjudication or source-image aligned Hieratic original readings.

## Frozen first-use Amarna POS scores (1649 original publisher labels)

| Denominator and outcome | Form-only POS | Context-assisted POS |
| --- | ---: | ---: |
| All Egyptian tokens, incl. 42 without publisher POS | 1,691 | 1,691 |
| Actually scoreable publisher POS tokens | 1,649 | 1,649 |
| POS assignments attempted on publisher-labeled tokens | 954 | 954 |
| **Correct predictions (abstentions count incorrect)** | **773 / 1,649** | **780 / 1,649** |
| **Full-denominator POS micro accuracy** | **0.46876895** | **0.47301395** |
| Coverage of POS-labeled original token units | 0.57853244 | 0.57853244 |
| Conditional accuracy *on 954 predictions* | 0.81027254 | 0.81761006 |
| Macro per-source-text-ID accuracy | 0.36066520 | 0.36289471 |

Other checks: **905/1,649** publisher POS tags are somewhere in the original train-attested candidate inventories (**54.881747% candidate recall**). Exactly **37** predicted POS assignments differ between methods, yielding a net gain of **7** correct predictions. Original-source context was sufficiently witnessed in **279** token units; **436** token units have multiple candidate POS alternatives; **570** adjacent predicted POS pairs have training-attested POS bigram evidence, *not dependency gold*. All **24** selected source-text groups have at least one scoreable original publisher POS label.

### Morphological feature candidates

All metrics refer to **publisher original label coverage**, NOT certified inflection or semantic accuracy. Each denominator is the number of real source tokens with that original feature label; conditional candidate *set recall* need not imply top-1 disambiguation.

| Source-original feature | Publisher labels | Candidate contains label | First candidate correct |
| --- | ---: | ---: | ---: |
| genus | 412 | 168 | 164 |
| numerus | 605 | 267 | 267 |
| status | 413 | 158 | 134 |
| inflection | 246 | 43 | 26 |
| voice | 146 | 48 | 47 |
| verbalClass | 287 | 98 | 93 |

Exact-head GitHub-hosted Project Governance `37923288454` on W12B implementation head `2c65fdaf88bb1feb3a88dd67acba4d29d1ce6e51` passed full suites: **34 governance, 182 data, 84 linguistics and 299 evaluation** tests. No cross-task files touched and scope LING-003 passed. Frozen deterministic report SHA-256: **`a339e434a29f735330151d31115d3d91828aa836b47b00e1f8b185907272f3a6`**.

## Reproducibility and scientific decision

```bash
python -m ling.translation.w12b_evaluation verify
python -m ling.translation.w12b_evaluation evaluate
python -m unittest tests.linguistics.test_translation_layer -v
```

**Scientific conclusion:** the source-grounded POS subsystem has measurable but limited true external publisher annotation accuracy; full-denominator POS is under 48% and morph feature recall is weak. The 81.76% conditional POS accuracy is on only 954/1,649 covered units and is NOT the headline. This experiment does not produce German sentence translations, identify ancient Egyptian subject/object roles or infer verified syntactic dependency trees; lexical and POS alternatives do not prove meaning. It uses source-authentic **editorial transliteration and annotation**, not physical Hieratic handwriting, independent reviewed unseen witnesses or blind semantic adjudication. LING-003 remains active at **0/2 scientific points**; canonical Hieratic-AI progress stays **34.5/100** and validated real Hieratic model experiments stay **0**. Subsequent scientific work needs lawfully sourced Egyptian grammatical dependency/role annotations and a NEW predeclared unseen source/witness cohort; the Amarna test is now exposed.
