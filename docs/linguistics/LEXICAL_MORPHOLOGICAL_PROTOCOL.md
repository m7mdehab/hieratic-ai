# Lexical and morphological interpretation protocol

## Layers and evidence boundary

LING-002 runs after LING-001 and keeps four layers distinct:

1. **Source annotation:** exact DATA-004 diplomatic transliteration, line/token/value IDs, alternative readings, annotation hash and existing lemma/morphology fields.
2. **Normalization:** the LING-001 profile/version and exact normalized alternative strings, with hashes and the original text retained.
3. **Lexical interpretation:** exact-form candidate lookup against a versioned lexicon, with lemma/root and attested or candidate part of speech.
4. **Morphological interpretation:** explicitly supplied feature bundles and inflection analyses attached to candidate entries. The engine does not infer a paradigm or repair unsupported features.

A new layer can add hypotheses but cannot overwrite or collapse its input. Unicode normalization collisions remain distinct source readings linked to the same normalized spelling. An exact lookup is not proof that two source readings are linguistically equivalent.

## Outcomes

- `interpreted`: exactly one normalized source reading has one candidate analysis and the source reading is marked certain.
- `ambiguous`: source alternatives remain, or multiple lexical/morphological candidates match. Every candidate remains in output; there is no implicit top choice.
- `unattested`: a usable source form has no exact lexicon entry. This means “not present in this lexicon,” not “not an Egyptian word.”
- `unknown`: input gold is missing, illegible, or pending adjudication, so lexical interpretation cannot be responsibly attempted.

No metric is computed. EVAL-001 identifiers `LEMMA_ACC`, `LEMMA_MACRO_F1`, `MORPH_BUNDLE_ACC`, and `MORPH_FEATURE_F1` require eligible expert gold, task-defined predictions, and their contract aggregation/alternative rules. A synthetic fixture is not an evaluation set.

## Lexicon admission

Each entry pins its Unicode form hash, version, lemma/root IDs, POS/features, inflection status, period, confidence and uncertainty. Scholarly attestations identify a source registry record, stable object, exact content hash, citation and locator, verified citation evidence, verifier and date. Use requires compatible verified source rights and an explicit intended purpose. Registry presence or a schema field is not itself rights clearance. Runtime does not scrape or fetch URLs; the independent source review must already have occurred.

Synthetic records use `scientific_status: illustrative_synthetic`, empty attestations and `SYNTHETIC` rights. They are accepted only with a synthetic source annotation and are never eligible for scoring or gold. Mixed synthetic and scholarly lexicon releases are rejected.

## Rules and limitations

Implemented rules are technical: exact string lookup after the declared LING-001 profile, deterministic candidate ordering, identity/hash checking and conservative outcome assignment. No Egyptian lexical, semantic, root, inflectional, or historical rule is asserted by the checked-in example. Future substantive rules require verified scholarly citations, explicit competing analyses, expert review and versioned regression evidence.

Unknown rights, invalid registry references, source-hash drift, unverified citations, incompatible rights, missing intended-use review and unsupported schema features fail closed. Candidate confidence is provenance metadata, not a calibrated probability. It is never used to rank away alternatives.

## CLI

```text
python -m tools.lexical_interpretation validate <normalization.json> --lexicon ling/lexical/examples/synthetic.yaml
python -m tools.lexical_interpretation interpret <normalization.json> --lexicon ling/lexical/examples/synthetic.yaml --output out/synthetic-interpretation.json
```

The example is a fabricated pipeline fixture. It is not an Egyptian lexicon or scholarly result.
