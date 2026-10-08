# Research Registry

This file tracks the compact research state. Detailed notes may later live under `docs/research/`.

## Evidence labels

- **VERIFIED-PRIMARY** — checked against the original paper/repository/dataset/site or other primary source.
- **VERIFIED-SECONDARY** — supported by a reliable secondary source but primary source not yet inspected.
- **CANDIDATE** — discovered during reconnaissance and awaiting verification.
- **REJECTED** — investigated and found irrelevant, inaccurate, inaccessible, or otherwise unsuitable.

## Current research conclusions

### R-001 — Overall feasibility

**Status:** preliminary, to be strengthened with primary-source citations.

The problem is best treated as a sequence of capabilities rather than a single classifier: script/document understanding, visual recognition/HTR, transliteration/normalization, linguistic interpretation, and translation.

The current program assumes that partial computational work on Hieratic exists while robust, general-purpose reading across unseen documents/scribes remains unsolved enough to justify research. This must be documented rigorously in FND-004.

### R-002 — HieraticBench

**Status:** CANDIDATE / external benchmark.

HieraticBench is treated as an external evaluation resource, not the definition of project success. Its exact composition, methodology, model results, source repository, leakage risks, and licensing must be verified from primary sources before being encoded into evaluation claims.

### R-003 — Data landscape

**Status:** CANDIDATE.

Initial reconnaissance identified candidate Hieratic sign/image resources, computational prior art, palaeographic databases, and at least one recent dataset direction. No candidate is considered cleared for training or redistribution until provenance, labels, access method, and license are verified.

### R-004 — Hieratic writing-system and machine-reading problem map

**Status:** VERIFIED-PRIMARY / completed as FND-003.

A source-grounded problem map is now available at `docs/research/HIERATIC_WRITING_SYSTEM_PROBLEM_MAP.md`.

Key validated implications:
- Hieratic varies strongly across period, register, scribe, material, and layout.
- Allography, abbreviation, and ligatures prevent a simple fixed-font classification framing.
- visually ambiguous signs can require phonetic/classifier and sequence context;
- image-to-translation must be decomposed into auditable recognition, standardized rendering, Egyptological transliteration, linguistic analysis, and translation layers;
- evaluation must eventually include provenance-aware held-out splits rather than random crop splits.

FND-003 is validated. It unblocks EVAL-001.

### R-005 — Verified prior art and data registry

**Status:** VERIFIED-PRIMARY / completed as FND-004.

The project now has a source-verified registry at `docs/research/PRIOR_ART_AND_DATA_REGISTRY.md`.

Key findings:
- Hieratic-specific computational/OCR work predates HieraticBench, including a 2021 CNN experiment, Tabin's 13,134-sign OCR corpus/tool, Isut, and the 2025 HieraticAI prototype.
- HieraticBench contains 268 repository item records and is now formally reserved for external evaluation rather than training.
- DDD (June 2026) is a high-value modern dataset candidate: 159 images, 50 papyri, 504 character/group categories, polygon annotations, and supplied closed/open-set split families.
- HPDB and AKU-PAL are strong palaeographic/sign-retrieval resources.
- TLA is strategically valuable for transliteration/linguistic modeling, but its live website terms do not allow bulk corpus extraction.
- Several resources require rights clarification at the data/image level even when their software repository is open source.

FND-004 is validated. It unblocks FND-005, EVAL-002, and (together with FND-003) EVAL-004.

## Active research questions

1. What are the strongest primary-source prior-art examples specifically involving Hieratic, distinct from hieroglyphic/Demotic/Coptic OCR?
2. What legally usable image/transliteration pairs exist at sign, line, page, and document level?
3. Which variation axes must be isolated in train/dev/test splits: document, scribe, period, material, collection, edition?
4. What constitutes a defensible transliteration target when multiple scholarly readings are valid?
5. Which external benchmark items may have appeared in foundation-model pretraining or public digital editions?
6. How should expert uncertainty and alternative readings be represented?
7. What is the best first specialist baseline that provides information useful to later VLM work?

## Immediate overseer research outputs

FND-003:
- **completed** — see `docs/research/HIERATIC_WRITING_SYSTEM_PROBLEM_MAP.md`.

FND-004:
- **completed** — see `docs/research/PRIOR_ART_AND_DATA_REGISTRY.md`.

FND-005:
- enforceable licensing/provenance policy.


### R-006 — Layered evaluation contract

**Status:** VERIFIED / completed as EVAL-001.

