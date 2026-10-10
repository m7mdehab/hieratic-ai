# LING-003 — Source-grounded Egyptian meaning and German translation diagnostic

The implementation at `tools/translation_layer.py` consumes the accepted AED/AES scholarly corpus as a separate linguistic layer. **This is executable software over 445 real published Egyptian source sentences and 444 German editorial translations, not an invented synthetic translation benchmark.** The publisher release explicitly includes independently typed sentence translations and word-level cotext glosses under CC BY-SA 4.0. Source: https://github.com/simondschweitzer/aes; exact pinned revision/source blob specified in `ling/lexical/data/scholarly_source_manifest.json`.

## Inputs and outputs

Given original Egyptian `written_form` tokens and source text ID, the lookup produces a **German contextual word-gloss sequence** based only on *other texts'* publisher cotext evidence. It leaves punctuation/syntax unrepaired and shows `[?]` for unknown forms. A token can have several incompatible German glosses; alternatives stay visible. Repeated text-form occurrences support a candidate only once per other text, avoiding inflated votes from repeated words in a single text. The source's actual sentence translation is never read by candidate generation.

The output type is `ORDERED_GERMAN_WORD_GLOSS_SEQUENCE_NOT_FLUENT_TRANSLATION` and explicitly records `certified_translation_accuracy: false`. This is a first empirical translation layer baseline and bottleneck diagnosis; it must not be portrayed as full fluent translation or semantically correct sentence reconstruction.

## Leakage-resistant, reproducible evaluation

For each of 445 AES publisher sentences, remove cotext reference records with its source `text` ID before translating; 444 have available actual German sentence references and one is missing. Compare the frozen predicted gloss string against the sentence's editorial reference using case-folded, punctuation-agnostic multiset word overlap. Report macro sentence F1, micro precision/recall/F1, source text groups, tokens and abstentions. Do not treat bag-of-word overlap as translation fidelity: different grammatical constructions, omission, ambiguous homographs and word order require real additional methods. Current translation text is German, while AED dictionary's English gloss layer is *not* substituted as a German sentence translation.

The same original publisher source is cited by LING-002, so **cross-text** exclusion does not prove independent editorial source/witness or model pretraining independence. No image, source photo, archaeological period holdout, contemporary Egyptologist adjudication, or full translation model is evaluated. Publisher-authored translation remains a reference rather than new blindly adjudicated gold. The score is a **development diagnostic, not a publishable generalization/quality estimate**.

## Commands

~~~bash
python -m tools.translation_layer verify
python -m tools.translation_layer evaluate
python -m tools.translation_layer evaluate --examples
python -m tools.translation_layer predict --sentence-id AES_SENTENCE_ID
python -m unittest tests.linguistics.test_translation_layer -v
~~~

The loader validates source revision and Git blob integrity, verified scholarly CC BY-SA 4.0 source registry and constant 445/444/311 population; missing or modified source data fail closed. Synthetic fixtures are not counted as real evidence. A deterministic SHA-256 of the full evaluation report is included to facilitate independent exact-execution comparison. No network access, paid API, manuscript image acquisition, data-release admission, or model training occurs.

## Next substantive scientific completion requirements

1. Build a sentence-level German grammatical translation component based on legitimate paired data, with genuine zero-shot/test holdout by physical witness and a documented causal training/evaluation split; do not claim success from word glosses alone.
2. Independently validate translation against a licensed heldout edition/human adjudication and score semantic adequacy (including alternatives, lacunae, restorations and unknowns) separately from OCR/transliteration errors.
3. Integrate image-recognition and linguistic outputs once Luna/Gemini's original-image and true model-input pathways provide usable authenticated predictions. Until then, report translation separately from recognition.

Retain canonical scientific points/status until review; the implementation is honest research progress, not automatic task completion.

## Exact other-source whole-sentence translation retrieval

A second production path indexes AES sentence translations by **the complete ordered sequence of Egyptian `written_form` values**. It chooses an actual publisher-translated **German sentence from a different source-text ID**, and retains competing alternatives; no target text's own translation enters the prediction. In this 445-sentence edition it yields **14 actual other-text full-sentence parallels**. It is explicitly labelled `CROSS_TEXT_EXACT_SENTENCE_PARALLEL`. All remaining sources use the word-gloss abstention-aware fallback. These 14 readings reflect shared phrases/formulae and may represent historical editorial or witness overlap; they do **not** constitute proof of generalization or machine-composed fluent translation.


