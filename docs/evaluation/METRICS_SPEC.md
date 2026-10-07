# Hieratic AI Evaluation Metrics Specification v1.0

**Task:** EVAL-001  
**Status:** Proposed for overseer acceptance  
**Date:** 2026-10-08  
**Scope:** Canonical metric definitions for the complete Hieratic-reading stack.

## 1. Purpose

This document defines what Hieratic AI means by **measurable reading capability**.

The project does not treat Hieratic reading as one undifferentiated end-to-end score. A system may succeed at one layer and fail at another: it may identify the script but not read it, recognize signs but mistransliterate them, or produce a fluent translation from prior knowledge while failing to recover the visual text.

The evaluation system therefore measures each layer independently and preserves the chain from image evidence to linguistic interpretation.

The canonical stack is:

1. script/domain identification;
2. layout and reading-order recovery;
3. sign/grapheme localization and recognition;
4. line/sequence recognition;
5. standardized hieroglyphic rendering;
6. Egyptological transliteration;
7. normalization/tokenization;
8. lexical and morphological interpretation;
9. translation/interpretation;
10. uncertainty/calibration;
11. generalization/robustness;
12. blind expert evaluation.

## 2. Evaluation principles

### 2.1 No fluent-hallucination credit

A semantically plausible modern-language translation is not proof that the image was read correctly.

Translation metrics are reported separately from recognition and transliteration metrics. Any serious end-to-end claim must expose either:
- auditable intermediate visual/linguistic outputs; or
- an evaluation protocol capable of independently testing visual faithfulness.

A system cannot compensate for catastrophic visual-reading failure merely by producing fluent target-language text.

### 2.2 No single score may hide layer failure

Version 1.0 has **no primary composite headline score**.

Layer-specific metrics are the scientific result. A public summary may later display a fixed secondary composite only after:
- its weights are predeclared;
- floors/gates prevent compensation across incompatible capabilities;
- all component metrics remain visible;
- the composite is versioned before test results are inspected.

### 2.3 Multiple scholarly readings are first-class

Hieratic can be visually, graphemically, lexically, or interpretively ambiguous. Gold data may therefore contain:
- several acceptable sign identities;
- several acceptable transliterations;
- uncertain spans;
- unscorable/illegible spans;
- alternative lexical parses;
- multiple acceptable translations.

Evaluation must score against valid alternatives instead of forcing false certainty.

### 2.4 Abstention is allowed but not free

A system may predict **unknown / illegible / abstain** when evidence is insufficient.

Abstention is evaluated by:
- coverage;
- selective accuracy/error;
- risk-coverage curves;
- calibration.

A model that abstains on everything cannot obtain a strong reading score.

### 2.5 Macro reporting is required

Large documents, frequent signs, or dominant sources must not silently determine the headline result.

Where applicable, report:
- item-level micro score;
- document-macro score;
- source/domain macro score;
- class-macro score;
- subgroup scores.

The primary aggregate for recognition/transliteration on heterogeneous corpora is normally **document-macro**, with micro metrics retained as diagnostics.

### 2.6 Evaluation rules are versioned

Metric definitions, normalization rules, acceptable-reference rules, subgroup definitions, and benchmark adapters must be versioned.

A rule may not be changed after sealed-test results are visible merely because the new definition improves the score.

## 3. Gold-data concepts

Each scored unit should be able to reference these fields when available.

### 3.1 Identity and provenance

- document ID;
- page/object ID;
- source/collection;
- line/region ID;
- scribe/writer grouping;
- period/date range;
- material/support;
- genre/register;
- damage/legibility class.

### 3.2 Reading targets

- script/domain label;
- text regions and reading order;
- Hieratic grapheme/sign identity;
- sign alternatives;
- ligature/group membership;
- standardized hieroglyphic rendering;
- Egyptological transliteration;
- normalized tokens;
- lemma;
- morphology;
- translation references;
- expert uncertainty.

