# Evaluation Scoring Examples v1.0

**Task:** EVAL-001  
**Status:** Proposed  
**Date:** 2026-10-08

## Purpose

These examples make edge-case behavior explicit before real model results exist.

The examples use simplified placeholder sign/transliteration symbols. They demonstrate scoring semantics, not Egyptological claims about any particular manuscript.

---

## Example 1 — Exact sign-sequence recognition

Gold grapheme sequence:

`[G1, G2, G3]`

Prediction:

`[G1, G2, G3]`

Result:

- GER = 0/3 = **0.000**
- exact sequence = **1**
- top-1 sign accuracy = **3/3**

---

## Example 2 — One substitution

Gold:

`[G1, G2, G3]`

Prediction:

`[G1, G7, G3]`

Minimum edit path:

- 1 substitution
- 0 deletions
- 0 insertions

Result:

- GER = 1/3 = **0.333**
- exact sequence = **0**

The evaluator does not consult translation meaning to decide that G7 was "close enough."

---

## Example 3 — Insertion and deletion

Gold:

`[G1, G2, G3, G4]`

Prediction:

`[G1, G2, GX, G4, G5]`

One optimal alignment may contain:
- 1 substitution or insertion/deletion combination depending on token alignment;
- edit distance is computed mechanically from the canonical token sequence.

The implementation must use the standard minimum edit distance and log S/D/I counts when available.

The scorer may not hand-pick a friendlier alignment after inspecting the system identity.

---

## Example 4 — Multiple acceptable sign identities

Gold acceptable set for one visual sign:

`{G12, G12_variant}`

Prediction top-1:

`G12_variant`

Result:

- SIGN-TOP1 = **correct**

Prediction:

`G99`

Result:

- SIGN-TOP1 = **incorrect**

The acceptable set must come from gold annotation/adjudication before sealed evaluation.

---

## Example 5 — Top-k is diagnostic, not ordinary accuracy

Gold:

`G12`

Model candidates:

1. G20
2. G12
3. G45

Result:

- SIGN-TOP1 = **0**
- SIGN-TOP3 = **1**

The public result must still expose top-1. The system cannot describe this item simply as "correct."

---

## Example 6 — Localized sequence ambiguity

Suppose the scholarly gold permits:

`G1 [G2 | G7] G3`

Prediction A:

`G1 G2 G3`

Prediction B:

`G1 G7 G3`

Both receive zero GER if the ambiguity lattice declares both alternatives acceptable.

Prediction C:

`G1 G8 G3`

receives one substitution.

The evaluator must not require the dataset to duplicate every complete sequence if ambiguity can be represented locally.

---

## Example 7 — Illegible gold span

Gold:

`G1 <ILLEGIBLE> G3`

The central span is adjudicated `illegible_unscorable`.

Prediction:

`G1 G9 G3`

The central position is not treated as a known wrong sign because no resolved gold exists.

Report:
- content score on scorable positions;
- gold unavailable-span count;
- model confidence/abstention behavior if recorded.

This does **not** mean the model is credited for G9.

---

## Example 8 — Model abstains on a legible item

Gold:

`G14` — status `certain`

Prediction:

`ABSTAIN`

Result:

- ordinary sign accuracy: not correct;
- answered coverage decreases;
- selective-risk evaluation treats it as rejected rather than a wrong asserted class.

If the model abstains on every item:
- selective accuracy among answered items may be undefined/high;
- coverage = 0;
- the risk-coverage report exposes the useless operating point.

---

## Example 9 — Alternative-set gaming

Gold:

`G4`

Model A prediction set:

`{G4, G7}`

Model B prediction set:

all 500 possible signs.

Both technically contain the gold.

Therefore report together:

- ALT-COVERAGE
- ALT-SIZE

Model B cannot claim strong uncertainty performance merely because its set always contains the answer.

---

## Example 10 — Transliteration Unicode normalization

Gold transliteration contains a precomposed Egyptological symbol.

Prediction uses the canonically equivalent combining-code-point sequence.

Under `translit_compare_v1`:
- Unicode NFC makes the representations identical;
- CER does not penalize an encoding-only difference.

If the prediction uses a **different Egyptological consonantal symbol**, it remains an error.

Normalization is representational, not linguistic correction.

---

## Example 11 — Formatting whitespace

Gold:

`TOKEN1 TOKEN2 TOKEN3`

Prediction serialization:

`TOKEN1   TOKEN2 TOKEN3`

If the active profile declares repeated spaces serialization-only:
- comparison normalizes the repeated whitespace;
- no error is counted.

If spaces are part of a token-boundary convention whose correctness is being evaluated, use the tokenized profile and preserve the relevant boundary behavior.

---

## Example 12 — Wrong reading but plausible translation

Image gold transliteration:

`A B C`

System recognized:

`X Y Z`

System translation:

"the king gave bread"

Suppose the reference translation is semantically close.

Result:

- transliteration CER/GER: poor;
- translation semantic score may be high;
- image-reading claim: **fails the visual-faithfulness chain**.

The translation score is not allowed to compensate for the recognition failure.

A research report must show both.

---

## Example 13 — Correct source reading, paraphrastic translation

Gold source reading is recovered correctly.

Reference translation:

"The scribe entered the house."

Prediction:

"The writer went into the building."

Automated n-gram overlap may be imperfect, while human semantic adequacy may be high.