## Downstream LING-002 integration

The same real AES German meaning evidence can now enrich **an immutable, schema-validated LING-002 interpretation manifest**, without changing the original item's diplomatic reading, alternative reading IDs, morphological features, lexical version, source identity or existing source ambiguity. Its output is a distinct, SHA-256-versioned translation layer rather than an edit of upstream gold:

~~~bash
python -m tools.translation_layer from-lexical --interpretation /path/to/LING002.json
# Mandatory for original AES source items, to prevent the same text's own glosses:
python -m tools.translation_layer from-lexical --interpretation /path/to/LING002_AES.json --exclude-text-id AES_ORIGINAL_TEXT_ID
~~~

The adapter verifies the **original LING-002 JSON Schema and canonical interpretation-version digest**, then attaches source-supported exact-form German gloss hypotheses to **each** alternative source reading. Unknown or unmatched readings abstain; multiple alternatives stay multiple, with support counts by **distinct other AES text IDs**. Synthetic source readings stay explicitly synthetic in origin; a German gloss lookup does not convert an upstream synthetic input into historical evidence. Authenticated new manuscripts can use published contextual glosses without falsely asserting the manuscript was found in AES. For an AES source identity, a supplied excluded source text ID is mandatory; the adapter never infers the ID from a different identity namespace.

This is **not** an Egyptological word-sense disambiguator, German grammatical sentence composition or blind image-to-translation evaluation. All versions, inputs and owner-visible ambiguity are traceable. In particular, adding German candidate glosses to a synthetic interpretation does not make them licensed scholarly gold for that synthetic text.

## W9 — Held-out authentic Egyptian→German contextual translation memory

**Corpus and provenance:** Four original Simon D. Schweitzer / TLA-AED AES subcorpora, 1,156 published Egyptian sentences, 1,151 German editorial translations, 418 text IDs. Source repository: https://github.com/simondschweitzer/aes at exact revision 35276d2527cca1a055e31ed5f6683e777717170f . All four publisher Git blobs and CC BY-SA 4.0 source conditions are verified against immutable hashes by the new loader. Attribution and CC BY-SA share-alike obligations remain. No new manuscript-image rights are claimed. Do not extend the dataset license to all live TLA website content, which has separate terms.

**Strict reserved test:** All 247 published sentence translations from the Tübingen stelae AES subcorpus (21 source-text IDs) are set aside as an **entire external subcorpus**. No German references, contextual word glosses, document frequency features, example phrases, tuning or other target labels from that collection enter the translation memory or model selection. The remaining 904 translated sentences in the Felsinschriften, SMAEK and Graeberspzt collections are subdivided into five fixed SHA-256(source-text-ID) development folds. Training and development for every fold use different source-text IDs, then select a similarity threshold from 0.00, 0.15, 0.30, 0.45, 0.60, 0.80 or 1.00 by **development micro word F1 only**. Ties choose the stricter threshold. The external subcorpus is scored once after selection.

**Method:** Real source Egyptian token sequences drive train-only, TF-IDF-style context-sensitive nearest-neighbor ranking with cosine overlap, length ratio and minimum shared-form/coverage constraints. A legitimate cross-text published **German sentence** is returned when sufficient contextual source evidence exists; otherwise the system returns a documented sequence of word cotext translations from training sources with **[?] unknowns**. It returns nearest publisher sentence provenance and explicit source-word differences, because a copied sentence may hallucinate a wrong name or grammatical agreement. These are *retrieval outputs*, not a trained generative grammar, verified Egyptological sentence readings or image-based OCR.

**Metrics:** case-folded punctuation-normalized German *multiset word F1* (micro and macro sentence) and in-house *mean character n-gram F2* over 1–6 codepoints (not sacreBLEU). Report exact denominators, prediction-mode counts, non-identical retrieval count, separate internal development metrics and external test metrics, original Git blobs, model-selection threshold and deterministic report SHA. German phrase overlap is **not semantic adequacy**. Editorial source-text IDs may conceal physical support/editor genealogy overlaps, and public corpus data may occur in pretraining. No blinding, third-party image ground truth, professional adjudication or 2.0 capability-credit claim follows from test results.

**Reproduction:**

    python -m ling.translation.contextual verify
    python -m ling.translation.contextual evaluate
    python -m ling.translation.contextual evaluate --output /tmp/aes-w9-translation.json
    python -m ling.translation.contextual predict --sentence-id EXACT_AES_SENTENCE_ID
    python -m unittest tests.linguistics.test_translation_layer -v