### 3.3 Gold status

Every target span/item should be able to declare:

- `certain`;
- `uncertain_with_alternatives`;
- `illegible_unscorable`;
- `missing_annotation`;
- `adjudication_pending`.

`illegible_unscorable` and `missing_annotation` are not silently scored as system errors. They are reported as unavailable gold and excluded according to the metric-specific denominator rules.

## 4. Metric families by layer

---

## 4.1 Script / domain identification

### Primary metrics

#### SCRIPT-ACC — accuracy

[
Accuracy = \frac{correct}{N}
]

Use only where each item has one resolved gold class.

#### SCRIPT-MACRO-F1 — macro F1

Compute F1 independently for each script/domain class and average classes equally.

Required when the evaluation includes imbalanced classes such as Hieratic, hieroglyphic, Demotic, Coptic, modern handwriting, and non-Egyptian controls.

### Secondary metrics

- per-class precision/recall/F1;
- confusion matrix;
- balanced accuracy.

### Abstention-aware reporting

If the model can output `uncertain`:
- coverage = fraction of examples on which it gives a non-abstained class;
- selective accuracy = accuracy among answered items;
- risk = 1 - selective accuracy;
- report the risk-coverage curve.

Do not map `uncertain` to a random class solely to preserve ordinary accuracy.

---

## 4.2 Layout and reading order

Layout metrics apply only when corresponding gold regions/order exist.

### Region localization

Use COCO-style average precision when box/polygon annotations and sufficient sample size exist:

- AP@[IoU=.50:.05:.95] as primary detector summary;
- AP50 and AP75 as supporting metrics;
- recall at declared proposal/detection budgets where useful.

For line segmentation where masks/polygons are available:
- region IoU;
- Dice/F1 may be reported as a secondary diagnostic.

### Reading-order metrics

Represent gold and prediction as ordered region/line IDs after region matching.

Report:

#### ORDER-PAIR-ACC

Fraction of evaluable region pairs whose relative order is correct.

#### ORDER-ER

Normalized edit distance between predicted and gold reading-order sequences after region matching:

[
ORDER\text{-}ER = \frac{S+D+I}{N}
]

This is preferred to exact-only page accuracy because one local order mistake should not erase all information.

Also report exact page reading-order accuracy when meaningful.

### Missing layout gold

If a source provides only cropped lines/signs:
- layout metrics are `not_applicable`;
- they are not imputed from model behavior;
- downstream recognition may still be evaluated on provided crops.

---

## 4.3 Sign/grapheme localization and recognition

Hieratic sign recognition must distinguish **visual detection** from **identity classification**.

### Detection

Where spatial annotations exist:
- DET-AP = AP@[.50:.05:.95];
- DET-AP50;
- DET-AP75;
- DET-RECALL.

For grouped signs/ligatures, the annotation policy must declare whether the object is:
- one ligature/group;
- multiple constituent signs;
- both hierarchical levels.

Do not compare detectors trained/scored under incompatible grouping policies without conversion.

### Classification

#### SIGN-TOP1

Prediction receives credit if its first candidate is in the acceptable gold identity set.

#### SIGN-TOPK

For fixed predeclared (k), success if any top-k candidate is acceptable.

Report at most a small fixed set such as k=1,3,5. Arbitrarily large k is not meaningful reading ability.

#### SIGN-MACRO-F1 / MACRO-ACC

Class-macro performance is required when sign frequencies are strongly imbalanced.

Rare-class performance must not be hidden by common-sign frequency.

### Alternative gold identities

For an item with acceptable set (G), top-1 is correct when (p_1 \in G).

For top-k, success when (P_k \cap G \neq \emptyset).

If experts disagree and no adjudicated acceptable set exists, mark the item adjudication-pending rather than forcing one label.

---

## 4.4 Palaeographic retrieval

Retrieval supports sign reading, allography, and tool-augmented VLM workflows.

