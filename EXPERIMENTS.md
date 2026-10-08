# Experiment Registry

No validated model experiments have been run yet.

## Rules

Every experiment receives a stable ID, e.g. `EXP-HTR-001`.

Minimum record:
- hypothesis;
- linked task;
- Git commit;
- dataset/manifests and split version;
- model/checkpoint;
- configuration and seed(s);
- execution environment;
- command/entry point;
- metrics;
- artifacts;
- result;
- interpretation;
- decision caused by the result;
- known caveats.

A failed experiment remains in the registry. Negative results may increase research coverage but do not automatically earn capability points.

## Template

```yaml
id: EXP-...
task_id: ...
status: planned
hypothesis: ...
code_commit: ...
data_version: ...
split_version: ...
model: ...
config: ...
seeds: []
metrics: {}
artifacts: []
result: ...
decision: ...
caveats: []
```


## EXP-LING-002-AED-AES-001 — Genuine published-text lexical/morphology diagnostic

- **Task:** LING-002 (accepted source-grounded linguistic interpretation; not an image OCR or model-experiment certification)
- **Classification:** completed_development_grade_scholarly_text_diagnostic; **not independently validated real model experiment**
- **Execution:** PR #88 exact-head GitHub Linux CI 37856429995; verified source registry PR #85
- **Hypothesis:** exact original Egyptian written-form lookup into scholarly AED dictionary and independent-other-text AES editorial annotations can recover useful lemma identities, grammatical alternatives and attested inflection bundles, without fabricating unseen-text gold.
- **Inputs:** AED-TEI 35,052 publisher lexemes, Git dictionary.xml original blob 078f2f7b83bd642b6530ed000dbc68f9aa79c06e; AES Felsinschriften 445 sentences, 311 text groups and 2,526 original editor tokens, source Git blob 7bfcba9678b64c3526a1123996a0714b5f76812f. See immutable source manifests and CC BY-SA 4.0 contributor attribution at ling/lexical/data/scholarly_source_manifest.json.
- **Splitter:** exhaustive leave-one-AES-source-text-ID-out. Every queried text ID excluded from AES candidate generation. Common AED published dictionary remains visible. Two text IDs had no scoreable lemma.
- **Prediction method:** deterministic exact form candidate union over AED's dictionary orthography and other-text AES form attestations; no trained weights, statistical model or hidden parameter tuning, seed not applicable. Source-native morphology is only transferred when another text attests the same form and lemma; alternatives preserved.
- **Measured real diagnostic:** of 2,305 tokens with published lemma labels, 1,709 (74.14%) have any lookup candidate and 1,621 (70.33%) have the editorial lemma among candidates. Exactly 1,102 produce a single candidate, with 1,062 matching the published lemma (96.37% among the single-candidate subset only). Of 753 tokens with publisher morphology bundles, 449 (59.63%) match some permitted cross-text candidate bundle. These are *candidate recall* and conditional source-lookup accuracy, not blind OCR accuracy.
- **Immutable report SHA-256:** 26ad977c29fdd8659157cb02bec04323b6b544dc8ca9425a13825ea629acedee. Script: python -m tools.lexical_interpretation scholarly-aes evaluate.
- **CI:** complete governance, data, linguistic and evaluation suites passed, LING-002 15-path scope check passed on exact source head.
- **Decision:** Accept LING-002 2.0-point *linguistic analysis capability only*; unblock the downstream LING-003 translation-engine task. Mark no genuine image-reading, no held-out independent manuscript or VLM result, no trained model, no independently validated model experiments. Input editor labels are genuine published scholarship, not newly blind reviewer-certified gold, and AED/AES publication overlap and unknown pretraining exposure remain substantive limitations.