The real textual dataset is separately licensed and must never be promoted to DATA-008 image corpus or become HieraticBench benchmark gold. Historical LING-003 2.0 points remain pending fluent semantically adequate translation and independent image/witness-grounded evaluation.


## W10 — preregistered genuinely new AES archive heldout + conservative compositional mechanism

**Registered before target ingestion:** `ling/translation/experiments/W10_PREREG_ARCHIVE_HOLDOUT.md`, registration Git commit `7bd1d01c1d9d6242625a1dcd3363e6aaac15ffba`. Only after registering source, hashed 32-group selection and fixed model thresholds was the full publisher archive blob accessed. The original AES Git blob is `014cccf04235d9e093fca24ed48c62630d235852` (5,855,067 bytes) at the same 2020–21 publisher revision as existing scholarly sources. The archive contains 3,081 sentences / 1,163 original source text IDs. The predeclared 32 SHA-256-ranked complete source groups yield 47 original editorial translation sentences. Their derived Git blob is `d3d7b57aef7bd10a48df6b1be340be8ff5b36e32`. No group identity overlaps any of the 418 prior W9 train/dev/Tübingen source text IDs; the prior Tübingen external benchmark is **exposed and excluded from all new method selection**.

**Rights:** Publisher AES files are CC BY-SA 4.0 (Simon D. Schweitzer and AED/AES scholarly editors). The derived archive cohort is also CC BY-SA 4.0 and retains publisher source/edition relationships; it includes only text `written_form` and publisher `sentence_translation`, not photographs or a claim to licensed manuscript gold. Live tla.digital website has separate bulk scientific-data restrictions. Independent physical-witness identity and editor genealogies remain unresolved.

**Code and fixed method:** `ling/translation/compositional.py` constructs original Egyptian token positions from source written forms, with lexical candidates restricted to the other training texts' published German cotext glosses. For a given Egyptian form, it chooses among attested glosses with an explicitly evidenced neighboring-form context only where at least **two independent training text IDs** support it; otherwise uses the most-attested train-only gloss. Unknown written forms produce `[?]`, preserving lexical alternatives and support. It can invert two adjacent German gloss units only when at least **two independent source-text training items** establish the reversed order in German publisher sentences and reversed support exceeds twice normal support. The two editorial cotext glosses must each occur exactly once without overlap in the training sentence. This is a **constrained lexical-unit compositional hypothesis**, not an inferred subject/verb/object parse or a complete fluent translation.

**Evaluation:** `ling/translation/w10_evaluation.py` compares (1) other-training-text glossary baseline, (2) W9 TF-IDF whole-sentence memory with its *previously selected* 0.0 similarity threshold and (3) frozen compositional method. The same 904 W9 non-Tübingen translated sentences supply training, with five SHA-256(text ID) folds only for historical internal development sanity. The archive 32 groups / 47 sentences are a separately preregistered external editor-text domain; only after frozen development are their publisher references scored. The module audits exact Git-blob identity, all four prior corpus text ID populations, complete heldout counts, exact result determinism, source-token abstention, accidental whole-training-sentence overlap, provenance/alternative candidates, known structural inversions and all failed comparison modes. Metrics remain German word multiset F1 and in-house char n-gram F2, **not** semantic accuracy or BLEU. No model training, GPU/API charges, expert gold, source image pairs or DATA-008 corpus admittance.

**Reproduce:**

    python -m ling.translation.w10_evaluation verify
    python -m ling.translation.w10_evaluation internal
    python -m ling.translation.w10_evaluation external
    python -m unittest tests.linguistics.test_translation_layer -v

This work provides a genuinely new **source-group-blocked publisher text reference population**, not a guarantee of independence by physical papyrus/scribe/editor, and a measurable structural mechanism instead of copying publisher German reference sentences. Its scientific acceptance and LING-003 2-point completion remain pending independent semantic review and end-to-end image-linked evidence.


**Per-item attribution and release gate:** `ling/translation/data/w10_archive_rights_manifest.json` captures all **47** publisher original sentence IDs, original source text IDs, original AES `owner` editor attribution, original pinned Git blob, derived cohort Git blob, `CC-BY-SA-4.0`/`OPEN-SA`, and explicit nonadmission to production training or DATA-008. The original full source's independently computed SHA-256 and source-to-photographic-physical identity are not available in this artifact; they are transparently marked unverified. This test-only licensed editorial data is not represented as a fully item-audited public training corpus.