This is why translation evaluation uses:
- reference metric(s) as secondary diagnostics;
- blind semantic adequacy/source-faithfulness review for serious claims.

---

## Example 14 — Hallucinated detail in fluent translation

Source supports:

"The scribe entered the house."

Prediction:

"The royal scribe entered the temple at dawn."

Fluency is high, but unsupported details were added.

Human/source-faithfulness rubric should penalize:
- "royal"
- "temple"
- "at dawn"

A target-only fluency metric cannot detect this reliably.

---

## Example 15 — Partial morphology

Gold annotation provides:
- lemma = L123
- POS = noun

but tense/number/gender are not annotated.

Prediction provides:
- lemma = L123
- POS = noun
- gender = masculine

Scoring:
- lemma and POS can be scored;
- gender is not treated as correct or incorrect from absent gold;
- report annotation coverage.

Missing gold is not negative evidence.

---

## Example 16 — Multiple valid morphological analyses

Gold acceptable bundles:

1. `{POS:noun, number:singular}`
2. `{POS:noun, number:unknown}`

Prediction:

`{POS:noun, number:singular}`

MORPH-BUNDLE-ACC = **1**

Prediction:

`{POS:verb, number:singular}`

MORPH-BUNDLE-ACC = **0**

---

## Example 17 — Document-macro vs micro

Document A:
- 900 graphemes
- GER = 2%

Document B:
- 100 graphemes
- GER = 40%

Global micro GER is dominated by Document A:

[
(18 + 40) / 1000 = 5.8\%
]

Document-macro GER:

[
(2\% + 40\%) / 2 = 21\%
]

Both are reported.

For a general-reading claim, document-macro more clearly exposes that the system performs badly on one document.

---

## Example 18 — Class imbalance

Class G_COMMON appears 10,000 times.
Ten rare classes appear 10 times each.

A system that predicts G_COMMON very well but fails every rare class may have high item-micro accuracy.

Required class-macro metrics prevent this from being presented as broad sign-reading capability.

---

## Example 19 — Cross-scribe generalization

Dev/in-domain:
- transliteration CER = 8%

Unseen-scribe test:
- CER = 24%

Report:
- unseen-scribe CER = 24%;
- absolute degradation = +16 percentage points;
- relative degradation = 200% increase in error.

Do not report only a pooled 10% corpus CER if the unseen-scribe subset is a central claim.

---

## Example 20 — Tiny subgroup

A period subgroup has only 4 documents.

The score may be shown descriptively with n=4.

Do not make a strong "the model generalizes to this period" inferential claim from that subgroup alone.

---

## Example 21 — Confidence calibration

For many predictions made at confidence 0.90, only 60% are correct.

Even if top-1 accuracy is respectable, the confidence is overconfident.

Calibration metrics such as Brier/NLL/ECE and reliability plots should reveal this.

A model used for expert assistance should not advertise 90% certainty when empirical correctness is much lower.

---

## Example 22 — Selective reading

System A answers 100% of items at 70% accuracy.

System B answers 60% at 92% accuracy and abstains on the rest.

Neither is universally "better" from accuracy alone.

Report:
- coverage;
- selective accuracy/risk;
- risk-coverage curve;
- task-specific operating point.

This lets an expert-assistance workflow choose the appropriate trade-off.

---

## Example 23 — Oracle top-k sequence

The correct transliteration is second in the beam.

Report:
- top-1 CER/exact score as the ordinary system result;
- oracle top-k score separately as a decoder-capacity diagnostic.

Do not replace the top-1 result with oracle beam accuracy.

---

## Example 24 — Gold available only for translation

An image has a published modern-language translation but no reliable image-aligned transliteration/sign reading.

The sample may contribute to a limited translation-reference analysis.

It **cannot** establish:
- GER;
- transliteration CER;
- sign accuracy;
- faithful image reading.

The report marks those layers `not_measured`.

---

## Example 25 — Benchmark adapter

HieraticBench has an official score for one task.

The project:
1. computes and reports the official benchmark score unchanged;
2. may also derive project-format diagnostics;
3. labels derived metrics separately;
4. does not rewrite benchmark gold or official scoring;
5. keeps benchmark data quarantined from training.

---

# Human rubric anchors

The final expert protocol will be refined later, but EVAL-001 fixes the direction.

## Source faithfulness / visual reading fidelity

**4 — Fully supported**
: Output accurately reflects the visible/readable source; no material unsupported assertions.

**3 — Mostly supported**
: Minor error/omission that does not materially change the reading.

**2 — Mixed**
: Important parts are supported, but one or more material reading errors exist.

**1 — Weak**
: A small amount of source content is recovered, but major portions are wrong/invented.

**0 — Unsupported**
: Output does not meaningfully correspond to the source or is effectively hallucinated.

## Uncertainty honesty

**4**
: All meaningful ambiguities/illegible regions are appropriately marked; confident assertions are well-supported.

**3**
: Mostly calibrated with minor over/understatement.

**2**
: Some useful uncertainty marking but important unsupported certainty or excessive abstention.

**1**
: Frequent false certainty or indiscriminate uncertainty.

**0**
: System presents fabricated/unsupported readings as certain or provides no meaningful usable uncertainty signal.

These anchors are provisional until GEN-004 expert-evaluation protocol is frozen, but they prevent evaluation design from assuming that uncertainty is merely a numeric afterthought.