The project now evaluates reading as a layered capability chain rather than as one end-to-end score.

Key decisions:
- visual recognition, transliteration, linguistic interpretation, translation, and uncertainty remain separately measurable;
- multiple acceptable scholarly readings and illegible spans are supported;
- document-macro aggregation is required where micro averaging could be dominated by large/easy documents;
- translation uses source-faithfulness plus adequacy, with automated MT metrics treated as supporting diagnostics;
- calibration and selective-risk reporting are part of the reading objective rather than optional polish;
- no primary composite score is used in evaluation v1.

See `docs/evaluation/METRICS_SPEC.md` and `eval/metric_contract.yaml`.


### R-007 — Pinned HieraticBench external reproduction (EVAL-002)

**Status:** VERIFIED-PRIMARY, source-code inspected and CI reproduced public aggregates.

Pinned benchmark commit: `d587dc990013f18007f1e7a8f56f96ff2f7127e2`; harness `0.1.0`.

Official structure: 268 items, 266 public + two sealed images of the same commissioned sentence; 150 public AKU-PAL single signs; 118 identify-eligible items; 13 published model/effort rows in the Oct 5 snapshot.

The benchmark's 0/0.5/1 script-ID credit, first-code sign scoring, bounded 1-minus-edit-distance sign/transliteration scoring and chrF translation function are **official benchmark rules**, not interchangeable with Hieratic AI's EVAL-001 metrics.

Reproducibility:
- successful independent GitHub Actions audit of pinned upstream public run data;
- 1,892 run records inspected, 1,738 item/model/rung means and 17 aggregate model/rung values verified against official leaderboard;
- 13 synthetic Python tests and eight original upstream scorer tests passed;
- model provider calls **not** rerun;
- no public machine-scored readings/translations for the sealed sentences; no answer key inferred.

