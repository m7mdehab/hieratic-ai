# EVAL-001 — Evaluation Metrics Across the Reading Stack

- **Task ID:** EVAL-001
- **Owner:** overseer
- **Depends on:** FND-003 — validated
- **Status at start:** ready
- **Primary write scope:** `docs/evaluation/`, `eval/` metric contracts/specifications, `RESEARCH.md` only if a research conclusion must be reconciled
- **Do not edit:** benchmark gold data, sealed test material, model results, task weights, or capability progress until acceptance

## Why this is overseer-owned

This task defines what the project will count as "reading Hieratic."

A weak metric design can reward fluent hallucination, benchmark leakage, memorized translations, or visually incorrect outputs. The evaluation contract must therefore separate visual recognition from linguistic interpretation while still supporting end-to-end systems.

## Objective

Produce the canonical evaluation specification for the full Hieratic-reading stack, including:

1. script/domain identification;
2. layout and reading-order recovery;
3. sign/grapheme localization and recognition;
4. line/sequence HTR;
5. standardized hieroglyphic rendering;
6. Egyptological transliteration;
7. normalization/tokenization;
8. lexical/morphological interpretation;
9. translation;
10. uncertainty/calibration;
11. generalization and robustness;
12. expert/blind evaluation.

The specification must define metrics, normalization rules, scoring units, ambiguity handling, aggregation, missing-data behavior, and anti-shortcut safeguards.

## Core principles

The metric system must enforce:

- no single aggregate score may hide catastrophic failure at an earlier layer;
- fluent translation is not credited as faithful reading if the visual/transliteration path is wrong;
- multiple defensible scholarly readings can receive credit;
- damaged/illegible text can remain uncertain rather than forcing a fabricated answer;
- sign-level and sequence-level performance are distinct;
- document-level macro averaging is preferred where micro averaging would let large documents dominate;
- confidence calibration is evaluated separately from raw accuracy;
- cross-document/scribe/period/media performance is reported explicitly;
- external benchmark metrics remain reproducible without becoming the project's sole success definition.

## Required metric families

### Script/domain identification

Define at least:
- accuracy;
- macro F1;
- confusion matrix;
- abstention-aware accuracy or selective risk when an "uncertain" option is supported.

### Layout / reading order

Define at least:
- region detection metric(s), e.g. IoU/mAP where appropriate;
- line/region order accuracy;
- sequence/order edit metric for pages with multiple lines/columns;
- rules for pages where full layout gold is unavailable.

### Sign/grapheme localization and recognition

Define:
- detection mAP/precision/recall when boxes/polygons exist;
- top-1 and top-k grapheme accuracy;
- macro accuracy across classes;
- retrieval metrics such as Recall@k / MRR for palaeographic exemplar retrieval;
- treatment of ligatures and multi-sign groups.

### Line/sequence recognition

Define:
- grapheme/sign error rate;
- character error rate for transliteration strings;
- word/token error rate where tokenization is defensible;
- exact sequence accuracy;
- sequence-level top-k if decoder alternatives are produced.

Specify normalization before edit-distance scoring.

### Hieroglyphic rendering / transliteration

Distinguish:
- sign-normalized hieroglyphic rendering;
- Egyptological transliteration.

Define canonicalization and equivalence rules so formatting conventions do not dominate scores.

### Linguistic interpretation

For lemma/morphology:
- exact/micro/macro metrics as appropriate;
- multi-label or structured scoring where multiple analyses are acceptable;
- partial credit only where linguistically justified.

### Translation

Do **not** rely on one n-gram metric.

Define a layered translation evaluation including:
- reference-based automated metrics where useful;
- semantic adequacy;
- faithfulness to recognized source;
- terminology/name handling;
- expert or rubric-based adjudication for serious claims.

Any LLM-as-judge use must be secondary, reproducible, model/version/prompt-logged, and never the sole scientific evidence.

### Uncertainty/calibration

Define at least:
- confidence calibration error or Brier/NLL where probabilistic outputs exist;
- coverage vs risk / selective accuracy for abstaining systems;
- accuracy of alternative-set inclusion;
- rules for "unknown/illegible" predictions.