## W11 — archive-only training expansion with fresh source-ID-locked biographies cohort

**Preregistered BEFORE opening biography publisher sentences:** `ling/translation/experiments/W11_PREREG_SCALED_TRAIN_BIOGRAPHY_HOLDOUT.md`, commit `c3f88e9274ce1f088619f45aef5ea74be21dcedb`. At that point, original source/blob IDs, source split, 32-group hash rule, exclusions, exact model classes, weights/thresholds and metrics were frozen.

The **additional training corpus** consists of 3,021 usable German-translated original AES archive sentences from 1,130 source-text IDs (owners Stephan Seidlmayer, Stefan Grunert and Ingelore Hafemann), added to the previously isolated 904 W9 training sentences. The full upstream archive Git blob is `014cccf04235d9e093fca24ed48c62630d235852`. The new derived training Git blob is `1354bbfd832680953bec25fb5742502599763bc1`. Exclusions are source-group-wide: all 32 earlier W10 archive test IDs, every Tübingen test source, all source IDs in earlier AES corpora and the new biographies target. One eligible translated original archive sentence with malformed tokens is explicitly excluded; 12 original archive rows lack publisher German translation. Training population is exactly **3,925** sentences (904 + 3,021), not an inferred figure.

The **new test** is AES published historical-biography corpus `_aes_bbawhistbiospzt.json`: exact upstream Git blob `6f26021ee4243e87657ff8afd59847f126d6ca65`, **6,279,800 original bytes**, 1,110 publisher sentences from 141 text IDs, of which the 32 predeclared SHA-256-sorted source-ID groups supply **180 whole-group sentences**, including **178 publisher German references** and 2 missing references. Derived Git blob is `7e5654b5d8194c3deb764cf37a8e2bce2c624855`. Source text-ID overlap against training, original W9 corpora, exposed Tübingen and W10 archive is **0**; independently verified distinct physical works, scribes or editorial lineages is unknown.

**Identical, frozen methods** (no parameter/search modification on revealed W10 archive): W9 904-sentence glossary and original W10 composer; expanded 3,925-sentence glossary and identical W10 composer; expanded whole-sentence retrieval at the previously selected W9 threshold 0.0 for copying-risk diagnosis only. Existing W10 compositional code is unchanged: contextual glosses need two independent train source IDs, local German unit reversal needs two independent train source IDs and >2x reverse versus original order; unknown tokens abstain, no invented agent-patient structure or unverified English→German conversion.

Executable evaluator and protections: `ling/translation/w11_evaluation.py`; publisher snippets `ling/translation/data/w11_archive_training_excluding_w10.json` and `ling/translation/data/w11_biography_external_32groups_ccby_sa.json`; per-sentence original editor attribution and source rights `ling/translation/data/w11_biography_rights_manifest.json`. Publisher source text and derived datasets retain CC BY-SA 4.0; physical-image source and trained-model release rights are separate. The corpus is **experimental editor-text evidence**, not admitted as DATA-008 train/test pixels or blind manuscript gold.

Reproduce on current main after review:

    python -m ling.translation.w11_evaluation verify
    python -m ling.translation.w11_evaluation evaluate
    python -m unittest tests.linguistics.test_translation_layer -v

Scoring reports all original groups and 178 scoreable publisher German references, including the 2 unscored missing-reference rows in the source census; German word multiset F1 and in-house character n-gram F2 are **not** expert semantic adequacy or original Hieratic OCR scores. This new biographies test becomes exposed after first execution and may not be used in future tuning. LING-003 milestone remains active, 0/2 points until scientifically independent fluency/semantic and manuscript-linked gold validation.


## W12/W12B — first publisher-annotated original Egyptian POS/morphology evaluation

W12 original temple-source preregistration (commit `b872644a040c6cc9784573695c5c58f5eded9356`) exposed an **insufficient corpus of 11 source text IDs** against the frozen requirement of 24; recorded as **BLOCKED** without quietly lowering the threshold or moving temple labels into training. W12B separate Amarna plan was preregistered (commit `d9e7bcb6b51742f527ae60830143b31cc67d6cde`) BEFORE opening original Amarna content. Published AES CC BY-SA 4.0 source at revision `35276d2527cca1a055e31ed5f6683e777717170f` has original Git blob `5e512681dc0d1ac7177a62531582b3473a0a11f2`; original 2,634 sentences, 399 text IDs. Fixed salted SHA-256 original-ID selection yielded **24 new complete source groups, 163 sentences, 1,691 Egyptian editor-transliterated word forms**, 1,649 with original published POS labels.

