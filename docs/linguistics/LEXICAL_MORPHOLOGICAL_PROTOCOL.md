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


## W8 — Authentic, source-licensed lexical and morphological interpretation

The LING-002 pipeline now includes an **actual Egyptological scholarly text corpus**, rather than only fictional fixtures. The sources are openly available under **CC BY-SA 4.0** from Simon D. Schweitzer's Ancient Egyptian Dictionary / TLA-AED conversions and original Egyptological research editors.

### Source evidence and scale

- AED-TEI, https://github.com/simondschweitzer/aed-tei : **35,052** real Egyptian lexicon entries with written form, grammatical class, root cross-reference where available and published English gloss. Publisher dictionary.xml pinned revision 462c722e0323e05641aea2eee8cdf1e27303d939, upstream Git blob 078f2f7b83bd642b6530ed000dbc68f9aa79c06e.
- AES, https://github.com/simondschweitzer/aes : Felsinschriften subcorpus has **445** genuine editor-annotated sentences from **311 source text IDs**, with **2,526** tokens and **2,305** published lemma IDs; selected raw _aes_bbawfelsinschriften.json pinned revision 35276d2527cca1a055e31ed5f6683e777717170f, upstream Git blob 7bfcba9678b64c3526a1123996a0714b5f76812f.
- Source licence evidence: each public GitHub project README expressly says **All files: CC BY-SA 4.0**. The actual Academy TLA independently publishes separately licensed raw datasets at https://aaew.bbaw.de/daten-veroeffentlichungen ; this work does **not** bulk scrape its restrictive live TLA website.
- Scholarly attribution: TLA/AED 2018 scholarly contributors and Simon D. Schweitzer (TEI and AES conversions). Preserve CC BY-SA 4.0, edition author references and conversion history on any derivatives. The two source records SRC-AED-TEI and SRC-AES-OPEN have separate approved **text-layer** provenance and do not authorize any historic manuscript pixels.
- Eight source-derived lexicon JSONL partitions and verbatim AES JSON are checked into the task-scoped data folder with exact Git blob identity pins. See scholarly_source_manifest.json for complete immutable source revisions and derivation metadata.

### Execute the actual scholarly analysis

~~~bash
python -m tools.lexical_interpretation scholarly-aes verify
python -m tools.lexical_interpretation scholarly-aes lookup --form ꜣ
python -m tools.lexical_interpretation scholarly-aes evaluate
~~~

The new offline evaluator accepts real Egyptian token spellings and returns **all matching published lemmas**, source orthography, original AED POS class, possible root references and independently source-observed morphological alternatives. Exact matching preserves competing forms rather than manufacturing a single answer. An unattested form means the lexicon has no exact candidate, not that it is not Egyptian. Morphological bundles are drawn only from actual *other-text* AES editor annotations; the engine does **not** infer tense, gender, number, verbal status or grammatical role merely from a dictionary gloss.

### Source-held-out evaluation

For each original AES text ID, the evaluator **removes all that text's editorial token records from candidate generation** before predicting its forms. It scores against the excluded text's genuine published lemma IDs, POS tags and morphology bundles. Both absent-gold source texts and missing source token IDs remain explicitly recorded. It reports:

- genuine source and group denominators, eligible forms, candidate recall and unique-lemma cases;
- morphological source-bundle candidate recall where a published form+lemma appears in other texts;
- all competing scholarly alternatives, token-source provenance and examples of failure;
- immutable summary digest and real-source SHA/partitions.

**Scientific interpretation:** This is a development-grade **published scholarly text/lexical** diagnostic, not Hieratic image OCR. AED and AES share historical editorial source material; different source text IDs do not prove distinct manuscript supports/scribes. This is not a certified sealed unseen test, independent two-reader review, calibrated accuracy, or an image-conditioned model result. The expert publication is genuine source-attested lexical evidence but not newly commissioned blind gold. Never promote to DATA-008 corpus, claim VLM-001 visual certification or infer generalization from 311 text IDs.

### Engineering integrity

Source-file Git object SHA-1 is checked from the actual raw bytes, not simply echoed from input. Publisher census and source-license manifest are also validated. Source rights cannot be self-authorized by edited JSON. No third-party media acquisition, provider inference, paid calls, benchmark source unblinding or secret exchange occurs.

Reproduce with:

~~~bash
python -m unittest tests.linguistics.test_lexical_interpretation -v
python -m tools.lexical_interpretation scholarly-aes evaluate
~~~

The existing strict LING-001 normalization input API and historical synthetic contract remain intact. Substantive scientific acceptance, capability accounting and any later LING-003 dependency transition require independent overseer review of the exact hosted test evidence.
