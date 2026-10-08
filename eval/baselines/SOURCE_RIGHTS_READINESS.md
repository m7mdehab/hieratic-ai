# W3 — Primary-source rights readiness and source-lineage risk for Hieratic AI

**Audit date:** 2026-10-08. **Owner:** overseer, EVAL-003 scientific/integration lane.
**Status:** metadata-only audit, **not a license clearance or new data acquisition**.

This audit evaluates potential training data, independent evaluation, provenance, and evidence gaps using current official source pages and the accepted `data/sources/registry.yaml`. Public accessibility is never equated with permission to redistribute, train commercially, expose benchmark gold, or release derived weights.

## Verified primary-source observations

| Source | Primary-source evidence | Observed, bounded statement | Project decision |
|---|---|---|---|
| HieraticBench | https://github.com/alymoursy/hieraticbench and pinned https://github.com/alymoursy/hieraticbench/tree/d587dc990013f18007f1e7a8f56f96ff2f7127e2 | External benchmark with mixed original image rights and two commissioned sealed items; 266 public script/sign item-rungs in accepted EVAL-002 manifest. | **EVALUATION ONLY**. Entire item lineage and near-duplicates excluded from train/dev/few-shot examples; don't publish sealed gold or raw responses. |
| HPDB | https://moeller.jinsha.tsukuba.ac.jp/en/datasets/ and https://moeller.jinsha.tsukuba.ac.jp/ | Official site explicitly licenses its datasets **CC BY 4.0**. Item index (2,065) and ID concordance (937) are available; underlying IIIF scans are noted as owned by the University of Tokyo's Asian Research Library. The *dataset metadata license* is not automatically a separate full re-licensing of every digitized scan. | **Conditional candidate for controlled sign/concordance metadata**, not automatic corpus admission. Preserve CC BY attribution, source image rights, edition provenance, and overlaps with HieraticBench before any image/derived-crop reuse. |
| AKU-PAL | https://aku-pal.uni-mainz.de/faq | Official FAQ explicitly conditions individual images on the license shown **on each image**, and distinguishes original SVG, third-party photographs and retro-digitized scans. Stable URLs such as `/signs/<ID>` and `/graphemes/<ID>` are appropriate citation identities; provisional AKU numbering is not. | **PER-ITEM**. Require immutable item URL, image-specific license evidence, creator/rightsholder, attribution, review and overlap exclusion. Not a blanket trainable database. |
| DDD | https://zenodo.org/records/20553713 | The published diagnostic Deir el-Medina dataset is **CC 4.0 BY-SA-NC** in its official notice; full papyrus images have individual copyright details in `papyri.json`. Metadata describes 159 images from 50 papyri and selected-character annotations, not full hierarchical transcription of all characters. | **NONCOMMERCIAL, per-image review**. Quarantine from default commercial-compatible model/corpus; no blanket complete-line gold assumed. Any research-only use needs terms, copyright and item-level reviewer evidence. |
| TLA | https://tla.digital/info/licenses | Official terms allow individual data records for academic research but explicitly prohibit reproducing entire subcorpora or larger sets (>10 website pages). Future separately licensed raw releases may be handled under their own terms. | **RESTRICTED**. No crawling or corpus extraction; use link/citation metadata only until a specifically licensed dataset or written permission is verified. |
| PaPYrus | https://github.com/jtabin/PaPYrus | GPL-3.0 software repository also includes dataset images organized by sign, provenance, text and facsimile maker. Code license alone is insufficient evidence for the underlying manuscript/facsimile authors' image reproduction and model-training rights. | **UNKNOWN image/data rights**. Code study only; no admission or copied assets. |
| HieraticAI | https://github.com/MargotBelot/HieraticAI | MIT-licensed educational proof of concept for character detection/classification, with described Westcar/facsimile-related data. An MIT software license is not an item-level license for source images and digital manuscripts. | **UNKNOWN image/data rights**. Treat as prior-art methodology; no dataset import. |
| Isut | See accepted DATA-001 `SRC-ISUT` provenance record; no new primary authorization established in this audit. | GPL program/annotation technology cannot by itself grant image-data licenses. | **UNKNOWN**: keep metadata-only. |

## Evidence hierarchy and inference limits

1. **Authoritative**: source/item copyright/terms/licensing pages and immutable item IDs, with access timestamp and literal rights class.
2. **Conditional**: catalogue metadata license, research publication, or project README. These support discovery and verification but not blanket rights to photographs, annotated gold, or downstream model weights.
3. **Insufficient**: GitHub repository software license, search snippet, another project's use, a free download button, or a reviewer saying "approved" without the actual item grant.
4. **Disallow**: sealed examples, unreviewed near-duplicates, missing manuscript object IDs, unreviewed rights, transformed image crops with no original hash, or training targets from evaluation-only sources.

### Why the EVAL-003 / VLM-001 / DATA-008 boundary matters

- **DATA-008** may package synthetic fixtures and build its corpus-release gate from validated DATA-002/003/004/005/006/007 plus EVAL-004, but a genuine train/dev/test release requires *real* item grants, source/document separation and cleared expert gold. A valid JSON schema does **not** turn missing rights into admissions.
- **VLM-001** may write model-adapter code and simulated offline inference, but no inference result or weighted baseline milestone exists without real approved image calls, exact frozen prompts and official matched scoring. HieraticBench public items are never few-shot demonstrations.
- **EVAL-003** separately pre-registers and compares vendor-hosted frontier models; the project cannot treat published leaderboard summaries, CI fixtures, or adapter outputs as newly measured results. Its official 116 script-identification and 150 isolated-sign samples remain **evaluation only** and have no public sentence-reading gold.

## Precise admission questions before real experiments

For each proposed item, record:
- canonical object/document/page ID; stable archive URI; provider/rightsholder; exact per-item data + image license text and evidence URL;
- copyright/attribution for original scan, derived photograph, facsimile, graphic crop, and annotation/translation independently;
- explicit permissions for access, training, evaluation, redistribution and publication of outputs/weights;
- authenticated person/date approving each source/item and permitted scope; no synthetic approvals;
- object/document/scan hashes and reviewed perceptual near-duplicates against **the pinned HieraticBench roster** and all train/dev/test material;
- documented script, period, writing material, scribe provenance (if known), and ambiguous readings; **never infer a scribe identity from visual similarity alone**;
- traceable gold alternatives and blinded independent expert adjudication before asserting a scientific reading result.

**Immediate dependency:** no confirmed broad, expert-labeled, rights-cleared Hieratic manuscript corpus is present in this project. Therefore do not call DATA-008's future synthetic example a released real model-training corpus.

## Candidate rights inquiries (not sent)

- HPDB: clarify whether CC BY 4.0 extends to every particular IIIF manuscript scan, what attribution/moral rights apply to source reproductions, and which objects overlap HieraticBench.
- AKU-PAL: request item-level license evidence for a selected, **non-benchmark** set of hieratograms and their associated annotations; clarify derivative/synthetic augmentation and model-weight use.
- DDD: clarify research-only terms for noncommercial experimentation and whether weights/derived sign crops can be shared; obtain `papyri.json` per-object rights review.
- TLA: request permission or identify a separately distributed raw dataset under a compatible explicit free license; do not scrape.
- PaPYrus/Isut/HieraticAI: obtain a separately stated license and rights provenance for the *image datasets*, not only source code.

**Safety/reproducibility note:** This audit is a rights-risk and evidence inventory, **not legal advice**; every future item still passes project policy and independent documented legal/rights judgment.