Primary metrics:

- RET-R@1;
- RET-R@5;
- RET-R@10;
- RET-MRR;
- optional nDCG when relevance has graded levels.

A query may have multiple relevant exemplars.

Relevance sets must be defined before evaluation, e.g.:
- same grapheme;
- same grapheme and period;
- same allograph family.

The project must name the relevance definition alongside every retrieval score.

---

## 4.5 Line / sequence recognition

Sequence recognition is the core reading metric for specialist HTR and multimodal systems.

### Grapheme Error Rate (GER)

For gold sequence (g) and prediction (p):

[
GER = \frac{S + D + I}{N}
]

where substitutions, deletions, and insertions are obtained from minimum edit distance over the canonical grapheme token sequence and (N) is gold grapheme count.

Lower is better.

### Transliteration Character Error Rate (CER)

Same formula after the declared transliteration normalization profile.

Evaluation is over Unicode grapheme clusters or a project-defined atomic transliteration symbol sequence, not arbitrary UTF-8 bytes.

### Token / Word Error Rate (WER/TER)

Used only where tokenization has a defensible scholarly definition.

Because ancient Egyptian orthographic/token boundaries may be editorial, the tokenization profile must be versioned with the metric.

### Exact sequence accuracy

Fraction of sequences exactly matching one acceptable normalized reference.

Useful but never the only sequence metric.

### Multiple valid references

If gold contains a finite acceptable set (G = \{g_1,...,g_m\}), use:

[
d(p,G) = \min_{g \in G} d(p,g)
]

for edit-distance metrics.

When ambiguity is localized, the preferred representation is a reference lattice/structured alternative graph so combinations of independent alternatives do not need to be enumerated manually.

### Top-k sequence output

If a decoder returns k hypotheses:
- top-1 score is always reported;
- oracle top-k score may be reported diagnostically;
- k must be fixed before sealed evaluation;
- oracle top-k is never presented as ordinary reader accuracy.

---

## 4.6 Standardized hieroglyphic rendering

This layer measures sign-normalized rendering separately from linguistic transliteration.

Primary metrics:
- HGR-SER — sign-token error rate;
- HGR-EXACT — exact normalized sequence accuracy.

Normalization may:
- normalize whitespace/encoding;
- normalize equivalent formatting syntax;
- canonicalize explicitly declared sign-code aliases.

Normalization may **not**:
- merge distinct signs merely because their readings overlap;
- silently correct a model's substantive sign choice;
- use downstream translation to rewrite sign output.

---

## 4.7 Egyptological transliteration

Primary metrics:
- TR-CER — transliteration character/symbol error rate;
- TR-TER — token error rate when tokenization profile applies;
- TR-EXACT — exact normalized transliteration sequence accuracy.

Secondary:
- top-k exact/CER for alternative hypotheses;
- per-sign alignment accuracy where gold alignment exists.

The comparison profile must preserve linguistically meaningful distinctions.

Only representational equivalences may be normalized automatically.

---

## 4.8 Normalization/tokenization

This layer evaluates whether diplomatic/transcribed text is mapped into the project's normalized linguistic representation.

Metrics:
- NORM-TOKEN-ACC;
- NORM-TER;
- NORM-EXACT.

Where several normalized forms are scholarly equivalents, score against the declared acceptable set.

Normalization is not allowed to use the sealed reference translation.

---

## 4.9 Lexical and morphological interpretation

### Lemma

- LEMMA-ACC;
- LEMMA-MACRO-F1 where lemma frequencies permit;
- LEMMA-TOPK for fixed k when alternatives are produced.

### Morphology

Represent morphology as a bundle of features.

Report:
- MORPH-BUNDLE-ACC — exact full-bundle accuracy;
- MORPH-MICRO-F1 — feature-level;
- MORPH-MACRO-F1 — across feature types where meaningful.

If the gold allows multiple analyses, a predicted bundle is correct when it matches any adjudicated acceptable bundle.

