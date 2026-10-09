# Experiment Registry

No validated model experiments have been run yet.

## Rules

Every experiment receives a stable ID, e.g. `EXP-HTR-001`.

Minimum record:
- hypothesis;
- linked task;
- Git commit;
- dataset/manifests and split version;
- model/checkpoint;
- configuration and seed(s);
- execution environment;
- command/entry point;
- metrics;
- artifacts;
- result;
- interpretation;
- decision caused by the result;
- known caveats.

A failed experiment remains in the registry. Negative results may increase research coverage but do not automatically earn capability points.

## Template

```yaml
id: EXP-...
task_id: ...
status: planned
hypothesis: ...
code_commit: ...
data_version: ...
split_version: ...
model: ...
config: ...
seeds: []
metrics: {}
artifacts: []
result: ...
decision: ...
caveats: []
```


## EXP-LING-002-AED-AES-001 — Genuine published-text lexical/morphology diagnostic

- **Task:** LING-002 (accepted source-grounded linguistic interpretation; not an image OCR or model-experiment certification)
- **Classification:** completed_development_grade_scholarly_text_diagnostic; **not independently validated real model experiment**
- **Execution:** PR #88 exact-head GitHub Linux CI 37856429995; verified source registry PR #85
- **Hypothesis:** exact original Egyptian written-form lookup into scholarly AED dictionary and independent-other-text AES editorial annotations can recover useful lemma identities, grammatical alternatives and attested inflection bundles, without fabricating unseen-text gold.
- **Inputs:** AED-TEI 35,052 publisher lexemes, Git dictionary.xml original blob 078f2f7b83bd642b6530ed000dbc68f9aa79c06e; AES Felsinschriften 445 sentences, 311 text groups and 2,526 original editor tokens, source Git blob 7bfcba9678b64c3526a1123996a0714b5f76812f. See immutable source manifests and CC BY-SA 4.0 contributor attribution at ling/lexical/data/scholarly_source_manifest.json.
- **Splitter:** exhaustive leave-one-AES-source-text-ID-out. Every queried text ID excluded from AES candidate generation. Common AED published dictionary remains visible. Two text IDs had no scoreable lemma.
- **Prediction method:** deterministic exact form candidate union over AED's dictionary orthography and other-text AES form attestations; no trained weights, statistical model or hidden parameter tuning, seed not applicable. Source-native morphology is only transferred when another text attests the same form and lemma; alternatives preserved.
- **Measured real diagnostic:** of 2,305 tokens with published lemma labels, 1,709 (74.14%) have any lookup candidate and 1,621 (70.33%) have the editorial lemma among candidates. Exactly 1,102 produce a single candidate, with 1,062 matching the published lemma (96.37% among the single-candidate subset only). Of 753 tokens with publisher morphology bundles, 449 (59.63%) match some permitted cross-text candidate bundle. These are *candidate recall* and conditional source-lookup accuracy, not blind OCR accuracy.
- **Immutable report SHA-256:** 26ad977c29fdd8659157cb02bec04323b6b544dc8ca9425a13825ea629acedee. Script: python -m tools.lexical_interpretation scholarly-aes evaluate.
- **CI:** complete governance, data, linguistic and evaluation suites passed, LING-002 15-path scope check passed on exact source head.
- **Decision:** Accept LING-002 2.0-point *linguistic analysis capability only*; unblock the downstream LING-003 translation-engine task. Mark no genuine image-reading, no held-out independent manuscript or VLM result, no trained model, no independently validated model experiments. Input editor labels are genuine published scholarship, not newly blind reviewer-certified gold, and AED/AES publication overlap and unknown pretraining exposure remain substantive limitations.


## EXP-LING-003-W9-EXTERNAL — Publisher source-memory test, negative
- **Task:** LING-003 (active 0/2); **classification:** REAL_PUBLISHER_TEXT_NONCERTIFIABLE_DIAGNOSTIC.
- **Inputs:** Pinned CC BY-SA 4.0 AES published text: 1,156 source sentences, 1,151 German references, 418 AES source text IDs. 904 internal translated training/development sentences; source-ID-heldout Tübingen (247 references/21 text IDs) was used only once for external testing and is NOW EXPOSED.
- **Method:** 5 text-ID-grouped dev folds with train-only lexical German glosses and TF-IDF German sentence retrieval, original frozen threshold 0.0. No original Hieratic image reading.
- **Result:** Internal micro German word F1 gloss 0.15368591 versus sentence memory 0.24261684, but on harder reserved Tübingen publisher text **fell** from 0.15275625 gloss to 0.14259102 contextual memory. 40 copied German sentences came from NONIDENTICAL original Egyptian token sequences.
- **Artifact:** `ling/translation/experiments/W9_CONTEXTUAL_TRANSLATION_EXTERNAL_TEST.md`; deterministic report SHA-256 `3e8b42915d0a5cfce9a1a8cde78d503b319c18cbd3ed3ec28cafa745167402aa`. **Decision:** No fluent translation claim; Tübingen never used again as unseen benchmark; no capability credit.

