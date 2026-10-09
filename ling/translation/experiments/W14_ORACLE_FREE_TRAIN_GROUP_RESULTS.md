# W14 — first real oracle-free Old Egyptian grammar group diagnostic

**Status:** Source-original train-only retrospective result. Full first-reconstruction denominators and exact predictions frozen by negative regression tests. This source originally belongs to the official UD **TRAIN** partition, which W13 already modeled in aggregate; no clean newly held-out test or image/scribe generalization claim is made.

## Data and ethics

Publisher: University of Jaén UD Egyptian-PC Old Egyptian Pyramid Texts; attributed Díaz Hernández and contributors; CC BY-SA 4.0 source tree `fca8538287cb69fd07b811eb55dcfd25584f3006`, original TRAIN Git blob `ea262ee047943b81c0e0db8ff139ec7deb9b7b53`. Only derived original TRAIN data `2b42a078e6ec4277a5ab7016d6f966c3545a7894` was added. Registration `W14_PREREG_ORACLE_FREE_TRAIN_GROUP.md` committed first (`b7424bf379616adecec7f96548cc808e3b6cde85`).

Original TRAIN group split:
- Train **Teti/Neith/Merenre:** 790 sentences / 9,157 real word tokens.
- Retrospective evaluation **Pepi:** 829 sentences / 10,329 real word tokens.
- Exact same FORM-sequence duplication across train/evaluation groups: **0** sentences. This does **not** prove absence of paraphrased shared Pyramid Text formulae, editorial genealogy or overlap in previous research/pretraining.

## Full fixed-denominator results

| Metric | Frozen naive train-majority UPOS + previous-token | True non-oracle FORM→UPOS→syntax | Privileged oracle gold-UPOS syntax |
| --- | ---: | ---: | ---: |
| Gold source word tokens | 10,329 | 10,329 | 10,329 |
| Correct dependency heads | 4,259 | **4,757** | 6,489 |
| Correct head and DEPREL | 750 | **2,811** | 4,316 |
| UAS | 41.2334% | **46.0548%** | 62.8231% |
| LAS | 7.2611% | **27.2146%** | 41.7853% |
| Invalid trees | 0 | 0 | 0 |

Non-oracle UPOS: **8,060 / 10,329 = 78.0327%** total POS accuracy; macro-F1 approximately **0.62421625** on the combined observed class inventory. Evidence categories across 10,329 target words: exact train form 8,240; unseen form suffix-3 829; suffix-2 346; suffix-1 776; global majority 138. Unknown and suffix cases remain explicitly labelled, not silently omitted.

**Comparison:** +498 correctly attached heads and +2,061 correct labelled arcs over the frozen deliberately weak naive baseline. The oracle gold-UPOS comparator gives +1,732 heads and +1,505 labelled arcs relative to the non-oracle pipeline, demonstrating major UPOS/inference-domain error propagation. The oracle is not included in the non-oracle headline.

## Interpretation and next gate

This is real **Old Egyptian original scholarly FORM input and published dependency-label scoring**, not synthetic gold or a Hieratic image experiment. The result is restricted to a deterministic frequency/suffix pipeline, a prior-exposed original TRAIN treebank and an editorial king-group split. No later Hieratic script OCR, modern-language meaning, fluent sentence translation, manually inspected independent manuscript line gold, official blind test or expert semantic adequacy was demonstrated.

**Scientific LING-003 milestone: active 0/2 points.** Project verified capability 34.5/100, historically recorded research coverage 14%, validated real Hieratic model experiment count 0, trained neural model count 0. The separate semantic source-external experiment is blocked by missing newly preregistered independently heldout legally admissible Egyptian/modern-language paired editorial references; old AES W9-W12 evaluations are exposed and invalid as fresh tests. Official UD Egyptian-PC TEST not accessed or evaluated.

## Reproduction

```bash
python -m ling.translation.w14_oracle_free verify
python -m ling.translation.w14_oracle_free evaluate
python -m unittest tests.linguistics.test_translation_layer -v
```

The dedicated W14 tests now enforce the exact counts above, complete source/role denominators, provenance and rights, no gold inference injection, heldout group isolation, deterministic SHA-256 report, and single-root/cycle-free predictions. Exact-head GitHub hosted Linux full-suite check is required before accepting this report.