### Generalization

Require separate reporting across available strata:
- unseen document;
- unseen scribe;
- period;
- material/support;
- genre/register;
- damage/degradation level.

Do not average away an entire failed stratum.

## Ambiguity and multiple valid readings

Specify a gold representation that can support:
- multiple acceptable sign identities;
- alternative transliterations;
- uncertain spans;
- partially unreadable text;
- equivalence classes;
- expert confidence/adjudication notes.

Metrics should score against a set/lattice of valid references where possible instead of arbitrarily choosing one string as truth.

## Aggregation rules

Define:
- primary unit of aggregation for each task;
- macro vs micro reporting;
- confidence intervals / bootstrap policy where sample sizes allow;
- per-document and per-source breakdowns;
- minimum sample thresholds before publishing subgroup claims;
- how excluded/invalid examples are logged.

Every exclusion must be auditable.

## Composite/public headline reporting

If a public composite score is used, it must:
- be secondary to layer-specific metrics;
- have fixed published weights;
- include hard floors/gates preventing a system with weak recognition from compensating via fluent translation;
- never replace the underlying metric table.

It is acceptable to conclude that no composite score should be used initially.

## Baseline and significance policy

Define:
- comparisons against untuned frontier VLM baselines;
- specialist baselines;
- confidence intervals or paired bootstrap/permutation testing where appropriate;
- minimum meaningful improvement policy;
- run/seed aggregation where stochastic training is involved.

Avoid p-value theater on tiny samples.

## Contamination and sealed-eval rules

The metric spec must interface with later EVAL-006 by defining:
- what counts as exposure/contamination metadata;
- when a result is invalidated;
- what can be tuned on dev;
- what cannot be inspected on sealed test;
- how benchmark-specific metrics are preserved without test adaptation.

## Required outputs

Produce:

1. `docs/evaluation/METRICS_SPEC.md` — human-readable canonical specification.
2. `eval/metric_contract.yaml` — machine-readable task/metric registry including:
   - metric ID;
   - task layer;
   - unit;
   - direction;
   - required gold fields;
   - normalization profile;
   - aggregation rule;
   - primary/secondary status;
   - uncertainty support;
   - subgroup reporting requirements.
3. `docs/evaluation/NORMALIZATION_PROFILES.md` — transliteration/string normalization rules.
4. `docs/evaluation/SCORING_EXAMPLES.md` — worked examples for exact, partially correct, ambiguous, and abstained predictions.
5. Any research citations or decision note needed to justify non-obvious scoring choices.

Implementation of all metrics is not required in EVAL-001; this task specifies the contract that later code will implement.

## Acceptance criteria

- [ ] Every reading layer has an explicit metric family.
- [ ] Recognition, transliteration, interpretation, and translation cannot be conflated.
- [ ] Multiple valid readings and uncertain spans are scoreable.
- [ ] Calibration/abstention is explicitly evaluated.
- [ ] Aggregation prevents large documents from dominating silently.
- [ ] Generalization strata are explicit.
- [ ] Translation evaluation cannot reward fluent hallucination without source faithfulness.
- [ ] Metric definitions include normalization and scoring units.
- [ ] Machine-readable metric contract exists and is internally consistent.
- [ ] Worked examples demonstrate edge cases.
- [ ] External benchmark metrics can be represented without redefining project success.
- [ ] The spec states what remains unknown/unmeasurable when gold data are absent.

## Prohibited shortcuts

- one end-to-end "accuracy" number;
- BLEU-only translation evaluation;
- micro averaging everything by default;
- scoring uncertain/illegible spans as forced errors without an ambiguity policy;
- letting generated translation compensate for wrong visual reading;
- using a proprietary LLM judge as sole evidence;
- changing metric definitions after test results are visible without a versioned decision.

## Evidence package on completion

The overseer returns:
- files created/changed;
- metric-family summary;
- acceptance checklist;
- unresolved scientific choices;
- newly unblocked tasks;
- exact capability-point implication if accepted.

EVAL-001 earns **1.5 capability points only after the complete evaluation specification is reviewed and accepted.**
