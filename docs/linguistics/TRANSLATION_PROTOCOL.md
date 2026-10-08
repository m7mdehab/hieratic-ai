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