The new `ling/translation/grammar_evidence.py` trains on 3,925 source-constrained original AES sentences (1,526 original text IDs) over the accepted developer subcorpora + W11 archive donor only. W9 Tübingen, W10 archive, W11 biographies and W12 temple **remain excluded**, as does every selected Amarna text ID. It builds exact-form, one-original-document-one-vote part-of-speech candidates, context-based POS choice ONLY when at least two independent training source texts support the same Egyptian neighboring-form context, and source-attested morphological candidates for genus/numerus/status/inflection/voice/verbalClass. Unknown forms abstain. It reports POS ambiguity and observed adjacent POS-pair source support, **not Egyptian syntactic dependencies or source-to-German grammatical reconstruction**.

Original target `written_form` inputs and publisher POS/morphology reference annotations are separate Git-pinned files; `ling/translation/w12b_evaluation.py` freezes all predictions before loading targets, validates the entire 399-ID original universe, enforces 24 exact selected groups, per-item publisher editor/license/test-only rights and disjoint train IDs. New outcome: **773/1649 (46.876895%)** POS baseline full-denominator micro accuracy versus **780/1649 (47.301395%)** from context; unchanged coverage **954/1649 (57.853244%)**, context-on-covered precision **780/954 (81.761006%)**, candidate-set POS recall **905/1649**. Published morphology recall is modest and explicitly conditional; no historical grammatical role or sentence-meaning adjudication follows. Full data and first-use report SHA `a339e434a29f735330151d31115d3d91828aa836b47b00e1f8b185907272f3a6`, and protected methodology documented at `ling/translation/experiments/W12B_AMARNA_GRAMMAR_RESULT.md`. W12B Amarna is now exposed after the first test. New revisions need different untouched references.

Reproduce with `python -m ling.translation.w12b_evaluation verify`, `python -m ling.translation.w12b_evaluation evaluate`, and `python -m unittest tests.linguistics.test_translation_layer -v`. No original Hieratic pixels, expert-reviewed dependency gold, German semantic adequacy, specialist model training or capability points were demonstrated. LING-003 remains **active 0/2**, canonical **34.5/100**.


## W13 — actual Old Egyptian syntactic dependency supervision (separate from AES translation)

**Licensed original primary source:** Universal Dependencies **UD_Egyptian-PC** from University of Jaén / original Pyramid Texts editors. Official repository `LICENSE.txt` grants **CC BY-SA 4.0**. Frozen source tree `fca8538287cb69fd07b811eb55dcfd25584f3006`, source train CoNLL-U Git blob `ea262ee047943b81c0e0db8ff139ec7deb9b7b53`, dev blob `78a9749f823441633836b63a952df05d8636624c`, test kept unopened. Historical Pyramid Texts script and Tübingen transliteration do not prove later Hieratic manuscript transfer.

**Scientific design:** Preregistered train-only dependent-UPOS/head-UPOS/left-right/DEPREL frequency language-rule model, greedy deterministic head selection with exact one-root/cycle repair. Each DEV input includes true published **gold UPOS**, so this is intentionally an oracle-POS conditional dependency parser, not predictions from raw text or original images. Dev gold HEAD/DEPREL never enters prediction. Frozen comparator is previous-token head and train-majority dependent-UPOS relation. Source train 1,619 sentences/19,486 tokens, dev 230 sentences/3,167 tokens, independent sentence IDs.

**Verified first DEV result:** baseline **UAS 0.43890117, LAS 0.17492895**; dependency model **UAS 0.58383328, LAS 0.36090938**. Zero predicted cycles/multiple roots. Diagnostics are whole-source DEV metrics (not cherry-picked) with deterministic report hash `da5710ab3ea140f34d68fba5457ad4cf56d1d0a7e4cf2a0ec7a050086e736f70`. Preregistration, complete score, rights/uncertainty boundaries and reproducibility in `ling/translation/experiments/W13_EGYPTIAN_PC_DEPENDENCY_RESULTS.md`. Hosted 34 governance / 182 data / 90 linguistic / 299 evaluation tests passed at exact PR #110 head.

