# W11 LING-003 — source-quarantined lexical scale-up and fresh historical biographies result

**Verdict:** A genuine, narrowly improved **lexical German word overlap** on an untouched editorial-source cohort, not demonstrated fluent or grammatically/semantically correct translation. The optional train-supported local German order-inversion rule **never activated**, and whole-sentence neighbor retrieval continues to copy nonidentical original Egyptian source sequences. No capability points are awarded.

## 1. Chronology, rights and source custody

- **Preregistered on 2026-10-09, before inspecting any biography reference translations:** `ling/translation/experiments/W11_PREREG_SCALED_TRAIN_BIOGRAPHY_HOLDOUT.md` at Git SHA `c3f88e9274ce1f088619f45aef5ea74be21dcedb`. Frozen: source files, provenance hash identities, disjoint source IDs, permanent quarantines, blind salted 32-group selection, exact five methods, existing word-order thresholds and all metrics.
- AES original publisher Simon D. Schweitzer / editor contributors, revision `35276d2527cca1a055e31ed5f6683e777717170f`, CC BY-SA 4.0 original scholarly text files. **Not** the differently restricted live TLA bulk service. Source image permission/physical-artefact identity are entirely separate.
- Extra TRAIN source: original archive `files/aes/_aes_bbawarchive.json`, Git blob `014cccf04235d9e093fca24ed48c62630d235852`, 5,855,067 bytes. Of its 3,081 original sentence records, excluded ALL **47** W10 held-out sentences by their **32 whole source-text IDs**. Another **12** original rows lack German editorial translation and **one** translated row has invalid/missing original Egyptian token forms, and were transparently omitted from training. The **3,021** remaining fully usable originally translated AES archive items represent **1,130 source IDs**, including publishers/editors Stephan Seidlmayer (550 sentences), Stefan Grunert (2,463), Ingelore Hafemann (8). Every donor remains in `w11_archive_training_excluding_w10.json`, blob `1354bbfd832680953bec25fb5742502599763bc1`.
- Original W9 training/dev 904 genuine translated AES sentences + 3,021 new archive items = **3,925** train-side translated sentences. NO Tübingen W9 exposed test, W10 archive external test, or W11 biography target sentence or text-ID belongs to training.
- New TEST source: `files/aes/_aes_bbawhistbiospzt.json` original 6,279,800 bytes / Git blob `6f26021ee4243e87657ff8afd59847f126d6ca65`. Original population: 1,110 sentence entries, 1,095 genuine German publisher sentences, 141 distinct original source-text IDs. The frozen SHA-256 source-text ID ranking picked **32 complete groups** spanning **180** original sentences. **178** have actual German published reference; **two** reference-less rows remain present, not made into invented scoreable gold. Source text IDs are disjoint from all preceding EOS/AES corpora and the archive donor/exposed W10 groups. The 178 scoreable references occupy **31** source-text IDs: the 32nd selected group has no scoreable German reference. No overlap by ID does **not** prove independent works, papyri, scribes or editorial genealogies.
- Test derived blob: `7e5654b5d8194c3deb764cf37a8e2bce2c624855`. Only original `written_form` values enter the predictions; target `sentence_translation` is accessed **after** predictions by the scorer. A separate per-sentence `w11_biography_rights_manifest.json` preserves original editorial `owner` attribution: Silke Grallert (101 rows), Gunnar Sperveslage (8), Roberto A. Díaz Hernández (57), John M. Iskander (14). All 180 rows are `OPEN-SA` (CC BY-SA 4.0); publisher text test-only, DATA-008 admission **false**, photographic/physical support match **unverified**.

## 2. Methods frozen before target publication

Existing 904-sentence training versus expanded 3,925-sentence training is evaluated with identical German source token word-form inputs. Exactly five deterministic systems were run over the entire new cohort:

1. W9 904-only **gloss** control.
2. W10 904-only **constrained composer**, unchanged.
3. W11 3,925-train **gloss** control, same method.
4. W11 3,925-train **constrained composer**, exact W10 model and parameters unchanged: neighbor cotext gloss selection requires at least 2 independent training text IDs, adjacent unit swaps require at least 2 and strictly >2× inversion versus normal support, no grammatical role inferred, unknown forms represented `[?]`.
5. W11 3,925-train **whole-sentence text memory** at **0.0**, exactly the original W9 selected similarity threshold, retained solely as copying-risk/word-overlap comparator.

No dictionary-generated German words, morphology labels from heldout source, GPT/paid inference, target-prompt tuning, reversed word-order parameter optimization, manual cherry-picking or post-hoc score weighting.

## 3. Exact-head hosted Linux first-run results

Project Governance passed on PR #105 exact initial head `8c9a1caf0b55c9dcda3901c922a6bda93d131a52` (run `37917822671`). Exact source-bound and adjudication tests, including the new complete five-way comparison, ran successfully: **34 governance**, **175 data**, **72 linguistic**, and **296 evaluation** tests. All five tests used the same full source population: **180 total**, **178 scored** German references, **32 selected** original text groups and **31** groups represented in the 178 scored references, **3,601** published German reference words.