Evidence: `docs/evaluation/HIERATICBENCH_REPRODUCTION.md`,
`eval/benchmarks/hieraticbench/`,
[Actions audit run 37693626552](https://github.com/m7mdehab/hieratic-ai/actions/runs/37693626552).

Methodological constraint: external item content, source near-duplicates, and benchmark gold stay out of training/dev, regardless of source-license permissiveness.


### R-008 — Error taxonomy and reproducible review workflow (EVAL-005)

**Status:** ACCEPTED methodology and software contract, not a reported model result.

Defines 48 failure codes across 16 visual, linguistic, uncertainty, generalization and evaluation-integrity layers. Review events are typed, evidence-linked, may express upstream causal relationships, and track adjudication, gold missingness, contamination, stratum metadata and publication scope. Public summary logic suppresses sealed-record aggregates. Error counts are not performance rates without frozen scored denominators.

Evidence: `docs/evaluation/ERROR_TAXONOMY_AND_ANALYSIS.md`, `eval/analysis/`, dedicated passing GitHub Actions error-analysis workflow, 23 new synthetic tests.


### R-009 — Untuned frontier model baseline preregistration

**Status:** PROTOCOL-STAGED / no experimental evidence.

A versioned, fail-closed untuned frontier VLM evaluation protocol has been implemented for public HieraticBench script-ID and isolated-sign rungs. Candidate provider lanes are OpenAI, Anthropic and Google; exact provider IDs/configurations remain unresolved. Prompt source and dataset commit are pinned to accepted EVAL-002, but frozen item manifest and exact prompt hashes still require verification.

Read-only tooling validates planned capture completeness, hashes and provider/prompt consistency using synthetic offline tests. No API calls, new model predictions, official new scores, or trained models have been produced. This is **not** a verified EVAL-003 baseline and does **not** change research coverage.

See `docs/evaluation/FRONTIER_BASELINES.md`, `eval/baselines/` and PR #31.


### R-010 — W1 acquisition, annotation and evaluation-split infrastructure (validated)

**Status:** REVIEWED TOOLING / NO CLAIM OF CORPUS ADMISSION OR GENERALIZATION.

The corrected W1 package passed live GitHub CI and was merged in independent PRs:
- **DATA-002 (#20):** acquisition-manifest rights/provenance planner, with item-level reviewer and licence evidence, benchmark-overlap review, SHA-256 lineage and fail-closed synthetic/placeholder checks. A conditional plan is not asset acquisition or admission.
- **DATA-004 (#23):** layered Hieratic annotation schema with strict certain-gold anchoring, acceptable alternatives, document/line/region/sign relations, coordinates, reviewer provenance, unique reading order and parent-region cycle checks.
- **EVAL-004 (#24):** deterministic document/scribe/period/source split planning and quarantine of unreviewed high-risk benchmark overlaps. Upstream benchmark public item roster is aggregate-only and production image overlap must receive independent item-level review.

Observed CI: DATA-002 final 34 governance/51 data/78 evaluation tests; DATA-004 34/32/57; EVAL-004 34/13/78, all passed with approved task-branch scopes. **No rights-controlled images, trained models, model experiments or unseen-scribe performance were produced.**

Capability points **+7.0** (11.5 -> 18.5), phase P2 **6.5/10**, phase P3 **7/20**. Research coverage remains **14%** pending its separate operational denominator.


### R-011 — Sealed evaluation policy, metric-claim auditing and public-freeze preregistration

**Status:** VERIFIED METHODOLOGY/TOOLING — NO REPORTED MODEL PERFORMANCE.

EVAL-006 created a versioned frozen **policy** for independent blind Hieratic evaluation, contamination response and release authority. It does not certify a real sealed corpus or evaluate a real checkpoint. Its linked redacted-report contract forbids missing/altered attempts, post-hoc metrics, composite scores, unsubstantiated stage/generalization claims and confidence intervals without document groups. Scientific release must also meet item-specific rights and benchmark-overlap evidence and independent review.

PRs #35 and #40 passed CI and were accepted (+2.0 points). A total of 145 evaluation tests passed in the final audit; this includes synthetic cases, **not** model runs.

Separately, EVAL-003's pinned public metadata freeze was implemented in PR #38. Ephemeral CI examined only permitted metadata/prompt source in the EVAL-002 upstream checkout at commit `d587dc990013f18007f1e7a8f56f96ff2f7127e2` and verified 116 public script-ID + 150 sign item/rung records (2 sealed items excluded). It creates no inference results or spending authorization; EVAL-003 retains 0/1.5 points.

New goal progress: **20.5/100**, P2 evaluation **8.5/10**, research coverage 14%, 0 validated experiments and 0 trained models.


### R-012 — W2 data-engine contracts and strict provenance/ambiguity gates

**Status: REVIEWED ENGINEERING INFRASTRUCTURE — not a real corpus or experimental result.**

DATA-003 #36: deterministic image preprocessing, SHA256 lineage, coordinate transforms and dataset IDs. DATA-005 #37: versioned Hieratic identity/variant claims separated from hieroglyphic and transliteration with verified citation metadata. DATA-006 #39: rights-linked image/line/sign/token alignment and synthetic-source exclusion from gold scoring. DATA-007 #41: independent blinded reviewer decisions, append-only supersessions, adjudication and transparent paired denominators.

All four merged following independent negative-test review, targeted fixes and final green CI (34 governance/80 data/145 evaluation tests by last PR). No copyrighted manuscript images, real historical mappings, expert adjudication, trained models, model outputs, or benchmark scores were produced.

**Verified progress +10.0** to 30.5/100, P3 17/20, P2 8.5/10, coverage unchanged at 14%. DATA-008, VLM-001 and LING-001 become dependency-ready only.


### R-013 — W3 original baseline freeze and primary-source rights readiness

**Status:** MERGED RESEARCH INFRASTRUCTURE, no model results. Date: 2026-10-08.

[PR #47](https://github.com/m7mdehab/hieratic-ai/pull/47) passed complete frontier-baseline CI: 175 evaluation tests and frozen pinned public inventory/prompt-source verification. `eval/baselines/run_freeze.py` rejects unapproved/unsafely stored, altered, missing or mismatched original model prompt/image attempt evidence; per-attempt private provider responses are checked against *individual* rendered prompt hashes, not only an upstream shared prompt-source digest. The tool purposely emits no raw responses, claims no real provider calls and cannot validate rights/consent from a Boolean flag alone.

Official evidence audit `eval/baselines/SOURCE_RIGHTS_READINESS.md` (primary sources as of audit date): HPDB data CC BY with distinct underlying source imaging rights; AKU-PAL per-image; DDD noncommercial/share-alike plus individual image copyright; TLA limits mass copying; PaPYrus, HieraticAI, Isut software rights not equal to images. HieraticBench quarantined externally for evaluation only. No unrestricted corpus admission from these observations.

W3's EVAL-003 remains active and earns zero until real inference, frozen run/cost/rights record, official scores, independent reproduction and human scientific review. No change to 30.5/100 progress, 14% coverage or 0 experiment/model counts.