### Partial analyses

If only lemma or partial morphology is annotated:
- score only annotated fields;
- report field coverage;
- do not count absent gold features as incorrect.

---

## 4.10 Translation / modern-language interpretation

Translation is intrinsically reference-variable and must be evaluated by multiple signals.

### Primary for research-grade claims

For a sufficiently important held-out set, use blind expert/human evaluation with separate dimensions:

1. **source faithfulness** — does the translation reflect the recovered Egyptian reading rather than invented content?
2. **semantic adequacy** — does it preserve the passage's meaning?
3. **uncertainty fidelity** — are ambiguous/illegible parts represented cautiously?
4. **critical terminology / names / numbers** — are content-bearing entities handled correctly?

Each dimension uses a fixed rubric, e.g. 0–4.

### Automated secondary metrics

Reference-based automated metrics may include:
- chrF/chrF++;
- target-language semantic similarity metrics;
- COMET-family metrics only when the chosen model is demonstrably appropriate for the language setup and its version/configuration is frozen.

Because ancient Egyptian is not a normal modern MT source language, no pretrained MT evaluator is assumed valid by default.

### LLM-as-judge

Allowed only as a **secondary diagnostic** when:
- model/provider/version is logged;
- exact judge prompt is stored;
- references and source representation shown to the judge are recorded;
- repeated/judge-ensemble variance is assessed where feasible;
- no major project claim depends solely on that judge.

### Translation gating

A translation result may be reported even when visual reading is poor, but it must be labeled accordingly.

For a claim of **image reading → translation**, publish alongside it at minimum:
- sequence/transliteration metric;
- translation metric;
- source-faithfulness evaluation.

---

## 4.11 Confidence, calibration, alternatives, and abstention

### Categorical predictions

When probabilities are available:
- Brier score;
- negative log-likelihood;
- expected calibration error (ECE), with binning scheme reported.

ECE is diagnostic, not sufficient on its own.

### Selective prediction

For systems that can abstain:
- coverage;
- selective risk/error;
- risk-coverage curve;
- area under risk-coverage curve (AURC) where sample size permits.

Report fixed operating points such as:
- accuracy/error at 50%, 75%, 90% coverage;
- coverage at a predeclared risk target.

### Alternative sets

For a model returning an explicit acceptable-candidate set:
- ALT-COVERAGE = fraction of items where the gold set intersects prediction set;
- ALT-SIZE = mean/median prediction-set size.

These must be reported together. Coverage alone can be gamed by returning every possible answer.

### Illegible prediction

If gold is `illegible_unscorable`, do not score ordinary content accuracy.

If gold is legible and the model says illegible:
- it counts as abstention/not answered;
- it affects coverage.

If gold is uncertain with alternatives:
- prediction may match alternatives according to the relevant set/lattice rule.

---

## 4.12 Generalization and robustness reporting

Every model intended to support a general Hieratic-reading claim must report results across available strata.

Required strata when metadata/sample size support them:
- unseen document;
- unseen scribe/writer;
- period;
- material/support;
- genre/register;
- institution/source;
- damage/degradation;
- layout type.

### Required summaries

For each primary metric:
- overall document-macro score;
- each evaluable subgroup;
- worst-group score;
- range/std across groups;
- absolute and relative drop from matched/in-domain reference where one exists.

No overall average may substitute for a catastrophic subgroup failure.

### Minimum subgroup sample

Do not publish strong subgroup conclusions from tiny counts.

Default:
- show raw score/count for any subgroup with data;
- label as descriptive when (n < 20) documents/items at the primary aggregation unit;
- use confidence intervals only where the sample supports them;
- avoid significance claims on tiny strata.

Exact thresholds may be revised with a versioned decision before sealed testing.

---

## 4.13 Blind expert evaluation

Expert evaluation is required for claims not fully captured by automatic gold, especially:
- ambiguous readings;
- linguistic interpretation;
- translation;
- unusual palaeography;
- out-of-distribution material.