| Fixed method | Micro German word F1 | Macro sentence word F1 | Mean in-house char n-gram F2 | German words emitted | Matching word occurrences |
|---|---:|---:|---:|---:|---:|
| Old 904 gloss | 0.09434764 | 0.07979164 | 0.16503839 | 3,458 | 333 |
| Old 904 composer | 0.09667330 | 0.08001438 | 0.16543850 | 3,433 | 340 |
| **Expanded 3,925 gloss** | **0.10736754** | **0.09020178** | **0.17756055** | **3,552** | **384** |
| **Expanded 3,925 composer** | **0.10791969** | **0.08787688** | **0.17735460** | **3,571** | **387** |
| Expanded 3,925 sentence retrieval | 0.11088737 | 0.09545649 | 0.18959062 | 3,848 | 413 |

Additional reproducible census over **2,264** original Egyptian written-form source tokens:

- Old gloss and composer abstained on **949** unknown Egyptian token units; new expanded gloss and composer abstained on **846**. **103 fewer unsupported units** are attributable to additional attested publisher cotext data, not syntactic improvement.
- Expanded composer used training-source-supported **neighbor-context sense selection 355 times**, versus no guaranteed correct German sense labels. **0** adjacent-unit swaps met the fixed reversal-vote rule on this previously unseen population; no evidence of grammatical word order generalization.
- Expanded composer generated **0** exact copies of nonidentical training German full sentences and never used whole-sentence retrieval.
- Expanded W9 memory did retrieve and copy publisher German whole sentences from **50 NONIDENTICAL** Egyptian token sequences, all 50 subject to formula/person/role contamination risk.
- Even with extra data, 846 of 2,264 Egyptian token units still lack a supported German gloss; genre transfer is seriously bottlenecked.

**Full deterministic first-run diagnostic SHA-256:** `c5b3d40e87bae24cf9574e5a6ee48e89acc0348b8e9346cdacc28b2fbf6aa48c` (hash over the evaluator report before attaching the derived CLI convenience hash). Commands:

```bash
python -m ling.translation.w11_evaluation verify
python -m ling.translation.w11_evaluation evaluate
python -m unittest tests.linguistics.test_translation_layer -v
```

## 4. Scientific interpretation, failures and remaining gates

The new source cohort **does show an improvement in lexical surface coverage** from increasing lawful training texts under a fixed protocol: unchanged W10 composer micro word F1 increased from **0.09667330** at 904 training sentences to **0.10791969** at 3,925. The former 47-item W10 archive showed much lower coverage and can no longer legitimately be used as an untouched generalization cohort. Neither score is a semantic translation quality percentage.

**Crucial negative result:** structural German unit inversions = **0** on this external population, so the claimed 'composer' did not exhibit new syntactic generalization. The highest word-F1 retrieval model copied 50 whole publisher German sentences from **different Egyptian sources** and must not be presented as verified fluent translation. Hidden grammatical roles, restored readings, named entities, genre-specific vocabulary and phrase-level meaning are not independently verified.

The result is text-only AES publisher transliteration and translated text evidence, **not** image-conditioned Hieratic recognition, a scoreable original manuscript line, physically disjoint original papyri, expert-blind German adequacy, model training of neural weights, or certifiable heldout Hieratic gold. The W11 new biography cohort is **now exposed**, never reusable for future clean model tuning.

**Decision:** Accept reproducible research software and qualified increased lexical evidence only. LING-003 remains active **0/2 scientific points**, canonical total **34.5/100**. Next legitimate research must incorporate independently supervised Egyptian grammar/roles and wider lawful source evidence, then evaluate in a *different* genuinely preregistered source/witness cohort with independent semantic adjudication. Do not tune on W9 Tübingen, W10 archive or W11 biographies and call the outcome unseen.


### Independent complete original source-ID universe verification

A post-run provenance review strengthened the cohort audit **without changing the locked model, data, test cohort or scores**: `ling/translation/data/w11_biography_source_id_universe.json` contains *all 141 original publisher biography source-text IDs* (no target translations), original total sentence count 1,110 and German-reference count 1,095, original source Git blob and exactly the predeclared selected 32. Pinned immutable Git blob: `16ac4c8cbc7ccd30c952b904825511b5756f3a27`. `w11_evaluation.load()` now independently computes source exclusions and SHA-256 ranks for the **entire** recorded 141-text source universe, refusing any selected cohort that is not **exactly** the highest-ranked 32. This removes the former weaker check in which sharing the final rank cutoff alone might not detect tampering of an intermediate source-ID group. Adversarial tests reject universe file mutation and verify global rank. The W11 first-use German score is unchanged by this metadata-only gate.
