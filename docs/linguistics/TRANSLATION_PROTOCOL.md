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