### Blinding

Where practical, experts should not know which system produced which output.

### Rubric

At minimum score separately:
- visual reading fidelity;
- transliteration adequacy;
- linguistic analysis adequacy;
- translation adequacy;
- uncertainty honesty.

Do not ask experts for only one holistic "good/bad" score.

### Agreement

With multiple raters:
- report inter-rater agreement, e.g. Krippendorff's alpha or another appropriate statistic;
- preserve individual ratings and adjudication decisions;
- disagreements are evidence, not noise to be silently discarded.

---

## 5. Normalization policy

All string/sequence metrics must name a normalization profile.

Canonical profiles are defined in `docs/evaluation/NORMALIZATION_PROFILES.md`.

Rules:
- Unicode normalization is representational, not linguistic correction.
- Whitespace formatting may be normalized where it carries no scholarly distinction.
- Editorial punctuation may be stripped only in a profile explicitly intended to ignore it.
- meaningful transliteration symbols are preserved.
- unknown/uncertain markers are preserved or masked only according to declared gold policy.
- normalization never consults the reference translation or downstream gold.

Every reported CER/WER/SER must state its profile ID.

## 6. Aggregation

### 6.1 Default hierarchy

For sequence metrics:

1. compute item/line errors;
2. aggregate within document;
3. macro-average documents for the primary corpus score.

Also report global micro error rate.

For sign classification:
- item micro;
- class macro;
- document macro.

For translation:
- human scores macro by passage/document;
- automated metric corpus score plus document distribution.

### 6.2 Why both macro and micro matter

Micro metrics answer: "How many total symbols/items were correct?"

Document-macro metrics answer: "How well does the system work on a typical document?"

Both are required because a small number of long/easy documents can dominate micro scores.

## 7. Confidence intervals and comparison policy

### 7.1 Bootstrap unit

Confidence intervals should resample at the highest independent unit that matches the claim, normally **document**, not individual signs from the same document.

Default:
- paired bootstrap over documents;
- 2,000 resamples;
- 95% percentile interval.

If the test set is too small, report the raw distribution and state that interval estimates are unstable.

### 7.2 Comparing two systems

For paired evaluation:
- compute per-document paired differences;
- report bootstrap CI of the difference;
- optionally paired randomization/permutation test where appropriate.

Do not use independent-sample tests when both systems score the same documents.

### 7.3 Stochastic training

When training stochastic models:
- preserve all declared seeds;
- report mean and dispersion across seeds where multiple full runs are feasible;
- never select the best seed as the sole headline result.

## 8. Exclusions and denominator integrity

Every exclusion from scoring must include a reason code.

Allowed examples:
- missing gold;
- adjudication pending;
- source file corrupt;
- genuinely out of task scope.

Not allowed:
- hard example;
- model could not parse;
- output format inconvenient;
- low confidence.

Each report must include:
- total candidate items;
- scored items;
- excluded items by reason;
- coverage.

## 9. Missing-gold policy

A layer with no gold is **not measured**.

Do not infer success at that layer from downstream fluency.

Example: if an image has only a published translation but no reliable transliteration, it may support limited translation analysis but cannot establish visual recognition accuracy.

## 10. External benchmark compatibility

HieraticBench remains an external benchmark, not the project success definition.

An adapter may map its tasks into this metric registry while preserving the benchmark's official scoring exactly.

Rules:
- official benchmark score is reported unchanged;
- project-normalized/derived metrics, if any, are labeled separately;
- benchmark items remain evaluation-only;
- no metric redesign is based on sealed answers;
- public benchmark performance is one column in a broader generalization table.

## 11. Metric report format

Every experiment report should eventually record:

- experiment/model ID;
- checkpoint/version;
- dataset version;
- split version;
- metric-contract version;
- normalization-profile version;
- metric values;
- aggregation unit;
- subgroup values;
- confidence intervals;
- exclusions;
- contamination status;
- code commit;
- evaluator version.

