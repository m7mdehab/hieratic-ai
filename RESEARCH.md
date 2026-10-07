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