## EXP-LING-003-W10-ARCHIVE — Preregistered new archive publisher cohort, negative
- **Task:** LING-003, PR #102 (merged `2004abf6175a33f40a1d76822f9baaaab73114cf`); **classification:** new AES editorial-text-domain external diagnostic, NOT original manuscript or independent blind semantic test.
- **Source lock/chronology:** Source/method preregistration commit `7bd1d01c1d9d6242625a1dcd3363e6aaac15ffba` PRECEDED viewing new archive references. AES original archive Git blob `014cccf04235d9e093fca24ed48c62630d235852` and frozen hash selection of 32 NEW complete text-ID groups, 47 original German publisher reference sentences, derived blob `d3d7b57aef7bd10a48df6b1be340be8ff5b36e32`.
- **Methods/results:** Identical 904 earlier W9 train reference sentences; plain gloss word F1 0.02312139, W9 German sentence memory 0.02136752, W10 train-only context-gloss local-composer 0.02285714; **107/162 Egyptian source tokens lack supported word glosses, 0 independently supported word-order inversions**, 5 retrieved publisher sentences copied from nonidentical Egyptian token sequences in W9 memory. Source IDs are not independently verified physical witnesses.
- **Artifact:** `ling/translation/experiments/W10_COMPOSITIONAL_ARCHIVE_EXTERNAL_REPORT.md`, report SHA-256 `da1d4275c9f78e4ad229ab1681de58a3374497df6a150e78cffc03c8f3c1b04c`. No tune-after-test, no reward; archive now EXPOSED.

## EXP-LING-003-W11-BIOGRAPHIES — Preregistered training expansion, qualified lexical gain
- **Task:** LING-003, PR #105, merged `96a9779dca04e5594a1e6413c28fccdac4a88999`; **classification:** first-use AES source-blocked original scholarly text, not expert adjudication.
- **Predeclared source and split:** Git preregistration `c3f88e9274ce1f088619f45aef5ea74be21dcedb` before opening new historical biography reference translations. Additional archive train-only published CC BY-SA 4.0 3,021 usable sentences/1,130 distinct original text IDs, permanently excluding all 32 W10 archive heldout source IDs and previously exposed Tübingen. Total train=3,925. New biographies original publisher blob `6f26021ee4243e87657ff8afd59847f126d6ca65`, hashed top 32 complete original biography source IDs among ALL 141 source IDs, producing 180 source sentences, **178 with German publisher references across 31 scoreable text groups**. Zero source-text-ID overlap; physical witness genealogy independent status unresolved.
- **Methods:** Frozen original 904 gloss/composer, expanded 3,925 gloss/composer with exactly the W10 context and swap parameters unchanged; expanded W9 nearest-neighbor memory threshold 0.0 only as risky copying comparator. No test references in training.
- **Full first-use results (micro German word F1):** 904 gloss **0.09434764**, 904 composer **0.09667330**, expanded gloss **0.10736754**, expanded composer **0.10791969**, expanded whole-sentence memory **0.11088737**. German word-overlap is not percentage of semantically correct Egyptian translation.
- **Other denominators:** 2,264 Egyptian source tokens: unknown cotext gloss abstentions **949 → 846** (103 recovered), expanded contextual unit selections 355, local word-order inversions **0**. Expanded memory copied **50** whole German sentences from nonidentical Egyptian source sequences.
- **Evidence:** Exact-head Project Governance `37918269880` passed; postmerge main governance `37918395022` passed. Report `ling/translation/experiments/W11_EXPANDED_TRAIN_BIOGRAPHY_EXTERNAL_REPORT.md`; diagnostic SHA-256 `c5b3d40e87bae24cf9574e5a6ee48e89acc0348b8e9346cdacc28b2fbf6aa48c`. Test source exact group selection independently audits all 141 original text IDs.
- **Decision:** Accept honest **lexical coverage** expansion, NOT learned grammar, independently reviewed semantics, manuscript OCR or gold. The W11 biographies are now EXPOSED. LING-003 remains active 0/2 and overall verified score 34.5/100. No neural model was trained.

## EXP-VLM-001-W10-CPU-CONTROLS — Agent-reported authentic Hieratic control diagnostics
- **Task:** VLM-001, PR #104 merged `dbc65cadee4466d45910669e2d1cd8454254b188`; **classification:** versioned fail-closed experiment software plus reported private-host execution, NOT a jointly independently rerun scientific result.
- **Input/weights:** Original Cat.2044/013 CC0 p01 JPEG SHA-256 `569e8e5bb446588481481bfea823fc95383bb7076270363c666f868b7fa5b912`; pinned SmolVLM-256M-Instruct revision `7e3e67edbbed1bf9888184d9df282b700a323964`, exact safetensors SHA-256 `74dea5904032e5ae99a2e0eef5179e6ac0f1dedc3ab0c7c2a5d4d387c843203e`. Agent reports **23 local AMD Ryzen CPU forward passes** over full authentic source, three unlabelled candidate crops and blank, inverse and scrambled-tile controls. Real private image/weights/receipt not committed.
- **Negative results:** Blank and scrambled controls produced descriptions of script despite absent/disrupted source structure, prompt-prior hallucination; Grade E visual sensitivity **NOT_VERIFIED**, Grade F authentic scholarly manuscript gold **STRICTLY_NO**, 0/2 VLM capability points. Scrambled tiles preserve within-tile stroke texture, cannot serve as proven complete sign-destruction gold; old W9 unqualified A-E claim is superseded by PR #100 reviewer corrections.
- **Hosted tests:** VLM Baselines Preflight `37919061764`, Project Governance `37919061772`, Error Analysis Integrity `37919061835` all passed exact-reviewed head. **No independently certified Hieratic transcription, translation, or benchmark accuracy.**
