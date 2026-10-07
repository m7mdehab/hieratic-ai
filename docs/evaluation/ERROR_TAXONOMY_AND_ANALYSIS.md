# Hieratic AI: Error Taxonomy and Analysis Workflow v1.0

**Task:** EVAL-005  
**Status:** Candidate for acceptance  
**Date:** 2026-10-08  
**Dependencies:** EVAL-001 (validated)  
**Codebook:** `eval/analysis/error_taxonomy.yaml`  
**Record schema:** `eval/analysis/review_record.schema.json`  
**Analysis CLI:** `eval/analysis/review.py`  

## 1. Scientific objective

The aim is not to assign one generic "wrong" tag to every prediction. It is to identify *where the evidence first supports a failure*, separate that failure from downstream symptoms, preserve ambiguity, and produce reproducible failure breakdowns for model development and later blind evaluation.

This is a diagnostic layer under the EVAL-001 metric contract. It **does not** compute new Hieratic-reading accuracy by counting error annotations. A corpus with 20 annotated errors and 20,000 correct predictions cannot be distinguished from a corpus with 20 errors and 20 total predictions without a frozen scored-item denominator. Any model performance claim therefore remains with the separately versioned EVAL-001 metrics.

## 2. Layers and taxonomy boundaries

The versioned machine codebook defines 48 named failure modes in these families:

| Family | What it isolates |
|---|---|
| Script identification | Wrong writing system, Egyptian-family confusion, unparseable label |
| Layout | Missed/extra text regions, boundaries, wrong reading order |
| Sign recognition | Wrong, omitted, inserted signs; ligature/group and allograph mismatch |
| Palaeographic retrieval | Wrong exemplars, missing relevant exemplars under fixed retrieval budget |
| Sequence recognition | Substitution, deletion, insertion, wrong sequence direction |
| Hieroglyphic rendering | Sign choice and group/ordering errors |
| Egyptological transliteration | Wrong symbol, segmentation error, editorial restoration presented as visible |
| Normalization | Canonical form and token/morpheme segmentation |
| Lexical analysis | Lemma mismatch or unsupported lexical disambiguation |
| Morphology | Feature/bundle mismatch |
| Translation | Omission, unsupported addition, contradiction, entity errors, fluent-hallucination masking |
| Calibration | Overconfidence, underconfidence, excessive abstention |
| Uncertainty | False certainty, missing valid alternatives, unresolved gold ambiguity |
| Generalization | Held-out scribe degradation, source/period shift, document leakage |
| Expert evaluation | Material scholarly disagreement, reviewer provenance deficiency |
| Evaluation integrity | Test contamination, missing gold, parse/format failure |

Each machine code has a fixed stable `code`, `layer` and plain-language `definition`. Code changes require a taxonomy-version increment and a controlled migration of existing annotations; old findings must remain reproducible.

**Scope caution:** The codebook names plausible failure categories. It does not claim that any real model has exhibited a particular error.

## 3. Unit of annotation and evidence

One error-review event corresponds to one identifiable observed failure at a task-scoring unit:

- sign;
- line;
- region;
- passage;
- document;
- or benchmark item.

Every record has IDs for model/run, dataset/split, document and unit, the EVAL-001 `metric_id` when measurable, gold annotation status, error labels, severity, exposure/contamination status, reviewer state and source metadata.

Review records carry **references to evidence** (`artifact:...`, `sha256:...`, or HTTPS links) rather than full model responses, manuscript transcriptions or benchmark answers. The strict JSON schema rejects arbitrary extra fields so a careless caller cannot introduce a `raw_secret_answer` property and leak it into an error-report pipeline.

A production deployment still needs access-control checks on external evidence URLs. Schema checks alone do not make an external artifact safe to publish.

## 4. Primary versus secondary error attribution

Each record may have several `error_codes`, but exactly one must be marked `primary_error`.

Primary selection rule: **Choose the earliest failure in the visual→linguistic chain that is independently evidenced for this unit.**

Example, synthetically:

1. A visual sign is read as the wrong grapheme, supported by adjudicated sign gold.
2. That mistake propagates into a word with the wrong transliteration.
3. A later translation presents an unsupported but fluent interpretation.

The sign substitution can be primary in its event. Translation failure is a separate, downstream event with an `upstream_record_ids` causal link **only when that link is supported**, not assumed from the timeline.

The validator enforces that causal links:
- point to existing error-review records;
- stay within the same model, run, dataset version, split and document;
- do not form cycles.

