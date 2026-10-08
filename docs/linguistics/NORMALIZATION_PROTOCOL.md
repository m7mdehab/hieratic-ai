# LING-001 transliteration and normalization protocol

LING-001 adds a deterministic text layer after visual/annotation recognition. It does not recognize signs, choose a reading, infer Egyptian lexical equivalences, translate, tokenize, or change expert linguistic analysis. Every normalized value points to the exact DATA-004 line/token and reading value that supplied it. DATA-004 alternatives stay separate even if two strings normalize to the same output.

## Representational layers

1. **Diplomatic transliteration** is the DATA-004 source value, including editorial punctuation, brackets, uncertainty and restoration marks exactly as recorded.
2. **Normalized representation** is a profile-specific, reproducible text transform. Its manifest records the profile/version, input/output hashes and non-reversible operations.
3. **Linguistic analysis** is the DATA-004 lemma, morphology and syntax annotation. LING-001 carries these fields as unmodified source-linked content; it does not derive or normalize them.

For a source layer with multiple acceptable readings, the request must enumerate every DATA-004 `value_id` in the layer's canonical order. A missing layer remains `missing_annotation` with an empty value list. Ambiguity, selected value, confidence, explanation and evidence references remain attached to their source candidates.

## Versioned profiles

Profiles are declared in `ling/normalization/profiles.yaml`. Profile IDs, versions, algorithm order, evaluation-profile references and reversibility notes are part of the output identity.

| Profile | Rules | Evidence/status |
|---|---|---|
| `identity/1.0.0` | Preserve exact code points and whitespace. | Supported identity operation; no linguistic claim. |
| `unicode-nfc/1.0.0` | Unicode NFC only. | Supported Unicode canonical normalization; the source is preserved because NFC may merge code-point sequences. |
| `translit_diplomatic_v1/1.0.0` | NFC, CR/LF normalization, trim terminal whitespace; preserve editorial marks and internal spacing. | Implements the accepted EVAL-001 diplomatic profile in [NORMALIZATION_PROFILES.md](../evaluation/NORMALIZATION_PROFILES.md#translit_diplomatic_v1). |
| `translit_compare_v1/1.0.0` | NFC, LF line endings, trim outer whitespace; collapse only spaces explicitly declared formatting-only or token separators. | Conservative executable subset of the accepted EVAL-001 comparison profile in [NORMALIZATION_PROFILES.md](../evaluation/NORMALIZATION_PROFILES.md#translit_compare_v1). |

The compare profile never case-folds, rewrites punctuation/editorial marks, changes signs, applies lexical rules, or tokenizes. If whitespace is significant or unknown, internal whitespace is retained. If line-break meaning is unknown, line boundaries are retained as LF. Normalization collisions are reported and both readings remain in the output.

No Egyptian lexical normalization rule is currently declared. Linguistically substantive normalization is therefore an explicit source value or analysis linked from DATA-004, not an inferred transform. Any future rule requires a new profile version, explicit scholarly source/evidence, reversible-or-lossy behavior, and regression tests.

## Commands

```text
python -m tools.linguistic_normalization validate ling/normalization/examples/synthetic.yaml --annotation data/examples/annotation_ambiguous.yaml
python -m tools.linguistic_normalization normalize ling/normalization/examples/synthetic.yaml --annotation data/examples/annotation_ambiguous.yaml --output out/synthetic-normalization.json
```

Validation checks the DATA-004 annotation schema and semantic invariants, exact annotation-byte SHA-256, line/token/value links, complete alternative sets, supported profile/version and declared whitespace/line-break semantics. The output includes a stable `ling-<sha256>` ID, original and normalized values/hashes, per-value reversibility, exact linguistic-analysis pass-through, profile provenance, and any retained collisions. Output writes use same-directory temporary files and an atomic hard-link create operation that refuses an existing or concurrently created destination (no silent overwrite).

## Limitations

The included request points to a fabricated synthetic ambiguous annotation only. Its readings do not represent Egyptian words, orthographic equivalences, transliteration conventions beyond formatting fixtures, or expert decisions. The supported normalization rules are technical conventions inherited from Unicode and EVAL-001, not a claim that differently written Egyptian readings are linguistically equivalent. Canonical tokenizer and lexical-analysis rules remain outside this task.