**Scientific gate:** This is real, source-verified **Old Egyptian syntactic dependency learning**; not German fluency or cross-period Hieratic accuracy. No independent semantic-role expert adjudication, manuscript pixel-to-line validation or blind new witness. Retain LING-003 at 0/2 and the canonical score at 34.5/100 pending broader acceptance.


---

# W14 — Real Egyptian-PC TRAIN-only oracle-free grammatical inference

**Preregistration (committed before W14 original train-group scoring):** [W14_PREREG_ORACLE_FREE_TRAIN_GROUP.md](experiments/W14_PREREG_ORACLE_FREE_TRAIN_GROUP.md). Registration was made after W13 published global TRAIN statistics, so this is a **retrospective internal diagnostic, not independent blind evaluation**. The publisher TRAIN file was accessed initially for source/group census and small incidental technical previews; new group scoring began afterward. The official UD Egyptian-PC TEST was neither read nor scored. The previously exposed official W13 DEV labels were never used for W14 training/evaluation/tuning.

**Original source:** UniversalDependencies/UD_Egyptian-PC (University of Jaén, Roberto A. Díaz Hernández and collaborators), Old Egyptian Pyramid Texts; publisher source tree `fca8538287cb69fd07b811eb55dcfd25584f3006`; original TRAIN Git blob `ea262ee047943b81c0e0db8ff139ec7deb9b7b53`, 2,563,828 bytes; dataset and annotations CC BY-SA 4.0 and derivatives remain attributed and share-alike. The original train has 1,619 publisher sentences, 19,486 UD word tokens. No image rights can be inferred from these annotated textual files. Source: https://github.com/UniversalDependencies/UD_Egyptian-PC .

**Reproducible published source-derived data:** `ling/translation/data/w14_egyptian_pc_train_only_ccby_sa.json`, Git blob `2b42a078e6ec4277a5ab7016d6f966c3545a7894`. Contains publisher original TRAIN FORM/UPOS/HEAD/DEPREL, source ID and king-group metadata. It is a licensed re-expression of previously public TRAIN material, **not DATA-008 gold or a newly admitted image corpus**. The loader strictly checks the original source lineage, derived Git blob, licence, population, group composition, dependency trees and absence of official test material.

## Frozen group split and algorithm

- Train: **Teti + Neith + Merenre**, 790 original sentences / 9,157 tokens.
- Internal retrospective heldout: **Pepi**, 829 original sentences / 10,329 tokens. Groups use publisher `# king` metadata, **not verified physically independent papyrus witnesses or scribes**. Shared literary formulae and editorial genealogy may contaminate inferred generalization. Report exact form-sequence overlaps.
- Train-only form-POS majority lookup; unknown forms use frozen 3-character suffix (3+ observations), else 2-character (5+), else 1-character (8+), else train-global majority. Deterministic lexical ties.
- Non-oracle POS is supplied to the *unchanged W13* UPOS/head-direction/DEPREL frequency scorer, trained again **only on allowed groups**, fixed distance penalty 0.02 and valid single-root/cycle-free tree repair. It consumes FORM strings only during inference. No publisher gold heldout UPOS, HEAD, DEPREL, lemma, FEATS or translation enters the nonoracle inference API.
- Two comparators: frozen **train global-majority POS + previous-token dependency** and separately marked **oracle gold-POS syntax** (upper-bound diagnostic, not the nonoracle result).
- Predictions are generated before comparison with original heldout HEAD/DEPREL; full 10,329-token denominators, POS accuracy and macro F1, UAS, LAS, oracle gaps, per-tag/relation errors, form coverage and non-silent negative outputs are recorded.

## Commands

```bash
python -m ling.translation.w14_oracle_free verify
python -m ling.translation.w14_oracle_free evaluate
python -m ling.translation.w14_oracle_free predict --form m --form n
python -m unittest tests.linguistics.test_translation_layer -v
```

Focused W14 tests have been added to the existing LING-003 test module: original source identity, role/source group counts, byte mutation, graph mutation, heldout contamination, forbidden gold inference, frozen predictions under target-label mutation, every heldout dependency tree, complete scored denominators, report determinism and CLI fail-closed behavior.

## Strict interpretation and blocked next scientific steps