Do not infer the visual root cause purely because translation is implausible. If only a translation is observed, it remains a translation-level observation.

## 5. Evidence certainty and adjudication

`attribution_status` is separate from whether a gold target is `certain`:

- **observed:** an output symptom was seen, but root cause not adjudicated;
- **adjudicated:** relevant gold/evidence was examined by an identified reviewer, and the label is independently supportable;
- **disputed:** reviewers disagree materially or further Egyptological judgment is needed.

Adjudicated records require:
- reviewer ID or pseudonym;
- review timestamp;
- at least one evidence reference;
- non-`unknown` contamination/exposure assessment.

A disputed record remains in review counts, but not in confirmed-error breakdowns until resolved.

### Adjudication procedure

1. Select the frozen task/metric/split version and original predicted unit.
2. Check the gold target's provenance, confidence and possible acceptable alternatives.
3. Independently inspect the unit in its authorized review environment.
4. Label observed error codes, affected layer and severity. Do not adjust gold to rescue the model.
5. Attribute a primary code only when its cause is actually supported.
6. Link known upstream events and record evidence references.
7. Resolve reviewer disagreement by expert adjudication or keep `disputed`.
8. Freeze signed/hashed review export before producing external comparative reports.

For expert evaluations, later GEN-004 should define review sampling, minimum reviewers and reliability statistics. EVAL-005 establishes data structure and decision flow, not a claim that expert review has already happened.

## 6. Severity rubric

Severity is a **human-adjudicated impact assessment**, not merely edit distance.

- **minor:** local non-material variation, formatting or narrow mistake with little effect on the intended source reading.
- **major:** materially changes a reading, token, syntactic link or a meaning-bearing claim.
- **critical:** invalidates a research claim, introduces fabricated core content or involves evaluation leakage/contamination.

Severity must never replace the primary EVAL-001 layer metric. One critical error and ten minor errors are not automatically "equalized" by an arbitrary weighted average.

Examples:
- one erroneous sign with otherwise stable lexical meaning may be minor or major, depending on source context;
- incorrect numeral/person in a document may be major despite a low character error rate;
- a convincing translation of a page whose source reading is demonstrably wrong may be critical for an asserted end-to-end reading claim;
- confirmed use of sealed test gold for training is critical evaluation-integrity failure, **not** merely poor model generalization.

## 7. Gold uncertainty and scoring eligibility

Gold status matches EVAL-001 exactly:

- `certain`;
- `uncertain_with_alternatives`;
- `illegible_unscorable`;
- `missing_annotation`;
- `adjudication_pending`.

Do not label a disputed grapheme as a confirmed sign substitution until its acceptable gold set is established.

For missing, illegible, or pending gold:
- `score_status` must be `excluded` or `pending`;
- content-reading errors cannot be confirmed;
- diagnostic uncertainty, expert-review and evaluation-integrity events may still be recorded.

Model `ABSTAIN` on legible gold is a coverage/selective-risk event rather than an automatic hallucination. A model claiming a specific reading on illegible gold may be an uncertainty-honesty concern, but cannot be given ordinary sign-accuracy credit.

## 8. Contamination and benchmark quarantine

Records track `exposure_status`: `clean`, `suspected`, `confirmed`, or `unknown`.

- Confirmed contamination may not be scored as clean evidence.
- Suspected/unknown exposure remains visible but cannot be counted as clean adjudicated errors.
- Sealed-benchmark items are represented as `sample_scope: sealed_aggregate`; EVAL-005 never asserts independent scored reading against sealed answers.
- Public report mode **drops sealed-aggregate records before computing any counts, subgroup breakdowns or example summaries**. Internal mode is only for an appropriately controlled environment and still never prints raw text.
- Review records must not contain source answers or images. Neither this tool nor its tests read HieraticBench images/answer keys.
- If a test-set violation is discovered, record it as an evaluation-integrity event and coordinate with EVAL-006 before publishing any affected metric.

The CLI cannot enforce the privacy of external references; reviewers must screen outgoing report artifacts and URLs.

## 9. Analysis workflow

### Step A — Metric evaluation

Run the frozen metric scorer over a frozen data split. Store its version, audit metadata and scored-item universe separately from review events.

### Step B — Candidate failure sampling

Propose annotation candidates from:
- failed exact-match / high GER or CER;
- high-confidence errors;
- repeated sign confusions;
- degraded period/scribe/material strata;
- translation source-faithfulness flags;
- annotator uncertainty/disagreement;
- contamination warnings.

