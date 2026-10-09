# W9 — Contextual translation memory: independently held-out subcorpus result

**Owner:** independent overseer, 2026-10-09  
**Task:** LING-003, active, 2.0 weighted points **not earned**  
**Status:** measured negative external-domain generalization result; genuine real scholarly text, not original Hieratic-image reading

## New source collection and chain of custody

Four verbatim CC BY-SA 4.0 AES Git objects at upstream revision 35276d2527cca1a055e31ed5f6683e777717170f, publisher Simon D. Schweitzer / TLA-AED contributors, from https://github.com/simondschweitzer/aes :

| Published AES subcorpus | Sentences | With German translation | Source text IDs | Selection |
|---|---:|---:|---:|---|
| Felsinschriften | 445 | 444 | 311 | internal train/development |
| SMAEK | 38 | 38 | 8 | internal train/development |
| Graeberspzt | 426 | 422 | 78 | internal train/development |
| **Tuebingerstelen** | **247** | **247** | **21** | **entirely reserved external test** |
| **Total** | **1,156** | **1,151** | **418** | |

The new original publisher file blobs are SHA-1 82f6f6229283d6c4174373e39b12871761bc81ec, a427ccf25e92fc7f5d849536af78ae39ae923327 and 87ac34335acd3dc1533580b2017a689fa87abda1; earlier accepted Felsinschriften blob 7bfcba9678b64c3526a1123996a0714b5f76812f. All four verified byte-for-byte. No image, benchmark gold or external API used.

## Method and preregistered separation

Train-only TF-IDF-style Egyptian source-form nearest-neighbor sentence retrieval with whole *published German* sentence transfer; requires common forms and source coverage; fallback to other-source published word cotext German glosses with explicit [?] unknowns. Nearest source text ID and differing Egyptian source forms are included for contamination auditing. Model does **not** read target sentence's German editorial translation or cotext gold.

The **Tübingen stelae** entire original AES subcorpus is excluded from training, source-word gloss counts, inverse document frequency, development folds, ranking and tuning. The remaining 904 translated sentences are assigned to five SHA-256(text-ID) folds with disjoint original text IDs in each fold. A source-text-held-out development word-overlap F1 selected similarity threshold **0.00** from fixed options (0.00, 0.15, 0.30, 0.45, 0.60, 0.80, 1.00). It was applied to the held-out Tübingen set without post-test threshold changes.

This is stronger than simply excluding the same sentence ID. Still, text IDs **do not prove independent physical manuscript witness, editor, formula or scribal origin**; the original publishers and any possible VLM pretraining may overlap.

## Genuine observed metrics — no selective improvement claim

| Comparison | Train-only German word-gloss control | Contextual nearest-sentence memory | Result |
|---|---:|---:|---|
| Five-fold internal development, corpus micro word F1 | **0.15368591** | **0.24261684** | Internal +0.08893093 |
| Reserved Tübingen external corpus, micro word F1 | **0.15275625** | **0.14259102** | **External −0.01016523** |
| External macro sentence word F1 | **0.11696788** | **0.10782073** | External negative |
| External macro character n-gram F2 (1–6) | **0.19738374** | **0.19597846** | External negative |
| External sentences | 247 | 247 | Identical scoring universe |
| External source text groups | 21 | 21 | Identical source-group universe |
| External retrieval versus gloss fallback | 0 / 247 | **40 / 207** | 40 context retrievals |
| Retrieved sentences with *nonidentical Egyptian source sequence* | 0 | **40 / 40** | High proper-name / clause-copying risk |

All published reference sentences were scored, not only favorable instances. Corpus denominator counts: gloss 345 matching German multiset words / 1,918 predicted words / 2,599 reference words; contextual 421 overlap / 3,306 predicted / 2,599 reference words. Although the context approach contains more individually overlapping German words, it emits many more *unsupported* words, reducing precision and overall word F1.

**Conclusion:** the in-domain dev improvement **failed to generalize** to a separately reserved published AES subcorpus. The apparent fluent German sentences often represent partially matching source formulae and risk preserving names and grammatical details from different source texts. Do not promote the retrieval as scientifically demonstrated Egyptian translation quality. Do not reverse-select thresholds from Tübingen, hide the 40 near-copy predictions, or award 2.0 LING-003 points.

The evaluation is an authentic **source-text publisher gold diagnostic** only in the colloquial corpus sense: no blind independent fresh scholarly adjudication, no manuscript pixel-to-transliteration alignment, no certified original Hieratic reading, and no expert-rated semantic adequacy. Term 'gold' must NOT be used for a verified held-out Hieratic manuscript reading here. Character F2 is an explicitly described in-house n-gram metric, **not** sacreBLEU.

**Deterministic full results SHA-256:** 3e8b42915d0a5cfce9a1a8cde78d503b319c18cbd3ed3ec28cafa745167402aa. Evidence was generated in successful hosted Project Governance tests, with exact data Git blob checks; available in PR #95 workflow job logs as W9_AUTHENTIC_TEXT_EVALUATION.

## Genuinely remaining scientific work

1. Improve **compositional contextual sentence realization** rather than retrieving memorized German sentences. Require lexical sense, syntax and proper-name fidelity separately; do not tune to the now-revealed Tübingen test.
2. Preregister a new, mutually disjoint source-domain test before trying any new retrieval threshold or method, preferably multiple Egyptian periods/genres and source-witness IDs, with leakage and edition genealogies examined.
3. Measure expert-adjudicated semantic adequacy and structure; word/chars metrics alone overreward formulaic copying.
4. Connect genuine original image and lawful edition line gold when the Luna/Gemini evidence provides real source/view-matched predictions.

The W9 engineering, source, strict holdout and diagnostic are complete as an experiment, **LING-003 scientific acceptance remains active and unearned**. Canonical capability remains **34.5/100**, validated Hieratic manuscript experiments remain 0, and trained neural models remain 0.

## Reproduce

    python -m ling.translation.contextual verify
    python -m ling.translation.contextual evaluate
    python -m unittest tests.linguistics.test_translation_layer -v

Review exact publisher source Git SHA and manifest under ling/translation/data before rerunning. Project's sample benchmark/heldout physical supports are not touched.
