# W13 — first genuine Old Egyptian dependency-role learning diagnostic

**Status:** Reproduced exact-head hosted Linux CI; task LING-003 scientific milestone remains active/unearned.

## Original primary source, scope and audit
- Source: [Universal Dependencies Egyptian-PC](https://github.com/UniversalDependencies/UD_Egyptian-PC), university of Jaén original manually annotated Old Egyptian Pyramid Texts; contributors and citations in official README; treebank `LICENSE.txt` expressly licenses text and annotations under **CC BY-SA 4.0** (OPEN-SA). Publisher tree object `fca8538287cb69fd07b811eb55dcfd25584f3006`.
- Original official **training** CoNLL-U source Git blob `ea262ee047943b81c0e0db8ff139ec7deb9b7b53` (2,563,828 bytes): **1,619 original sentences / 19,486 word tokens**. Derivative contains only train-side UPOS/head-POS/direction/relation frequencies, Git blob `4bedc6cd872cc9e93339bd0fad4bba780b5cda49`, versioned and confined to `ling/translation/data/`.
- Original official **development** CoNLL-U Git blob `78a9749f823441633836b63a952df05d8636624c` (404,035 bytes): **230 distinct original source sentences / 3,167 word tokens**. Development annotations are stored in reduced derived form with original sentence IDs, token positions, UPOS/HEAD/DEPREL, Git blob `2694c4aa14dd6712b9fb45d714caead1c8856d64`, CC BY-SA 4.0 and attribution preserved.
- Official **test** Git blob `f40982ca7dc7b67a5ed6d6bc90f4fe8dcd8085f6` was **identified by Git tree only, not opened, scored or used**. Excluded from all experiments and preserved for later properly registered independent evaluation.
- Training and development original sentence-ID intersection: **zero**. Texts are all the same Pyramid Texts literary family, so original sentence-ID disjointness alone does not prove physical-witness, scribal, inscription, formula or editorial genealogical independence. No previously exposed AES German translation references entered this original dependency annotation study.
- Protocol preregistration `W13_PREREG_EGYPTIAN_PC_DEPENDENCIES.md` committed **before fetching original dev labels**; thereafter the published gold was used only for post-hoc evaluation. Dev is now **exposed** and cannot count as a later untouched model-selection test.

## Frozen experimental model

The primitive comparator attaches the first token to synthetic ROOT, every subsequent token to the immediately preceding token, and chooses its most frequent published training relation for the current dependent UPOS (excluding root). The statistical system uses only **published training** UPOS/dependency labels to count relations conditioned on (dependent UPOS, candidate head UPOS, left/right/root direction) and ranks candidate heads by log-smoothed frequency minus frozen distance penalty 0.02 × absolute token offset. Selects exactly one root from independent training root-UPOS frequency and breaks all cycles deterministically. Every generated tree is acyclic and single-root.

**Oracle input privilege:** Both models are supplied with each held-out development token's **published gold UPOS** at prediction time. Predictions do not use dev GOLD HEAD/DEPREL, names, German meanings, published lemma or morphology. A separate adversarial regression replaces these target labels and confirms prediction does not change. Gold labels are opened only by scorer/audit.

## Full development results

| Measure | Previous-token baseline | Train-side grammatical role model |
| --- | ---: | ---: |
| Original development sentences | 230 | 230 |
| Original development word tokens | 3,167 | 3,167 |
| Correct dependency heads | 1,390 | **1,849** |
| Correct head + relation | 554 | **1,143** |
| Unlabeled attachment score (UAS) | 0.43890117 | **0.58383328** |
| Labeled attachment score (LAS) | 0.17492895 | **0.36090938** |
| Invalid predicted trees | 0 | 0 |

UAS improvement is **+14.493211 percentage points** (1,849 vs 1,390 correct heads, +459), LAS improvement **+18.598043 percentage points** (1,143 vs 554 correct head+relation, +589), relative to this deliberately weak fixed baseline. The complete report includes UPOS-conditioned denominators, correct counts, source/training revision evidence and zero-invalid-tree certification.

**Deterministic complete results SHA-256:** `da5710ab3ea140f34d68fba5457ad4cf56d1d0a7e4cf2a0ec7a050086e736f70`.

**Hosted code and regression evidence:** `Project Governance` run [37929587916](https://github.com/m7mdehab/hieratic-ai/actions/runs/37929587916) on PR #110 exact head `1a51dfbac41f1cb7f031b1b18e89035f2a28867c`: **34 governance tests, 182 data, 90 linguistics, 299 evaluation**, all successful. Six targeted W13 tests validate source byte hash/ref, unknown source edits, proper original gold graph, single-root/cycle-free predictions, refusal on invalid labels, prohibition on inference-time dev dependency gold and deterministic report.

## Scientific outcome and limitations

This is **positive reproducible structure-learning evidence** from a genuine *pre-Coptic Egyptian* primary grammatical resource, unlike earlier lexical sentence copying, and it supplies actual observed dependency labels. It is nevertheless restricted: Old Egyptian Pyramid Texts are not the later manuscript Hieratic source domain; dev UPOS is a publisher-gold privileged input; no independently verified physical manuscript witness holdout, historical-period transfer, unseen official test, original image-to-text pair, fluent German semantic decoding or independent expert review was performed. Neither the modest UAS/LAS above nor synthetic sentence fixtures count as accurate Hieratic reading, translating, or a certified LING-003 milestone.

**Task LING-003 remains active 0/2; canonical goal progress remains 34.5/100, historic research coverage 14%, validated real manuscript experiments 0.** Next truly independent step is predeclared official-test only *after* model freeze plus a separately licensable and source-exact later Egyptian manuscript line-pair for cross-period transfer, without conflating statistical dependencies with semantic roles in German.