This is **Old Egyptian grammar applied to authentic scholarly token forms**, not Hieratic image reading, not handwritten transliteration, not cross-period transfer and not German translation. W13's previously published complete-TRAIN frequency statistics invalidate any claim that the new train-only partition is a completely unseen independent test. The method is deterministic frequency lookup, **not a trained neural model**. If it improves on a weak comparator, that does not establish general grammatical or semantic competence.

The separate source-external **semantic adequacy evaluation is blocked**: this wave did not identify and preregister a new, independently licensed Egyptian↔modern-language expert reference set outside the already exposed W9–W12 AES cohorts; the existing W13 treebank is grammatical annotations, not full German parallel translation; zero authenticated image/text/semantic-gold alignments exist. No semantic score or human adjudication is inferred.

Do not upgrade LING-003 from active 0/2, verified capability 34.5/100, trained-model count zero or validated real Hieratic manuscript experiment count zero until original scientific acceptance gates are separately satisfied. Scientific report must distinguish a source-validated internal retrospective grammatical experiment from any independent unseen evaluation.


---

## W15 — Later-period TLA text transfer source and strict evaluation firewall

Source and rights: [TLA Academies' original 2025 raw-data publication](https://aaew.bbaw.de/daten-veroeffentlichungen), published [TLA Late Egyptian v19 premium 3,606 sentences](https://huggingface.co/datasets/thesaurus-linguae-aegyptiae/tla-late_egyptian-v19-premium), CC BY-SA 4.0. This separately licensed publisher release is NOT a blanket grant over live TLA website or manuscript images.

A new preregistered source-external **corpus-transfer** code path in \`ling/translation/w15_tla_transfer.py\` uses only authentic previously-pinned W11 AES TRAIN donor form/cotext German glosses. Target input is Late Egyptian \`transliteration\` alone; generation cannot see TLA translation, glossary, POS or reference annotations. Full targets, once original bytes are accessible and cryptographically verified, will be scored against actual German publisher translations on all reported rows, explicitly as lexical German word-overlap diagnostics rather than semantic adequacy.

**Present status:** target exact raw publisher file has not been acquired as trustworthy bytes in the current execution environment; real new-cohort scoring remains **BLOCKED** and no numeric performance claim is made. The reproducibility contract and synthetic/adversarial tests may be run without target data. Main note: the TLA dataset card contains eight fields but **no document/witness ID**, and the same editorial ecosystem may underlie historic AES; therefore no independent source/witness split can be asserted on this target, even after file acquisition. Original UD Egyptian-PC TEST is still unopened. No new project capability awarded.

Method, acquired-source blockers, rights, and complete preregistration: \`ling/translation/experiments/W15_TLA_LATE_EGYPTIAN_TRANSFER_READINESS.md\` and \`W15_PREREG_TLA_LATE_EGYPTIAN_TRANSFER.md\`.


## W28 authentic first-use AES BBAW letters result (2026-10-10; negative)

A NEW exact original publisher BBAW letters family `_aes_bbawbriefe.json` was frozen at pre-source-inspection Git commit `46c2efb818aaac0834ad6c853bbc4c18ff6c8fd1`. Original publisher Git blob `2c8db01616a37c75a3566e3b64d94a75fdf194c2` and actual source SHA256 `97929b4fb89f8336bbd5c87f98b1ae781e406d1b27b38475d0375760d91a75b0` were independently verified in hosted original-source run [38085816438](https://github.com/m7mdehab/hieratic-ai/actions/runs/38085816438). The SHA-seeded **32 distinct source-text groups** yielded **285** original publisher sentences, **284** German editorial references, **3,835** Egyptian tokens; predictions were locked before reference file exposure, reference labels were not passed to predictor. Gloss-only German word micro-F1 `0.06578947`; W10 constrained composition `0.06616012`; W28 train-voted 3-token grammar extension **`0.06616012`**, **zero** source-supported reorderings; W28-W10 improvement **0**, text-group bootstrap interval [0,0]. **1,660** original words abstained. Full raw input/target/output bytes were ephemeral, not committed or uploaded; cryptographic receipts and full denominator in [W28 result](../../ling/translation/experiments/W28_ORIGINAL_AES_LETTERS_HOSTED_RESULT.md). Newly tested BBAW letters references are now exposed and **must not** be used as virgin gold again. No physical manuscript witness independence, fluent semantic expert quality, actual hieratic image, or accepted LING-003 reading. **Status active, 0/2; weighted progress unchanged 34.5/100, research-space coverage 18.**