Sampling probabilities and inclusion rules must be logged. A hand-curated failure set is not a random error-rate sample.

### Step C — Blind labeling and adjudication

Review sampled items against permitted evidence. Keep raw images/readings in the restricted evaluation environment, not in the GitHub error-report record. Freeze review outputs and keep disagreements.

### Step D — Schema and taxonomy validation

```bash
python -m pip install -r requirements-projectctl.txt

python -m eval.analysis.review validate \
  --input eval/analysis/examples/synthetic_reviews.jsonl

python -m unittest discover -s tests/evaluation -v
```

Invalid codes, unknown metric IDs, duplicate records, missing evidence/reviewer identities, missing gold, contamination mislabeling and cyclic causal links fail closed.

### Step E — Deterministic descriptive reporting

```bash
python -m eval.analysis.review summarize \
  --input eval/analysis/examples/synthetic_reviews.jsonl \
  --publication public
```

Report outputs:
- number of review events;
- adjudicated, **clean**, scorable error events;
- affected documents;
- primary error counts (mutually exclusive *per event*);
- all-code occurrence counts (multi-label; **not mutually exclusive**);
- primary layer and severity distributions;
- document counts per available source/period/scribe/material/genre/damage stratum;
- review/scoring/gold/exposure status counts;
- explicit warning that error rates cannot be computed from review records alone.

Only adjudicated + clean + scored reviews contribute to confirmed-error distributions.

**Do not interpret counts as accuracy, class error rates, sign error rate or population prevalence.** Those require a frozen denominator and sampling assumptions. A case-control or uncertainty-enriched review set is particularly unsuitable for raw rate estimates.

### Step F — Research feedback and future split freeze

Feed repeated, verified failure categories into hypothesis generation and planned training-data improvements **using only authorized training/development evidence**.

Do not adapt a model, annotation policy, tokenizer, normalization profile or taxonomy based on sealed test outcomes. The locked test results remain evaluation evidence, not an error-driven training curriculum.

## 10. Reproducibility and statistical limitations

The report is deterministic over the same JSONL, taxonomy and metric contract. No random resampling is performed.

For credible *population* error rates and subgroup comparisons, a later reporting layer must join:

- exact model/run and dataset/split versions;
- frozen evaluated unit IDs and denominators, including correct predictions;
- independent document-group identifiers;
- sampled-review inclusion probabilities, when review is not exhaustive;
- eligibility/exclusion and uncertainty masks;
- source/scribe/period/damage metadata.

Then use EVAL-001 document-level macro statistics and document bootstrap for uncertainty. For small subgroups, report descriptive counts rather than a strong generalization claim.

Until those data are present, `rates_computable: false` is mandatory and accurate.

## 11. Interfaces to related tasks

| Related task | Interface |
|---|---|
| EVAL-001 | Metric IDs and gold statuses derive from its frozen contract; no alternate definitions |
| DATA-004 | Future annotation IDs, uncertainty/gold and reviewer provenance link through stable IDs, without copying full annotations |
| EVAL-004 | Frozen split version, document grouping and contamination checks supplied to events |
| EVAL-006 | Sealed access policy, frozen evaluation release gates and contamination adjudication |
| EVAL-003 | Frontier baseline diagnostics use same codebook; model comparisons remain EVAL-001 metric-based |
| GEN-004 | Blind expert review rubric, reliability and adjudication |
| CTRL-003 | Future dashboard may consume redacted aggregate report, never raw review/secret material |

The codebook is orthogonal to Luna's in-progress EVAL-004 split implementation and Sonnet's dashboard files; their write scopes do not overlap.

## 12. Acceptance and future hardening

The minimum accepted EVAL-005 capability is:
- versioned machine taxonomy with explicit reading layers;
- schema-validated structured reviewer evidence;
- distinct observed/adjudicated/disputed handling;
- documented primary/cascade reasoning;
- gold missingness and uncertainty integrity;
- reproducible descriptive reporting with no false denominator;
- sealed benchmark/public report protection;
- synthetic negative tests and CI.

Before production use, follow-on work must define:
- dataset-specific EVAL-001 denominator joins;
- annotator recruitment/sampling and blind expert protocol;
- controlled permissions for evidence artifacts and internal sealed reports;
- source-specific adjudication templates;
- reproducibility checks of full model failure traces.

No model experiments, trained models, or research claims are invented by EVAL-005.