A score without its contract/profile version is incomplete evidence.

## 12. Primary and secondary metrics by capability

| Layer | Primary metric(s) | Required supporting metrics |
|---|---|---|
| Script ID | macro F1, accuracy | confusion, coverage |
| Layout | AP@[.50:.05:.95], order error | AP50/AP75, pairwise order accuracy |
| Sign recognition | top-1, macro F1 | top-k, class/document macro |
| Retrieval | Recall@k, MRR | relevance definition |
| Sequence HTR | GER, document-macro GER | CER/TER, exact, micro GER |
| Hieroglyphic rendering | SER | exact |
| Transliteration | CER, document-macro CER | TER, exact |
| Normalization | TER/token accuracy | exact |
| Lemma | accuracy / macro F1 | top-k if applicable |
| Morphology | bundle accuracy | feature micro/macro F1 |
| Translation | blind source-faithfulness + adequacy rubric | chrF/semantic diagnostics |
| Calibration | Brier/NLL + risk-coverage | ECE, fixed coverage points |
| Generalization | subgroup primary metric + worst group | relative/absolute drop |
| Expert | dimension-specific blind rubric | agreement/adjudication |

## 13. Anti-shortcut safeguards

The evaluation system explicitly rejects these shortcuts:

- using script identification as evidence of reading;
- random crop leakage across the same document;
- tuning on sealed test results;
- reporting only common-sign micro accuracy;
- reporting only the best seed;
- using oracle top-k as ordinary accuracy;
- hiding exclusions;
- treating an LLM judge as ground truth;
- using translation fluency as evidence of visual reading;
- changing normalization after seeing test errors;
- collapsing uncertain scholarly readings to one arbitrary answer;
- reporting an overall score without document/source breakdown.

## 14. Open scientific choices

These remain versioned open questions rather than hidden assumptions:

1. exact grapheme token inventory for GER;
2. authoritative tokenization rules for Egyptian WER/TER;
3. representation of localized ambiguity as finite references vs lattice;
4. final expert rubric anchors for each 0–4 level;
5. whether a future public composite score is scientifically useful;
6. minimum sample sizes for inferential subgroup claims;
7. which automated translation metrics are suitable once target language(s) and gold sets are fixed;
8. calibration representation for structured sequence outputs.

These choices are delegated to later data/schema and sealed-evaluation tasks where appropriate.

## 15. Evidence basis

This specification combines the project's source-grounded Hieratic problem map with established evaluation conventions.

Relevant references include:

- COCO detection evaluation: https://cocodataset.org/dataset/detection-eval.htm
- Guo et al. (2017), *On Calibration of Modern Neural Networks*: https://proceedings.mlr.press/v70/guo17a.html
- Geifman & El-Yaniv (2017), *Selective Classification for Deep Neural Networks*: https://papers.nips.cc/paper_files/paper/2017/hash/4a8423d5e91fda00bb7e46540e2b0cf1-Abstract.html
- Popović (2015), chrF: https://aclanthology.org/W15-3049/
- Rei et al. (2020), COMET: https://aclanthology.org/2020.emnlp-main.213/
- Koehn (2004), paired significance testing / bootstrap practice in MT evaluation: https://aclanthology.org/W04-3250/
- Hieratic writing-system/problem map: `docs/research/HIERATIC_WRITING_SYSTEM_PROBLEM_MAP.md`

## 16. EVAL-001 acceptance mapping

### Criterion
> Metrics and scoring rules cover script ID, recognition, transliteration, uncertainty, and translation without conflating tasks.

**Satisfied by design:** each layer has separate primary/supporting metrics, explicit uncertainty handling, aggregation rules, and anti-shortcut constraints.

The machine-readable registry in `eval/metric_contract.yaml`, normalization specification, and worked scoring examples are part of the same acceptance package.
