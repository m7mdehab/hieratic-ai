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
