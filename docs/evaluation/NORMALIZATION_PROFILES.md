# Evaluation Normalization Profiles v1.0

**Task:** EVAL-001  
**Status:** Proposed  
**Date:** 2026-10-08

## Purpose

Edit-distance and exact-match metrics are only meaningful when representational normalization is fixed in advance.

These profiles normalize **encoding and formatting**, not substantive readings. A model does not receive credit because the evaluator silently repairs a wrong sign, wrong transliteration, or wrong linguistic analysis.

Every reported sequence metric must name the profile used.

---

## raw_identity

### Intended use

- class labels;
- IDs;
- structured fields;
- scores where no string normalization is appropriate.

### Transformation

None beyond parser-level type handling.

---

## grapheme_v1

### Intended use

- Hieratic grapheme/sign token sequences;
- GER;
- exact grapheme sequence accuracy.

### Input assumption

The sequence is already tokenized into project grapheme IDs or an equivalent canonical symbolic inventory.

### Allowed normalization

- trim leading/trailing whitespace around serialized tokens;
- collapse formatting-only repeated whitespace;
- normalize separator representation used only by serialization;
- preserve token identity exactly.

### Forbidden normalization

- mapping one grapheme ID to another because they share a phonetic value;
- replacing a predicted allograph with the gold grapheme unless the annotation schema explicitly declares the allographs equivalent at this metric layer;
- splitting or merging ligatures differently from the declared annotation/scoring policy;
- using downstream linguistic context to rewrite the prediction.

### Ambiguity

If the gold annotation permits multiple grapheme identities, the scorer compares against the acceptable set/reference lattice. The normalizer itself does not choose the most favorable reading.

---

## hieroglyphic_v1

### Intended use

- standardized hieroglyphic rendering;
- HGR-SER;
- exact standardized sign-sequence accuracy.

### Allowed normalization

- Unicode normalization where applicable;
- canonical whitespace;
- canonical serialization of sign separators/group markers that have no semantic distinction in the evaluation representation;
- explicitly versioned aliases between technically equivalent sign-code spellings.

### Required preservation

- sign identity;
- ordering;
- grouping distinctions that the gold schema treats as meaningful;
- damaged/uncertain markers if they are part of the scoring representation.

### Forbidden normalization

- replacing a substantively wrong sign with a sign of similar reading;
- correcting sign order;
- inferring omitted signs from translation;
- collapsing distinct Gardiner/sign IDs solely because their linguistic values overlap.

---

## translit_diplomatic_v1

### Intended use

- preservation/display of the model's diplomatic Egyptological transliteration output;
- audit logs;
- human review.

### Allowed normalization

- Unicode NFC;
- normalize line endings;
- trim terminal whitespace;
- preserve editorial punctuation and uncertainty markers.

### Note

This profile is intended for faithful retention, not forgiving comparison.

---

## translit_compare_v1

### Intended use

- transliteration CER;
- exact normalized transliteration accuracy;
- sequence comparison.

### Allowed normalization

1. Unicode NFC.
2. Normalize equivalent whitespace:
   - trim leading/trailing whitespace;
   - collapse repeated internal spaces only where spaces are token separators in the declared target convention.
3. Normalize technically equivalent code-point sequences that render the **same Egyptological symbol**.
4. Normalize a small, documented set of serialization-only punctuation variants if the annotation policy declares them non-semantic.
5. Normalize line-break formatting where line breaks are not themselves part of the target sequence.

### Required preservation

The following may not be collapsed unless a future versioned scholarly decision explicitly declares an equivalence:

- distinct Egyptological consonantal/transliteration symbols;
- omitted vs present signs;
- morphemes/tokens;
- uncertainty vs certainty;
- restored vs actually visible content when the annotation schema distinguishes them;
- sign/order distinctions.

### Editorial marks

Editorial marks must be assigned one of three statuses in the dataset/schema:

- `scored`;
- `ignored_formatting`;
- `gold_metadata_only`.

The metric does not decide this ad hoc.

### Case

Case-folding is **off by default**. If a target convention later proves case-insensitive, that requires a new profile version.

---

## tokenized_egyptian_v1

### Intended use

- transliteration token error rate;
- normalized linguistic token accuracy/error;
- lemma/morphology alignment.

### Dependency

The tokenization convention must come from the canonical annotation/data schema.

### Allowed normalization

Apply `translit_compare_v1`, then use only the versioned project tokenizer.

### Forbidden behavior

- splitting tokens differently per model;
- hand-editing tokenization after seeing predictions;
- using translation references to choose boundaries;
- silently discarding clitics/morphemes that are represented in gold.

### Missing canonical tokenizer

Until DATA-004/DATA-006 freeze the actual tokenizer, metrics requiring this profile are specified but may be **not yet measurable**.

That is acceptable; the metric contract is ahead of some data contracts by design.

---

## translation_reference_v1

### Intended use

- chrF and other target-language reference metrics;
- human/semantic evaluation packet preparation.

### Allowed normalization

- Unicode NFC;
- normalize line endings;
- trim leading/trailing whitespace;
- collapse formatting-only repeated whitespace.

### Punctuation/case

By default:
- preserve punctuation;
- preserve case.

If a specific automated metric performs its own documented tokenization/case handling, that configuration must be logged with the metric.

### Forbidden normalization

- paraphrasing either prediction or reference before scoring;
- automatically replacing names/numbers;
- fixing grammar;
- using an LLM to rewrite predictions into a closer reference before evaluation.

---

# Gold uncertainty and masks

Normalization profiles do not decide whether a gold span is scorable.

Gold status is handled separately:

- `certain`: scored normally;
- `uncertain_with_alternatives`: score against declared alternatives/lattice;
- `illegible_unscorable`: excluded from content denominator and counted in coverage metadata;
- `missing_annotation`: not measured;
- `adjudication_pending`: excluded from final claims until resolved.

A prediction of `unknown` against a legible gold item is treated as abstention, not as a normalization match.

---

# Versioning policy

A normalization profile changes only through a versioned edit.

If a change can alter previously reported scores:
- issue a new profile ID/version;
- preserve the old implementation;
- state which experiments were rescored;
- do not overwrite historical numbers silently.

A sealed-test error is never sufficient reason by itself to alter a profile.
